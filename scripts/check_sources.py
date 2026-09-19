"""Check every source this site cites: is it still there, and is it still the page we named?

    python scripts/check_sources.py                  # check everything, write the report
    python scripts/check_sources.py --limit 40       # a sample, for a quick look
    python scripts/check_sources.py --only arxiv.org # one host
    python scripts/check_sources.py --fail-on-dead   # exit 1 if anything is gone

Why this exists: the site's rule is that every claim comes from the maker's own page, so a page
that is renamed, rewritten or taken down quietly turns a sourced claim into an unsourced one. An
audit on 09/19/2026 found exactly that, by hand: OpenRouter had rewritten the front page a
quotation came from, and four source titles no longer matched the page they pointed at. Nothing
was watching for it. This is what watches.

What it reports per source:

  gone        the URL does not resolve, after a retry, and we have no archived copy of it
  archived    the original does not resolve, or no longer serves the page we named, but this
              citation already records an archive_url, which is the copy the page actually
              quotes: handled, not a defect
  moved       it redirects somewhere else (the new address is printed)
  drifted     it resolves, but the page's own <title> no longer resembles the title we cite.
              Where the page's text still names the thing anyway, the line says so: that is
              usually a maker's page titled after the maker rather than after the product, and
              not a defect at all
  blocked     the host refuses automated requests, twice; not a defect, read it by hand. Meta
              and ISO answer a script with 400 or 403 however the request is dressed

  ok          resolves, and the title still matches

A first version of this script reported six sources gone and three of those were its own fault:
one transient network error it never retried, one redirect it read as a failure, and one host
that answers a script with 400 rather than 403. Hence the retry, the redirect handling and the
wider set of refusal codes. The 09/19/2026 run then cried wolf a second way: asking for several
hundred pages at once got eight of them rate-limited, which reads as a refusal on one try, and
two of those came back as a challenge page whose title looked like drift. Hence the second fetch
after a pause when a host refuses. A checker that cries wolf gets ignored, which is worse than no
checker.

It makes no judgement about the words quoted from a page. Only a person re-reading the page can
do that, and `drifted` is the signal to go and do it. Network only: this calls no model, and it
is never run by the test suite.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
MDX = ROOT / "site" / "src" / "content"
REPORT = ROOT / ".local" / "research" / "source-check.md"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

class Source(collections.namedtuple("Source", "url title where archive")):
    __slots__ = ()


# Codes a host uses to refuse a script rather than to say a page is gone. 400 is here because
# Meta answers every automated request to ai.meta.com with it, browser headers and all.
REFUSAL_CODES = {400, 401, 403, 405, 406, 409, 429, 451, 503}


def _mdx_sources() -> list[Source]:
    """Every `sources:` entry in a page's frontmatter."""
    out: list[Source] = []
    for path in sorted(MDX.rglob("*.mdx")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        front = text.split("\n---", 1)[0]
        for block in re.split(r"\n  - ", front)[1:]:
            url = re.search(r'url:\s*"([^"]+)"', block)
            title = re.search(r'title:\s*"([^"]+)"', block)
            if url:
                out.append(Source(url.group(1), title.group(1) if title else "", path.relative_to(ROOT).as_posix(), ""))
    return out


def _json_sources() -> list[Source]:
    """Sources in the content files: timeline milestones and measures, and the registry."""
    out: list[Source] = []
    timeline_path = CONTENT / "timeline.json"
    if timeline_path.exists():
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        for group, label in ((timeline.get("milestones", []), "milestone"), (timeline.get("measures", []), "measure")):
            for item in group:
                source = item.get("source") or {}
                if source.get("url"):
                    out.append(Source(source["url"], source.get("title", ""), f"timeline.json {label} {item.get('id')}", source.get("archive_url", "")))
    landscape_path = CONTENT / "landscape.json"
    if landscape_path.exists():
        landscape = json.loads(landscape_path.read_text(encoding="utf-8"))
        for key in ("models", "products", "tools"):
            for entry in landscape.get(key, []):
                if entry.get("source"):
                    out.append(Source(entry["source"], entry.get("name", ""), f"landscape.json {entry.get('id')}", entry.get("archive_url", "")))
    # The frontier blocks. These are the site's fastest-rotting citations: a page about what is
    # unsolved cites work published this year, and a preprint that becomes a conference paper
    # moves. Every entry's `quote` is what the level page prints, so a drift here is a quotation
    # on a live page that no longer exists on the page it names.
    frontier_path = CONTENT / "frontier.json"
    if frontier_path.exists():
        frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
        for level in frontier.get("levels", []):
            for entry in level.get("open", []):
                for source in entry.get("sources", []):
                    if source.get("url"):
                        out.append(Source(source["url"], source.get("title", ""),
                                          f"frontier.json level {level.get('order')} {entry.get('id')}", ""))

    capability_path = CONTENT / "capability.json"
    if capability_path.exists():
        source = json.loads(capability_path.read_text(encoding="utf-8")).get("source") or {}
        if source.get("url"):
            out.append(Source(source["url"], source.get("title", ""), "capability.json", ""))
    return out


def _title_of(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if not match:
        match = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html, re.I)
    if not match:
        return ""
    title = re.sub(r"\s+", " ", match.group(1))
    for a, b in (("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">"), ("’", "'"), ("‘", "'")):
        title = title.replace(a, b)
    return title.strip()


# A page that answers 200 with one of these is refusing a script, not serving the page. Microsoft
# does this: the body is "Your request has been blocked." PyPI does it under load: the body is a
# 228-byte page titled "Client Challenge". Read as a title, that looked like drift on two release
# histories in the 09/19/2026 run, which it was not.
_BLOCK_SIGNS = (
    "your request has been blocked",
    "request blocked",
    "access denied",
    "are you a robot",
    "enable javascript and cookies to continue",
    "checking your browser",
    "client challenge",
)


def _cited_title(title: str) -> str:
    """The part of a cited title that names the page. Several citations append how the page was
    read, e.g. "Learning to Reason with LLMs (read through the Internet Archive's capture of
    September 13, 2024)". The archive serves the original page, whose own title never carries
    that note, so comparing the whole string reports drift that is not there."""
    return re.sub(r"\s*\((?:read through|via|archived)[^)]*\)\s*$", "", title).strip()


def _words(text: str) -> set[str]:
    small = {"a", "an", "and", "the", "of", "for", "to", "in", "on", "with", "our", "is", "at", "by", "from"}
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in small and len(w) > 2}


def _text_of(html: str) -> str:
    """Tags out, entities left alone. Good enough to ask whether a page still says a word."""
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html))


