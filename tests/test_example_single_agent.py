"""Tests for examples/single_agent: the plan-and-execute example for the single-agent technique
page. Mirrors the shape of tests/test_examples.py's ExampleTraceTests and AgenticCapTests: run
end to end on a scripted StubModel and check the trace's decided_by pattern, then check the step
cap and the token budget each force a stop.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.single_agent.__main__ import SCRIPTED  # noqa: E402
from examples.single_agent.run import run  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "What does the DW-300's drain pump cost, and how long is it under warranty?"

# The canonical end-to-end sequence: a plan, two actions on it, then the stop. Mirrored in
# examples/single_agent/__main__.py's SCRIPTED.
SEQUENCE = [
    StubResponse(text="1. Search for the warranty term. 2. Look up the part price."),
    StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 full warranty parts and labor"})]),
    StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
    StubResponse(text="$46.00, covered in full for 2 years. Sources: parts-list#2, warranty-policy#1"),
]


class SingleAgentExampleTests(unittest.TestCase):
    def test_the_plan_is_a_model_step_the_code_decided_to_make(self) -> None:
        # the plan call is kind "model" (a model ran) but decided_by "code" (the program always
        # makes this call and always moves on to the loop, whatever the plan says)
        model = StubModel(
            [
                StubResponse(text="1. Look up the drain pump price. 2. Check the warranty length."),
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
                StubResponse(text="$46.00, covered for 2 years. Sources: parts-list#2, warranty-policy#1"),
            ]
        )
        tracer = Tracer(example="single_agent", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        plan_steps = [s for s in tracer.steps if s.title == "Model writes a plan"]
        self.assertEqual(len(plan_steps), 1)
        self.assertEqual(plan_steps[0].kind, "model")
        self.assertEqual(plan_steps[0].decided_by, "code")
        self.assertEqual(plan_steps[0].edge, "solid")

    def test_records_a_model_decided_step_for_every_action_and_the_stop(self) -> None:
        model = StubModel(list(SEQUENCE))
        tracer = Tracer(example="single_agent", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        # two actions plus the stop: three model-decided steps; the plan itself is not one of them
        self.assertEqual(tracer.model_decided_count(), 3)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertTrue(all(s.kind == "model" for s in model_steps))
        self.assertTrue(all(s.edge == "dashed" for s in model_steps))
        self.assertIn("parts-list#2", answer.citations)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, `python -m examples.single_agent --model stub:scripted`
        stops demonstrating the loop this test says the example runs."""
        self.assertEqual(list(SCRIPTED), SEQUENCE)

    def test_every_section_the_scripted_answer_cites_was_really_retrieved(self) -> None:
        # This example's citations come from the tools, not from the reply. A scripted answer
        # citing something retrieval never found would print an answer and a citation list that
        # contradict each other.
        model = StubModel(list(SEQUENCE))
        tracer = Tracer(example="single_agent", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        claimed = set(re.findall(r"[a-z0-9-]+#\d+", SEQUENCE[-1].text))
        self.assertTrue(claimed, "the scripted final answer cites nothing")
        self.assertTrue(claimed <= set(answer.citations), f"{claimed - set(answer.citations)} was never retrieved")

    def test_running_a_tool_and_returning_its_result_are_always_code(self) -> None:
        model = StubModel(
            [
                StubResponse(text="1. Look up the part."),
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
                StubResponse(text="$46.00."),
            ]
        )
        tracer = Tracer(example="single_agent", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        tool_steps = [s for s in tracer.steps if s.title.startswith("Run tool")]
        self.assertTrue(tool_steps, "no tool step was recorded")
        for step in tool_steps:
            self.assertEqual(step.decided_by, "code")
            self.assertEqual(step.kind, "code")
            self.assertEqual(step.edge, "solid")

    def test_step_cap_forces_a_stop_and_the_forced_answer_is_codes_decision(self) -> None:
        # the plan call returns fixed text; the loop that follows then never stops on its own
        responses_used = {"n": 0}

        def responder(messages, tools):
            responses_used["n"] += 1
            if responses_used["n"] == 1:
                return StubResponse(text="1. Keep searching.")
            return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "warranty"})])

        model = StubModel(responder, model_id="stub-loop")
        tracer = Tracer(example="single_agent", level=5, model_id="stub-loop")
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
        responses_used = {"n": 0}

        def responder(messages, tools):
            responses_used["n"] += 1
            if responses_used["n"] == 1:
                return StubResponse(text="1. Keep searching.")
            return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "warranty"})])

        model = StubModel(responder, model_id="stub-loop")
        tracer = Tracer(example="single_agent", level=5, model_id="stub-loop")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_steps=50, max_tokens=1)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        self.assertLess(len(tracer.steps), 10, "the loop should stop almost immediately, not run near 50 steps")

    def test_an_unknown_tool_is_reported_to_the_model_rather_than_raised(self) -> None:
        model = StubModel(
            [
                StubResponse(text="1. Try a tool."),
                StubResponse(tool_calls=[ToolCall(name="delete_everything", arguments={})]),
                StubResponse(text="I could not find that."),
            ]
        )
        tracer = Tracer(example="single_agent", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIn("unknown tool", " ".join(s.detail for s in tracer.steps))
        self.assertIsInstance(answer.text, str)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.single_agent.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 5)


if __name__ == "__main__":
    unittest.main()
