"""Tests for the project-tracker-upkeep example.

The reconcile half (level 0, no model): what is applied, what is queued, what is left alone, and
what nobody confirmed. The last of those is the failure this recipe is written around, so it is
attacked from both ends: a source that stopped advancing, and a record that fell out of a source
that is otherwise current. In both cases the test that matters is the negative control, that the
same run with the source refreshed reports nothing aging, because otherwise "absence is reported"
is a sentence and not a behavior.

The reading half (level 1 on its own): one call per message, one retry, and the quote check that
throws away a proposal the model paraphrased instead of copying.

The gate (what makes the joined job level 3): nothing the model returned reaches the document,
a person-written field is never overwritten by a source, and a value a person approved survives
the next week's run.
"""
from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.project_tracker_upkeep.run import (  # noqa: E402
    AGING_DAYS,
    LEVEL,
    SAMPLE_DOCUMENT,
    SAMPLE_INPUT,
    SAMPLE_LAST_SEEN,
    SAMPLE_SOURCES,
    Cell,
    InboxMessage,
    TrackerRecord,
    approve,
    run,
)

MOVED = {
    "proposals": [
        {
            "project": "Brightwater Commons",
            "field": "milestone_date",
            "value": "10/02/2026",
            "quote": "the permit hearing has been moved to 10/02/2026",
        }
    ]
}
BREAKDOWN = {
    "proposals": [
        {
            "project": "Ferndale Library",
            "field": "risk",
            "value": "The board wants a line-by-line shelving breakdown before sign-off.",
            "quote": "the board wants a line-by-line breakdown of the shelving costs",
        }
    ]
}
NOTHING = {"proposals": []}


def tracer() -> Tracer:
    return Tracer(example="project_tracker_upkeep", level=LEVEL, model_id="stub-1")


def replies(*payloads: dict) -> StubModel:
    return StubModel([StubResponse(text=json.dumps(p)) for p in payloads])


def sample_week() -> StubModel:
    return replies(MOVED, BREAKDOWN, NOTHING)


