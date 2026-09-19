"""Tests for examples/trip_planning: the loop of read-only lookups plus the held-booking
checkpoint, mirroring the shape of tests/test_example_agentic_rag.py (the loop's decided_by
pattern, the step cap and the token budget) and tests/test_example_human_in_the_loop.py (pause,
then a separate resume call). Two things are specific to this recipe and get their own tests:
`book` pauses instead of running, and `approve` is attacked with a call whose arguments were
changed after it was approved.
"""
from __future__ import annotations

import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.trip_planning.run import (  # noqa: E402
    LEVEL,
    SAMPLE_INPUT,
    PendingBooking,
    approve,
    run,
)


def _tracer() -> Tracer:
    return Tracer(example="trip_planning", level=LEVEL, model_id="stub-1")


# The same four calls, in order, as examples/trip_planning/__main__.py's SCRIPTED: three read-only
# lookups the model chooses for itself, then a book call that pauses the run.
SEQUENCE = [
    StubResponse(tool_calls=[ToolCall(name="search_routes", arguments={"origin": "Wrenfield", "destination": "Aldercliff"})]),
    StubResponse(tool_calls=[ToolCall(name="search_stays", arguments={"city": "Aldercliff"})]),
    StubResponse(tool_calls=[ToolCall(name="opening_hours", arguments={"place": "Aldercliff Museum of Tides"})]),
    StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R1"})]),
]


class TripPlanningExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_and_approve_function(self) -> None:
        self.assertEqual(LEVEL, 5)
        self.assertTrue(callable(run))
        self.assertTrue(callable(approve))
        self.assertIsInstance(SAMPLE_INPUT, str)
        self.assertTrue(SAMPLE_INPUT.strip())

    def test_read_only_lookups_run_unattended_and_match_the_scripted_calls(self) -> None:
        """Three read-only tool calls plus the stop: every one of those is the model's own
        choice, so the trace should show exactly four model-decided steps -- the number a
        fixed-order workflow could not commit to in advance, since a real run might need one
        lookup or five depending on what comes back."""
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="search_routes", arguments={"origin": "Wrenfield", "destination": "Aldercliff"})]),
                StubResponse(tool_calls=[ToolCall(name="search_stays", arguments={"city": "Aldercliff"})]),
                StubResponse(tool_calls=[ToolCall(name="opening_hours", arguments={"place": "Aldercliff Museum of Tides"})]),
                StubResponse(text="Fly R1 at 08:10 for $89.00, stay at the Cormorant Inn, the museum opens at 09:00."),
            ]
        )
        tracer = _tracer()
        answer = run(SAMPLE_INPUT, model, tracer)
        self.assertEqual(tracer.model_decided_count(), 4)
        tool_steps = [s for s in tracer.steps if s.title.startswith("Run tool")]
        self.assertEqual(len(tool_steps), 3)
        self.assertTrue(all(s.decided_by == "code" for s in tool_steps))
        self.assertIn("89.00", answer.text)

    def test_a_book_call_pauses_with_the_price_and_terms_and_books_nothing(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R2"})])])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        self.assertIsInstance(pending, PendingBooking)
        self.assertEqual(pending.call.kind, "route")
        self.assertEqual(pending.call.ref, "R2")
        self.assertEqual(pending.call.price_cents, 6400)
        self.assertEqual(pending.call.cancellation, "Non-refundable.")
        # the pause is recorded, but nothing was booked: no execution step exists
        self.assertFalse(any(s.title == "Execute the approved booking" for s in tracer.steps))
        pause_steps = [s for s in tracer.steps if s.title == "Pause for approval before booking"]
        self.assertEqual(len(pause_steps), 1)
        self.assertEqual(pause_steps[0].decided_by, "code")
        self.assertIn("64.00", pause_steps[0].detail)
        self.assertIn("Non-refundable", pause_steps[0].detail)

    def test_a_book_call_for_a_stay_also_pauses_with_its_own_price_and_terms(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "stay", "ref": "S1"})])])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        self.assertIsInstance(pending, PendingBooking)
        self.assertEqual(pending.call.price_cents, 11200)
        self.assertIn("Cormorant Inn", pending.call.detail)

    def test_a_book_call_for_an_unknown_reference_is_refused_not_invented(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R9"})])])
        tracer = _tracer()
        with self.assertRaises(ValueError):
            run(SAMPLE_INPUT, model, tracer)

    def test_approval_executes_exactly_the_approved_call(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R1"})])])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        before = len(tracer.steps)
        answer = approve(pending, "approve", tracer)
        self.assertIn("R1", answer.text)
        self.assertIn("89.00", answer.text)
        self.assertIn("Refundable", answer.text)
        self.assertEqual(answer.citations, ["R1"])
        executed = [s for s in tracer.steps if s.title == "Execute the approved booking"]
        self.assertEqual(len(executed), 1)
        # approve's own steps are code's decision; the run() steps before it (the model's own
        # choice to call book) are untouched by this check
        after_steps = tracer.steps[before:]
        self.assertTrue(after_steps)
        self.assertTrue(all(s.decided_by == "code" for s in after_steps))

    def test_rejecting_books_nothing_and_names_no_price(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R1"})])])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        answer = approve(pending, "reject", tracer)
        self.assertEqual(answer.citations, [])
        self.assertIn("declined", answer.text)
        self.assertFalse(any(s.title == "Execute the approved booking" for s in tracer.steps))

    def test_an_approval_whose_price_changed_after_approval_is_refused(self) -> None:
        """The attack this recipe is about: something between approval and execution changed
        the price on the call that is about to run. `approve` must catch this itself, not trust
        that the call it is holding is still the one a person saw."""
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R1"})])])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        tampered_call = dataclasses.replace(pending.call, price_cents=1)
        tampered = dataclasses.replace(pending, call=tampered_call)
        with self.assertRaises(ValueError):
            approve(tampered, "approve", tracer)
        self.assertFalse(any(s.title == "Execute the approved booking" for s in tracer.steps))
        refused = [s for s in tracer.steps if s.title.startswith("Refuse")]
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0].decided_by, "code")

    def test_an_approval_whose_date_changed_after_approval_is_refused(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="book", arguments={"kind": "route", "ref": "R1"})])])
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        tampered_call = dataclasses.replace(pending.call, detail=pending.call.detail.replace("2026-11-14", "2026-12-25"))
        tampered = dataclasses.replace(pending, call=tampered_call)
        with self.assertRaises(ValueError):
            approve(tampered, "approve", tracer)
        self.assertFalse(any(s.title == "Execute the approved booking" for s in tracer.steps))

    def test_an_unknown_tool_name_is_reported_to_the_model_rather_than_raised(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="cancel_everything", arguments={})]),
                StubResponse(text="I can only search and book."),
            ]
        )
        tracer = _tracer()
        answer = run(SAMPLE_INPUT, model, tracer)
        self.assertIsInstance(answer.text, str)
        self.assertIn("unknown tool", " ".join(s.detail for s in tracer.steps))

    def test_the_step_cap_forces_a_stop_that_is_codes_decision(self) -> None:
        def always_search(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="search_routes", arguments={"origin": "Wrenfield", "destination": "Aldercliff"})])

        model = StubModel(always_search, model_id="stub-loop")
        tracer = _tracer()
        answer = run(SAMPLE_INPUT, model, tracer, max_steps=3)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertEqual(forced[0].decided_by, "code")
        self.assertIn("step cap", forced[0].detail)
        self.assertIsInstance(answer.text, str)
        # the model never chose to stop, so no "Model stops and answers" step exists
        self.assertEqual(sum(1 for s in tracer.steps if s.title == "Model stops and answers"), 0)

    def test_the_token_counts_the_page_quotes(self) -> None:
        """The recipe page's walkthrough and cost strip quote this exact scripted run -- three
        searches, then a book call, then approval -- so pin the totals here rather than letting
        the page restate a number nothing recomputes."""
        model = StubModel(list(SEQUENCE))
        tracer = _tracer()
        pending = run(SAMPLE_INPUT, model, tracer)
        self.assertEqual(tracer.model_decided_count(), 4)
        self.assertEqual(tracer.tokens_in_total(), 1009)
        self.assertEqual(tracer.tokens_out_total(), 37)
        answer = approve(pending, "approve", tracer)
        self.assertIn("89.00", answer.text)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        from examples.trip_planning.__main__ import SCRIPTED

        self.assertEqual(SCRIPTED, SEQUENCE)

    def test_the_command_prints_every_lookup_and_what_it_returned(self) -> None:
        """The README describes three searches before the pause. They live in the tracer, not in
        the returned text, so `__main__` has to print them: without this the command showed only
        the held booking and a reader saw none of the run that reached it."""
        import io
        from contextlib import redirect_stdout

        from examples.trip_planning.__main__ import main as demo_main

        out = io.StringIO()
        with redirect_stdout(out):
            code = demo_main(["--model", "stub:scripted"])
        printed = out.getvalue()

        self.assertEqual(code, 0)
        for tool in ("search_routes", "search_stays", "opening_hours"):
            self.assertIn(f"Model calls a tool: {tool}", printed)
            self.assertIn(f"Run tool: {tool}", printed)
        # What came back, not only that something was called.
        self.assertIn("The Cormorant Inn", printed)
        self.assertIn("open 09:00-17:00", printed)
        # And the pause is still the last thing, printed once rather than twice.
        self.assertEqual(printed.count("R1: Wrenfield -> Aldercliff, 2026-11-14 08:10-10:55\n"), 1)
        self.assertIn("PAUSED for approval", printed)

    def test_the_token_budget_forces_a_stop_before_the_step_cap(self) -> None:
        def always_search(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="search_routes", arguments={"origin": "Wrenfield", "destination": "Aldercliff"})])

        model = StubModel(always_search, model_id="stub-loop")
        tracer = _tracer()
        run(SAMPLE_INPUT, model, tracer, max_steps=50, max_tokens=1)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        self.assertLess(len(tracer.steps), 10, "the loop should stop almost immediately, not run near 50 steps")


if __name__ == "__main__":
    unittest.main()
