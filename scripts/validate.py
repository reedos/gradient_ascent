"""Validate content/taxonomy.json and content/landscape.json.

Rules:
  1. Page slugs are unique across levels and tracks.
  2. Level orders run 0..n-1 with no gaps.
  3. Every relation, recipe, thread and teardown reference resolves to a page or a track.
  4. Every relation type is declared.
  5. The `requires` graph has no cycle.
  6. Every registry entry has a name, a category and at least one `demonstrates` reference,
     and each reference resolves. A model's `developer` must be a listed developer.
  7. Registry ids are unique.
  8. An entry marked verified must carry a source and a checked date.
  8a. An entry that is `retired` or has a `superseded_by` carries a `note` saying what happened
      and what replaced it; `superseded_by` resolves to another registry id, never to itself.
  8b. An entry with a `formerly` name carries a source: a rename is a claim about the world.
  8c. `category` is a plain description: at most seven words, no title case, no marketing word.
  9. Every tier has a title, a short line, a who-decides line and a description.
  10. Every page (a tier's page or a track's page) has a title, a summary and a status drawn
      from the declared `statuses`.
  11. Every internal `<Link href="...">` in `site/src/content/**/*.mdx` resolves to a real route:
      a technique, a level, a recipe, or one of the site's fixed pages.
  12. Every `<CodeFile file="..." />` names a file that exists, and its `func=`/`cls=` names a
      function or class that file actually defines.
  13. Every run file in `site/src/data/runs/` has an `h` that clears its lowest node, and no node
      placed so far sideways that the diagram has to shrink to fit.
  14. Every entry in `stages` has an id, a title, `kinds`, a `line` and a non-empty `levels`
      list, and the `levels` lists, concatenated in stage order, cover every tier order exactly
      once in ascending order (0, 1, 2, ... with no gap, repeat or reorder).
  15. Teardowns: the listed teardowns stay inside the cap, each decodes at least one technique
      (rule 3 already checks that each of those slugs resolves), every teardown in the taxonomy
      has an MDX file under `site/src/content/teardowns/` and every such file is in the taxonomy,
      and each file's frontmatter names its own slug, a reviewed date, at least one source and at
      least one registry id under `products`.
  16. An unverified registry entry may not be named by a `published` page, and may not be a
      teardown's `products` id at all.
  17. Every recipe has a `domain` drawn from the declared `domains`, and at least one domain is
      declared. The recipes index groups by domain; an unlisted one drops a recipe out of every
      heading on the page.

Techniques with no named example are reported, not failed.

Usage: python scripts/validate.py [content_dir]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REGISTRY_LISTS = ("models", "products", "tools")

# A category says what a thing is, in the words a reader would use. These are the words that
# turn one into a pitch; they are rejected outright rather than argued about per entry.
MARKETING_WORDS = frozenset(
    """
    advanced best cutting-edge easiest enterprise-grade fastest flagship innovative
    intelligent leading next-generation powerful premier revolutionary robust seamless
    smartest state-of-the-art ultimate unmatched world-class
    """.split()
)
CATEGORY_MAX_WORDS = 7


def category_problem(category: str) -> str | None:
    """Why this category is not a plain lower-case description, or None if it is fine.

    Acronyms and mixed-case names keep their capitals ("model API", "LoRA and other adapters",
    "vector search in Postgres"), so the test is only on the first word, and only for plain
    Title Case -- "Coding Agent". A proper noun that would lead the category gets rephrased so
    the description leads instead, which is the point of the rule.
    """
    words = category.split()
    if not words:
        return "is empty"
    if len(words) > CATEGORY_MAX_WORDS:
        return f"is {len(words)} words; keep it to {CATEGORY_MAX_WORDS} or fewer"
    first = words[0]
    if len(first) > 1 and first[0].isupper() and first[1:].islower():
        return f"is title case ({first!r}); start it with a lower-case description"
    hits = sorted({w.strip(",.").lower() for w in words} & MARKETING_WORDS)
    if hits:
        return f"uses marketing wording: {', '.join(hits)}"
    return None


def load(content_dir: Path) -> tuple[dict, dict | None]:
    taxonomy = json.loads((content_dir / "taxonomy.json").read_text(encoding="utf-8"))
    land_path = content_dir / "landscape.json"
    landscape = json.loads(land_path.read_text(encoding="utf-8")) if land_path.exists() else None
    return taxonomy, landscape


GLOSSARY_MIN_WORDS = 8
GLOSSARY_MAX_WORDS = 60


def validate_glossary(glossary: dict, taxonomy: dict) -> list[str]:
    """Rules for content/glossary.json, a generated-index data file (finish-indexes).

    1. Every term is unique, case-insensitive, counting every `aka` as its own name.
    2. Every `page` resolves to a real tier page, track page/id, or thread id in taxonomy.json.
       A thread is the right home for a term that names two different techniques at once --
       "graph engineering" is one word for the level-2 and level-6 pages both -- and pointing
       such a term at either one of them would teach the confusion the thread exists to undo.
    3. Every `see` resolves to another entry's `term` or `aka`, case-insensitive.
    4. Every `definition` is 8 to 60 words: short enough to stay plain, long enough to say
       something a newcomer can use.
    """
    errors: list[str] = []
    level_pages, track_pages, tracks = page_ids(taxonomy)
    threads = {t["id"] for t in taxonomy.get("threads", [])}
    page_ids_set = set(level_pages) | set(track_pages) | set(tracks) | threads

    terms = glossary.get("terms", [])
    seen: dict[str, str] = {}
    for entry in terms:
        term = entry.get("term", "<no term>")
        names = [term] + list(entry.get("aka", []))
        for name in names:
            key = name.strip().lower()
            if key in seen and seen[key] != term:
                errors.append(f"glossary: {name!r} duplicates a name already used by {seen[key]!r}")
            elif key in seen:
                errors.append(f"glossary: {name!r} is listed twice for term {term!r}")
            else:
                seen[key] = term

        page = entry.get("page")
        if page not in page_ids_set:
            errors.append(
                f"glossary: term {term!r} has page {page!r}, which is not a real technique, "
                "topic slug or thread id"
            )

        definition = entry.get("definition", "")
        word_count = len(definition.split())
        if not (GLOSSARY_MIN_WORDS <= word_count <= GLOSSARY_MAX_WORDS):
            errors.append(
                f"glossary: term {term!r} definition is {word_count} words; "
                f"keep it to {GLOSSARY_MIN_WORDS}-{GLOSSARY_MAX_WORDS}"
            )

    # `see` is checked in a second pass so a term appearing later in the file can still resolve.
    all_names = set(seen)
    for entry in terms:
        term = entry.get("term", "<no term>")
        for ref in entry.get("see", []):
            if ref.strip().lower() not in all_names:
                errors.append(f"glossary: term {term!r} has a see reference that resolves to nothing: {ref!r}")

    return errors


def status_by_id(taxonomy: dict) -> dict[str, str]:
    """Every page id (tier page, track root, track page) mapped to its declared status."""
    out: dict[str, str] = {}
    for tier in taxonomy.get("tiers", []):
        for page in tier.get("pages", []):
            out[page["slug"]] = page.get("status", "")
    for track in taxonomy.get("tracks", []):
        out[track["id"]] = track.get("status", "")
        for page in track.get("pages", []):
            out[page["slug"]] = page.get("status", "")
    return out


def page_ids(taxonomy: dict) -> tuple[list[str], list[str], list[str]]:
    level_pages = [p["slug"] for tier in taxonomy["tiers"] for p in tier["pages"]]
    track_pages = [p["slug"] for tr in taxonomy["tracks"] for p in tr.get("pages", [])]
    tracks = [tr["id"] for tr in taxonomy["tracks"]]
    return level_pages, track_pages, tracks


def find_cycle(requires: dict[str, list[str]]) -> list[str] | None:
    state: dict[str, int] = {}

    def visit(node: str, path: list[str]) -> list[str] | None:
        if state.get(node) == 1:
            return path + [node]
        if state.get(node) == 2:
            return None
        state[node] = 1
        for nxt in requires.get(node, []):
            found = visit(nxt, path + [node])
            if found:
                return found
        state[node] = 2
        return None

    for start in list(requires):
        found = visit(start, [])
        if found:
            return found
    return None


def validate(taxonomy: dict, landscape: dict | None) -> tuple[list[str], dict]:
    errors: list[str] = []
    level_pages, track_pages, tracks = page_ids(taxonomy)
    all_pages = level_pages + track_pages
    ids = set(all_pages) | set(tracks)

    for slug in sorted({s for s in all_pages if all_pages.count(s) > 1}):
        errors.append(f"duplicate slug: {slug}")

    orders = [tier["order"] for tier in taxonomy["tiers"]]
    if orders != list(range(len(orders))):
        errors.append(f"level orders must run 0..{len(orders) - 1} in sequence, got {orders}")

    statuses = set(taxonomy.get("statuses", []))
    for tier in taxonomy["tiers"]:
        for field in ("title", "short", "who", "description"):
            if not tier.get(field):
                errors.append(f"tier {tier['id']} has no {field}")
        for page in tier["pages"]:
            for field in ("title", "summary"):
                if not page.get(field):
                    errors.append(f"page {page['slug']} has no {field}")
            if page.get("status") not in statuses:
                errors.append(f"page {page['slug']} has no valid status: {page.get('status')!r}")
    for track in taxonomy.get("tracks", []):
        for page in track.get("pages", []):
            for field in ("title", "summary"):
                if not page.get(field):
                    errors.append(f"page {page['slug']} has no {field}")
            if page.get("status") not in statuses:
                errors.append(f"page {page['slug']} has no valid status: {page.get('status')!r}")

    # Rule 14: `stages` is the home-page climb chart's own grouping of the tiers into four ways
    # of working with a model, plus order zero. Every tier must appear in exactly one stage, in
    # order, or the chart and the taxonomy it is drawn from can silently drift apart (a tier
    # added, removed or reordered without the chart's data catching up).
    stages = taxonomy.get("stages", [])
    for stage in stages:
        stage_id = stage.get("id", "<no id>")
        for field in ("id", "title", "kinds", "line"):
            if not stage.get(field):
                errors.append(f"stage {stage_id} has no {field}")
        if not stage.get("levels"):
            errors.append(f"stage {stage_id} has no levels")
    if stages:
        covered = [level for stage in stages for level in stage.get("levels", [])]
        expected = list(range(len(taxonomy["tiers"])))
        if covered != expected:
            errors.append(
                f"stage levels must cover every tier exactly once in ascending order: "
                f"expected {expected}, got {covered}"
            )

    types = taxonomy.get("relation_types", {})
    requires: dict[str, list[str]] = {}
    for rel in taxonomy.get("relations", []):
        if rel["type"] not in types:
            errors.append(f"unknown relation type: {rel['type']} ({rel['from']} -> {rel['to']})")
        for end in ("from", "to"):
            if rel[end] not in ids:
                errors.append(f"relation references unknown id: {rel[end]}")
        if rel["type"] == "requires":
            requires.setdefault(rel["from"], []).append(rel["to"])
    # Rule 17: a recipe's domain says which audience its page is written for, and the recipes
    # index groups by it. An unlisted domain would silently drop a recipe out of both headings,
    # which is a page that exists and is linked from nowhere.
    domains = set(taxonomy.get("domains", []))
    if not domains:
        errors.append("taxonomy declares no domains")
    for recipe in taxonomy.get("recipes", []):
        if recipe.get("domain") not in domains:
            errors.append(
                f"recipe {recipe['slug']} has no valid domain: {recipe.get('domain')!r}"
            )
        for ref in recipe["uses"]:
            if ref not in ids:
                errors.append(f"recipe {recipe['slug']} uses unknown id: {ref}")
    for thread in taxonomy.get("threads", []):
        for ref in thread["pages"]:
            if ref not in ids:
                errors.append(f"thread {thread['id']} lists unknown id: {ref}")
    for teardown in taxonomy.get("teardowns", {}).get("first", []):
        for ref in teardown.get("patterns", []):
            if ref not in ids:
                errors.append(f"teardown {teardown['slug']} lists unknown id: {ref}")

    cycle = find_cycle(requires)
    if cycle:
        errors.append("requires cycle: " + " > ".join(cycle))

    named: set[str] = set()
    statuses_by_id = status_by_id(taxonomy)
    counts = {key: 0 for key in REGISTRY_LISTS}
    if landscape is not None:
        developers = {d["id"] for d in landscape.get("developers", [])}
        registry_ids = {
            entry["id"]
            for key in REGISTRY_LISTS
            for entry in landscape.get(key, [])
            if entry.get("id")
        }
        seen: set[str] = set()
        for key in REGISTRY_LISTS:
            for entry in landscape.get(key, []):
                counts[key] += 1
                eid = entry.get("id", "<no id>")
                if eid in seen:
                    errors.append(f"duplicate registry id: {eid}")
                seen.add(eid)
                for field in ("name", "category"):
                    if not entry.get(field):
                        errors.append(f"registry entry {eid} has no {field}")
                refs = entry.get("demonstrates", [])
                if not refs:
                    errors.append(f"registry entry {eid} demonstrates nothing")
                for ref in refs:
                    if ref not in ids:
                        errors.append(f"registry entry {eid} demonstrates unknown id: {ref}")
                    named.add(ref)
                if key == "models" and entry.get("developer") not in developers:
                    errors.append(f"model {eid} has unknown developer: {entry.get('developer')}")
                if key != "models" and not entry.get("by") and entry.get("developer") not in developers:
                    errors.append(f"registry entry {eid} has no maker")
                if entry.get("verified") and not (entry.get("source") and entry.get("checked")):
                    errors.append(f"registry entry {eid} is verified without a source and a checked date")

                # Rule 16 (the project plan, Named things: "Seed entries are `verified: false` until
                # confirmed against the primary source, which must happen before the first page
                # citing them is published"). A draft page may name a seed; a published one may
                # not. Today every page is a draft, so this rule is quiet -- it exists to bite on
                # the day the first page is promoted, which is exactly when nobody will be
                # re-reading the registry.
                if not entry.get("verified"):
                    for ref in refs:
                        if statuses_by_id.get(ref) == "published":
                            errors.append(
                                f"registry entry {eid} is not verified but is named by published "
                                f"page {ref}"
                            )

                problem = category_problem(entry.get("category") or "")
                if entry.get("category") and problem:
                    errors.append(f"registry entry {eid} category {problem}")

                # A reader who meets a retired product needs to be told, in the entry itself,
                # that it is gone and what took over. Without this the site can say "retired:
                # 2026-12-11" and nothing else, which is worse than not listing it.
                if (entry.get("retired") or entry.get("superseded_by")) and not entry.get("note"):
                    errors.append(
                        f"registry entry {eid} is retired or superseded and has no note saying "
                        f"what happened and what replaced it"
                    )
                successor = entry.get("superseded_by")
                if successor is not None:
                    if successor == eid:
                        errors.append(f"registry entry {eid} is superseded by itself")
                    elif successor not in registry_ids:
                        errors.append(
                            f"registry entry {eid} is superseded by unknown id: {successor}"
                        )

                # A rename is a claim about the world like any other, so it needs a page that
                # says the rename happened.
                if entry.get("formerly") and not entry.get("source"):
                    errors.append(f"registry entry {eid} records a former name with no source")

    report = {
        "levels": len(taxonomy["tiers"]),
        "level_pages": len(level_pages),
        "track_pages": len(track_pages),
        "recipes": len(taxonomy.get("recipes", [])),
        "recipes_by_domain": {
            domain: sum(1 for r in taxonomy.get("recipes", []) if r.get("domain") == domain)
            for domain in taxonomy.get("domains", [])
        },
        "teardowns": len((taxonomy.get("teardowns") or {}).get("first", [])),
        "relations": len(taxonomy.get("relations", [])),
        "registry": counts,
        "unnamed": sorted(set(level_pages) - named) if landscape is not None else [],
    }
    return errors, report


# `<Link href="/x/">` is the only sanctioned way to link internally, so one scan of the MDX
# catches every internal link on the site. Markdown's own `](/...)` syntax is banned separately
# (it drops the Pages base path); this finds it too, rather than letting it through unchecked.
LINK_RE = re.compile(r"<Link\b[^>]*?\bhref=\"([^\"]*)\"")
MD_LINK_RE = re.compile(r"\]\((/[^)\s]*)\)")
CODEFILE_RE = re.compile(r"<CodeFile\b([^>]*?)/>", re.S)
ATTR_RE = re.compile(r"(\w+)=\"([^\"]*)\"")
NUM_ATTR_RE = re.compile(r"(\w+)=\{(\d+)\}")


def mdx_routes(taxonomy: dict, pages_dir: Path) -> set[str]:
    """Every internal path a page may link to, in the form `<Link>` writes it."""
    level_pages, track_pages, tracks = page_ids(taxonomy)
    routes = {f"/techniques/{slug}/" for slug in level_pages + track_pages + tracks}
    routes |= {f"/levels/{tier['order']}/" for tier in taxonomy["tiers"]}
    routes |= {f"/recipes/{r['slug']}/" for r in taxonomy.get("recipes", [])}
    routes |= {f"/threads/{t['id']}/" for t in taxonomy.get("threads", [])}
    # The fixed pages, read off the routes Astro generates rather than listed here, so a page
    # added or renamed under site/src/pages/ cannot leave this rule stale.
    for path in sorted(pages_dir.rglob("*.astro")):
        rel = path.relative_to(pages_dir).as_posix()
        if "[" in rel:  # a dynamic route; its slugs are already covered above
            continue
        stem = rel[: -len(".astro")]
        if stem == "404":
            continue
        routes.add("/" if stem == "index" else f"/{stem.removesuffix('/index')}/")
    return routes


def check_mdx(repo_root: Path, taxonomy: dict) -> list[str]:
    """Rules 11 and 12: internal links and `CodeFile` references resolve.

    Both failures are silent without this: a `<Link>` to a slug that does not exist renders as a
    live link to an empty page, and a `CodeFile` pointing at a function that has been renamed
    throws only at build time, on whichever page happens to build first.
    """
    errors: list[str] = []
    content_root = repo_root / "site" / "src" / "content"
    pages_dir = repo_root / "site" / "src" / "pages"
    if not content_root.is_dir() or not pages_dir.is_dir():
        return errors
    routes = mdx_routes(taxonomy, pages_dir)
    # Every milestone id and shift id is an anchor on /timeline/.
    timeline_anchors: set[str] | None = None
    timeline_path = repo_root / "content" / "timeline.json"
    if timeline_path.exists():
        tl = json.loads(timeline_path.read_text(encoding="utf-8"))
        timeline_anchors = {m.get("id") for m in tl.get("milestones", [])} | {x.get("id") for x in tl.get("shifts", [])}

    for mdx in sorted(content_root.rglob("*.mdx")):
        where = mdx.relative_to(repo_root).as_posix()
        text = mdx.read_text(encoding="utf-8")

        for href in LINK_RE.findall(text):
            if not href.startswith("/"):
                errors.append(f"{where}: Link href is not a site-relative path: {href!r}")
            elif href.split("#", 1)[0] not in routes:
                # A fragment (`/timeline/#reasoning-models`) names an anchor on the page; the
                # route is what has to exist. Timeline anchors are checked separately below.
                errors.append(f"{where}: Link href resolves to no route: {href!r}")
            elif href.startswith("/timeline/#") and timeline_anchors is not None                     and href.split("#", 1)[1] not in timeline_anchors:
                errors.append(f"{where}: Link href names no anchor on the timeline page: {href!r}")
        for href in MD_LINK_RE.findall(text):
            errors.append(
                f"{where}: raw Markdown link to {href!r}; use <Link href=\"...\"> so the "
                f"Pages base path is applied"
            )

        for raw in CODEFILE_RE.findall(text):
            attrs = dict(ATTR_RE.findall(raw))
            nums = {k: int(v) for k, v in NUM_ATTR_RE.findall(raw)}
            target = attrs.get("file")
            if not target:
                errors.append(f"{where}: CodeFile has no file=")
                continue
            path = repo_root / target
            if not path.is_file():
                errors.append(f"{where}: CodeFile file does not exist: {target}")
                continue
            body = path.read_text(encoding="utf-8")
            if attrs.get("func") and not re.search(rf"^def {re.escape(attrs['func'])}\(", body, re.M):
                errors.append(f"{where}: CodeFile func {attrs['func']!r} is not defined in {target}")
            if attrs.get("cls") and not re.search(rf"^class {re.escape(attrs['cls'])}[(:]", body, re.M):
                errors.append(f"{where}: CodeFile cls {attrs['cls']!r} is not defined in {target}")

            # A pinned range is a line number written about a file the page does not own. The
            # range itself cannot be wrong in a way the build notices, so `expect=` -- a literal
            # the block must still contain -- is what makes a slid window fail loudly.
            start, end = nums.get("start"), nums.get("end")
            if start is not None and end is not None:
                body_lines = body.replace("\r\n", "\n").split("\n")
                if start < 1 or end > len(body_lines) or start > end:
                    errors.append(
                        f"{where}: CodeFile range {start}-{end} is outside {target} "
                        f"({len(body_lines)} lines)"
                    )
                elif attrs.get("expect") and attrs["expect"] not in "\n".join(body_lines[start - 1 : end]):
                    errors.append(
                        f"{where}: CodeFile range {start}-{end} in {target} no longer contains "
                        f"{attrs['expect']!r}; the range has slid"
                    )
    return errors


def parse_frontmatter(text: str) -> dict[str, object]:
    """The frontmatter of an MDX file as `{key: scalar or list of item strings}`.

    Enough YAML for the schemas this repository actually writes: top-level scalars, inline lists
    (`products: [a, b]`) and `- ` item blocks. An item's own nested keys are not parsed -- only
    the item's first line is kept -- because every rule below asks how many items there are and
    what a `products` id says, never what is inside a source entry. `site/src/content.config.ts`
    is what type-checks the rest, at build time.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)

    out: dict[str, object] = {}
    key: str | None = None
    for line in body:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0 and ":" in line:
            key, _, raw = line.partition(":")
            key = key.strip()
            raw = raw.strip()
            if raw.startswith("[") and raw.endswith("]"):
                out[key] = [v.strip().strip("'\"") for v in raw[1:-1].split(",") if v.strip()]
            elif raw:
                out[key] = raw.strip("'\"")
            else:
                out[key] = []
        elif key is not None and isinstance(out.get(key), list) and line.lstrip().startswith("- "):
            out[key].append(line.lstrip()[2:].strip())  # type: ignore[union-attr]
    return out


