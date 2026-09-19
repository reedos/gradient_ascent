"""Tests for examples/skills: the model-chosen skill-loading example for the skills technique
page. Mirrors the shape of tests/test_examples.py's ExampleTraceTests and AgenticCapTests: run
end to end on a scripted StubModel, check the trace's decided_by pattern, and check both caps
force a stop.
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
from examples.skills.run import SKILLS, run  # noqa: E402

QUESTION = "Is the DW-480 drain pump covered under warranty, and for how long?"


class SkillsExampleTests(unittest.TestCase):
    def test_choosing_a_skill_and_stopping_are_the_only_model_decisions(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="load_skill", arguments={"name": "warranty-checklist"})]),
                StubResponse(text="Covered: the 2-year warranty applies and nothing here voids it."),
            ]
        )
        tracer = Tracer(example="skills", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer)
        self.assertEqual(tracer.model_decided_count(), 2)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertTrue(all(s.kind == "model" for s in model_steps))
        self.assertTrue(all(s.edge == "dashed" for s in model_steps))
        self.assertEqual(answer.citations, ["warranty-checklist"])

    def test_the_loaded_skill_body_reaches_the_model(self) -> None:
        seen_bodies = []

        def responder(messages, tools):
            text = "\n".join(str(m.content) for m in messages)
            if "warranty-checklist" in text and SKILLS["warranty-checklist"].body in text:
                seen_bodies.append(True)
            if not seen_bodies:
                return StubResponse(tool_calls=[ToolCall(name="load_skill", arguments={"name": "warranty-checklist"})])
            return StubResponse(text="Covered under the 2-year warranty.")

        tracer = Tracer(example="skills", level=5, model_id="stub-1")
        run(QUESTION, StubModel(responder), None, tracer)
        self.assertTrue(seen_bodies, "the skill's body never reached a later prompt")

    def test_an_unknown_skill_name_is_reported_rather_than_raised(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="load_skill", arguments={"name": "does-not-exist"})]),
                StubResponse(text="I could not find that skill."),
            ]
        )
        tracer = Tracer(example="skills", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer)
        load_steps = [s for s in tracer.steps if s.title == "Load the skill body into context"]
        self.assertEqual(len(load_steps), 1)
        self.assertIn("unknown skill", load_steps[0].detail)
        self.assertEqual(answer.citations, [], "an unknown skill is never counted as loaded")

    def test_loading_a_skill_and_returning_its_body_are_always_code(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="load_skill", arguments={"name": "unit-conversion"})]),
                StubResponse(text="10 gallons is about 37.85 liters."),
            ]
        )
        tracer = Tracer(example="skills", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer)
        code_steps = [s for s in tracer.steps if s.title == "Load the skill body into context"]
        self.assertTrue(code_steps)
        for step in code_steps:
            self.assertEqual(step.decided_by, "code")
            self.assertEqual(step.kind, "code")

    def test_the_descriptions_are_listed_before_any_skill_is_loaded(self) -> None:
        model = StubModel([StubResponse(text="No skill needed for this one.")])
        tracer = Tracer(example="skills", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer)
        listing_steps = [s for s in tracer.steps if s.title.startswith("List skill descriptions")]
        self.assertEqual(len(listing_steps), 1)
        for skill in SKILLS.values():
            self.assertIn(skill.name, listing_steps[0].detail)
            self.assertIn(skill.description, listing_steps[0].detail)
            # only the description is listed up front, never the longer body
            self.assertNotIn(skill.body, listing_steps[0].detail)

    def test_step_cap_forces_a_stop(self) -> None:
        def always_load(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="load_skill", arguments={"name": "citation-style"})])

        model = StubModel(always_load, model_id="stub-loop")
        tracer = Tracer(example="skills", level=5, model_id="stub-loop")
        answer = run(QUESTION, model, None, tracer, max_steps=3)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertEqual(forced[0].decided_by, "code")
        self.assertIn("step cap", forced[0].detail)
        self.assertIsInstance(answer.text, str)

    def test_token_budget_forces_a_stop_before_the_step_cap(self) -> None:
        def always_load(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="load_skill", arguments={"name": "citation-style"})])

        model = StubModel(always_load, model_id="stub-loop")
        tracer = Tracer(example="skills", level=5, model_id="stub-loop")
        run(QUESTION, model, None, tracer, max_steps=50, max_tokens=1)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        self.assertLess(len(tracer.steps), 10)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.skills.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 5)


if __name__ == "__main__":
    unittest.main()
