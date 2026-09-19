"""Tests for examples/human_in_the_loop: pause on a fixed threshold, resume with an injected
reviewer decision. Mirrors the shape of tests/test_examples.py's ExampleTraceTests, plus the
pause/resume split this technique adds: `run` on a StubModel, and a scripted reviewer function
standing in for a person, feeding a decision back into `resume`.
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
from examples.human_in_the_loop.run import PendingReview, resume, run  # noqa: E402
from examples.human_in_the_loop.__main__ import SCRIPTED  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"

# The one reply examples/human_in_the_loop/__main__.py scripts for `--model stub:scripted`: a
# draft naming a real dollar figure, which trips the high_cost threshold and pauses the run.
SEQUENCE = ["It costs $52.00. Sources: parts-list#2"]


def _scripted_reviewer(pending: PendingReview) -> str:
    """Stands in for a person: approves a low-confidence draft with no changes, and always
    approves a high-cost one after reading it (the point being that a person, not code, makes
    this call — the test just needs a deterministic stand-in)."""
    return "approve"


class HumanInTheLoopExampleTests(unittest.TestCase):
    def test_a_confident_cheap_draft_returns_an_answer_with_no_pause(self) -> None:
        model = StubModel([StubResponse(text="Every 30 cycles. Sources: dw300-manual#6")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        result = run("How often should the DW-300's filter be cleaned?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertFalse(isinstance(result, PendingReview))
        self.assertEqual(result.citations, ["dw300-manual#6"])
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertFalse(any(s.title == "Pause for human approval" for s in tracer.steps))

    def test_a_draft_with_no_citation_pauses_as_low_confidence(self) -> None:
        model = StubModel([StubResponse(text="I do not have that information.")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        result = run("What color is the DW-300?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIsInstance(result, PendingReview)
        self.assertEqual(result.reason, "low_confidence")
        pause_steps = [s for s in tracer.steps if s.title == "Pause for human approval"]
        self.assertEqual(len(pause_steps), 1)
        self.assertEqual(pause_steps[0].detail, "low_confidence")

    def test_a_draft_naming_a_dollar_figure_pauses_as_high_cost(self) -> None:
        model = StubModel([StubResponse(text="It costs $52.00. Sources: parts-list#2")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        result = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIsInstance(result, PendingReview)
        self.assertEqual(result.reason, "high_cost")

    def test_every_step_is_decided_by_code_even_when_paused(self) -> None:
        model = StubModel([StubResponse(text="It costs $52.00. Sources: parts-list#2")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_resume_approve_ships_the_original_draft_unchanged(self) -> None:
        model = StubModel([StubResponse(text="It costs $52.00. Sources: parts-list#2")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        pending = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        decision = _scripted_reviewer(pending)
        answer = resume(pending, decision, tracer)
        self.assertIn("52.00", answer.text)
        self.assertEqual(answer.citations, pending.citations)

    def test_resume_edit_replaces_the_draft_with_the_reviewers_note(self) -> None:
        model = StubModel([StubResponse(text="It costs $52.00. Sources: parts-list#2")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        pending = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        answer = resume(pending, "edit", tracer, note="It costs $54.00 as of this week's price update.")
        self.assertEqual(answer.text, "It costs $54.00 as of this week's price update.")
        self.assertEqual(answer.citations, pending.citations)

    def test_resume_reject_ships_no_answer_and_no_citations(self) -> None:
        model = StubModel([StubResponse(text="It costs $52.00. Sources: parts-list#2")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        pending = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        answer = resume(pending, "reject", tracer)
        self.assertEqual(answer.citations, [])
        self.assertIn("rejected", answer.text)

    def test_resume_itself_is_decided_by_code(self) -> None:
        model = StubModel([StubResponse(text="It costs $52.00. Sources: parts-list#2")])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        pending = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        before = len(tracer.steps)
        resume(pending, "approve", tracer)
        after_steps = tracer.steps[before:]
        self.assertTrue(after_steps)
        self.assertTrue(all(s.decided_by == "code" for s in after_steps))

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.human_in_the_loop.run as module

        self.assertTrue(callable(module.run))
        self.assertTrue(callable(module.resume))
        self.assertEqual(module.LEVEL, 3)


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)

    def test_the_scripted_sequence_pauses_for_high_cost(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        result = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIsInstance(result, PendingReview)
        self.assertEqual(result.reason, "high_cost")

    def test_approve_and_reject_resume_to_visibly_different_answers(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="human_in_the_loop", level=3, model_id="stub-1")
        pending = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        approved = resume(pending, "approve", tracer)
        rejected = resume(pending, "reject", tracer)
        self.assertNotEqual(approved.text, rejected.text)
        self.assertIn("52.00", approved.text)
        self.assertEqual(rejected.citations, [])


if __name__ == "__main__":
    unittest.main()