def check_teardowns(repo_root: Path, taxonomy: dict, landscape: dict | None = None) -> list[str]:
    """Rule 15: the teardown layer, in the taxonomy and on disk, agree.

    A teardown is the one page kind with a shelf life and the one whose whole subject is named
    products, so three things that are silent everywhere else have to fail here: a teardown listed
    in the taxonomy with no page (the route builds and renders an empty outline), a page with no
    taxonomy entry (it has no route at all and simply never appears), and a teardown page with no
    sources (a page whose claims are all about somebody else's product, citing nothing).
    """
    errors: list[str] = []
    block = taxonomy.get("teardowns") or {}
    listed = block.get("first", [])
    cap = block.get("cap")
    if isinstance(cap, int) and len(listed) > cap:
        errors.append(
            f"teardowns: {len(listed)} are listed but the cap is {cap}; retire one before adding another"
        )

    slugs: list[str] = []
    for teardown in listed:
        slug = teardown.get("slug") or "<no slug>"
        if slug in slugs:
            errors.append(f"teardown {slug} is listed twice")
        slugs.append(slug)
        if not teardown.get("title"):
            errors.append(f"teardown {slug} has no title")
        if not teardown.get("patterns"):
            errors.append(f"teardown {slug} decodes no techniques")

    content_dir = repo_root / "site" / "src" / "content" / "teardowns"
    if not content_dir.is_dir():
        if listed:
            errors.append(
                "site/src/content/teardowns/ does not exist, but content/taxonomy.json lists "
                f"{len(listed)} teardown(s)"
            )
        return errors

    files = {path.stem: path for path in sorted(content_dir.glob("*.mdx"))}
    for slug in slugs:
        if slug not in files:
            errors.append(
                f"teardown {slug} is in taxonomy.json with no page at "
                f"site/src/content/teardowns/{slug}.mdx"
            )
    for stem in files:
        if stem not in slugs:
            errors.append(
                f"site/src/content/teardowns/{stem}.mdx has no matching teardown in taxonomy.json"
            )

    registry_ids: set[str] = set()
    unverified_ids: set[str] = set()
    if landscape is not None:
        registry_ids = {
            entry["id"]
            for key in REGISTRY_LISTS
            for entry in landscape.get(key, [])
            if entry.get("id")
        }
        unverified_ids = {
            entry["id"]
            for key in REGISTRY_LISTS
            for entry in landscape.get(key, [])
            if entry.get("id") and not entry.get("verified")
        }

    for stem, path in files.items():
        where = f"site/src/content/teardowns/{stem}.mdx"
        front = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not front:
            errors.append(f"{where}: has no frontmatter block")
            continue
        if front.get("slug") != stem:
            errors.append(f"{where}: frontmatter slug is {front.get('slug')!r}, not {stem!r}")
        if not front.get("reviewed"):
            errors.append(f"{where}: has no reviewed date")
        sources = front.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(
                f"{where}: has no sources; a teardown states what a maker documents about its "
                f"own product, so it cites that page"
            )
        products = front.get("products")
        if not isinstance(products, list) or not products:
            errors.append(f"{where}: names no products; list the registry ids it decodes")
        elif registry_ids:
            for pid in products:
                if pid not in registry_ids:
                    errors.append(f"{where}: product {pid!r} is not an id in content/landscape.json")
                elif pid in unverified_ids:
                    # The same rule as rule 16, applied where it bites hardest. A teardown has no
                    # status of its own: it is live from the moment it is written, and it is about
                    # the product, not about a technique that merely ships in one.
                    errors.append(
                        f"{where}: product {pid!r} is not verified against its maker's own page; "
                        f"a teardown may not decode a registry seed"
                    )

    return errors


