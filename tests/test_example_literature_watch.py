"""End-to-end tests for the literature-watch example, one half at a time.

The watch half (level 0, no model): what counts as new, what a re-listed preprint does, what a
source that returns nothing does, and what happens to a record that is retitled between versions.
The read half (level 1, one call per item): a valid reply is accepted first time, an invalid one
costs exactly one retry, and a record whose summary never validates is reported rather than
dropped.

The rule that holds the join together is attacked directly: the citation is built by code from
the source record, so a model that writes its own link, or a plausible wrong author and year,
changes nothing about the citation the digest prints.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.literature_watch.run import (  # noqa: E402
    LEVEL,
    SAMPLE_INPUT,
    SAMPLE_SEEN,
    SOURCES,
    Record,
    _cite,
    run,
    title_key,
)

# The two replies the sample week asks for, in the order the watch hands records over: the
# journal source is read before the preprint source, because the watch walks its sources by name.
VALID = {
    "what_is_new": "Matches 2,800 anonymized walking trips against a modeled shade map at the hour each trip was taken.",
    "why_it_matters": "It puts a number on how far people will walk out of their way for shade, and the temperature at which they stop.",
    "read_if": "You are deciding where shade is worth building along a walking route.",
}
SECOND = {
    "what_is_new": "Two years of operating a 120-unit street-level logger network, including the failures.",
    "why_it_matters": "The enclosure revision and the field calibration procedure are both published.",
    "read_if": "You are running or planning a low-cost sensor network outdoors.",
}


def tracer() -> Tracer:
    return Tracer(example="literature_watch", level=LEVEL, model_id="stub-1")


def replies(*records: dict) -> StubModel:
    return StubModel([StubResponse(text=json.dumps(r)) for r in records])


class TheWatchHalfTests(unittest.TestCase):
    """Level 0. None of these call a model at all, which is the point: what counts as new is
    decided by code before anything is read."""

    def test_the_sample_week_finds_exactly_the_two_genuinely_new_records(self) -> None:
        digest = run(SAMPLE_INPUT, replies(VALID, SECOND), tracer())
        self.assertEqual([it.record.id for it in digest.items], ["j-8822", "pp-2304"])

    def test_a_record_dated_before_the_last_run_is_not_new(self) -> None:
        digest = run(SAMPLE_INPUT, replies(VALID, SECOND), tracer())
        self.assertNotIn("pp-2260", [it.record.id for it in digest.items])
        feed = next(s for s in digest.sources if s.source == "preprint-feed")
        self.assertEqual((feed.returned, feed.fresh, feed.new), (3, 1, 1))

    def test_the_journal_version_of_a_reported_preprint_is_not_reported_twice(self) -> None:
        """j-8814 is the peer-reviewed version of a preprint last week's digest already carried.
        A different id, a different date, a different capitalization, the same work."""
        digest = run(SAMPLE_INPUT, replies(VALID, SECOND), tracer())
        self.assertNotIn("j-8814", [it.record.id for it in digest.items])
        self.assertEqual(len(digest.already_reported), 1)
        journal = next(s for s in digest.sources if s.source == "journal-contents")
        self.assertEqual((journal.returned, journal.fresh, journal.new), (2, 2, 1))

    def test_a_source_that_returns_nothing_is_reported_as_silent(self) -> None:
        """A source whose feed broke returns an empty list, which looks exactly like a quiet
        week to anything that only prints items. The digest says which it was."""
        digest = run(SAMPLE_INPUT, replies(VALID, SECOND), tracer())
        quiet = next(s for s in digest.sources if s.source == "city-open-data-notices")
        self.assertTrue(quiet.silent)
        self.assertIn("returned nothing at all", digest.text)

    def test_a_retitled_version_comes_through_again_as_new(self) -> None:
        """The weakness of comparing titles, stated as a test rather than left for a reader to
        discover: change the title and the same work is new again. Nothing in code catches this,
        and the recipe page says so under the watch half's failure modes."""
        retitled = Record(
            id="j-9001",
            title="Nighttime cooling and street tree canopy across three mid-sized cities",
            authors="Halloran, D. and Vetsch, R.",
            venue="Journal of Urban Microclimate 14(4)",
            date="2026-09-18",
            url="https://example.org/journals/jum/14/4/9001",
            abstract="The same three-city study, retitled for the print issue.",
        )
        digest = run(
            SAMPLE_INPUT,
            replies(VALID),
            tracer(),
            sources={"journal-contents": (retitled,)},
        )
        self.assertEqual([it.record.id for it in digest.items], ["j-9001"])
        self.assertEqual(digest.already_reported, ())

    def test_a_week_with_nothing_new_calls_no_model_at_all(self) -> None:
        model = StubModel([])  # any call at all raises IndexError
        digest = run("2026-09-30", model, tracer())
        self.assertEqual(digest.items, ())
        self.assertEqual(sum(s.new for s in digest.sources), 0)

    def test_the_history_grows_by_the_titles_actually_reported(self) -> None:
        digest = run(SAMPLE_INPUT, replies(VALID, SECOND), tracer())
        self.assertEqual(len(digest.seen_after), len(SAMPLE_SEEN) + 2)
        for it in digest.items:
            self.assertIn(title_key(it.record.title), digest.seen_after)

    def test_title_key_ignores_case_and_punctuation(self) -> None:
        self.assertEqual(
            title_key("Street Tree Canopy and Nighttime Cooling in Three Mid-Sized Cities"),
            title_key("street tree canopy and nighttime cooling in three mid sized cities"),
        )


