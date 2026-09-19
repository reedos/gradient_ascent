"""Tests for scripts/review_queue.py, the review-freshness report.

No network, no fixtures outside the repository. Most tests drive build_queue and parse_date
directly with synthetic records, the pure parts that decide age, expiry and state; a handful read
the real site/src/content/ tree to check the file-reading layer finds something there, skipped
when that directory does not exist.

Usage: python -m unittest tests.test_review_queue -v
"""
from __future__ import annotations

import datetime as dt
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import review_queue  # noqa: E402


def record(path: str, collection: str, reviewed: str | None, slug: str = "") -> dict:
    return {"path": path, "collection": collection, "slug": slug or path, "reviewed": reviewed}


class ParseDateTests(unittest.TestCase):
    def test_a_real_iso_date_parses(self) -> None:
        self.assertEqual(review_queue.parse_date("2026-09-18"), dt.date(2026, 9, 18))

    def test_none_is_not_a_date(self) -> None:
        self.assertIsNone(review_queue.parse_date(None))

    def test_an_empty_string_is_not_a_date(self) -> None:
        self.assertIsNone(review_queue.parse_date(""))

    def test_a_non_date_string_does_not_raise(self) -> None:
        self.assertIsNone(review_queue.parse_date("not-a-date"))

    def test_a_month_only_value_is_not_a_full_date(self) -> None:
        self.assertIsNone(review_queue.parse_date("2026-09"))

    def test_a_shape_that_matches_the_pattern_but_is_not_a_real_calendar_date(self) -> None:
        # 2026-13-40 matches \d{4}-\d{2}-\d{2} but is not a month or day that exists.
        self.assertIsNone(review_queue.parse_date("2026-13-40"))


class AgeAndFlagTests(unittest.TestCase):
    """The core 90-day rule, matched against site/src/components/page/Reviewed.astro's own
    `const stale = ageDays > 90;`: exactly at the threshold is not yet stale, one day past is."""

    def setUp(self) -> None:
        self.today = dt.date(2026, 9, 19)

    def test_a_page_exactly_at_the_threshold_is_not_flagged(self) -> None:
        reviewed = (self.today - dt.timedelta(days=90)).isoformat()
        rows, skipped = review_queue.build_queue([record("a.mdx", "techniques", reviewed)], self.today, days=90)
        self.assertEqual(skipped, 0)
        self.assertEqual(rows[0]["age_days"], 90)
        self.assertEqual(rows[0]["state"], "ok")
        self.assertFalse(rows[0]["flagged"])

    def test_a_page_one_day_past_the_threshold_is_flagged(self) -> None:
        reviewed = (self.today - dt.timedelta(days=91)).isoformat()
        rows, _ = review_queue.build_queue([record("a.mdx", "techniques", reviewed)], self.today, days=90)
        self.assertEqual(rows[0]["age_days"], 91)
        self.assertEqual(rows[0]["state"], "stale")
        self.assertTrue(rows[0]["flagged"])

    def test_a_freshly_reviewed_page_is_not_flagged(self) -> None:
        reviewed = self.today.isoformat()
        rows, _ = review_queue.build_queue([record("a.mdx", "techniques", reviewed)], self.today, days=90)
        self.assertEqual(rows[0]["age_days"], 0)
        self.assertEqual(rows[0]["state"], "ok")
        self.assertFalse(rows[0]["flagged"])

    def test_a_different_days_threshold_changes_where_the_line_falls(self) -> None:
        reviewed = (self.today - dt.timedelta(days=45)).isoformat()
        rows, _ = review_queue.build_queue([record("a.mdx", "techniques", reviewed)], self.today, days=30)
        self.assertEqual(rows[0]["state"], "stale")
        rows, _ = review_queue.build_queue([record("a.mdx", "techniques", reviewed)], self.today, days=60)
        self.assertEqual(rows[0]["state"], "ok")

    def test_empty_input_yields_an_empty_queue_and_no_skips(self) -> None:
        rows, skipped = review_queue.build_queue([], self.today)
        self.assertEqual(rows, [])
        self.assertEqual(skipped, 0)


class OrderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today = dt.date(2026, 9, 19)

    def test_rows_come_back_oldest_reviewed_date_first(self) -> None:
        records = [
            record("b.mdx", "techniques", "2026-08-01"),
            record("a.mdx", "techniques", "2026-01-01"),
            record("c.mdx", "techniques", "2026-09-01"),
        ]
        rows, _ = review_queue.build_queue(records, self.today)
        self.assertEqual([r["path"] for r in rows], ["a.mdx", "b.mdx", "c.mdx"])

    def test_a_tie_on_reviewed_date_breaks_on_path_so_the_order_is_stable(self) -> None:
        records = [
            record("z.mdx", "techniques", "2026-01-01"),
            record("m.mdx", "techniques", "2026-01-01"),
            record("a.mdx", "techniques", "2026-01-01"),
        ]
        rows, _ = review_queue.build_queue(records, self.today)
        self.assertEqual([r["path"] for r in rows], ["a.mdx", "m.mdx", "z.mdx"])


class TeardownExpiryTests(unittest.TestCase):
    """A teardown is judged by reviewed + expires_days, not the 90-day rule, and the row says
    which of the two states applies: expiring (close, not yet past) or expired (already past)."""

    def setUp(self) -> None:
        self.today = dt.date(2026, 9, 19)

    def test_a_teardown_far_from_its_expiry_is_ok(self) -> None:
        reviewed = self.today.isoformat()  # expires in 180 days by default: nowhere near due
        rows, _ = review_queue.build_queue(
            [record("t.mdx", "teardowns", reviewed)], self.today, teardown_expires_days=180, expiry_warning_days=14
        )
        self.assertEqual(rows[0]["rule"], "expiry")
        self.assertEqual(rows[0]["state"], "ok")
        self.assertFalse(rows[0]["flagged"])

    def test_a_teardown_inside_the_warning_window_is_expiring_not_yet_expired(self) -> None:
        # expires_days=10, warning=14: reviewed 5 days ago means 5 days left, inside the window.
        reviewed = (self.today - dt.timedelta(days=5)).isoformat()
        rows, _ = review_queue.build_queue(
            [record("t.mdx", "teardowns", reviewed)], self.today, teardown_expires_days=10, expiry_warning_days=14
        )
        self.assertEqual(rows[0]["state"], "expiring")
        self.assertTrue(rows[0]["flagged"])
        self.assertEqual(rows[0]["days_to_expiry"], 5)

    def test_a_teardown_past_its_expiry_is_expired(self) -> None:
        reviewed = (self.today - dt.timedelta(days=200)).isoformat()
        rows, _ = review_queue.build_queue(
            [record("t.mdx", "teardowns", reviewed)], self.today, teardown_expires_days=180, expiry_warning_days=14
        )
        self.assertEqual(rows[0]["state"], "expired")
        self.assertTrue(rows[0]["flagged"])
        self.assertLess(rows[0]["days_to_expiry"], 0)

    def test_the_ninety_day_sentence_does_not_apply_to_a_teardown(self) -> None:
        """Changing --days must never move a teardown's row, and its note must never talk about
        a day limit the way a technique or recipe row's note does."""
        reviewed = self.today.isoformat()
        rows_30, _ = review_queue.build_queue(
            [record("t.mdx", "teardowns", reviewed)], self.today, days=30, teardown_expires_days=180
        )
        rows_900, _ = review_queue.build_queue(
            [record("t.mdx", "teardowns", reviewed)], self.today, days=900, teardown_expires_days=180
        )
        self.assertEqual(rows_30[0]["state"], rows_900[0]["state"])
        self.assertEqual(rows_30[0]["note"], rows_900[0]["note"])
        self.assertNotIn("day limit", rows_30[0]["note"])

    def test_a_non_teardown_row_is_judged_by_the_review_rule_not_expiry(self) -> None:
        reviewed = (self.today - dt.timedelta(days=200)).isoformat()
        rows, _ = review_queue.build_queue([record("r.mdx", "recipes", reviewed)], self.today)
        self.assertEqual(rows[0]["rule"], "review")
        self.assertIsNone(rows[0]["expiry_date"])


class SkippedRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today = dt.date(2026, 9, 19)

    def test_a_missing_reviewed_value_is_skipped_not_crashed(self) -> None:
        rows, skipped = review_queue.build_queue([record("a.mdx", "techniques", None)], self.today)
        self.assertEqual(rows, [])
        self.assertEqual(skipped, 1)

    def test_a_malformed_reviewed_value_is_skipped_not_crashed(self) -> None:
        rows, skipped = review_queue.build_queue([record("a.mdx", "techniques", "next Tuesday")], self.today)
        self.assertEqual(rows, [])
        self.assertEqual(skipped, 1)

    def test_a_mix_of_good_and_bad_records_keeps_only_the_good_ones(self) -> None:
        records = [
            record("a.mdx", "techniques", "2026-01-01"),
            record("b.mdx", "techniques", None),
            record("c.mdx", "techniques", "garbage"),
            record("d.mdx", "techniques", "2026-02-01"),
        ]
        rows, skipped = review_queue.build_queue(records, self.today)
        self.assertEqual([r["path"] for r in rows], ["a.mdx", "d.mdx"])
        self.assertEqual(skipped, 2)


class FormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today = dt.date(2026, 9, 19)

    def test_format_table_on_no_rows_says_so_rather_than_printing_an_empty_header(self) -> None:
        self.assertEqual(review_queue.format_table([]), "(nothing to show)")

    def test_format_table_includes_every_row_path(self) -> None:
        rows, _ = review_queue.build_queue(
            [record("a.mdx", "techniques", "2026-01-01"), record("b.mdx", "recipes", "2026-02-01")], self.today
        )
        table = review_queue.format_table(rows)
        self.assertIn("a.mdx", table)
        self.assertIn("b.mdx", table)

    def test_format_summary_reports_the_oldest_reviewed_date(self) -> None:
        rows, skipped = review_queue.build_queue(
            [record("a.mdx", "techniques", "2026-03-01"), record("b.mdx", "recipes", "2026-01-01")], self.today
        )
        summary = review_queue.format_summary(rows, skipped, 90)
        self.assertIn("2026-01-01", summary)
        self.assertIn("2 page(s)", summary)

    def test_format_summary_on_an_empty_queue_does_not_crash(self) -> None:
        summary = review_queue.format_summary([], 3, 90)
        self.assertIn("0 page(s)", summary)
        self.assertIn("3 skipped", summary)


