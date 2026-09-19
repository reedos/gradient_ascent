"""End-to-end test for the prompt-engineering example.

The technique page's claim is that a structured prompt (role, format instructions, one worked
example) gets a reply an automatic check can pass, while a bare prompt against the same facts
does not -- checkable, not just felt. Both runs go through `StubModel` with a scripted reply that
stands in for what a real model tends to do given each style of prompt; the stub itself proves
nothing about real models; the citations in `prompt-engineering.mdx` do.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.prompt_engineering.run import LEVEL, run  # noqa: E402

QUESTION = "What is the DW-480's drain pump part number and price?"


class PromptEngineeringExampleTests(unittest.TestCase):
    def test_structured_prompt_parses_and_cites_both_sources(self) -> None:
        model = StubModel([StubResponse(text="PART: HLV-2205\nPRICE: $52.00")])
        tracer = Tracer(example="prompt_engineering", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer, structured=True)
        self.assertEqual(answer.citations, ["dw480-manual#8", "parts-list#2"])
        self.assertTrue(tracer.steps, "no steps were recorded")

    def test_bare_prompt_with_no_format_instruction_fails_the_check(self) -> None:
        model = StubModel([StubResponse(
            text="I believe it's one of the HLV-22 series pumps, but I'm not certain of the exact price."
        )])
        tracer = Tracer(example="prompt_engineering", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer, structured=False)
        self.assertEqual(answer.citations, [])

    def test_every_step_is_decided_by_code(self) -> None:
        # level 1: nobody decides which step happens next, so nothing here may be model-decided
        for structured in (True, False):
            model = StubModel([StubResponse(text="PART: HLV-2205\nPRICE: $52.00")])
            tracer = Tracer(example="prompt_engineering", level=LEVEL, model_id="stub-1")
            run(QUESTION, model, tracer, structured=structured)
            self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
            self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))

    def test_the_structured_system_prompt_names_the_format_and_gives_one_example(self) -> None:
        from examples.prompt_engineering.run import STRUCTURED_SYSTEM

        self.assertIn("PART:", STRUCTURED_SYSTEM)
        self.assertIn("PRICE:", STRUCTURED_SYSTEM)
        self.assertIn("Example", STRUCTURED_SYSTEM)

    def test_structured_now_defaults_to_true_so_one_question_is_a_complete_call(self) -> None:
        # `structured` used to be required with no default, which record_trace.py's shared
        # (text, model, tracer) convention cannot fill in from --question alone. It now defaults
        # to True, so an unadorned recording captures the structured prompt; the bare-prompt run
        # is still reachable by calling run(..., structured=False) directly.
        model = StubModel([StubResponse(text="PART: HLV-2205\nPRICE: $52.00")])
        tracer = Tracer(example="prompt_engineering", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer)
        self.assertEqual(answer.citations, ["dw480-manual#8", "parts-list#2"])

    def test_record_trace_now_classifies_prompt_engineering_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("prompt_engineering")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