def _names_it(cited: str, body: str) -> bool:
    """Does the page's text still name the thing we cite, even though its <title> does not?

    The registry cites a maker's page by the thing's name, and a maker's page is usually titled
    after the maker or the section. Black Forest Labs lists FLUX 3 on a page titled "Models";
    Runway names Gen-4.5 on a home page titled after the company. Comparing those titles reports
    drift every run, forever, on citations that are perfectly good. This does not change the
    state, because a page that mentions a name is not proof it is still the page we meant. It
    puts the finding in the report so whoever triages it can see which lines to look at first."""
    words = _words(_cited_title(cited))
    if not words:
        return False
    text = _text_of(body).lower()
    return sum(1 for w in words if w in text) / len(words) >= 0.6


def _same_page(url: str, final: str) -> bool:
    """A redirect that only adds or changes a query string on the same path is not a move: it is
    a campaign parameter, a language hint or a session marker the server attached to the page we
    already asked for. Salesforce appends ?bc=OTH; putting that in a citation would be worse than
    the finding it silences."""
    def parts(u: str) -> tuple[str, str]:
        head = u.split("#", 1)[0]
        path, _, _query = head.partition("?")
        return path.rstrip("/"), _query
    return parts(url)[0] == parts(final)[0]


def _resembles(cited: str, actual: str) -> bool:
    """Does the page's own title still look like the title we cite? Generous on purpose: a site
    appending its own name, reordering, or adding a subtitle is not drift. Losing the subject is."""
    if not cited or not actual:
        return True
    a, b = _words(_cited_title(cited)), _words(actual)
    if not a or not b:
        return True
    return len(a & b) / len(a) >= 0.5


def _fetch(url: str, timeout: float) -> tuple[str, str, str]:
    """(final_url, body, error). A network error is returned, never raised: it is a result."""
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - documented sources only
            return response.geturl(), response.read(200_000).decode("utf-8", errors="replace"), ""
    except urllib.error.HTTPError as err:
        if err.code in REFUSAL_CODES:
            return url, "", f"refused: HTTP {err.code}"
        if 300 <= err.code < 400:
            # urllib declined to follow it (no Location, a loop, or a scheme it will not take).
            return err.headers.get("Location", url), "", f"redirect: HTTP {err.code}"
        return url, "", f"HTTP {err.code}"
    except Exception as err:  # noqa: BLE001 - any network failure is a result, not a crash
        return url, "", type(err).__name__


