"""Tests for the built search index, site/dist/search-index.json (finish-search).

Checked against the *output*, the same way tests/test_indexes.py checks the generated index
pages: search-index.json.ts and search.astro are TypeScript/Astro Vite compiles, so the honest
test is to build the site and read what came out. Every test here skips cleanly, with a message,
when site/dist does not exist yet: run `npm run build` in `site/` (behind `.local/build.lock`,
per the project's build rules) first.

Usage: python -m unittest tests.test_search -v
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "site" / "dist"
BUILD_LOCK = ROOT / ".local" / "build.lock"
# Astro writes its prerender chunks here during a build and removes the directory when the build
# completes, so a dist that still has one is a half-written tree, not a site.
PRERENDER = DIST / ".prerender"
INDEX_PATH = DIST / "search-index.json"
TAXONOMY_PATH = ROOT / "content" / "taxonomy.json"
GLOSSARY_PATH = ROOT / "content" / "glossary.json"

# The size this task set out to stay well under.
MAX_INDEX_BYTES = 300 * 1024


def _skip_if_no_dist(test_case: unittest.TestCase) -> None:
    """Skip when there is no built site to read, or when one is being written right now.

    `npm run build` empties `site/dist` and writes it again, so a test run that overlaps a build,
    or that follows a build which died part way through, reads a tree with most of its pages
    missing. Two signals say the tree is not a finished site: `.local/build.lock`, which a build
    holds for its whole duration, and `dist/.prerender`, which Astro writes during a build and
    removes when it finishes. Either one means skip rather than fail about another process's
    directory. Same helper, same reasoning, as tests/test_indexes.py.
    """
    if BUILD_LOCK.exists():
        test_case.skipTest("a build holds .local/build.lock; site/dist is being rewritten")
    if not DIST.is_dir():
        test_case.skipTest(f"{DIST} does not exist; run `npm run build` in site/ first (see .local/build.lock)")
    if PRERENDER.is_dir():
        test_case.skipTest(f"{PRERENDER} is still there, so the last build did not finish; re-run `npm run build`")


def _skip_if_no_index(test_case: unittest.TestCase) -> None:
    _skip_if_no_dist(test_case)
    if not INDEX_PATH.is_file():
        test_case.skipTest(f"{INDEX_PATH} does not exist; run `npm run build` in site/ first")


def _read_dist(test_case: unittest.TestCase, path: Path) -> str:
    """Read a file out of the built site. A missing file skips if a build has started since the
    check above, and fails with the path if not; it never raises a bare FileNotFoundError."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _skip_if_no_dist(test_case)
        raise AssertionError(f"{path} is missing from the built site; run `npm run build` in site/") from None


def _assert_all_present(test_case: unittest.TestCase, missing: list, message: str) -> None:
    """Assert that nothing was missing from dist, unless a build started while we were looking."""
    if missing:
        _skip_if_no_dist(test_case)
    test_case.assertEqual(missing, [], message)


def _dist_path_for_url(href: str) -> Path | None:
    """Map a site-relative URL (with the /gradient_ascent/ base, and possibly a #fragment or
    ?query) to the dist/ file it should resolve to. Mirrors test_indexes.py's own helper."""
    if href.startswith("http://") or href.startswith("https://"):
        m = re.match(r"https?://[^/]+(/.*)?$", href)
        if not m or not m.group(1):
            return None
        href = m.group(1)
    path = href
    if path.startswith("/gradient_ascent/"):
        path = path[len("/gradient_ascent"):]
    elif path.startswith("/gradient_ascent"):
        path = path[len("/gradient_ascent"):] or "/"
    if not path.startswith("/"):
        return None
    path = path.split("#")[0].split("?")[0]
    if path.endswith(".md") or path.endswith(".txt") or path.endswith(".json"):
        return DIST / path.lstrip("/")
    if path == "/":
        return DIST / "index.html"
    return DIST / path.strip("/") / "index.html"


class SearchIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_index(self)
        self.raw = INDEX_PATH.read_bytes()
        self.docs = json.loads(self.raw.decode("utf-8"))
        self.taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
        self.glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))["terms"]

    def _technique_slugs(self) -> list[str]:
        slugs = [p["slug"] for tier in self.taxonomy["tiers"] for p in tier["pages"]]
        for track in self.taxonomy["tracks"]:
            slugs.append(track["id"])
            slugs.extend(p["slug"] for p in track.get("pages", []))
        return slugs

    def _by_kind(self, kind: str) -> list[dict]:
        return [d for d in self.docs if d.get("kind") == kind]

    # -- size --------------------------------------------------------------------------------

    def test_index_is_under_the_size_budget(self) -> None:
        self.assertLess(
            len(self.raw),
            MAX_INDEX_BYTES,
            f"search-index.json is {len(self.raw)} bytes, over the {MAX_INDEX_BYTES}-byte budget",
        )

    def test_index_is_a_non_empty_json_array(self) -> None:
        self.assertIsInstance(self.docs, list)
        self.assertGreater(len(self.docs), 0)

    # -- coverage: technique and topic pages --------------------------------------------------

    def test_every_technique_and_topic_present_exactly_once(self) -> None:
        titles_by_url = {}
        for d in self._by_kind("technique"):
            titles_by_url.setdefault(d["url"], []).append(d)
        slugs = self._technique_slugs()
        self.assertEqual(len(self._by_kind("technique")), len(slugs), "technique/topic doc count does not match the taxonomy")
        missing = [s for s in slugs if not any(d["url"].rstrip("/").endswith(f"/techniques/{s}") for d in self._by_kind("technique"))]
        self.assertEqual(missing, [], f"techniques/topics missing from the search index: {missing}")
        dupes = [url for url, ds in titles_by_url.items() if len(ds) > 1]
        self.assertEqual(dupes, [], f"technique/topic URLs listed more than once: {dupes}")

    # -- coverage: recipes ---------------------------------------------------------------------

    def test_every_recipe_present_exactly_once(self) -> None:
        recipe_slugs = [r["slug"] for r in self.taxonomy["recipes"]]
        recipe_docs = self._by_kind("recipe")
        self.assertEqual(len(recipe_docs), len(recipe_slugs), "recipe doc count does not match the taxonomy")
        missing = [s for s in recipe_slugs if not any(d["url"].rstrip("/").endswith(f"/recipes/{s}") for d in recipe_docs)]
        self.assertEqual(missing, [], f"recipes missing from the search index: {missing}")

    # -- coverage: levels ----------------------------------------------------------------------

    def test_every_level_present_exactly_once(self) -> None:
        level_docs = self._by_kind("level")
        tier_orders = [t["order"] for t in self.taxonomy["tiers"]]
        # +1 for the tracks overview page ("Topics at every level").
        self.assertEqual(len(level_docs), len(tier_orders) + 1, "level doc count does not match the taxonomy")
        for order in tier_orders:
            hit = [d for d in level_docs if d["url"].rstrip("/").endswith(f"/levels/{order}")]
            self.assertEqual(len(hit), 1, f"level {order} listed {len(hit)} times, expected exactly 1")
        tracks_hit = [d for d in level_docs if d["url"].rstrip("/").endswith("/levels/tracks")]
        self.assertEqual(len(tracks_hit), 1, "the tracks overview level listed other than exactly once")

    # -- coverage: glossary ---------------------------------------------------------------------

    def test_every_glossary_term_present_exactly_once(self) -> None:
        glossary_docs = self._by_kind("glossary")
        self.assertEqual(len(glossary_docs), len(self.glossary), "glossary doc count does not match content/glossary.json")
        doc_titles = [d["title"] for d in glossary_docs]
        missing = [t["term"] for t in self.glossary if t["term"] not in doc_titles]
        self.assertEqual(missing, [], f"glossary terms missing from the search index: {missing}")
        dupes = [t for t in doc_titles if doc_titles.count(t) > 1]
        self.assertEqual(dupes, [], f"glossary terms listed more than once: {sorted(set(dupes))}")

    # -- former names --------------------------------------------------------------------------

    def test_registry_entries_carry_a_former_name_when_the_registry_has_one(self) -> None:
        landscape = json.loads((ROOT / "content" / "landscape.json").read_text(encoding="utf-8"))
        all_entries = landscape["models"] + landscape["products"] + landscape["tools"]
        by_id = {e["id"]: e for e in all_entries}
        name_docs = {d["id"]: d for d in self._by_kind("name") if d["id"].startswith("name:")}
        checked = 0
        for entry_id, entry in by_id.items():
            formerly = entry.get("formerly")
            if not formerly:
                continue
            doc = name_docs.get(f"name:{entry_id}")
            self.assertIsNotNone(doc, f"registry entry {entry_id} missing from the search index")
            alt = doc.get("alt") or []
            former_bare = re.sub(r"\s*\([^)]*\)\s*$", "", formerly).strip()
            self.assertIn(former_bare, alt, f"{entry_id}: former name {former_bare!r} not carried as alt")
            checked += 1
        self.assertGreater(checked, 0, "sanity: the registry should have at least one formerly-named entry")

    # -- every URL resolves to a real file in dist ----------------------------------------------

    def test_every_doc_url_exists_in_dist(self) -> None:
        missing: list[str] = []
        for d in self.docs:
            for key in ("url", "secondaryUrl"):
                href = d.get(key)
                if not href:
                    continue
                target = _dist_path_for_url(href)
                if target is None or not target.is_file():
                    missing.append(f"{d['id']} {key}={href!r} -> {target}")
        _assert_all_present(self, missing, f"search doc URLs that do not resolve to a file in dist: {missing[:20]}")

    # -- the page itself -------------------------------------------------------------------------

    def test_search_page_exists_and_carries_the_noscript_fallback(self) -> None:
        html = _read_dist(self, DIST / "search" / "index.html")
        self.assertIn("search-noscript-only", html)
        self.assertIn("search-js-only", html)
        # Every glossary term should appear somewhere in the no-JS listing.
        for term in self.glossary:
            self.assertIn(term["term"], html, f"glossary term {term['term']!r} missing from the no-JS search fallback")


if __name__ == "__main__":
    unittest.main()
