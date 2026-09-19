"""Tests for examples/function_calling: the one-tool-call-at-most example for the function-calling
technique page (level 4).

Mirrors the shape of tests/test_example_routing.py: run the example end to end on a scripted
StubModel and check the trace's decided_by pattern (docs/EVALS.md: level 4 records exactly one
model-decided step per run, the tool call or the decision to answer without one) alongside the
function-calling-specific behaviour -- which tool ran, that a second requested call is dropped
rather than run, and that an unrecognized tool name does not raise.
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
from examples.function_calling.run import run  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"


class FunctionCallingExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.function_calling.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 4)

    def test_a_tool_call_is_the_only_model_decided_step(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2205"})]),
                StubResponse(text="Part HLV-2205 is a drain pump and costs $52.00. Sources: parts-list#2"),
            ]
        )
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        answer = run("What does part HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.model_decided_count(), 1, "exactly one step should be decided_by model")
        decided_by_model = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(decided_by_model), 1)
        self.assertIn("lookup_part", decided_by_model[0].title)
        self.assertIn("52.00", answer.text)
        self.assertIn("parts-list#2", answer.citations)

    def test_answering_without_a_tool_is_still_the_one_model_decided_step(self) -> None:
        model = StubModel([StubResponse(text="A dishwasher and a dryer are both major appliances.")])
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        answer = run("What is a major appliance?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.model_decided_count(), 1, "declining to call a tool is still a model decision")
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "no second call when nothing was run")
        self.assertEqual(answer.text, "A dishwasher and a dryer are both major appliances.")
        self.assertEqual(answer.citations, [])

    def test_a_second_requested_tool_call_is_dropped_not_run(self) -> None:
        model = StubModel(
            [
                StubResponse(
                    tool_calls=[
                        ToolCall(name="lookup_part", arguments={"part_number": "HLV-2205"}),
                        ToolCall(name="search", arguments={"query": "drain pump"}),
                    ]
                ),
                StubResponse(text="Part HLV-2205 costs $52.00."),
            ]
        )
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        run("What does part HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        call_step = next(s for s in tracer.steps if s.title.startswith("Model calls"))
        self.assertIn("dropped 1 further call", call_step.detail)
        # only the first tool actually ran
        run_steps = [s for s in tracer.steps if s.title.startswith("Run tool")]
        self.assertEqual(len(run_steps), 1)
        self.assertIn("lookup_part", run_steps[0].title)

    def test_the_final_call_is_never_offered_a_tool_so_the_run_cannot_grow_past_one_call(self) -> None:
        # A second tool call would show up as a second StubResponse with tool_calls that never
        # gets consumed; StubModel raises IndexError only if `complete` is called a third time,
        # so two scripted responses are enough to prove the run stops after the follow-up call.
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "warranty"})]),
                StubResponse(text="Two years from delivery."),
            ]
        )
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        run("How long is the warranty?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "one tool call, one follow-up, then stop")

    def test_an_unrecognized_tool_name_is_reported_rather_than_raised(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="delete_everything", arguments={})]),
                StubResponse(text="I could not do that."),
            ]
        )
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        answer = run("Do something unsupported", model, None, tracer, corpus_dir=CORPUS_DIR)
        run_step = next(s for s in tracer.steps if s.title.startswith("Run tool"))
        self.assertIn("unknown tool", run_step.detail)
        self.assertEqual(answer.citations, [])

    def test_a_part_number_not_in_the_parts_list_is_reported_not_found(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-9999"})]),
                StubResponse(text="That part is not in the parts list."),
            ]
        )
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        answer = run("What does part HLV-9999 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        run_step = next(s for s in tracer.steps if s.title.startswith("Run tool"))
        self.assertIn("not found", run_step.detail)
        self.assertEqual(answer.citations, [])


if __name__ == "__main__":
    unittest.main()