# RunDiagram draws a node box 132 units wide and 38 tall, centered on (x, y), and sizes the SVG
# from the run file's own `h`. Neither number is checked anywhere, and three run files shipped in
# wave 3 with the final node sliced in half because `h` had been set to the last node's `y`. It
# builds green and shows up only in a screenshot.
NODE_HALF_W = 66
NODE_HALF_H = 19
BASE_CANVAS_W = 340  # what every run file is drawn against
# The component widens the viewBox rather than clipping a node that overruns the base canvas, so
# a stray x is not cut off -- it shrinks the whole diagram. Past about this width the 11.5px
# labels fall under 9px at the 430px display cap, which is the real failure.
MAX_DRAWN_W = 460


# One `decided_by="model"` site in an example is one recorded model decision. Written as a
# module constant so the rule is greppable from the example side too.
MODEL_DECIDED_RE = re.compile(r"""decided_by\s*=\s*["']model["']""")


def check_runs(repo_root: Path) -> list[str]:
    """Rule 13: a run diagram fits the box it declares."""
    errors: list[str] = []
    runs_dir = repo_root / "site" / "src" / "data" / "runs"
    if not runs_dir.is_dir():
        return errors
    for path in sorted(runs_dir.glob("*.json")):
        where = path.relative_to(repo_root).as_posix()
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{where}: not valid JSON: {exc}")
            continue
        nodes = run.get("nodes") or []
        if not nodes:
            errors.append(f"{where}: has no nodes")
            continue
        height = run.get("h")
        if not isinstance(height, (int, float)):
            errors.append(f"{where}: has no numeric h")
            continue

        lowest = max(nodes, key=lambda n: n["y"])
        needed = lowest["y"] + NODE_HALF_H
        if needed > height:
            errors.append(
                f"{where}: h is {height}, which clips node {lowest['id']!r} at y={lowest['y']}; "
                f"a node is drawn to y+{NODE_HALF_H}, so h must be at least {needed}"
            )

        xs = [n["x"] for n in nodes]
        left = min([0] + [x - NODE_HALF_W - 2 for x in xs])
        right = max([BASE_CANVAS_W] + [x + NODE_HALF_W + 2 for x in xs])
        if right - left > MAX_DRAWN_W:
            far = min(nodes, key=lambda n: min(n["x"], BASE_CANVAS_W - n["x"]))
            errors.append(
                f"{where}: nodes span {right - left} drawn units (node {far['id']!r} is at "
                f"x={far['x']}); keep every x inside the {BASE_CANVAS_W}-unit canvas so the "
                f"diagram does not shrink past {MAX_DRAWN_W} units to fit"
            )
    return errors


