"""Tests for examples/evaluator_optimizer: the write-and-check example for the
evaluator-optimizer technique page. Mirrors the shape of tests/test_examples.py's
ExampleTraceTests: run end to end on a scripted StubModel and check the trace's decided_by
pattern, plus the loop's own behavior (early exit on a pass, and the hard cap when it never
passes).
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
from examples.evaluator_optimizer.run import PASS_TOKEN, run  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "How often should the DW-300's filter be cleaned?"


class EvaluatorOptimizerExampleTests(unittest.TestCase):
    def test_a_draft_that_passes_immediately_makes_exactly_two_calls(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6"),
            StubResponse(text=PASS_TOKEN),
        ])
        tracer = Tracer(example="evaluator_optimizer", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "draft + one check, no revision")
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(answer.citations, ["dw300-manual#6"])
        self.assertFalse(any(s.title == "Stop: revision cap reached" for s in tracer.steps))

    def test_a_bad_citation_is_caught_and_fixed_within_the_cap(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6"),
            StubResponse(text=PASS_TOKEN),
        ])
        tracer = Tracer(example="evaluator_optimizer", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        revise_steps = [s for s in tracer.steps if s.title == "Revise using the checker's feedback"]
        self.assertEqual(len(revise_steps), 1, "should stop revising once the second check passes")
        self.assertNotIn("recall-notice#1", answer.citations)
        self.assertEqual(answer.citations, ["dw300-manual#6"])
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))

    def test_a_draft_that_never_passes_stops_at_the_cap_and_still_returns_an_answer(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
        ])
        tracer = Tracer(example="evaluator_optimizer", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_revisions=2)
        revise_steps = [s for s in tracer.steps if s.title == "Revise using the checker's feedback"]
        check_steps = [s for s in tracer.steps if s.title == "Check citations against the sources"]
        self.assertEqual(len(revise_steps), 2, "must not exceed max_revisions")
        self.assertEqual(len(check_steps), 3, "one check before any revision, then one after each of the 2 revisions")
        stop_steps = [s for s in tracer.steps if s.title == "Stop: revision cap reached"]
        self.assertEqual(len(stop_steps), 1)
        self.assertIn("2 revision", stop_steps[0].detail)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps), "the cap itself must be a code decision")
        self.assertIsInstance(answer.text, str)
        self.assertTrue(answer.text)

    def test_max_revisions_zero_never_revises_even_if_the_check_fails(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
        ])
        tracer = Tracer(example="evaluator_optimizer", level=3, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_revisions=0)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "draft + one check, no revision allowed")
        self.assertTrue(any(s.title == "Stop: revision cap reached" for s in tracer.steps))

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.evaluator_optimizer.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 3)


if __name__ == "__main__":
    unittest.main()
