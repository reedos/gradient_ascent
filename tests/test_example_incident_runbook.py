"""Tests for examples/incident_runbook: pull a timeline out of a write-up, draft a runbook step
for each repeatable event, verify in code, and hold for the incident owner's approval.

Four things are being pinned here, matching the recipe's own claim.

- **The chain calls the model exactly twice, in order, and code decides both calls.** Extraction
  first, drafting second, whatever either reply says.
- **A step whose `from_event` names an event that is not in the timeline is dropped, not kept
  with a dangling citation.** This is the attack on the chain's own weak point: a model can cite
  an id that never existed.
- **A step with no role or no check is kept and flagged incomplete, not silently accepted.** The
  other attack: a model can satisfy the shape of a step (an action, an event id) while leaving out
  exactly the two fields that make it usable.
- **A one-off action the model wrongly turns into a step is not caught here at all.** Waking a
  named person and emailing named customers can carry a perfectly plausible role and check; there
  is nothing in their shape that marks them as belonging to this one incident rather than the
  next one. Code cannot tell the difference, and this test says so directly: the assertion is
  that the bad step survives verification unflagged, which is the argument for the approval gate,
  not a gap in it.
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
from examples.incident_runbook.run import (  # noqa: E402
    LEVEL,
    SAMPLE_INPUT,
    PendingApproval,
    Runbook,
    resume,
    run,
)

RUN_PY = ROOT / "examples" / "incident_runbook" / "run.py"

# Seven timeline events: five happened but never become steps on their own (the page, joining
# the call, reading logs, the queue peaking, closing the page), two are one-off (e3, e7), and
# four are the ones the recipe says would be done again (e2, e4, e5, e6).
TIMELINE_RESPONSE = json.dumps({
    "events": [
        {"time": "02:14", "actor": "on-call system", "action": "pages jrivera; order-sync-worker queue-depth alert, over threshold"},
        {"time": "02:19", "actor": "jrivera", "action": "checks the queue-depth dashboard: order-sync-queue at 42,100 and climbing, normal is under 500"},
        {"time": "02:26", "actor": "jrivera", "action": "decides this is bad enough to wake the on-call lead and calls dcho"},
        {"time": "02:38", "actor": "dcho", "action": "restarts the order-sync-worker pool"},
        {"time": "02:47", "actor": "dcho", "action": "rolls the worker image back to the previous build; queue depth keeps climbing for a few minutes, the rollback alone does not change the direction"},
        {"time": "03:16", "actor": "jrivera", "action": "checks the order-sync-lag metric: back under 30 seconds, inside the normal range"},
        {"time": "03:20", "actor": "dcho", "action": "drafts a short email to the three enterprise accounts with delayed orders"},
    ]
})
# The four repeatable events (e2, e4, e5, e6), each a complete step.
GOOD_STEP_RESPONSE = json.dumps({
    "steps": [
        {"action": "Check the order-sync-queue depth on the queue-depth dashboard", "role": "on-call engineer", "check": "depth is at or below 500", "from_event": "e2"},
        {"action": "Restart the order-sync-worker pool", "role": "on-call engineer", "check": "crash-looping pods report running and the crash count stops climbing", "from_event": "e4"},
        {"action": "If a recent deploy is suspected, roll back the image, but do not expect the rollback alone to drain the queue", "role": "on-call engineer", "check": "queue depth starts dropping only after the pool is restarted, not from the rollback by itself", "from_event": "e5"},
        {"action": "Check the order-sync-lag metric", "role": "on-call engineer", "check": "lag is back under 30 seconds", "from_event": "e6"},
    ]
})


def tracer() -> Tracer:
    return Tracer(example="incident_runbook", level=LEVEL, model_id="stub-1")


def _good_model() -> StubModel:
    return StubModel([StubResponse(text=TIMELINE_RESPONSE), StubResponse(text=GOOD_STEP_RESPONSE)])


class ChainOrderTests(unittest.TestCase):
    def test_the_model_is_called_twice_in_order_extract_then_draft(self) -> None:
        trace = tracer()
        run(SAMPLE_INPUT, _good_model(), trace)
        model_titles = [s.title for s in trace.steps if s.kind == "model"]
        self.assertEqual(model_titles, ["Pull the timeline out of the write-up", "Turn the repeatable events into runbook steps"])

    def test_every_step_including_both_model_calls_is_the_codes_decision(self) -> None:
        trace = tracer()
        run(SAMPLE_INPUT, _good_model(), trace)
        self.assertTrue(trace.steps)
        self.assertEqual(trace.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" for s in trace.steps))

    def test_the_source_records_no_model_decision_anywhere(self) -> None:
        # scripts/validate.py reads examples for this string; the example must not carry one.
        self.assertNotIn('decided_by="model"', RUN_PY.read_text(encoding="utf-8"))

    def test_the_good_run_keeps_all_four_repeatable_steps_and_drops_nothing(self) -> None:
        pending = run(SAMPLE_INPUT, _good_model(), tracer())
        self.assertEqual(len(pending.timeline), 7)
        self.assertEqual([s.from_event for s in pending.steps], ["e2", "e4", "e5", "e6"])
        self.assertEqual(pending.dropped, ())
        self.assertTrue(all(not s.incomplete for s in pending.steps))


class VerificationCatchesDanglingCitations(unittest.TestCase):
    """Attack: a drafted step names an event id nothing in the timeline has."""

    def test_a_step_citing_an_event_not_in_the_timeline_is_dropped_and_reported(self) -> None:
        timeline = json.dumps({"events": [{"time": "02:14", "actor": "jrivera", "action": "checks the dashboard"}]})
        steps = json.dumps({"steps": [
            {"action": "Check the dashboard", "role": "on-call engineer", "check": "depth is normal", "from_event": "e1"},
            {"action": "Page the vendor", "role": "on-call engineer", "check": "vendor acks", "from_event": "e99"},
        ]})
        model = StubModel([StubResponse(text=timeline), StubResponse(text=steps)])
        pending = run("one event", model, tracer())
        self.assertEqual([s.from_event for s in pending.steps], ["e1"])
        self.assertEqual(len(pending.dropped), 1)
        self.assertIn("e99", pending.dropped[0])
        self.assertIn("not in the timeline", pending.dropped[0])


class VerificationFlagsIncompleteSteps(unittest.TestCase):
    """Attack: a drafted step has a real event id and an action, and nothing else."""

    def test_a_step_with_no_check_is_kept_and_flagged_incomplete_not_silently_accepted(self) -> None:
        timeline = json.dumps({"events": [{"time": "02:14", "actor": "jrivera", "action": "checks the dashboard"}]})
        steps = json.dumps({"steps": [{"action": "Check the dashboard", "role": "on-call engineer", "check": "", "from_event": "e1"}]})
        model = StubModel([StubResponse(text=timeline), StubResponse(text=steps)])
        pending = run("one event", model, tracer())
        self.assertEqual(len(pending.steps), 1, "an incomplete step is kept, not dropped")
        self.assertTrue(pending.steps[0].incomplete)
        self.assertIn("no check", pending.steps[0].problems)
        self.assertIn("INCOMPLETE", pending.text)

    def test_a_step_with_no_role_is_kept_and_flagged_incomplete(self) -> None:
        timeline = json.dumps({"events": [{"time": "02:14", "actor": "jrivera", "action": "checks the dashboard"}]})
        steps = json.dumps({"steps": [{"action": "Check the dashboard", "check": "depth is normal", "from_event": "e1"}]})
        model = StubModel([StubResponse(text=timeline), StubResponse(text=steps)])
        pending = run("one event", model, tracer())
        self.assertEqual(len(pending.steps), 1)
        self.assertTrue(pending.steps[0].incomplete)
        self.assertIn("no role", pending.steps[0].problems)


class OneOffPromotionIsNotCaughtByCode(unittest.TestCase):
    def test_a_one_off_action_with_a_plausible_role_and_check_passes_verification_unflagged(self) -> None:
        """This is the failure mode the page calls out plainly: code checks that a step traces
        to a real event and names a role and a check, and 'waking a specific person' passes both
        of those exactly as well as 'checking a queue depth' does. There is no field to test for
        one-off-ness, so the assertion here is the negative: verification does not drop this step
        and does not flag it incomplete. Only a person who ran the incident, reading the draft at
        the approval gate, knows that dcho does not need waking for every order-sync incident."""
        timeline = json.dumps({"events": [{"time": "02:26", "actor": "jrivera", "action": "decides to wake the on-call lead and calls dcho"}]})
        steps = json.dumps({"steps": [
            {"action": "Call dcho and wake them", "role": "on-call engineer", "check": "dcho joins the incident call", "from_event": "e1"},
        ]})
        model = StubModel([StubResponse(text=timeline), StubResponse(text=steps)])
        pending = run("one event", model, tracer())
        self.assertEqual(len(pending.steps), 1)
        self.assertFalse(pending.steps[0].incomplete)
        self.assertEqual(pending.dropped, ())


class JsonRetryTests(unittest.TestCase):
    def test_a_malformed_draft_reply_is_retried_once_and_the_corrected_reply_is_used(self) -> None:
        timeline = json.dumps({"events": [{"time": "02:14", "actor": "jrivera", "action": "checks the dashboard"}]})
        good_steps = json.dumps({"steps": [{"action": "Check the dashboard", "role": "on-call engineer", "check": "depth is normal", "from_event": "e1"}]})
        model = StubModel([
            StubResponse(text=timeline),
            StubResponse(text="not json at all"),
            StubResponse(text=good_steps),
        ])
        trace = tracer()
        pending = run("one event", model, trace)
        self.assertEqual(len(pending.steps), 1)
        self.assertEqual(pending.steps[0].from_event, "e1")
        retry_titles = [s.title for s in trace.steps if s.title == "Ask again with the validation error"]
        self.assertEqual(len(retry_titles), 1)

    def test_two_malformed_draft_replies_in_a_row_give_up_with_no_steps_rather_than_raising(self) -> None:
        timeline = json.dumps({"events": [{"time": "02:14", "actor": "jrivera", "action": "checks the dashboard"}]})
        model = StubModel([
            StubResponse(text=timeline),
            StubResponse(text="still not json"),
            StubResponse(text="{\"steps\": not even close"),
        ])
        pending = run("one event", model, tracer())
        self.assertEqual(pending.steps, ())
        self.assertEqual(pending.dropped, ())

    def test_a_malformed_timeline_reply_is_retried_and_recovers(self) -> None:
        good_timeline = json.dumps({"events": [{"time": "02:14", "actor": "jrivera", "action": "checks the dashboard"}]})
        steps = json.dumps({"steps": []})
        model = StubModel([StubResponse(text="nope"), StubResponse(text=good_timeline), StubResponse(text=steps)])
        pending = run("one event", model, tracer())
        self.assertEqual(len(pending.timeline), 1)
        self.assertEqual(pending.timeline[0].id, "e1")


class ResumeTests(unittest.TestCase):
    def _pending(self) -> PendingApproval:
        return run(SAMPLE_INPUT, _good_model(), tracer())

    def test_approve_ships_the_draft_text_and_keeps_the_steps(self) -> None:
        pending = self._pending()
        result = resume(pending, "approve", tracer())
        self.assertIsInstance(result, Runbook)
        self.assertTrue(result.approved)
        self.assertEqual(result.text, pending.text)
        self.assertEqual(result.steps, pending.steps)

    def test_edit_replaces_the_text_with_the_reviewers_note_but_keeps_the_steps(self) -> None:
        pending = self._pending()
        result = resume(pending, "edit", tracer(), note="1. check the dashboard\n2. restart the pool")
        self.assertTrue(result.approved)
        self.assertEqual(result.text, "1. check the dashboard\n2. restart the pool")
        self.assertEqual(result.steps, pending.steps)

    def test_reject_ships_no_steps_at_all(self) -> None:
        pending = self._pending()
        result = resume(pending, "reject", tracer())
        self.assertFalse(result.approved)
        self.assertEqual(result.steps, ())
        self.assertIn("rejected", result.text)

    def test_resumes_own_step_is_the_codes_decision(self) -> None:
        pending = self._pending()
        trace = tracer()
        resume(pending, "approve", trace)
        self.assertEqual(trace.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" for s in trace.steps))


class CostFigureTests(unittest.TestCase):
    def test_the_token_counts_the_page_quotes(self) -> None:
        """The recipe page's cost strip quotes these two totals for the sample write-up above,
        run through the same scripted good-path model; pin them so the page cannot drift from
        what the code actually sends and receives."""
        trace = tracer()
        run(SAMPLE_INPUT, _good_model(), trace)
        self.assertEqual(trace.tokens_in_total(), 785)
        self.assertEqual(trace.tokens_out_total(), 427)


class SampleInputTests(unittest.TestCase):
    def test_sample_input_is_the_module_level_writeup(self) -> None:
        self.assertGreater(len(SAMPLE_INPUT.splitlines()), 15)
        self.assertIn("Thistledown Labs", SAMPLE_INPUT)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))


if __name__ == "__main__":
    unittest.main()
