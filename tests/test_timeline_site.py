"""Tests for /timeline/ and the home page's timeline strip, run against a built site/dist.

Checked against the *output*, the same way tests/test_search.py and tests/test_indexes.py check
their own generated pages: Timeline.astro, TimelineStrip.astro and timeline.astro are Astro/Vite
compiles, so the honest test is to build the site and read what came out. Every test here skips
cleanly, with a message, when site/dist does not exist yet: run `npm run build` in `site/` (behind
`.local/build.lock`, per the project's build rules) first.

Nothing here hard-codes a date, milestone id or level count from content/timeline.json -- every
assertion is built by reading that file fresh and checking the built HTML reflects it, so this
test keeps passing (and keeps checking something real) after timeline-review changes the data.

Usage: python -m unittest tests.test_timeline_site -v
"""
from __future__ import annotations

import html
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "site" / "dist"
TIMELINE_HTML = DIST / "timeline" / "index.html"
HOME_HTML = DIST / "index.html"
TIMELINE_JSON = ROOT / "content" / "timeline.json"

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Keys on a `levels[]` entry that are not marked dates: the level number, its note, and the
# `candidates` list (the milestones considered for each mark, with the reason each was or was not
# chosen). Anything else on the entry is a marked date pointing at a milestone id.
NON_MARK_LEVEL_KEYS = ("level", "note", "candidates")


def _format_date(date: str, precision: str) -> str:
    """Python port of site/src/lib/timeline.ts's formatDate, kept in sync by hand: an independent
    re-implementation, not a call into the TypeScript, so this test can fail if the two drift."""
    parts = date.split("-")
    if precision == "year":
        return parts[0]
    month = MONTH_NAMES[int(parts[1]) - 1]
    if precision == "month":
        return f"{month} {parts[0]}"
    day = int(parts[2])
    return f"{month} {day}, {parts[0]}"


def _skip_if_no_dist(test_case: unittest.TestCase) -> None:
    if not DIST.is_dir():
        test_case.skipTest(f"{DIST} does not exist; run `npm run build` in site/ first (see .local/build.lock)")


def _skip_if_no_timeline_page(test_case: unittest.TestCase) -> None:
    _skip_if_no_dist(test_case)
    if not TIMELINE_HTML.is_file():
        test_case.skipTest(f"{TIMELINE_HTML} does not exist; run `npm run build` in site/ first")


class TimelinePageTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_timeline_page(self)
        self.html_raw = TIMELINE_HTML.read_text(encoding="utf-8")
        self.html_unescaped = html.unescape(self.html_raw)
        self.data = json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))
        self.milestones = self.data["milestones"]
        self.levels = self.data["levels"]
        self.by_id = {m["id"]: m for m in self.milestones}

    # -- every milestone appears exactly once as an anchor --------------------------------------

    def test_every_milestone_id_is_an_anchor_exactly_once(self) -> None:
        missing: list[str] = []
        duplicated: list[str] = []
        for m in self.milestones:
            mid = m["id"]
            count = len(re.findall(r'id="' + re.escape(mid) + r'"', self.html_raw))
            if count == 0:
                missing.append(mid)
            elif count > 1:
                duplicated.append(f"{mid} ({count}x)")
        self.assertEqual(missing, [], f"milestone ids with no anchor in the built page: {missing}")
        self.assertEqual(duplicated, [], f"milestone ids anchored more than once: {duplicated}")

    # -- every marked date per level is rendered -------------------------------------------------

    def test_every_marked_date_per_level_is_rendered(self) -> None:
        missing: list[str] = []
        checked = 0
        for entry in self.levels:
            for key, value in entry.items():
                if key in NON_MARK_LEVEL_KEYS or value is None:
                    continue
                m = self.by_id.get(value)
                if m is None:
                    continue  # scripts/validate.py separately enforces this resolves
                text = _format_date(m["date"], m["precision"])
                checked += 1
                if text not in self.html_unescaped:
                    missing.append(f"level {entry['level']} {key}={value!r} -> {text!r}")
        self.assertGreater(checked, 0, "sanity: at least one marked date should exist in the data")
        self.assertEqual(missing, [], f"marked dates not found rendered in the timeline page: {missing}")

    def test_a_missing_mark_renders_no_single_date_not_a_blank_cell(self) -> None:
        has_a_null_mark = any(
            value is None
            for entry in self.levels
            for key, value in entry.items()
            if key not in NON_MARK_LEVEL_KEYS
        )
        self.assertTrue(has_a_null_mark, "sanity: the data should have at least one null marked date to check this against")
        self.assertIn("No single date", self.html_raw)

    def test_no_negative_interval_is_ever_printed(self) -> None:
        # A reversed interval (the product came first / the later level arrived first) must show
        # as a positive number of months with words explaining the direction, never a bare
        # negative figure like "-3 mo".
        negatives = re.findall(r"-\d+\s*mo\b", self.html_unescaped)
        self.assertEqual(negatives, [], f"raw negative month figures found on the timeline page: {negatives}")

    def test_every_level_note_is_rendered_verbatim(self) -> None:
        notes = [entry["note"] for entry in self.levels if entry.get("note")]
        self.assertGreater(len(notes), 0, "sanity: the data should have at least one level note to check this against")
        missing = [n for n in notes if n not in self.html_unescaped]
        self.assertEqual(missing, [], f"level notes not found verbatim on the timeline page: {missing}")

    # -- the candidates behind each mark, and archive captures -----------------------------------

    def test_every_candidate_reason_is_rendered(self) -> None:
        # A marked date is a choice between dated candidates. The losing candidates and the
        # one-line reason each lost must reach the page, not sit unread in content/timeline.json.
        reasons = [c["why"] for entry in self.levels for c in entry.get("candidates", [])]
        self.assertGreater(len(reasons), 0, "sanity: the data should record candidates for its marks")
        missing = [r for r in reasons if r not in self.html_unescaped]
        self.assertEqual(missing, [], f"candidate reasons not found on the timeline page: {missing}")

    def test_every_archive_capture_is_linked(self) -> None:
        # Where a maker's page would not open and the site read the Internet Archive's capture of
        # it instead, the reader gets both links: the original page and the capture actually read.
        captures = [
            (m["id"], m["source"]["archive_url"])
            for m in self.milestones
            if m["source"].get("archive_url")
        ]
        self.assertGreater(len(captures), 0, "sanity: some milestone should be read through a capture")
        missing = [mid for mid, u in captures if f'href="{u}"' not in self.html_raw]
        self.assertEqual(missing, [], f"archive captures not linked on the timeline page: {missing}")

    def test_a_milestone_verified_through_a_capture_also_names_the_original_page(self) -> None:
        bad = [
            m["id"]
            for m in self.milestones
            if m.get("verified") and m["source"].get("archive_url") and not m["source"].get("url")
        ]
        self.assertEqual(bad, [], f"verified through a capture with no original url: {bad}")

    # -- every source link is https ---------------------------------------------------------------

    def test_every_source_link_on_the_page_is_https(self) -> None:
        hrefs = re.findall(r'href="(https?://[^"]+)"', self.html_raw)
        self.assertGreater(len(hrefs), 0, "sanity: the page should link out to at least one source")
        insecure = [h for h in hrefs if h.startswith("http://")]
        self.assertEqual(insecure, [], f"non-https links on the timeline page: {insecure}")

    def test_every_milestone_source_url_in_the_data_is_https(self) -> None:
        # A companion check on the data itself: if a source url in content/timeline.json were ever
        # http://, the page-level check above could not catch it landing correctly escaped.
        non_https = [m["id"] for m in self.milestones if not m["source"]["url"].startswith("https://")]
        self.assertEqual(non_https, [], f"milestones whose source url is not https: {non_https}")

    # -- measures quotations appear character for character ---------------------------------------

    def test_every_measure_quote_appears_character_for_character(self) -> None:
        measures = self.data.get("measures", [])
        self.assertGreater(len(measures), 0, "sanity: the data should carry at least one measure")
        missing = [m["id"] for m in measures if m["quote"] not in self.html_unescaped]
        self.assertEqual(missing, [], f"measure quotations not found verbatim in the timeline page: {missing}")

    def test_every_measure_scope_and_source_appear(self) -> None:
        for m in self.data.get("measures", []):
            self.assertIn(m["scope"], self.html_unescaped, f"measure {m['id']}: scope text not found on the page")
            self.assertIn(m["source"]["url"], self.html_raw, f"measure {m['id']}: source url not linked on the page")

    # -- criteria text is rendered somewhere -------------------------------------------------------

    def test_criteria_text_is_rendered(self) -> None:
        criteria = self.data.get("criteria", {})
        for key, text in criteria.items():
            self.assertIn(text, self.html_unescaped, f"criteria.{key} not found rendered on the page")

    # -- accessibility wiring -----------------------------------------------------------------------

    def test_the_chart_names_itself_and_says_where_the_text_version_is(self) -> None:
        """`role="img"` makes the chart one graphic to assistive technology, so its accessible
        name is the whole of what a screen-reader user gets from it. It has to say that the
        milestones are listed as text below, because that is where they have to go for them."""
        m = re.search(r'<div class="tl-chart"[^>]*aria-label="([^"]+)"', self.html_raw)
        self.assertIsNotNone(m, "the chart has no accessible name")
        label = m.group(1)
        self.assertIn("listed as text below", label, f"the chart's name does not point at the list: {label!r}")

    def test_the_chart_holds_no_tab_stops_of_its_own(self) -> None:
        """An audit (wave 6) found `role="img"` wrapped around 451 focusable descendants: 96
        focusable dots and their tooltip links. ARIA seals a `role="img"` subtree, so a keyboard
        user crossed 451 stops that no screen reader announced. The dots are not focusable now
        and the tooltip links are out of the tab order; every one of those links is on the
        milestone's own entry in the list below. The chart itself stays focusable because it
        scrolls sideways.
        """
        start = self.html_raw.index('<div class="tl-chart"')
        end = self.html_raw.index('id="timeline-list-heading"') if 'id="timeline-list-heading"' in self.html_raw else len(self.html_raw)
        chart = self.html_raw[start:end]
        # One stop: the scrollable chart container itself.
        self.assertEqual(chart.count('tabindex="0"'), 1, "something inside the chart is focusable again")
        self.assertNotIn('<a href', chart.split('tl-tip-links')[0][200:], "a link crept back into the chart's own markup")


