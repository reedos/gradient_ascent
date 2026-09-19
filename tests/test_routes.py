"""Every address the built site offers actually resolves, and everything the agent guide
promises is really served.

These run against `site/dist`, not against the source, because the question they answer is the
one a reader or a reader's agent asks: I followed this link, was there a file at the other end?
A green `astro check` does not answer it. Astro resolves `<Link href>` at build time and will
happily emit a link to a route that no longer exists, and the two Markdown-twin endpoints and the
`/data/*.json` endpoints are separate route modules that can each stop emitting a file without
anything upstream noticing.

Every test skips cleanly, with a message, when there is no finished build to read -- see
tests/test_indexes.py, whose `_skip_if_no_dist` this module reuses rather than duplicating.

Usage: python -m unittest tests.test_routes -v
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree

from tests.test_indexes import DIST, _skip_if_no_dist

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = ROOT / "content" / "taxonomy.json"

SITE_ORIGIN = "https://reedos.github.io"
BASE = "/gradient_ascent"

# href= and src= on anything: links, stylesheets, scripts, images, the canonical tag, the feed.
ATTR_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]*)"')
# A Markdown link target, for the .md twins and llms.txt.
MD_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"```[\s\S]*?```")

# Pages built from the site's own data rather than from an MDX file. They have no Markdown twin
# by design: an agent is pointed at /llms.txt for the list instead, and /agents.md now says so.
# Listed here so that a page kind losing its twin by accident still fails, rather than being
# waved through by a rule that says "index pages are exempt".
NO_TWIN = {
    "",  # the home page
    "failures",
    "glossary",
    "map",
    "method",
    "names",
    "recipes",
    "search",
    "teardowns",
    "techniques",
    "timeline",
}


def _target_for(href: str, from_file: Path) -> tuple[str, Path | None]:
    """Map one href to (kind, file it must resolve to). `kind` is 'internal' for anything this
    site serves, and 'external', 'scheme' or 'anchor' for what this module does not check."""
    h = href.strip()
    if not h:
        return ("empty", None)
    if h.startswith(("mailto:", "tel:", "javascript:", "data:", "//")):
        return ("scheme", None)
    if h.startswith("#"):
        return ("anchor", None)
    if h.startswith(("http://", "https://")):
        m = re.match(r"https?://([^/]+)(/.*)?$", h)
        if not m:
            return ("external", None)
        if f"https://{m.group(1)}" != SITE_ORIGIN:
            return ("external", None)
        h = m.group(1 + 1) or "/"
    if not h.startswith("/"):
        # A relative link. Resolved against the linking file's own directory.
        target = (from_file.parent / h.split("#")[0].split("?")[0]).resolve()
        return ("internal", target)
    path = h.split("#")[0].split("?")[0]
    if path.startswith(BASE):
        path = path[len(BASE) :] or "/"
    else:
        # An absolute path that forgot the configured base path. On GitHub Pages this 404s.
        return ("no-base", None)
    if path == "/":
        return ("internal", DIST / "index.html")
    if re.search(r"\.[A-Za-z0-9]{1,6}$", path):
        return ("internal", DIST / path.lstrip("/"))
    return ("internal", DIST / path.strip("/") / "index.html")


def _page_slugs(taxonomy: dict) -> dict[str, list[str]]:
    techniques = [p["slug"] for tier in taxonomy["tiers"] for p in tier["pages"]]
    for track in taxonomy["tracks"]:
        techniques.append(track["id"])
        techniques.extend(p["slug"] for p in track.get("pages", []))
    return {
        "techniques": techniques,
        "recipes": [r["slug"] for r in taxonomy["recipes"]],
        "teardowns": [t["slug"] for t in taxonomy["teardowns"]["first"]],
        "threads": [t["id"] for t in taxonomy["threads"]],
        "levels": [str(tier["order"]) for tier in taxonomy["tiers"]],
    }


class InternalLinkTests(unittest.TestCase):
    """Crawl every built page and every Markdown twin, and resolve every internal link."""

    def setUp(self) -> None:
        _skip_if_no_dist(self)

    def test_every_internal_link_on_every_built_page_resolves_to_a_file(self) -> None:
        broken: list[str] = []
        checked = 0
        pages = sorted(DIST.rglob("*.html"))
        self.assertGreater(len(pages), 50, "sanity: the built site should have a lot of pages")
        for page in pages:
            rel = page.relative_to(DIST).as_posix()
            text = page.read_text(encoding="utf-8", errors="replace")
            for href in ATTR_RE.findall(text):
                kind, target = _target_for(href, page)
                if kind != "internal":
                    continue
                checked += 1
                if target is None or not target.is_file():
                    # 404.html is served by GitHub Pages at every missing address, so its own
                    # canonical necessarily names an address that is not a built file.
                    if rel == "404.html" and href.rstrip("/").endswith("/404"):
                        continue
                    broken.append(f"{rel} -> {href}")
        self.assertGreater(checked, 1000, "sanity: this crawl should be checking a lot of links")
        if broken:
            _skip_if_no_dist(self)
        self.assertEqual(broken, [], f"links that resolve to no file in dist: {broken[:20]}")

    def test_no_page_links_an_absolute_path_that_forgot_the_base_path(self) -> None:
        """`/techniques/rag/` instead of `/gradient_ascent/techniques/rag/` works in `npm run dev`
        and 404s on the deployed site, which is the worst kind of bug to find after a push."""
        bad: list[str] = []
        for page in sorted(DIST.rglob("*.html")):
            text = page.read_text(encoding="utf-8", errors="replace")
            for href in ATTR_RE.findall(text):
                if _target_for(href, page)[0] == "no-base":
                    bad.append(f"{page.relative_to(DIST).as_posix()} -> {href}")
        self.assertEqual(bad, [], f"absolute links missing the base path: {bad[:20]}")

    def test_every_link_in_every_markdown_twin_resolves(self) -> None:
        """The twins are what an agent reads. A twin whose links are broken sends it nowhere."""
        broken: list[str] = []
        twins = sorted(DIST.rglob("*.md"))
        self.assertGreater(len(twins), 50, "sanity: there should be a Markdown twin per page")
        for twin in twins:
            text = FENCE_RE.sub("", twin.read_text(encoding="utf-8", errors="replace"))
            for href in MD_LINK_RE.findall(text):
                kind, target = _target_for(href, twin)
                if kind != "internal":
                    continue
                if target is None or not target.is_file():
                    broken.append(f"{twin.relative_to(DIST).as_posix()} -> {href}")
        if broken:
            _skip_if_no_dist(self)
        self.assertEqual(broken, [], f"broken links inside Markdown twins: {broken[:20]}")


class MarkdownTwinTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_dist(self)
        self.taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))

    def test_every_content_page_has_its_markdown_twin(self) -> None:
        """One check over all five page kinds, threads included. tests/test_indexes.py covers
        techniques, recipes and levels; threads and teardowns had no twin test at all, and
        threads are the newest page kind, which is exactly where one goes missing."""
        slugs = _page_slugs(self.taxonomy)
        missing: list[str] = []
        for folder, names in slugs.items():
            for name in names:
                twin = DIST / folder / f"{name}.md"
                if not twin.is_file():
                    missing.append(twin.relative_to(DIST).as_posix())
                elif not twin.read_text(encoding="utf-8").strip():
                    missing.append(f"{twin.relative_to(DIST).as_posix()} (empty)")
        _assert_nothing_missing(self, missing, "Markdown twins missing from the built site")

    def test_the_pages_with_no_twin_are_exactly_the_ones_the_agent_guide_names(self) -> None:
        """The guide tells an agent to read pages in their `.md` form and then names the pages
        that have none. If a page loses or gains a twin, that sentence goes stale silently, and
        an agent either misses a page or follows an address that 404s."""
        without: set[str] = set()
        for index in sorted(DIST.rglob("index.html")):
            rel = index.relative_to(DIST).parent.as_posix()
            rel = "" if rel == "." else rel
            twin = DIST / (f"{rel}.md" if rel else "index.md")
            if not twin.is_file():
                without.add(rel)
        self.assertEqual(
            without,
            NO_TWIN,
            "the set of pages with no Markdown twin changed; update NO_TWIN here and the list "
            "the agent guide prints in site/src/lib/agents.ts",
        )
        guide = (DIST / "agents.md").read_text(encoding="utf-8")
        for rel in sorted(NO_TWIN):
            if not rel:
                continue
            self.assertIn(
                f"`/{rel}/`",
                guide,
                f"/{rel}/ has no Markdown twin, so the agent guide has to say so",
            )


class PublishedFileTests(unittest.TestCase):
    """Everything /agents.md and /llms.txt list is served, and parses as what it claims to be."""

    def setUp(self) -> None:
        _skip_if_no_dist(self)
        self.guide = (DIST / "agents.md").read_text(encoding="utf-8")

    def _guide_urls(self) -> list[str]:
        urls = re.findall(rf"\(({re.escape(SITE_ORIGIN)}{re.escape(BASE)}/[^)\s]+)\)", self.guide)
        self.assertGreater(len(urls), 10, "sanity: the guide should list its files")
        return sorted(set(urls))

    def test_every_file_the_agent_guide_lists_is_served(self) -> None:
        missing = []
        for u in self._guide_urls():
            kind, target = _target_for(u, DIST / "agents.md")
            if kind != "internal" or target is None or not target.is_file():
                missing.append(u)
        _assert_nothing_missing(self, missing, "files the agent guide lists but the build does not serve")

    def test_every_json_file_the_guide_lists_parses_as_json(self) -> None:
        """An agent is told to fetch these and read them as data. A route that throws mid-render
        can still emit a truncated file, and nothing else on the site would look wrong."""
        seen = 0
        for u in self._guide_urls():
            if not u.endswith(".json"):
                continue
            _, target = _target_for(u, DIST / "agents.md")
            assert target is not None
            seen += 1
            try:
                payload = json.loads(target.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self.fail(f"{u} does not parse as JSON: {exc}")
            self.assertTrue(payload, f"{u} parsed to an empty document")
        self.assertGreaterEqual(seen, 6, "sanity: the guide publishes several JSON files")

    def test_the_change_feed_parses_as_atom_and_covers_every_entry(self) -> None:
        feed = DIST / "changes.xml"
        self.assertTrue(feed.is_file(), "the Atom feed at /changes.xml is not in the built site")
        ns = "{http://www.w3.org/2005/Atom}"
        try:
            root = ElementTree.parse(feed).getroot()
        except ElementTree.ParseError as exc:
            self.fail(f"/changes.xml does not parse as XML: {exc}")
        self.assertEqual(root.tag, f"{ns}feed", "/changes.xml is not an Atom feed")
        entries = root.findall(f"{ns}entry")
        changes = json.loads((ROOT / "content" / "changes.json").read_text(encoding="utf-8"))["changes"]
        self.assertEqual(
            len(entries),
            len(changes),
            f"the feed carries {len(entries)} entries and content/changes.json has {len(changes)}",
        )
        for entry in entries:
            self.assertTrue((entry.findtext(f"{ns}title") or "").strip(), "a feed entry has no title")
            self.assertTrue((entry.findtext(f"{ns}updated") or "").strip(), "a feed entry has no date")


class SearchIndexTests(unittest.TestCase):
    """The index is what the search box reads. A page kind missing from it is unfindable, and
    every check on the site stays green while it is."""

    def setUp(self) -> None:
        _skip_if_no_dist(self)
        self.docs = json.loads((DIST / "search-index.json").read_text(encoding="utf-8"))
        self.taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
        self.by_id = {d["id"]: d for d in self.docs}

    def test_every_thread_is_in_the_index(self) -> None:
        missing = [t["id"] for t in self.taxonomy["threads"] if f"thread:{t['id']}" not in self.by_id]
        self.assertEqual(missing, [], f"threads missing from the search index: {missing}")

    def test_every_teardown_is_in_the_index(self) -> None:
        missing = [
            t["slug"]
            for t in self.taxonomy["teardowns"]["first"]
            if f"teardown:{t['slug']}" not in self.by_id
        ]
        self.assertEqual(missing, [], f"teardowns missing from the search index: {missing}")

    def test_the_data_built_views_are_in_the_index(self) -> None:
        """/shapes/, /changes/ and /agents/ shipped after the view list was written by hand and
        were the three pages a reader could not find by searching for them by name."""
        for view in ("map", "timeline", "worksheet", "shapes", "changes", "agents", "method"):
            self.assertIn(f"view:{view}", self.by_id, f"/{view}/ is missing from the search index")

    def test_every_indexed_url_resolves_to_a_built_file(self) -> None:
        broken = []
        for doc in self.docs:
            kind, target = _target_for(doc["url"], DIST / "search-index.json")
            if kind != "internal" or target is None or not target.is_file():
                broken.append(f"{doc['id']} -> {doc['url']}")
        _assert_nothing_missing(self, broken, "search results pointing at no built file")


def _assert_nothing_missing(test_case: unittest.TestCase, missing: list, message: str) -> None:
    """Fail with the list, unless a build started while we were reading, in which case skip."""
    if missing:
        _skip_if_no_dist(test_case)
    test_case.assertEqual(missing, [], f"{message}: {missing[:20]}")


if __name__ == "__main__":
    unittest.main()
