"""Tests for examples/agentic_rag: the search-then-read loop for the agentic-rag technique page.
Mirrors the shape of tests/test_example_single_agent.py and tests/test_example_agent_harness.py:
run end to end on a scripted StubModel and check the trace's decided_by pattern, then check the
step cap and the token budget each force a stop. The same behavior is also exercised inside the
shared tests/test_examples.py (which this file does not replace); this file gives agentic_rag its
own page-scoped test module, the same way single_agent and agent_harness already have one.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.agentic_rag.run import run  # noqa: E402
from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "How often should the DW-300's filter be cleaned?"


class AgenticRagExampleTests(unittest.TestCase):
    def test_records_a_model_decided_step_for_every_tool_call_and_the_stop(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 filter"})]),
                StubResponse(tool_calls=[ToolCall(name="read", arguments={"cite": "dw300-manual#6"})]),
                StubResponse(text="Every 30 cycles, per dw300-manual#6."),
            ]
        )
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        # one search call, one read call, one stop: three model-decided steps
        self.assertEqual(tracer.model_decided_count(), 3)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertTrue(all(s.kind == "model" for s in model_steps))
        self.assertTrue(all(s.edge == "dashed" for s in model_steps))
        self.assertEqual(answer.citations, ["dw300-manual#6"])

    def test_running_a_tool_and_returning_its_result_are_always_code(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "filter"})]),
                StubResponse(text="25 cycles."),
            ]
        )
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        tool_steps = [s for s in tracer.steps if s.title.startswith("Run tool")]
        self.assertTrue(tool_steps, "no tool step was recorded")
        for step in tool_steps:
            self.assertEqual(step.decided_by, "code")
            self.assertEqual(step.kind, "code")
            self.assertEqual(step.edge, "solid")

    def test_step_cap_forces_a_stop_and_the_forced_answer_is_codes_decision(self) -> None:
        def always_search(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "filter"})])

        model = StubModel(always_search, model_id="stub-loop")
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-loop")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_steps=3)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertEqual(forced[0].decided_by, "code")
        self.assertIn("step cap", forced[0].detail)
        self.assertIsInstance(answer.text, str)
        # the model never chose to stop, so the stop is not counted as its decision
        stop_steps = [s for s in tracer.steps if s.title == "Model stops and answers"]
        self.assertEqual(len(stop_steps), 0)

    def test_token_budget_forces_a_stop_before_the_step_cap(self) -> None:
        def always_search(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "filter"})])

        model = StubModel(always_search, model_id="stub-loop")
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-loop")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_steps=50, max_tokens=1)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        self.assertLess(len(tracer.steps), 10, "the loop should stop almost immediately, not run near 50 steps")

    def test_an_unknown_tool_is_reported_to_the_model_rather_than_raised(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="delete_everything", arguments={})]),
                StubResponse(text="I could not find that."),
            ]
        )
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIn("unknown tool", " ".join(s.detail for s in tracer.steps))
        self.assertIsInstance(answer.text, str)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.agentic_rag.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 5)


if __name__ == "__main__":
    unittest.main()
