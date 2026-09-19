"""Tests for examples/organizations_swarms: the shared task board and coordinator example for
the organizations-of-agents technique page. Checks the decided_by pattern, and the two guarantees
this page is built around: a role can never be assigned more than its budget in one round, and a
task the coordinator proposes assigning twice in one call is only ever claimed once.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.organizations_swarms.__main__ import SCRIPTED  # noqa: E402
from examples.organizations_swarms.run import BUDGET_PER_ROLE, SAMPLE_TASKS, Board, Task, coordinate  # noqa: E402

# The same sequence examples/organizations_swarms/__main__.py plays under --model stub:scripted.
SEQUENCE = [
    StubResponse(
        tool_calls=[
            ToolCall(name="assign", arguments={"task_id": "T1", "role": "researcher"}),
            ToolCall(name="assign", arguments={"task_id": "T2", "role": "writer"}),
            ToolCall(name="assign", arguments={"task_id": "T3", "role": "reviewer"}),
            ToolCall(name="assign", arguments={"task_id": "T4", "role": "researcher"}),
            ToolCall(name="assign", arguments={"task_id": "T1", "role": "writer"}),
        ]
    ),
]


def _tracer() -> Tracer:
    return Tracer(example="organizations_swarms", level=7, model_id="stub-1")


def _board(*descriptions: str) -> Board:
    return Board(tasks=[Task(id=f"T{i+1}", description=d) for i, d in enumerate(descriptions)])


class OrganizationsSwarmsExampleTests(unittest.TestCase):
    def test_a_round_records_exactly_one_model_decided_step(self) -> None:
        board = _board("look up a warranty term")
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="assign", arguments={"task_id": "T1", "role": "researcher"})])])
        tracer = _tracer()
        made = coordinate(board, model, tracer)

        self.assertEqual(tracer.model_decided_count(), 1)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(model_steps), 1)
        self.assertEqual(model_steps[0].title, "Coordinator assigns open tasks to roles")
        self.assertEqual(model_steps[0].edge, "dashed")
        self.assertEqual(made, [{"task": "T1", "role": "researcher"}])
        self.assertEqual(board.get("T1").status, "claimed")
        self.assertEqual(board.get("T1").assigned_to, "researcher")

    def test_an_empty_board_never_calls_the_model(self) -> None:
        board = Board(tasks=[Task(id="T1", description="already done", status="done")])
        model = StubModel([])  # would raise if ever called
        tracer = _tracer()
        made = coordinate(board, model, tracer)
        self.assertEqual(made, [])
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_a_role_cannot_be_assigned_past_its_budget(self) -> None:
        board = _board("task one", "task two", "task three")
        # the coordinator tries to give all three tasks to the same role in one call
        model = StubModel(
            [
                StubResponse(
                    tool_calls=[
                        ToolCall(name="assign", arguments={"task_id": "T1", "role": "writer"}),
                        ToolCall(name="assign", arguments={"task_id": "T2", "role": "writer"}),
                        ToolCall(name="assign", arguments={"task_id": "T3", "role": "writer"}),
                    ]
                )
            ]
        )
        tracer = _tracer()
        made = coordinate(board, model, tracer)

        writer_assignments = [m for m in made if m["role"] == "writer"]
        self.assertEqual(len(writer_assignments), BUDGET_PER_ROLE)
        self.assertLessEqual(board.assigned_count["writer"], BUDGET_PER_ROLE)
        # the task that didn't fit the budget stays open, not silently dropped
        open_ids = [t.id for t in board.tasks if t.status == "open"]
        self.assertEqual(len(open_ids), 1)
        refusals = [s for s in tracer.steps if s.title == "Refuse: role is over budget"]
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].decided_by, "code")

    def test_a_task_cannot_be_claimed_twice_in_one_round(self) -> None:
        board = _board("only one task")
        # the coordinator's own output proposes the same task to two different roles
        model = StubModel(
            [
                StubResponse(
                    tool_calls=[
                        ToolCall(name="assign", arguments={"task_id": "T1", "role": "researcher"}),
                        ToolCall(name="assign", arguments={"task_id": "T1", "role": "writer"}),
                    ]
                )
            ]
        )
        tracer = _tracer()
        made = coordinate(board, model, tracer)

        self.assertEqual(made, [{"task": "T1", "role": "researcher"}])
        self.assertEqual(board.get("T1").assigned_to, "researcher")  # the second proposal never overwrote the first
        self.assertEqual(board.assigned_count["writer"], 0)
        refusals = [s for s in tracer.steps if s.title == "Refuse: task is not open"]
        self.assertEqual(len(refusals), 1)

    def test_a_task_cannot_be_claimed_twice_across_two_rounds_either(self) -> None:
        # T2 stays open through both rounds on purpose: without it the second round returns
        # before the model is called, and this test would pass without checking the claim rule
        board = _board("task one", "task two")
        model1 = StubModel([StubResponse(tool_calls=[ToolCall(name="assign", arguments={"task_id": "T1", "role": "researcher"})])])
        coordinate(board, model1, _tracer())
        self.assertEqual(board.get("T1").assigned_to, "researcher")

        tracer = _tracer()
        model2 = StubModel([StubResponse(tool_calls=[ToolCall(name="assign", arguments={"task_id": "T1", "role": "reviewer"})])])
        made2 = coordinate(board, model2, tracer)
        self.assertEqual(tracer.model_decided_count(), 1)  # the coordinator really did run this round
        self.assertEqual(made2, [])  # already claimed by researcher in round one
        self.assertEqual(board.get("T1").assigned_to, "researcher")
        self.assertEqual(board.assigned_count["reviewer"], 0)

    def test_the_budget_refills_each_round_but_claims_do_not(self) -> None:
        """Two rules that look alike and are not. A role's budget is spent per round and starts
        full in the next one; a claim on a task is permanent until the task is done."""
        board = _board("t1", "t2", "t3", "t4", "t5")
        fill = [ToolCall(name="assign", arguments={"task_id": t, "role": "writer"}) for t in ("T1", "T2", "T3")]
        coordinate(board, StubModel([StubResponse(tool_calls=fill)]), _tracer())
        self.assertEqual(board.assigned_count["writer"], BUDGET_PER_ROLE)
        claimed_first_round = {t.id for t in board.tasks if t.status == "claimed"}
        self.assertEqual(len(claimed_first_round), BUDGET_PER_ROLE)

        # round two: the same role can take work again, and the round-one claims still stand
        more = [ToolCall(name="assign", arguments={"task_id": t, "role": "writer"}) for t in ("T1", "T4")]
        made = coordinate(board, StubModel([StubResponse(tool_calls=more)]), _tracer())
        self.assertEqual(made, [{"task": "T4", "role": "writer"}])  # T1 refused: still claimed
        self.assertEqual(board.assigned_count["writer"], 1)  # the counter refilled, then spent one

    def test_an_unknown_role_is_refused_not_assigned(self) -> None:
        board = _board("a task")
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="assign", arguments={"task_id": "T1", "role": "intern"})])])
        made = coordinate(board, model, _tracer())
        self.assertEqual(made, [])
        self.assertEqual(board.get("T1").status, "open")

    def test_declares_its_level(self) -> None:
        import examples.organizations_swarms.run as module

        self.assertEqual(module.LEVEL, 7)

    def test_the_command_s_scripted_round_splits_the_work_and_refuses_the_double_claim(self) -> None:
        """The end-to-end scenario `python -m examples.organizations_swarms --model
        stub:scripted` runs: the three sample tasks plus one built from a question, coordinated
        by the same sequence SCRIPTED plays. Checks that all four open tasks land on the roles
        the coordinator named, and that its later attempt to also hand T1 to a second role is
        refused rather than overwriting the first claim."""
        board = _board(*[t.description for t in SAMPLE_TASKS], "Fact-check the DW-300 section before it ships")
        model = StubModel(list(SCRIPTED))
        tracer = _tracer()
        made = coordinate(board, model, tracer)

        self.assertEqual(
            made,
            [
                {"task": "T1", "role": "researcher"},
                {"task": "T2", "role": "writer"},
                {"task": "T3", "role": "reviewer"},
                {"task": "T4", "role": "researcher"},
            ],
        )
        self.assertEqual([t.id for t in board.tasks if t.status == "open"], [])
        refusals = [s for s in tracer.steps if s.title == "Refuse: task is not open"]
        self.assertEqual(len(refusals), 1)
        self.assertIn("T1", refusals[0].detail)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does. Every entry here is a StubResponse with tool calls, not plain
        text, so the sequences are compared directly rather than by their `.text`."""
        self.assertEqual(SCRIPTED, SEQUENCE)


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(question, model, tracer)` is the entry point `record_trace.py` calls: one round over
    the three fixed sample tasks plus one open task built from `question`."""

    def test_run_assigns_the_task_built_from_question(self) -> None:
        from examples.organizations_swarms.run import run

        model = StubModel([StubResponse(tool_calls=[ToolCall(name="assign", arguments={"task_id": "T4", "role": "researcher"})])])
        tracer = _tracer()
        made = run("Fact-check the DW-300 section", model, tracer)
        self.assertEqual(made, [{"task": "T4", "role": "researcher"}])

    def test_record_trace_classifies_organizations_swarms_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("organizations_swarms")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