class TheReadHalfTests(unittest.TestCase):
    """Level 1. One call per new record, everything it needs in the call."""

    def test_one_model_call_per_new_record_and_no_more(self) -> None:
        model = replies(VALID, SECOND)
        digest = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len(digest.items), 2)
        with self.assertRaises(IndexError):
            model.complete([])

    def test_every_step_is_decided_by_code(self) -> None:
        """Level 1: the code decided that every call would happen and what came next. No step
        on this path is model-decided, and the join does not change that."""
        t = tracer()
        run(SAMPLE_INPUT, replies(VALID, SECOND), t)
        self.assertEqual(t.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" for s in t.steps), [s.title for s in t.steps])
        self.assertEqual(sum(1 for s in t.steps if s.kind == "model"), 2)

    def test_an_invalid_reply_costs_exactly_one_retry(self) -> None:
        model = StubModel(
            [
                StubResponse(text="Here you go: {not json"),
                StubResponse(text=json.dumps(VALID)),
                StubResponse(text=json.dumps(SECOND)),
            ]
        )
        digest = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len(digest.items), 2)
        self.assertEqual(digest.failed, ())

    def test_a_record_that_never_validates_is_reported_not_dropped(self) -> None:
        model = StubModel(
            [
                StubResponse(text="{}"),
                StubResponse(text=json.dumps({"what_is_new": "x"})),
                StubResponse(text=json.dumps(SECOND)),
            ]
        )
        digest = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(digest.failed, ("j-8822",))
        self.assertEqual([it.record.id for it in digest.items], ["pp-2304"])
        self.assertIn("Could not summarize: j-8822", digest.text)

    def test_an_empty_field_does_not_pass_validation(self) -> None:
        model = StubModel(
            [
                StubResponse(text=json.dumps({**VALID, "read_if": "   "})),
                StubResponse(text=json.dumps(VALID)),
                StubResponse(text=json.dumps(SECOND)),
            ]
        )
        digest = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len(digest.items), 2)


class TheCitationRuleTests(unittest.TestCase):
    """The seam. Whatever the model writes, the citation comes from the record."""

    def test_the_citation_is_built_from_the_record(self) -> None:
        digest = run(SAMPLE_INPUT, replies(VALID, SECOND), tracer())
        for it in digest.items:
            self.assertEqual(it.citation, _cite(it.record))
            self.assertIn(it.record.url, it.citation)
            self.assertIn(it.record.authors, it.citation)
            self.assertIn(it.record.date[:4], it.citation)

    def test_a_model_that_writes_its_own_link_does_not_change_the_citation(self) -> None:
        invented = {
            **VALID,
            "why_it_matters": "See the full text at https://example.org/not-this-paper for the tables.",
        }
        digest = run(SAMPLE_INPUT, StubModel([StubResponse(text=json.dumps(invented))]), tracer(), sources={"preprint-feed": (SOURCES["preprint-feed"][1],)})
        item = digest.items[0]
        self.assertEqual(item.citation, _cite(item.record))
        self.assertNotIn("not-this-paper", item.citation)
        self.assertEqual(item.flagged, ("why_it_matters",))
        self.assertIn("the model wrote a link", digest.text)

    def test_a_model_that_writes_a_wrong_author_and_year_changes_nothing(self) -> None:
        """The schema has no author or year field, so a model that puts one in its prose is
        writing prose, not a citation. The line under the title is still the record's."""
        wrong = {**VALID, "what_is_new": "Builds on Okonkwo and Reyes (2019), who found the opposite."}
        digest = run(SAMPLE_INPUT, StubModel([StubResponse(text=json.dumps(wrong))]), tracer(), sources={"preprint-feed": (SOURCES["preprint-feed"][1],)})
        item = digest.items[0]
        self.assertIn("Ferrante, N., Okoye, B. and Lindqvist, S. (2026).", item.citation)
        self.assertNotIn("Okonkwo", item.citation)
        # Nothing in code catches a wrong reference inside prose. The page says so.
        self.assertEqual(item.flagged, ())

    def test_the_schema_has_no_citation_field(self) -> None:
        from examples.literature_watch.run import SCHEMA, SUMMARY_FIELDS

        self.assertEqual(tuple(SCHEMA["properties"]), SUMMARY_FIELDS)
        for forbidden in ("citation", "url", "link", "authors", "year", "source"):
            self.assertNotIn(forbidden, SCHEMA["properties"])


class PageFiguresTests(unittest.TestCase):
    """The recipe page and its run diagram quote this run's numbers, so they are pinned here."""

    def test_the_sample_run_reports_two_items_from_four_records_across_three_sources(self) -> None:
        digest = run(SAMPLE_INPUT, replies(VALID, SECOND), tracer())
        self.assertEqual(len(digest.sources), 3)
        self.assertEqual(sum(s.returned for s in digest.sources), 5)
        self.assertEqual(len(digest.items), 2)
        self.assertEqual(len(digest.already_reported), 1)
        self.assertEqual(sum(1 for s in digest.sources if s.silent), 1)

    def test_the_example_declares_level_one(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))


if __name__ == "__main__":
    unittest.main()