class CliTests(unittest.TestCase):
    """--today pins the date so a run is reproducible; --stale-only, --json and --fail-on-stale
    are exercised through main() with a content directory this test controls, never the real one,
    so the assertions do not depend on what happens to be in site/src/content/ today."""

    def setUp(self) -> None:
        import shutil
        import tempfile

        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        content_dir = self.tmp / "content"
        (content_dir / "techniques").mkdir(parents=True)
        (content_dir / "teardowns").mkdir(parents=True)
        (content_dir / "techniques" / "fresh.mdx").write_text(
            "---\nslug: fresh\nreviewed: 2026-09-19\n---\nbody\n", encoding="utf-8"
        )
        (content_dir / "techniques" / "old.mdx").write_text(
            "---\nslug: old\nreviewed: 2020-01-01\n---\nbody\n", encoding="utf-8"
        )
        (content_dir / "techniques" / "no-date.mdx").write_text(
            "---\nslug: no-date\n---\nbody\n", encoding="utf-8"
        )
        (content_dir / "teardowns" / "gone.mdx").write_text(
            "---\nslug: gone\nreviewed: 2020-01-01\n---\nbody\n", encoding="utf-8"
        )
        self.content_dir = content_dir
        self.taxonomy_path = self.tmp / "taxonomy.json"
        self.taxonomy_path.write_text('{"teardowns": {"expires_days": 180}}', encoding="utf-8")

        self.orig_root = review_queue.ROOT
        self.orig_content_dir = review_queue.CONTENT_DIR
        self.orig_taxonomy_path = review_queue.TAXONOMY_PATH
        review_queue.ROOT = self.tmp
        review_queue.CONTENT_DIR = self.content_dir
        review_queue.TAXONOMY_PATH = self.taxonomy_path
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        review_queue.ROOT = self.orig_root
        review_queue.CONTENT_DIR = self.orig_content_dir
        review_queue.TAXONOMY_PATH = self.orig_taxonomy_path

    def _run(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = review_queue.main(argv)
        return code, buf.getvalue()

    def test_today_makes_two_runs_produce_identical_output(self) -> None:
        code1, out1 = self._run(["--today", "2026-09-19"])
        code2, out2 = self._run(["--today", "2026-09-19"])
        self.assertEqual(code1, 0)
        self.assertEqual(out1, out2)

    def test_an_invalid_today_value_is_reported_not_crashed(self) -> None:
        code, _ = self._run(["--today", "not-a-date"])
        self.assertEqual(code, 2)

    def test_stale_only_omits_the_fresh_page(self) -> None:
        _, out = self._run(["--today", "2026-09-19", "--stale-only"])
        self.assertIn("old.mdx", out)
        self.assertNotIn("fresh.mdx", out)

    def test_stale_only_still_says_how_many_pages_were_checked(self) -> None:
        """The summary counts the whole queue, not the filtered view. Reporting only what it
        printed made an unfiltered "0 page(s)" indistinguishable from a run that read nothing."""
        _, out = self._run(["--today", "2026-09-19", "--stale-only"])
        self.assertIn("3 page(s) checked", out)  # fresh, old, gone; no-date is skipped
        self.assertIn("2 flagged", out)  # old.mdx is stale, gone.mdx expired
        self.assertIn("1 skipped", out)
        self.assertNotIn("fresh.mdx", out)

    def test_json_output_parses_and_carries_the_skip_count(self) -> None:
        import json

        _, out = self._run(["--today", "2026-09-19", "--json"])
        data = json.loads(out)
        self.assertEqual(data["skipped"], 1)  # no-date.mdx
        paths = {row["path"] for row in data["rows"]}
        self.assertIn("content/techniques/old.mdx", paths)
        self.assertIn("content/teardowns/gone.mdx", paths)

    def test_fail_on_stale_exits_1_when_something_is_flagged(self) -> None:
        code, _ = self._run(["--today", "2026-09-19", "--fail-on-stale"])
        self.assertEqual(code, 1)

    def test_fail_on_stale_exits_0_when_only_fresh_pages_are_present(self) -> None:
        # Point at a content dir with only the fresh page, so nothing is flagged.
        only_fresh = self.tmp / "content_fresh_only" / "techniques"
        only_fresh.mkdir(parents=True)
        (only_fresh / "fresh.mdx").write_text(
            "---\nslug: fresh\nreviewed: 2026-09-19\n---\nbody\n", encoding="utf-8"
        )
        review_queue.CONTENT_DIR = only_fresh.parent
        code, _ = self._run(["--today", "2026-09-19", "--fail-on-stale"])
        self.assertEqual(code, 0)

    def test_default_exit_is_zero_even_with_flagged_rows(self) -> None:
        code, _ = self._run(["--today", "2026-09-19"])
        self.assertEqual(code, 0)


class RealContentSmokeTest(unittest.TestCase):
    """A light check against the repository's actual site/src/content/, skipped cleanly if that
    directory is not there, the same way tests/test_timeline_site.py skips when site/dist is not
    built yet."""

    def setUp(self) -> None:
        if not review_queue.CONTENT_DIR.is_dir():
            self.skipTest(f"{review_queue.CONTENT_DIR} does not exist")

    def test_discovery_finds_at_least_one_page_with_a_reviewed_date(self) -> None:
        records = review_queue.discover_records()
        self.assertGreater(len(records), 0)
        today = dt.date.today()
        rows, _skipped = review_queue.build_queue(records, today)
        self.assertGreater(len(rows), 0)

    def test_every_discovered_path_is_repository_relative(self) -> None:
        for rec in review_queue.discover_records():
            self.assertFalse(Path(rec["path"]).is_absolute(), rec["path"])
            self.assertNotIn("\\", rec["path"], rec["path"])

    def test_running_the_script_over_real_content_exits_cleanly(self) -> None:
        code = review_queue.main(["--today", "2026-09-19"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