class TimelineHomeStripTests(unittest.TestCase):
    def setUp(self) -> None:
        _skip_if_no_dist(self)
        if not HOME_HTML.is_file():
            self.skipTest(f"{HOME_HTML} does not exist; run `npm run build` in site/ first")
        self.html_raw = HOME_HTML.read_text(encoding="utf-8")

    def test_home_page_contains_the_timeline_strip(self) -> None:
        self.assertIn('id="timeline"', self.html_raw, "home page has no #timeline section")
        self.assertIn('class="tls"', self.html_raw, "home page does not render the compact timeline strip")

    def test_timeline_strip_sits_after_the_climb_curve_and_before_the_thesis(self) -> None:
        climb_idx = self.html_raw.find('id="climb-curve"')
        strip_idx = self.html_raw.find('id="timeline"')
        thesis_idx = self.html_raw.find('class="stack-thesis"')
        self.assertGreater(climb_idx, -1, "climb curve section not found")
        self.assertGreater(strip_idx, -1, "timeline strip section not found")
        self.assertGreater(thesis_idx, -1, "thesis line not found")
        self.assertTrue(
            climb_idx < strip_idx < thesis_idx,
            f"expected climb-curve < timeline strip < thesis, got positions {climb_idx}, {strip_idx}, {thesis_idx}",
        )

    def test_home_strip_links_to_the_full_timeline(self) -> None:
        self.assertIn('href="/gradient_ascent/timeline/"', self.html_raw)


class TimelineSearchIndexTests(unittest.TestCase):
    """A light companion to tests/test_search.py, focused on the milestone kind this task adds."""

    def setUp(self) -> None:
        _skip_if_no_dist(self)
        index_path = DIST / "search-index.json"
        if not index_path.is_file():
            self.skipTest(f"{index_path} does not exist; run `npm run build` in site/ first")
        self.docs = json.loads(index_path.read_text(encoding="utf-8"))
        self.data = json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))

    def test_every_milestone_is_indexed_as_its_own_kind_linking_into_the_timeline_page(self) -> None:
        milestone_docs = [d for d in self.docs if d.get("kind") == "milestone"]
        self.assertEqual(len(milestone_docs), len(self.data["milestones"]), "milestone doc count does not match content/timeline.json")
        for m in self.data["milestones"]:
            doc = next((d for d in milestone_docs if d["id"] == f"milestone:{m['id']}"), None)
            self.assertIsNotNone(doc, f"milestone {m['id']} missing from the search index")
            self.assertEqual(doc["url"], f"/gradient_ascent/timeline/#{m['id']}", f"milestone {m['id']} has the wrong search url")


if __name__ == "__main__":
    unittest.main()
