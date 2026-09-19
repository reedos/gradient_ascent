"""Tests for examples/agent_teammates: the scheduler-tick, propose-and-classify example for the
always-on-assistants technique page. Checks the decided_by pattern, that all three policy classes
are reachable in one tick, and -- the property this page exists to prove -- that a forbidden
action never reaches the mailbox, not on the first tick and not through a later approval call.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.agent_teammates.__main__ import SCRIPTED  # noqa: E402
from examples.agent_teammates.run import Mailbox, approve, run_tick  # noqa: E402
from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

EVENTS = "3 new emails: a newsletter, a meeting request from a client, and an invoice asking to be paid."

# The same sequence examples/agent_teammates/__main__.py plays under --model stub:scripted.
SEQUENCE = [
    StubResponse(
        tool_calls=[
            ToolCall(name="archive_email", arguments={"detail": "newsletter"}),
            ToolCall(name="send_email", arguments={"detail": "confirm the meeting"}),
            ToolCall(name="make_payment", arguments={"detail": "pay the invoice, $4,200"}),
        ]
    ),
]


def _tracer() -> Tracer:
    return Tracer(example="agent_teammates", level=7, model_id="stub-1")


class AgentTeammatesExampleTests(unittest.TestCase):
    def test_a_tick_records_exactly_one_model_decided_step(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="archive_email", arguments={"detail": "newsletter"})])])
        tracer = _tracer()
        box = Mailbox()
        result = run_tick(EVENTS, model, tracer, box, approvals=[])

        self.assertEqual(tracer.model_decided_count(), 1)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(model_steps), 1)
        self.assertEqual(model_steps[0].title, "Model decides whether anything needs doing, and proposes actions")
        self.assertEqual(model_steps[0].edge, "dashed")
        self.assertEqual(tracer.steps[0].title, "Scheduler tick wakes the agent")
        self.assertEqual(tracer.steps[0].decided_by, "code")
        self.assertEqual(result.executed, [{"action": "archive_email", "detail": "newsletter"}])
        self.assertEqual(box.archived, ["newsletter"])

    def test_an_empty_proposal_is_a_model_decision_too(self) -> None:
        # the model can decide nothing needs doing; that is still the one decided_by: model step
        model = StubModel([StubResponse(text="Nothing needs attention right now.")])
        tracer = _tracer()
        result = run_tick(EVENTS, model, tracer, Mailbox(), approvals=[])
        self.assertEqual(tracer.model_decided_count(), 1)
        self.assertEqual((result.executed, result.queued, result.refused), ([], [], []))

    def test_all_three_policy_classes_in_one_tick(self) -> None:
        model = StubModel(list(SEQUENCE))
        tracer = _tracer()
        box = Mailbox()
        approvals: list[dict] = []
        result = run_tick(EVENTS, model, tracer, box, approvals=approvals)

        self.assertEqual(result.executed, [{"action": "archive_email", "detail": "newsletter"}])
        self.assertEqual(result.queued, [{"action": "send_email", "detail": "confirm the meeting"}])
        self.assertEqual(result.refused, [{"action": "make_payment", "detail": "pay the invoice, $4,200"}])
        self.assertEqual(box.archived, ["newsletter"])
        self.assertEqual(box.sent, [])  # queued, not sent -- nobody approved it yet
        self.assertEqual(box.payments, [])  # forbidden: never runs, unattended or otherwise
        self.assertEqual(approvals, [{"action": "send_email", "detail": "confirm the meeting"}])

    def test_policy_classifies_every_action_the_example_defines(self) -> None:
        # the guarantee that a forbidden action never runs depends entirely on this table never
        # drifting: every action a tool exists for must be classified, or it silently falls back
        # to the safe default (forbidden) rather than being missed and defaulting to auto.
        from examples.agent_teammates.run import ACTION_TOOLS, DEFAULT_POLICY, POLICY

        self.assertEqual(DEFAULT_POLICY, "forbidden")
        for tool in ACTION_TOOLS:
            self.assertIn(tool["name"], POLICY)
        self.assertEqual(POLICY["make_payment"], "forbidden")
        self.assertEqual(POLICY["share_credential"], "forbidden")

    def test_run_tick_never_queues_a_forbidden_action_for_approval(self) -> None:
        model = StubModel(
            [
                StubResponse(
                    tool_calls=[
                        ToolCall(name="make_payment", arguments={"detail": "$9,000 wire"}),
                        ToolCall(name="share_credential", arguments={"detail": "the admin password"}),
                    ]
                )
            ]
        )
        tracer = _tracer()
        box = Mailbox()
        approvals: list[dict] = []
        result = run_tick(EVENTS, model, tracer, box, approvals=approvals)
        self.assertEqual(approvals, [])  # neither forbidden action ever entered the approval queue
        self.assertEqual(box.payments, [])
        self.assertEqual(len(result.refused), 2)
        for step in tracer.steps:
            if step.title.startswith("Refuse"):
                self.assertEqual(step.decided_by, "code")  # the refusal is the policy's decision, not the model's

    def test_an_unclassified_action_defaults_to_forbidden_not_auto(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="delete_everything", arguments={"detail": "oops"})])])
        tracer = _tracer()
        box = Mailbox()
        result = run_tick(EVENTS, model, tracer, box, approvals=[])
        self.assertEqual(result.refused, [{"action": "delete_everything", "detail": "oops"}])
        self.assertEqual(result.executed, [])

    def test_approve_runs_a_queued_action_only_on_approval(self) -> None:
        box = Mailbox()
        approvals = [{"action": "send_email", "detail": "confirm the meeting"}]
        tracer = _tracer()
        approve(box, approvals, 0, "reject", tracer, approver="dana")
        self.assertEqual(box.sent, [])
        self.assertEqual(approvals, [])  # resolved either way: it does not sit in the queue forever

        approvals = [{"action": "send_email", "detail": "confirm the meeting"}]
        resolved = approve(box, approvals, 0, "approve", tracer, approver="dana")
        self.assertEqual(box.sent, ["confirm the meeting"])
        self.assertEqual(resolved["approver"], "dana")  # who decided is recorded, not just that someone did

    def test_an_approval_with_nobody_behind_it_runs_nothing(self) -> None:
        tracer = _tracer()
        for approver in ("", "   "):
            with self.subTest(approver=approver):
                box = Mailbox()
                approvals = [{"action": "send_email", "detail": "confirm the meeting"}]
                approve(box, approvals, 0, "approve", tracer, approver=approver)
                self.assertEqual(box.sent, [])

    def test_approve_rechecks_the_policy_and_cannot_run_a_forbidden_action(self) -> None:
        """The approval queue is persisted, so an item in it was classified by whatever the
        policy said at the time. Anything that is not `approval` NOW must not run, however it
        got into the queue."""
        tracer = _tracer()
        for action, detail in [("make_payment", "$9,000 wire"), ("share_credential", "the admin password"), ("delete_everything", "oops")]:
            with self.subTest(action=action):
                box = Mailbox()
                approvals = [{"action": action, "detail": detail}]
                resolved = approve(box, approvals, 0, "approve", tracer, approver="dana")
                self.assertEqual(resolved["decision"], "refused")
                self.assertEqual(box.payments, [])
                self.assertEqual(box.sent, [])
                self.assertEqual(box.meetings, [])

    def test_the_model_is_never_offered_a_way_to_approve(self) -> None:
        # the guarantee that only a person can release a queued action rests on the model having
        # no tool for it: every tool comes from POLICY, and approving is not an entry there
        from examples.agent_teammates.run import ACTION_TOOLS, POLICY

        names = {tool["name"] for tool in ACTION_TOOLS}
        self.assertEqual(names, set(POLICY))
        for forbidden_name in ("approve", "approval", "set_policy", "run_tick"):
            self.assertNotIn(forbidden_name, names)

    def test_declares_its_level(self) -> None:
        import examples.agent_teammates.run as module

        self.assertEqual(module.LEVEL, 7)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does. Every entry here is a StubResponse with tool calls, not plain
        text, so the sequences are compared directly rather than by their `.text`."""
        self.assertEqual(SCRIPTED, SEQUENCE)


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(events, model, tracer)` is the entry point `record_trace.py` calls: one tick against
    a fresh mailbox and empty approval queue, the same defaults `__main__.py`'s `main` builds."""

    def test_run_is_a_tick_against_a_fresh_mailbox(self) -> None:
        from examples.agent_teammates.run import run

        model = StubModel([StubResponse(tool_calls=[ToolCall(name="archive_email", arguments={"detail": "newsletter"})])])
        tracer = _tracer()
        result = run(EVENTS, model, tracer)
        self.assertEqual(result.executed, [{"action": "archive_email", "detail": "newsletter"}])

    def test_record_trace_classifies_agent_teammates_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("agent_teammates")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