def check_run_model_steps(repo_root: Path, taxonomy: dict) -> list[str]:
    """Rule 14: a run diagram and its example must agree about WHETHER the model decides.

    The rule in `examples/common/trace.py` is that a step is model-decided when the model's own
    output selected what happens next. Two things follow, and both are checkable by reading:

    1. Levels 0 to 3 leave every decision with the person or the code, so a run file for a page
       at those levels may not play a model-decided step, and its example may not contain a
       `decided_by="model"` site. This is the site's central claim; nothing enforced it before.
    2. An example that never records a model decision cannot illustrate one, and an example that
       does must not be drawn as though code chose everything. Presence must match, in both
       directions.

    Counts are deliberately NOT compared. A source-site count is neither an upper nor a lower
    bound on what a trace records -- a loop fires one site many times, a branch fires one site of
    two -- so requiring equality against a static read reports false failures on eight of this
    repository's own pages. Comparing real counts needs a recorded trace per run file, which is
    what `published` status is for. Where a diagram knowingly draws one model call as two edges,
    the run file says so in `"trace_note"`, which this check requires to be a non-empty string
    when present.
    """
    errors: list[str] = []
    runs_dir = repo_root / "site" / "src" / "data" / "runs"
    examples_dir = repo_root / "examples"
    if not runs_dir.is_dir():
        return errors

    level_of: dict[str, int] = {}
    for tier in taxonomy.get("tiers", []):
        for page in tier.get("pages", []):
            level_of[page["slug"]] = tier["order"]

    for path in sorted(runs_dir.glob("*.json")):
        slug = path.stem
        where = path.relative_to(repo_root).as_posix()
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue  # check_runs already reports this
        note = run.get("trace_note")
        if note is not None and not (isinstance(note, str) and note.strip()):
            errors.append(f"{where}: trace_note must be a non-empty string when present")
        by_edge = {e["id"]: e.get("by") for e in run.get("edges") or []}
        played = sum(1 for s in run.get("steps") or [] if by_edge.get(s.get("e")) == "model")

        level = level_of.get(slug)
        if level is not None and level <= 3 and played:
            errors.append(
                f"{where}: {slug} is at level {level}, where the person or the code decides every "
                f"step, but the run plays {played} model-decided step(s)"
            )

        if slug.startswith("recipe-"):
            continue  # a recipe's diagram is assembled from several examples, not one
        example = examples_dir / slug.replace("-", "_") / "run.py"
        if not example.is_file():
            continue
        rel = example.relative_to(repo_root).as_posix()
        sites = len(MODEL_DECIDED_RE.findall(example.read_text(encoding="utf-8")))
        if level is not None and level <= 3 and sites:
            errors.append(f"{rel}: level {level} example has {sites} decided_by=\"model\" site(s)")
        if played and not sites:
            errors.append(
                f"{where}: plays a model-decided step, but {rel} never records one "
                f"(no decided_by=\"model\" site) -- examples/common/trace.py"
            )
        if sites and not played:
            errors.append(
                f"{where}: plays no model-decided step, but {rel} records one "
                f"(a decided_by=\"model\" site) -- examples/common/trace.py"
            )
    return errors


