"""Tests for examples/computer_use: the one-action-on-a-screen example for the computer-use
technique page (level 4).

Mirrors tests/test_example_function_calling.py's decided_by pattern, plus what is specific to
this technique: an allowed click or type actually runs, and an action against an element outside
`ALLOWED_ELEMENT_IDS` -- or a tool name outside {click, type} -- is refused rather than run, the
same way a malicious code-execution expression is refused rather than evaluated.
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
from examples.computer_use.run import ALLOWED_ELEMENT_IDS, render_screen, run  # noqa: E402


class RenderScreenTests(unittest.TestCase):
    def test_every_element_appears_with_its_id_and_label(self) -> None:
        text = render_screen([{"id": "e1", "kind": "button", "label": "Go"}])
        self.assertIn("[e1]", text)
        self.assertIn("button", text)
        self.assertIn('"Go"', text)


class ComputerUseExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.computer_use.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 4)

    def test_clicking_an_allowed_element_is_the_only_model_decided_step(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="click", arguments={"id": "search-button"})])])
        tracer = Tracer(example="computer_use", level=4, model_id="stub-1")
        answer = run("Search for warranty information", model, None, tracer)
        self.assertEqual(tracer.model_decided_count(), 1)
        decided_by_model = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(decided_by_model), 1)
        self.assertEqual(answer.text, "Clicked search-button.")

    def test_typing_into_an_allowed_field_runs(self) -> None:
        model = StubModel(
            [StubResponse(tool_calls=[ToolCall(name="type", arguments={"id": "search-box", "text": "warranty"})])]
        )
        tracer = Tracer(example="computer_use", level=4, model_id="stub-1")
        answer = run("Search for warranty information", model, None, tracer)
        self.assertEqual(answer.text, "Typed 'warranty' into search-box.")

    def test_clicking_an_element_off_the_allowlist_is_refused(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="click", arguments={"id": "delete-account"})])])
        tracer = Tracer(example="computer_use", level=4, model_id="stub-1")
        answer = run("Delete the account", model, None, tracer)
        self.assertTrue(answer.text.startswith("Refused:"))
        self.assertNotIn("delete-account", ALLOWED_ELEMENT_IDS)
        refusal = next(s for s in tracer.steps if s.title.startswith("Action refused"))
        self.assertEqual(refusal.decided_by, "code")
        # the model's own choice is still the one recorded model-decided step; refusing it is code's call
        self.assertEqual(tracer.model_decided_count(), 1)

    def test_clicking_the_cookie_button_is_also_refused(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="click", arguments={"id": "cookie-accept"})])])
        tracer = Tracer(example="computer_use", level=4, model_id="stub-1")
        answer = run("Accept the cookies", model, None, tracer)
        self.assertTrue(answer.text.startswith("Refused:"))

    def test_an_action_outside_click_and_type_is_refused_even_with_an_allowed_id(self) -> None:
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="run_shell", arguments={"id": "search-box"})])])
        tracer = Tracer(example="computer_use", level=4, model_id="stub-1")
        answer = run("Do something else", model, None, tracer)
        self.assertTrue(answer.text.startswith("Refused:"))

    def test_no_action_is_still_the_one_model_decided_step(self) -> None:
        model = StubModel([StubResponse(text="The search box is already focused; nothing to do.")])
        tracer = Tracer(example="computer_use", level=4, model_id="stub-1")
        answer = run("Check the search box", model, None, tracer)
        self.assertEqual(tracer.model_decided_count(), 1)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertEqual(answer.text, "The search box is already focused; nothing to do.")

    def test_the_run_never_takes_a_second_screenshot(self) -> None:
        """The level-4/level-5 boundary this page draws: exactly one screen render per run,
        never a loop back to render_screen after an action."""
        model = StubModel([StubResponse(tool_calls=[ToolCall(name="click", arguments={"id": "search-button"})])])
        tracer = Tracer(example="computer_use", level=4, model_id="stub-1")
        run("Search", model, None, tracer)
        render_steps = [s for s in tracer.steps if s.title == "Render the screen as text"]
        self.assertEqual(len(render_steps), 1)


if __name__ == "__main__":
    unittest.main()
