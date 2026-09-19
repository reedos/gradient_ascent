"""Tests for finish-indexes' generated pages, run against a built site/dist.

These check the *output*, not site/src/lib/indexes.ts directly -- indexes.ts is a TypeScript
module Astro/Vite compiles, so the honest test of "does the failure gallery actually list every
failure mode" is to build the site and read what came out, the same way a reader would. Every
test in this module skips cleanly, with a message, when site/dist does not exist yet: run
`npm run build` in `site/` (behind `.local/build.lock`, per the project's build rules) first.

Usage: python -m unittest tests.test_indexes -v
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
CONTENT_TECHNIQUES = ROOT / "site" / "src" / "content" / "techniques"
CONTENT_RECIPES = ROOT / "site" / "src" / "content" / "recipes"
GLOSSARY_PATH = ROOT / "content" / "glossary.json"
TAXONOMY_PATH = ROOT / "content" / "taxonomy.json"

# A rough, independent count of failure modes directly over the MDX source: every mode object in
# a `<FailureModes modes={[...]}>` array carries exactly one `notice:` field, written as an
# object-literal key at the start of its (indented) line -- `^\s*notice:\s*['"]`. Anchoring to
# line start is what keeps this an independent cross-check rather than a copy of indexes.ts's own
# JS-literal parser: a plain `\bnotice:\s*['"]` also matches running prose that happens to use the
# word before a quotation, such as orchestrator-workers.mdx's "carries a maintenance notice:
# "AutoGen is now in maintenance mode..."" -- one false positive this anchor rules out.
NOTICE_KEY_RE = re.compile(r"^\s*notice:\s*['\"]", re.MULTILINE)


def _skip_if_no_dist(test_case: unittest.TestCase) -> None:
    """Skip when there is no built site to read, or when one is being written right now.

    `npm run build` empties `site/dist` and writes it again, so a test run that overlaps a build,
    or that follows a build which died part way through, reads a tree with most of its pages
    missing and reports twenty failures about pages nobody touched. Two signals say the tree is
    not a finished site: `.local/build.lock`, which a build holds for its whole duration (several
    agents share this repository), and `dist/.prerender`, which Astro writes during a build and
    removes when it finishes. Either one means skip rather than fail. Without this, these tests
    fail once and pass on a re-run with nothing changed, which is worse than not running them.
    """
    if BUILD_LOCK.exists():
        test_case.skipTest("a build holds .local/build.lock; site/dist is being rewritten")
    if not DIST.is_dir():
        test_case.skipTest(f"{DIST} does not exist; run `npm run build` in site/ first (see .local/build.lock)")
    if PRERENDER.is_dir():
        test_case.skipTest(f"{PRERENDER} is still there, so the last build did not finish; re-run `npm run build`")


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
    """Map a site-relative or absolute URL to the dist/ file it should resolve to, or None for
    an external link. Strips the configured base path (astro.config.mjs: '/gradient_ascent/')."""
    if href.startswith("http://") or href.startswith("https://"):
        # An absolute URL (llms.txt uses these): keep only the path, and only if it is this site.
        m = re.match(r"https?://[^/]+(/.*)?$", href)
        if not m or not m.group(1):
            return None
        href = m.group(1)
    path = href
    if path.startswith("/gradient_ascent/"):
        path = path[len("/gradient_ascent") :]
    elif path.startswith("/gradient_ascent"):
        path = path[len("/gradient_ascent") :] or "/"
    if not path.startswith("/"):
        return None
    path = path.split("#")[0].split("?")[0]
    if path.endswith(".md") or path.endswith(".txt"):
        return DIST / path.lstrip("/")
    if path == "/":
        return DIST / "index.html"
    return DIST / path.strip("/") / "index.html"


class FailureGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_dist(self)

    def test_gallery_lists_at_least_as_many_failure_modes_as_the_mdx_source(self) -> None:
        direct_count = 0
        for mdx in CONTENT_TECHNIQUES.glob("*.mdx"):
            text = mdx.read_text(encoding="utf-8")
            if "<FailureModes" in text:
                direct_count += len(NOTICE_KEY_RE.findall(text))
        self.assertGreater(direct_count, 0, "sanity: the MDX source itself should have failure modes to count")

        html = _read_dist(self, DIST / "failures" / "index.html")
        gallery_count = len(re.findall(r'class="failure-mode"', html))
        self.assertGreaterEqual(
            gallery_count,
            direct_count,
            f"failure gallery shows {gallery_count} failure modes but the MDX source has at least {direct_count}",
        )

    def test_gallery_page_exists_and_is_not_empty(self) -> None:
        html = _read_dist(self, DIST / "failures" / "index.html")
        self.assertIn("Failure gallery", html)
        self.assertIn("How to notice it", html)
        self.assertIn("How to test for it", html)


class GlossaryPageTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_dist(self)
        self.glossary = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))["terms"]
        self.html = _read_dist(self, DIST / "glossary" / "index.html")

    def test_every_glossary_term_is_present_in_the_page(self) -> None:
        missing = [t["term"] for t in self.glossary if t["term"] not in self.html]
        self.assertEqual(missing, [], f"terms missing from the rendered glossary page: {missing}")

    def test_every_glossary_term_links_to_a_page_that_exists_in_dist(self) -> None:
        """A term's `page` is a technique or topic slug, or a thread id for the few terms that
        name two techniques at once (scripts/validate.py allows both). Either way the page it
        points at has to exist in the built site."""
        missing_targets: list[str] = []
        for entry in self.glossary:
            technique = DIST / "techniques" / entry["page"] / "index.html"
            thread = DIST / "threads" / entry["page"] / "index.html"
            if not technique.is_file() and not thread.is_file():
                missing_targets.append(f"{entry['term']} -> {entry['page']}")
        _assert_all_present(self, missing_targets, f"glossary link targets not found in dist: {missing_targets}")

    def test_glossary_count_reported_on_page_matches_the_data_file(self) -> None:
        self.assertIn(f"{len(self.glossary)} terms", self.html)


class LlmsTxtTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_dist(self)
        self.text = _read_dist(self, DIST / "llms.txt")
        self.taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))

    def _technique_slugs(self) -> list[str]:
        slugs = [p["slug"] for tier in self.taxonomy["tiers"] for p in tier["pages"]]
        for track in self.taxonomy["tracks"]:
            slugs.append(track["id"])
            slugs.extend(p["slug"] for p in track.get("pages", []))
        return slugs

    def test_every_technique_and_topic_listed_exactly_once(self) -> None:
        for slug in self._technique_slugs():
            hits = len(re.findall(rf"\(https?://[^)]*?/techniques/{re.escape(slug)}/\)", self.text))
            self.assertEqual(hits, 1, f"technique/topic {slug!r} listed {hits} times in llms.txt, expected exactly 1")

    def test_every_recipe_listed_exactly_once(self) -> None:
        for recipe in self.taxonomy["recipes"]:
            slug = recipe["slug"]
            hits = len(re.findall(rf"\(https?://[^)]*?/recipes/{re.escape(slug)}/\)", self.text))
            self.assertEqual(hits, 1, f"recipe {slug!r} listed {hits} times in llms.txt, expected exactly 1")

    def test_every_level_listed_exactly_once(self) -> None:
        for tier in self.taxonomy["tiers"]:
            order = tier["order"]
            hits = len(re.findall(rf"\(https?://[^)]*?/levels/{order}/\)", self.text))
            self.assertEqual(hits, 1, f"level {order} listed {hits} times in llms.txt, expected exactly 1")

    def test_every_link_target_exists_in_dist(self) -> None:
        urls = re.findall(r"\]\((https?://[^)]+)\)", self.text)
        self.assertGreater(len(urls), 20, "sanity: llms.txt should carry a good number of links")
        missing = []
        for href in urls:
            target = _dist_path_for_url(href)
            if target is None or not target.is_file():
                missing.append((href, str(target)))
        _assert_all_present(self, missing, f"llms.txt links that do not resolve to a file in dist: {missing}")


class MarkdownEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_dist(self)
        self.taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))

    def _assert_clean_markdown(self, path: Path) -> None:
        text = _read_dist(self, path)
        self.assertTrue(text.strip(), f"{path} is empty")
        # Strip fenced and inline code before checking for a stray HTML/JSX tag, the same
        # exemption site/src/lib/indexes.ts's own flattener applies before it throws.
        without_code = re.sub(r"```[\s\S]*?```", "", text)
        without_code = re.sub(r"`[^`]*`", "", without_code)
        bad = re.search(r"<[a-zA-Z/][^\n]*", without_code)
        self.assertIsNone(bad, f"{path} contains what looks like an HTML/JSX tag outside a code fence: {bad and bad.group(0)[:120]!r}")

    def test_every_technique_md_endpoint_exists_and_is_clean(self) -> None:
        slugs = [p["slug"] for tier in self.taxonomy["tiers"] for p in tier["pages"]]
        for track in self.taxonomy["tracks"]:
            slugs.append(track["id"])
            slugs.extend(p["slug"] for p in track.get("pages", []))
        for slug in slugs:
            self._assert_clean_markdown(DIST / "techniques" / f"{slug}.md")

    def test_every_recipe_md_endpoint_exists_and_is_clean(self) -> None:
        for recipe in self.taxonomy["recipes"]:
            self._assert_clean_markdown(DIST / "recipes" / f"{recipe['slug']}.md")

    def test_every_level_md_endpoint_exists_and_is_clean(self) -> None:
        for tier in self.taxonomy["tiers"]:
            self._assert_clean_markdown(DIST / "levels" / f"{tier['order']}.md")
        self._assert_clean_markdown(DIST / "levels" / "tracks.md")

    def test_a_technique_md_endpoint_carries_its_sources_and_reviewed_date(self) -> None:
        text = _read_dist(self, DIST / "techniques" / "rag.md")
        self.assertIn("## Sources", text)
        self.assertIn("Last reviewed", text)
        self.assertIn("# Retrieval-augmented generation (RAG)", text)


if __name__ == "__main__":
    unittest.main()