# A milestone's `date` must match its declared `precision`, so a coarser precision cannot hide
# behind a fake day. `_date_key` turns any of the three into a sortable (year, month, day) tuple
# by treating a coarser date as the start of the period it names, which is what "not after as_of"
# needs: a milestone dated "2026-09" is not future relative to an as_of of "2026-09-18", but one
# dated "2026-10" is.
DATE_PATTERNS = {
    "day": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "month": re.compile(r"^\d{4}-\d{2}$"),
    "year": re.compile(r"^\d{4}$"),
}

# The three dates the timeline marks per level. `described` is the first publication of the
# idea, `buildable` the first open framework or API a developer could build it with, and
# `available` the first product an ordinary customer could simply use. Keeping them apart is
# the point: a developer framework is not a product, and saying so was the defect this key set
# was added to fix.
MARKED_DATE_KEYS = ("described", "buildable", "available")

# How available a product was on the date its milestone marks. Optional, but when present it has
# to come from this list: "the earliest date an ordinary customer could get in" is a different
# claim from "the day the maker first wrote about it", and the difference has to be sayable in
# the data rather than only in prose.
AVAILABILITY_VALUES = ("general", "preview", "waitlist", "paid plans")


def _date_key(date_str: str) -> tuple[int, int, int]:
    parts = date_str.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 else 1
    return (year, month, day)


