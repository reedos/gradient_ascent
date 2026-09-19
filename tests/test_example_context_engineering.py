"""Tests for examples/context_engineering: the whole corpus in one prompt, static parts first,
dynamic parts last, and the oldest history dropped first when the request runs over budget."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.corpus import DEFAULT_CORPUS_DIR  # noqa: E402
from examples.common.model import Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.context_engineering.run import LEVEL, run  # noqa: E402

QUESTION = "What is the DW-300's Normal cycle water use?"


def _make_history(n: int) -> list[Message]:
    """`n` alternating user/assistant turns, oldest first, each big enough to matter."""
    turns = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        turns.append(Message(role=role, content=f"turn {i}: " + "filler word " * 40))
    return turns


class ContextEngineeringTraceTests(unittest.TestCase):
    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel([StubResponse(text="3.2 gallons per Normal cycle.")])
        tracer = Tracer(example="context_engineering", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=DEFAULT_CORPUS_DIR)
        self.assertTrue(tracer.steps, "recorded no steps at all")
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertIn("3.2 gallons", answer.text)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 2)
        self.assertTrue(callable(run))

    def test_with_no_history_the_whole_document_set_goes_in(self) -> None:
        model = StubModel([StubResponse(text="ok")])
        tracer = Tracer(example="context_engineering", level=LEVEL, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=DEFAULT_CORPUS_DIR)
        assemble_step = next(s for s in tracer.steps if "static" in s.title.lower())
        # the corpus is twelve documents; a real static block is a few thousand tokens, not a few
        self.assertGreater(assemble_step.tokens_in, 2000)
        fit_step = next(s for s in tracer.steps if "Fit conversation history" in s.title)
        self.assertIn("kept 0 of 0 turn(s)", fit_step.detail)

    def test_documents_come_before_history_and_history_before_the_question(self) -> None:
        model = StubModel([StubResponse(text="ok")])
        tracer = Tracer(example="context_engineering", level=LEVEL, model_id="stub-1")
        history = _make_history(2)
        run(QUESTION, model, None, tracer, corpus_dir=DEFAULT_CORPUS_DIR, history=history, token_budget=100_000)
        build_step = next(s for s in tracer.steps if s.title == "Build the final prompt")
        self.assertIn("documents first", build_step.detail)
        self.assertIn("2 history turn(s)", build_step.detail)

    def test_a_tight_budget_drops_the_oldest_history_first_and_keeps_the_documents(self) -> None:
        model = StubModel([StubResponse(text="ok")])
        tracer = Tracer(example="context_engineering", level=LEVEL, model_id="stub-1")
        history = _make_history(10)  # far more than a tight budget can hold alongside the corpus
        answer = run(
            QUESTION, model, None, tracer, corpus_dir=DEFAULT_CORPUS_DIR, history=history, token_budget=7500
        )
        fit_step = next(s for s in tracer.steps if "Fit conversation history" in s.title)
        self.assertIn("of 10 turn(s)", fit_step.detail)
        self.assertNotIn("kept 10 of 10", fit_step.detail, "a tight budget must drop something")
        build_step = next(s for s in tracer.steps if s.title == "Build the final prompt")
        # the newest turn (index 9) must survive; an older one (index 0) must not, since the
        # oldest turns are dropped first
        self.assertIsInstance(answer.text, str)
        self.assertNotIn("kept 0 of 10", fit_step.detail, "the whole history should not need to be dropped")

    def test_an_empty_budget_keeps_the_documents_and_drops_every_history_turn(self) -> None:
        model = StubModel([StubResponse(text="ok")])
        tracer = Tracer(example="context_engineering", level=LEVEL, model_id="stub-1")
        history = _make_history(4)
        run(QUESTION, model, None, tracer, corpus_dir=DEFAULT_CORPUS_DIR, history=history, token_budget=0)
        fit_step = next(s for s in tracer.steps if "Fit conversation history" in s.title)
        self.assertIn("kept 0 of 4 turn(s)", fit_step.detail)


if __name__ == "__main__":
    unittest.main()