class TheReconcileHalfTests(unittest.TestCase):
    """Level 0. Field by field, against the source that owns the field."""

    def test_the_sample_week_changes_two_fields_and_leaves_nineteen_alone(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        self.assertEqual(len(result.applied), 2)
        self.assertEqual(result.unchanged, 19)
        self.assertEqual(
            sorted((c.project, c.field) for c in result.applied),
            [("Ferndale Library", "milestone_date"), ("Ferndale Library", "status")],
        )

    def test_a_code_written_field_is_updated_without_asking_and_keeps_its_old_value(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        change = next(c for c in result.applied if c.field == "status")
        self.assertEqual((change.old, change.new), ("Design development", "Cost estimate out"))
        self.assertEqual(result.document.row("Ferndale Library").cells["status"].value, "Cost estimate out")

    def test_a_field_a_person_typed_in_is_never_overwritten_by_a_source(self) -> None:
        """The export says the hearing is on 09/21/2026 and somebody typed 09/24/2026 in after a
        call. The document keeps what the person wrote and the disagreement goes in the queue."""
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        cell = result.document.row("Brightwater Commons").cells["milestone_date"]
        self.assertEqual(cell.value, "09/24/2026")
        self.assertEqual(cell.written_by, "person")
        queued = next(p for p in result.pending if p.why.startswith("the project tracker disagrees"))
        self.assertEqual((queued.old, queued.new), ("09/24/2026", "09/21/2026"))

    def test_a_project_the_document_does_not_cover_becomes_a_queued_row_not_a_written_one(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        new_row = next(p for p in result.pending if p.field == "(new row)")
        self.assertEqual(new_row.project, "Mavis Street")
        self.assertIsNone(result.document.row("Mavis Street"))
        self.assertIn("needs an owner", new_row.why)


class AbsenceTests(unittest.TestCase):
    """The failure this recipe is written around. A source that goes quiet reads as "nothing
    changed" in any document that only shows values, and quietly ages the whole thing."""

    def test_a_source_that_did_not_advance_is_named_as_stale(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        self.assertEqual(result.stale_sources, ("time spreadsheet",))

    def test_a_stale_source_ages_the_fields_it_owns_instead_of_confirming_them(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        hours = [a for a in result.aging if a.field == "hours_used"]
        self.assertEqual(len(hours), 3)
        for entry in hours:
            self.assertGreaterEqual(entry.days, AGING_DAYS)
            self.assertIn("has not been refreshed", entry.reason)

    def test_the_same_run_with_the_spreadsheet_refreshed_ages_nothing_it_owns(self) -> None:
        """The negative control, and the test that makes the one above mean something: identical
        numbers, an `as_of` that moved, and the fields are confirmed rather than aged."""
        refreshed = replace(SAMPLE_SOURCES, hours_as_of="2026-09-18")
        result = run(SAMPLE_INPUT, sample_week(), tracer(), sources=refreshed)
        self.assertEqual(result.stale_sources, ())
        self.assertEqual([a for a in result.aging if a.reason.startswith("the time spreadsheet")], [])
        confirmed = result.document.row("Brightwater Commons").cells["hours_used"]
        self.assertEqual(confirmed.value, "65.0")
        self.assertEqual(confirmed.updated, "2026-09-18")

    def test_a_project_missing_from_a_current_export_is_reported_and_not_closed(self) -> None:
        """The second shape of absence. The export no longer lists this project. Its status is
        left exactly as it was, and the run says the export stopped mentioning it."""
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        self.assertEqual(result.absent_rows, ("Halloway Bridge Survey",))
        cells = result.document.row("Halloway Bridge Survey").cells
        self.assertEqual(cells["status"].value, "Field work")
        self.assertEqual(cells["status"].updated, "2026-09-08")
        reasons = {a.reason for a in result.aging if a.project == "Halloway Bridge Survey"}
        self.assertIn("the project tracker no longer lists this project", reasons)

    def test_a_project_listed_again_next_week_stops_being_absent(self) -> None:
        listed = replace(
            SAMPLE_SOURCES,
            tracker=SAMPLE_SOURCES.tracker
            + (TrackerRecord("Halloway Bridge Survey", "Field work", "Draft report", "10/09/2026"),),
        )
        result = run(SAMPLE_INPUT, sample_week(), tracer(), sources=listed)
        self.assertEqual(result.absent_rows, ())
        self.assertEqual(result.document.row("Halloway Bridge Survey").cells["status"].updated, "2026-09-18")


class TheReadingHalfTests(unittest.TestCase):
    """One call per unread message, and everything it returns is a claim."""

    def test_one_call_per_message_and_no_more(self) -> None:
        model = sample_week()
        run(SAMPLE_INPUT, model, tracer())
        with self.assertRaises(IndexError):
            model.complete([])

    def test_a_message_that_changes_nothing_proposes_nothing(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        self.assertEqual([p.id for p in result.pending if "IN-53" in p.why], [])

    def test_a_quote_the_model_paraphrased_is_thrown_away_and_named(self) -> None:
        """The check the page teaches. The value may well be right; the proposal is dropped
        anyway, because a quote that is not in the message is a sentence the model wrote."""
        paraphrased = {
            "proposals": [
                {
                    "project": "Brightwater Commons",
                    "field": "milestone_date",
                    "value": "10/02/2026",
                    "quote": "the hearing was pushed back to the second of October",
                }
            ]
        }
        result = run(SAMPLE_INPUT, replies(paraphrased, NOTHING, NOTHING), tracer())
        self.assertEqual([p for p in result.pending if p.quote], [])
        self.assertTrue(any("quote that is not in the message" in d for d in result.dropped))

    def test_a_quote_that_only_differs_in_line_wrapping_is_kept(self) -> None:
        """A model re-wraps a sentence even when it copies the words. The comparison normalizes
        whitespace so that is not treated as a paraphrase."""
        wrapped = json.loads(json.dumps(MOVED))
        wrapped["proposals"][0]["quote"] = "the permit hearing has been\n  moved to 10/02/2026"
        result = run(SAMPLE_INPUT, replies(wrapped, NOTHING, NOTHING), tracer())
        self.assertEqual(len([p for p in result.pending if p.quote]), 1)

    def test_a_real_sentence_read_to_mean_the_wrong_thing_is_not_caught(self) -> None:
        """The limit of a quote check, proved rather than described: the quote is genuinely in
        the message and the value read out of it is wrong. Only a person catches this, which is
        why the quote is printed next to the change in the queue."""
        misread = {
            "proposals": [
                {
                    "project": "Brightwater Commons",
                    "field": "milestone_date",
                    "value": "09/25/2026",
                    "quote": "We will need the updated site plan a week before that.",
                }
            ]
        }
        result = run(SAMPLE_INPUT, replies(misread, NOTHING, NOTHING), tracer())
        queued = next(p for p in result.pending if p.quote)
        self.assertEqual(queued.new, "09/25/2026")
        self.assertEqual(result.dropped, ())

    def test_a_proposal_for_a_project_or_a_field_the_tracker_does_not_have_is_dropped(self) -> None:
        stray = {
            "proposals": [
                {"project": "Mavis Street", "field": "note", "value": "x", "quote": "Nothing needed from us this week."},
                {"project": "Halloway Bridge Survey", "field": "invoice_total", "value": "x", "quote": "Thanks for the photographs."},
            ]
        }
        result = run(SAMPLE_INPUT, replies(NOTHING, NOTHING, stray), tracer())
        self.assertTrue(any("named a project no row covers" in d for d in result.dropped))
        self.assertTrue(any("named a field the tracker does not have" in d for d in result.dropped))

    def test_a_proposal_that_repeats_what_the_document_already_says_is_dropped(self) -> None:
        already = {
            "proposals": [
                {
                    "project": "Halloway Bridge Survey",
                    "field": "status",
                    "value": "Field work",
                    "quote": "Thanks for the photographs.",
                }
            ]
        }
        result = run(SAMPLE_INPUT, replies(NOTHING, NOTHING, already), tracer())
        self.assertTrue(any("which already says that" in d for d in result.dropped))

    def test_an_invalid_reply_costs_exactly_one_retry(self) -> None:
        model = StubModel(
            [
                StubResponse(text="Sure! {not json"),
                StubResponse(text=json.dumps(MOVED)),
                StubResponse(text=json.dumps(NOTHING)),
                StubResponse(text=json.dumps(NOTHING)),
            ]
        )
        result = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len([p for p in result.pending if p.quote]), 1)
        self.assertEqual(result.dropped, ())

    def test_a_message_that_never_validates_is_reported_not_skipped(self) -> None:
        model = StubModel(
            [
                StubResponse(text="{}"),
                StubResponse(text="{}"),
                StubResponse(text=json.dumps(NOTHING)),
                StubResponse(text=json.dumps(NOTHING)),
            ]
        )
        result = run(SAMPLE_INPUT, model, tracer())
        self.assertTrue(any("IN-51 was never read" in d for d in result.dropped))

    def test_a_quiet_inbox_calls_no_model_at_all(self) -> None:
        """A source that did not advance is not read again, so a week with no new mail costs
        nothing and still reports the tracker's own changes."""
        quiet = replace(SAMPLE_SOURCES, inbox_as_of="2026-09-11")
        result = run(SAMPLE_INPUT, StubModel([]), tracer(), sources=quiet)
        self.assertEqual(len(result.applied), 2)


class TheGateTests(unittest.TestCase):
    """What makes the joined job level 3: the run writes to a document, so some writes wait."""

    def test_nothing_the_model_returned_reaches_the_document(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        self.assertEqual(result.document.row("Brightwater Commons").cells["milestone_date"].value, "09/24/2026")
        self.assertEqual(result.document.row("Ferndale Library").cells["risk"].value, "")
        from_prose = [p for p in result.pending if p.quote]
        self.assertEqual(len(from_prose), 2)

    def test_every_queued_change_carries_both_values_and_a_reason(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        for item in result.pending:
            self.assertTrue(item.why)
            self.assertTrue(item.id)
            self.assertIsNotNone(item.old)
            self.assertTrue(item.new)

    def test_approving_writes_only_what_was_accepted_and_marks_it_a_persons_value(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        after = approve(result, ["P-04"], as_of=SAMPLE_INPUT)
        risk = after.row("Ferndale Library").cells["risk"]
        self.assertEqual(risk.value, "The board wants a line-by-line shelving breakdown before sign-off.")
        self.assertEqual(risk.written_by, "person")
        self.assertEqual(after.row("Brightwater Commons").cells["milestone_date"].value, "09/24/2026")

    def test_approving_two_changes_to_one_cell_is_refused(self) -> None:
        """The queue legitimately holds two different answers for one field: the export's date
        and the client's. Picking between them is the decision, so applying both is an error and
        not a last-one-wins."""
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        with self.assertRaises(ValueError) as caught:
            approve(result, ["P-01", "P-03"], as_of=SAMPLE_INPUT)
        self.assertIn("Brightwater Commons.milestone_date", str(caught.exception))

    def test_a_value_a_person_approved_is_not_overwritten_next_week(self) -> None:
        """The round trip, which is the whole difference between a report and a document: what
        the person decided this week survives the next run of the same code."""
        first = run(SAMPLE_INPUT, sample_week(), tracer())
        document = approve(first, ["P-03"], as_of=SAMPLE_INPUT)
        next_week = replace(SAMPLE_SOURCES, tracker_as_of="2026-09-25", inbox_as_of="2026-09-25", inbox=())
        seen = {**SAMPLE_LAST_SEEN, "project tracker": "2026-09-18", "shared inbox": "2026-09-18"}
        second = run("2026-09-25", StubModel([]), tracer(), document=document, sources=next_week, last_seen=seen)
        self.assertEqual(second.document.row("Brightwater Commons").cells["milestone_date"].value, "10/02/2026")
        self.assertTrue(any(p.field == "milestone_date" and p.new == "09/21/2026" for p in second.pending))

    def test_every_step_is_decided_by_code(self) -> None:
        t = tracer()
        run(SAMPLE_INPUT, sample_week(), t)
        self.assertEqual(t.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in t.steps if s.kind == "model"), 3)


class PageFiguresTests(unittest.TestCase):
    """Numbers the recipe page and its run diagram quote, pinned here."""

    def test_the_sample_week_is_the_one_the_page_walks_through(self) -> None:
        result = run(SAMPLE_INPUT, sample_week(), tracer())
        self.assertEqual(
            (len(result.applied), len(result.pending), result.unchanged, len(result.aging)),
            (2, 4, 19, 6),
        )
        self.assertEqual(len(SAMPLE_DOCUMENT.rows), 3)
        self.assertEqual(sum(len(r.cells) for r in SAMPLE_DOCUMENT.rows), 21)

    def test_the_run_costs_three_calls_at_the_token_counts_the_page_states(self) -> None:
        t = tracer()
        run(SAMPLE_INPUT, sample_week(), t)
        self.assertEqual(t.tokens_in_total(), 920)
        self.assertEqual(t.tokens_out_total(), 99)

    def test_the_example_declares_level_three(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))

    def test_the_document_carries_provenance_on_every_cell(self) -> None:
        """Nothing in this recipe works without it, so it is asserted rather than assumed."""
        for row in SAMPLE_DOCUMENT.rows:
            for name, cell in row.cells.items():
                self.assertIsInstance(cell, Cell)
                self.assertIn(cell.written_by, ("code", "person"), f"{row.project}.{name}")
                self.assertTrue(cell.updated)

    def test_the_command_plays_the_same_three_replies_these_tests_are_written_against(self) -> None:
        """Three messages, three replies, in reading order. If the demo command's sequence and
        this file's payloads drift apart, the command demonstrates a run nothing here checked."""
        from examples.project_tracker_upkeep.__main__ import SCRIPTED

        self.assertEqual(SCRIPTED, [json.dumps(MOVED), json.dumps(BREAKDOWN), json.dumps(NOTHING)])

    def test_the_sample_inbox_is_three_messages_one_of_which_says_nothing(self) -> None:
        self.assertEqual(len(SAMPLE_SOURCES.inbox), 3)
        for message in SAMPLE_SOURCES.inbox:
            self.assertIsInstance(message, InboxMessage)


if __name__ == "__main__":
    unittest.main()