def validate_timeline(timeline: dict, taxonomy: dict, landscape: dict | None) -> list[str]:
    """Rules for content/timeline.json, the levels-over-time data (added by timeline-research).

    1. Milestone ids are unique.
    2. Every milestone's `level` is one of the taxonomy's tier orders (0..7 today).
    3. `date` matches its declared `precision` (day, month or year).
    4. No milestone `date` is after `as_of`.
    5. Each entry in `levels` names a level at most once; its `described`, `buildable` and
       `available` each resolve to a milestone actually AT that level, or are null and carry a
       `note` explaining why (level 0 has no maker announcing availability; level 7 has no open
       framework of its own that could be dated here).
    6. A milestone's `technique`, when present, resolves to a taxonomy page slug; its
       `registry_id`, when present, resolves to a landscape.json entry.
    7. `verified: true` requires both `source.url` and `checked`. A milestone verified through an
       archive capture (`source.archive_url`) must still carry `source.url`: the capture is
       evidence about a particular page, so the page it captures has to be named.
    7a. `availability`, when present, is one of AVAILABILITY_VALUES.
    7b. `levels[*].candidates`, when present, is a list of {mark, id, chosen, why}: `mark` is one
        of the three marked-date keys, `id` resolves to some milestone (a candidate may have been
        rejected precisely because it sits at another level), `why` is non-empty, and the
        candidate marked `chosen` for a key is the one the level actually marks for that key.
    8. Every entry in `measures` has a non-empty `quote`, `scope` and `source.url`.
    9. `criteria` defines each of the three marked dates: `described`, `buildable`, `available`.
       The three mean different things and a reader has to be told which is which.

    Completeness -- that `levels` eventually covers every tier -- is deliberately NOT checked
    here: the data is built one level at a time across several commits, and each of those
    commits must still pass this validator.
    """
    errors: list[str] = []

    criteria = timeline.get("criteria") or {}
    for key in MARKED_DATE_KEYS:
        if not criteria.get(key):
            errors.append(f"timeline: criteria has no {key} definition")

    as_of = timeline.get("as_of", "")
    as_of_key: tuple[int, int, int] | None = None
    if not DATE_PATTERNS["day"].match(as_of):
        errors.append(f"timeline: as_of {as_of!r} is not a YYYY-MM-DD date")
    else:
        as_of_key = _date_key(as_of)

    tier_orders = {tier["order"] for tier in taxonomy.get("tiers", [])}
    level_pages, track_pages, tracks = page_ids(taxonomy)
    technique_ids = set(level_pages) | set(track_pages) | set(tracks)

    registry_ids: set[str] = set()
    if landscape is not None:
        for key in REGISTRY_LISTS:
            for entry in landscape.get(key, []):
                if entry.get("id"):
                    registry_ids.add(entry["id"])

    seen_ids: set[str] = set()
    milestones_by_level: dict[int, set[str]] = {}
    for m in timeline.get("milestones", []):
        mid = m.get("id", "<no id>")
        if mid in seen_ids:
            errors.append(f"timeline: duplicate milestone id: {mid}")
        seen_ids.add(mid)

        level = m.get("level")
        if level not in tier_orders:
            errors.append(f"timeline: milestone {mid} has no valid level: {level!r}")
        else:
            milestones_by_level.setdefault(level, set()).add(mid)

        date = m.get("date", "")
        precision = m.get("precision")
        pattern = DATE_PATTERNS.get(precision)
        if pattern is None:
            errors.append(f"timeline: milestone {mid} has no valid precision: {precision!r}")
        elif not pattern.match(date):
            errors.append(
                f"timeline: milestone {mid} date {date!r} does not match precision {precision!r}"
            )
        elif as_of_key is not None and _date_key(date) > as_of_key:
            errors.append(f"timeline: milestone {mid} date {date!r} is after as_of {as_of!r}")

        technique = m.get("technique")
        if technique is not None and technique not in technique_ids:
            errors.append(f"timeline: milestone {mid} technique resolves to nothing: {technique!r}")

        registry_id = m.get("registry_id")
        if registry_id is not None and registry_id not in registry_ids:
            errors.append(f"timeline: milestone {mid} registry_id resolves to nothing: {registry_id!r}")

        source = m.get("source") or {}
        if m.get("verified") and not (source.get("url") and m.get("checked")):
            errors.append(f"timeline: milestone {mid} is verified without a source url and a checked date")
        if m.get("verified") and source.get("archive_url") and not source.get("url"):
            errors.append(
                f"timeline: milestone {mid} is verified through an archive capture without naming "
                f"the original page in source.url"
            )

        availability = m.get("availability")
        if availability is not None and availability not in AVAILABILITY_VALUES:
            errors.append(
                f"timeline: milestone {mid} has an unknown availability: {availability!r} "
                f"(expected one of {', '.join(AVAILABILITY_VALUES)})"
            )

    seen_levels: set[int] = set()
    for entry in timeline.get("levels", []):
        level = entry.get("level")
        if level in seen_levels:
            errors.append(f"timeline: level {level} appears more than once in levels")
        seen_levels.add(level)
        for key in MARKED_DATE_KEYS:
            ref = entry.get(key)
            if ref is None:
                if not entry.get("note"):
                    errors.append(f"timeline: level {level} has no {key} milestone and no note explaining why")
            elif ref not in milestones_by_level.get(level, set()):
                errors.append(
                    f"timeline: level {level} {key} points at a milestone that is not at this "
                    f"level: {ref!r}"
                )

        candidates = entry.get("candidates")
        if candidates is not None:
            if not isinstance(candidates, list):
                errors.append(f"timeline: level {level} candidates is not a list")
                candidates = []
            for cand in candidates:
                cid = (cand or {}).get("id")
                mark = (cand or {}).get("mark")
                if mark not in MARKED_DATE_KEYS:
                    errors.append(
                        f"timeline: level {level} candidate {cid!r} has no valid mark: {mark!r}"
                    )
                if cid not in seen_ids:
                    errors.append(
                        f"timeline: level {level} candidate resolves to no milestone: {cid!r}"
                    )
                if not (cand or {}).get("why"):
                    errors.append(f"timeline: level {level} candidate {cid!r} has no reason")
                if cand.get("chosen") and mark in MARKED_DATE_KEYS and entry.get(mark) != cid:
                    errors.append(
                        f"timeline: level {level} candidate {cid!r} is marked chosen for {mark} "
                        f"but the level marks {entry.get(mark)!r}"
                    )

    for measure in timeline.get("measures", []):
        measure_id = measure.get("id", "<no id>")
        for field in ("quote", "scope"):
            if not measure.get(field):
                errors.append(f"timeline: measure {measure_id} has no {field}")
        if not (measure.get("source") or {}).get("url"):
            errors.append(f"timeline: measure {measure_id} has no source url")

    # Shifts: changes in the models themselves that cut across the levels. Each hangs off one
    # milestone for its date and source, so an unresolvable id would leave it undated.
    seen_shifts: set[str] = set()
    for shift in timeline.get("shifts", []):
        shift_id = shift.get("id", "<no id>")
        if shift_id in seen_shifts:
            errors.append(f"timeline: duplicate shift id: {shift_id}")
        seen_shifts.add(shift_id)
        for field in ("title", "summary"):
            if not shift.get(field):
                errors.append(f"timeline: shift {shift_id} has no {field}")
        if not shift.get("body"):
            errors.append(f"timeline: shift {shift_id} has no body")
        for ref in [shift.get("milestone"), *(shift.get("also") or [])]:
            if ref not in seen_ids:
                errors.append(f"timeline: shift {shift_id} points at no milestone: {ref!r}")
        technique = shift.get("technique")
        if technique and technique not in technique_ids:
            errors.append(f"timeline: shift {shift_id} technique resolves to nothing: {technique!r}")
        for app in shift.get("applications") or []:
            if not app.get("title") or not app.get("text"):
                errors.append(f"timeline: shift {shift_id} has an application with no title or text")
            if app.get("technique") and app["technique"] not in technique_ids:
                errors.append(f"timeline: shift {shift_id} application technique resolves to nothing: {app['technique']!r}")

    return errors


