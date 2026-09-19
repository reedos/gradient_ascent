"""Tests for examples/parallelization: sectioning, run on a StubModel.

The StubModel here must be built from a callable (a pure function of the messages), never from a
fixed response list: the example calls the model from several threads at once, and a fixed-list
StubModel advances a shared counter with no lock, which is not safe to call concurrently. A
callable that reads which section's citation appears in the prompt has no shared mutable state,
so it is safe under `ThreadPoolExecutor` and it is what keeps this test deterministic regardless
of which thread's call actually finishes first.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.parallelization.run import NO_ANSWER, run  # noqa: E402
from examples.parallelization.__main__ import SCRIPTED  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "What is the DW-480's Normal cycle water use, and how often should its filter be cleaned?"

# The real top-3 candidates bm25 returns for QUESTION, confirmed against the actual corpus.
CANDIDATES = ["care-and-cleaning-guide#1", "dw480-manual#3", "dw480-manual#6"]

# The same three replies examples/parallelization/__main__.py scripts for `--model stub:scripted`,
# one per candidate above, in that order.
SEQUENCE = [
    NO_ANSWER,
    "The Normal cycle uses 3.0 gallons of water.",
    "The DW-480's filter is self-cleaning and needs no routine cleaning.",
]


def _keyed_responder(answers: dict[str, str]):
    """A StubModel responder that answers based on which section citation is in the prompt, so
    the result does not depend on call order."""

    def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
        del tools
        prompt = messages[-1].content
        for cite, text in answers.items():
            if f"[{cite}]" in prompt:
                return StubResponse(text=text)
        raise AssertionError(f"no scripted answer for prompt: {prompt[:120]!r}")

    return responder


class ParallelizationExampleTests(unittest.TestCase):
    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel(_keyed_responder({
            "care-and-cleaning-guide#1": "The DW-480's filter is self-cleaning and needs no routine cleaning.",
            "dw480-manual#6": "The DW-480's filter is self-cleaning and needs no routine cleaning.",
            "dw480-manual#3": "The Normal cycle uses 3.0 gallons of water.",
        }))
        tracer = Tracer(example="parallelization", level=3, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps), "parallelization recorded a model-decided step")
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_sections_that_answer_part_of_the_question_are_combined_and_cited(self) -> None:
        model = StubModel(_keyed_responder({
            "care-and-cleaning-guide#1": NO_ANSWER,
            "dw480-manual#6": "The DW-480's filter is self-cleaning and needs no routine cleaning.",
            "dw480-manual#3": "The Normal cycle uses 3.0 gallons of water.",
        }))
        tracer = Tracer(example="parallelization", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIn("self-cleaning", answer.text)
        self.assertIn("3.0 gallons", answer.text)
        self.assertEqual(answer.citations, sorted(["dw480-manual#6", "dw480-manual#3"]))
        combine_step = next(s for s in tracer.steps if s.title == "Combine the sections that answered")
        self.assertIn("2 of 3", combine_step.detail)

    def test_a_declining_section_never_contributes_a_citation(self) -> None:
        model = StubModel(_keyed_responder({
            "care-and-cleaning-guide#1": NO_ANSWER,
            "dw480-manual#3": "The Normal cycle uses 3.0 gallons of water.",
            "dw480-manual#6": NO_ANSWER,
        }))
        tracer = Tracer(example="parallelization", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(answer.citations, ["dw480-manual#3"])
        self.assertNotIn("care-and-cleaning-guide#1", answer.citations)

    def test_no_section_answering_returns_a_clear_empty_result_rather_than_guessing(self) -> None:
        model = StubModel(_keyed_responder({c: NO_ANSWER for c in CANDIDATES}))
        tracer = Tracer(example="parallelization", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(answer.citations, [])
        self.assertIn("None of the retrieved sections answered", answer.text)

    def test_candidate_order_is_retrieval_order_not_completion_order(self) -> None:
        model = StubModel(_keyed_responder({
            "care-and-cleaning-guide#1": "cleaning answer",
            "dw480-manual#6": "cleaning answer",
            "dw480-manual#3": "water answer",
        }))
        tracer = Tracer(example="parallelization", level=3, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        pick_step = next(s for s in tracer.steps if s.title == "Pick sections to answer in parallel")
        self.assertEqual(pick_step.detail, ", ".join(CANDIDATES))
        model_steps = [s for s in tracer.steps if s.kind == "model"]
        self.assertEqual([s.title for s in model_steps], [f"Answer from {c} alone" for c in CANDIDATES])

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.parallelization.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 3)


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)

    def test_the_scripted_sequence_is_stable_under_real_concurrent_calls(self) -> None:
        # examples/common/cli.py's scripted stub answers by a shared, unlocked call counter, and
        # run() fires all three calls from a real ThreadPoolExecutor rather than one at a time.
        # Executor.map submits futures in candidate order and returns results in that same order
        # regardless of which thread finishes first, so this should be stable; run it several
        # times against the real scripted stub (not the keyed responder the other tests use) to
        # catch the case where it is not.
        from examples.common.cli import scripted_stub

        for _ in range(20):
            model = scripted_stub(SCRIPTED, example="parallelization")
            tracer = Tracer(example="parallelization", level=3, model_id="stub-scripted")
            answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
            self.assertEqual(answer.citations, sorted(["dw480-manual#3", "dw480-manual#6"]))
            self.assertIn("3.0 gallons", answer.text)
            self.assertIn("self-cleaning", answer.text)


if __name__ == "__main__":
    unittest.main()