def _classify(source: Source, final: str, body: str, error: str) -> dict:
    """One fetch's outcome, as a state. Pure, so the rules can be tested without a network."""
    if error.startswith("refused"):
        return {**source._asdict(), "state": "blocked", "detail": error, "final": source.url}
    if error.startswith("redirect"):
        return {**source._asdict(), "state": "moved", "detail": error, "final": final}
    if error:
        state = "archived" if source.archive else "gone"
        return {**source._asdict(), "state": state, "detail": error, "final": source.url}

    lowered = body[:4000].lower()
    if any(sign in lowered for sign in _BLOCK_SIGNS):
        return {**source._asdict(), "state": "blocked", "detail": "refused: a block page, HTTP 200", "final": source.url}

    actual = _title_of(body)
    if not _same_page(source.url, final):
        return {**source._asdict(), "state": "moved", "detail": actual, "final": final}
    if not _resembles(source.title, actual):
        # A citation that already records an archived copy quotes that copy, not the live page.
        # The original drifting out from under it is the case archive_url was written for, so it
        # is handled rather than a defect. Neeva's post is the worked example: neeva.com answers
        # with a redirect stub now, and the capture of the publication day holds the wording.
        state = "archived" if source.archive else "drifted"
        detail = actual
        if state == "drifted" and _names_it(source.title, body):
            detail = f"{actual or '(no title)'} [the page's text still names it]"
        return {**source._asdict(), "state": state, "detail": detail, "final": final}
    return {**source._asdict(), "state": "ok", "detail": actual, "final": final}


def _check(source: Source, timeout: float) -> dict:
    final, body, error = _fetch(source.url, timeout)
    if error and not error.startswith(("refused", "redirect", "HTTP")):
        # A transient failure looks exactly like a dead host on one try. Ask twice before saying
        # a source is gone: the first version of this script called a live page dead this way.
        time.sleep(1.5)
        final, body, error = _fetch(source.url, timeout)

    result = _classify(source, final, body, error)
    if result["state"] == "blocked":
        # A rate limit is indistinguishable from a ban on one try, and this script asks for
        # several hundred pages at once. In the 09/19/2026 run that cost six false positives on
        # openai.com and two on pypi.org: every one of them served the page when asked again
        # after a pause. Wait longer than a burst window and ask once more before calling a host
        # closed to us.
        time.sleep(6.0)
        final, body, error = _fetch(source.url, timeout)
        result = _classify(source, final, body, error)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--limit", type=int, help="check only this many sources")
    parser.add_argument("--only", help="check only URLs containing this string")
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--workers", type=int, default=4, help="parallel requests, across hosts")
    parser.add_argument("--fail-on-dead", action="store_true", help="exit 1 if any source is gone")
    args = parser.parse_args()

    sources = _mdx_sources() + _json_sources()
    seen: dict[str, Source] = {}
    for source in sources:
        seen.setdefault(source.url, source)
    unique = list(seen.values())
    if args.only:
        unique = [s for s in unique if args.only in s.url]
    if args.limit:
        unique = unique[: args.limit]
    print(f"{len(sources)} citations, {len(unique)} distinct URLs to check", flush=True)

    results: list[dict] = []
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda s: _check(s, args.timeout), unique):
            results.append(result)
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(unique)}", flush=True)
            time.sleep(0.05)

    by_state = collections.Counter(r["state"] for r in results)
    order = ["gone", "drifted", "moved", "blocked", "archived", "ok"]
    lines = [
        "# Source check",
        "",
        f"Run {dt.date.today().strftime('%m/%d/%Y')} over {len(unique)} distinct URLs "
        f"({len(sources)} citations; a URL cited by several pages is fetched once).",
        "",
        "| state | count | what it means |",
        "|---|---|---|",
        f"| gone | {by_state['gone']} | does not resolve, and no archived copy is recorded: the claim it supports has no source |",
        f"| drifted | {by_state['drifted']} | resolves, but the page is no longer the one we named: re-read it |",
        f"| moved | {by_state['moved']} | redirects: update the URL to where it now lives |",
        f"| blocked | {by_state['blocked']} | the host refuses automated requests; read it by hand |",
        f"| archived | {by_state['archived']} | the original is gone, but the citation records the archived copy it quotes: handled |",
        f"| ok | {by_state['ok']} | still there, still the page we named |",
        "",
    ]
    for state in order:
        rows = [r for r in results if r["state"] == state]
        if not rows or state in ("ok", "archived"):
            continue
        lines += [f"## {state} ({len(rows)})", ""]
        for row in sorted(rows, key=lambda r: r["where"]):
            lines.append(f"- **{row['where']}** — {row['url']}")
            lines.append(f"  - cited as: {row['title'] or '(no title)'}")
            if state == "moved":
                lines.append(f"  - now at: {row['final']}")
            if state == "drifted":
                lines.append(f"  - page now says: {row['detail'] or '(no title)'}")
            if state in ("gone", "blocked", "moved"):
                lines.append(f"  - {row['detail']}")
        lines.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print()
    for state in order:
        print(f"  {state:9} {by_state[state]}")
    print(f"\nwrote {REPORT.relative_to(ROOT)}")
    if args.fail_on_dead and by_state["gone"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