def main(argv: list[str]) -> int:
    content_dir = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / "content"
    taxonomy, landscape = load(content_dir)
    errors, report = validate(taxonomy, landscape)
    repo_root = content_dir.parent
    errors = (
        errors
        + check_mdx(repo_root, taxonomy)
        + check_runs(repo_root)
        + check_run_model_steps(repo_root, taxonomy)
        + check_teardowns(repo_root, taxonomy, landscape)
    )

    glossary_path = content_dir / "glossary.json"
    glossary_count = 0
    if glossary_path.exists():
        glossary = json.loads(glossary_path.read_text(encoding="utf-8"))
        glossary_count = len(glossary.get("terms", []))
        errors = errors + validate_glossary(glossary, taxonomy)

    timeline_path = content_dir / "timeline.json"
    timeline_count = 0
    if timeline_path.exists():
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        timeline_count = len(timeline.get("milestones", []))
        errors = errors + validate_timeline(timeline, taxonomy, landscape)

    print(f"levels {report['levels']}, techniques {report['level_pages'] + report['track_pages']} "
          f"({report['level_pages']} level pages, {report['track_pages']} track pages), "
          f"recipes {report['recipes']}, teardowns {report['teardowns']}, "
          f"relations {report['relations']}")
    by_domain = report.get("recipes_by_domain") or {}
    if by_domain:
        print("recipes by domain: " + ", ".join(f"{k} {v}" for k, v in by_domain.items()))
    reg = report["registry"]
    print(f"registry: {reg['models']} models, {reg['products']} products, {reg['tools']} tools")
    if glossary_path.exists():
        print(f"glossary: {glossary_count} terms")
    if timeline_path.exists():
        print(f"timeline: {timeline_count} milestones")
    if report["unnamed"]:
        print("techniques with no named example: " + ", ".join(report["unnamed"]))
    for err in errors:
        print("ERROR " + err)
    print("ok" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
