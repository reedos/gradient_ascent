"""End-to-end test for the inference-time-reasoning example: majority vote over five scripted
samples picks the answer most of them agree on, not the first one or the last one."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.inference_time_reasoning.__main__ import SCRIPTED  # noqa: E402
from examples.inference_time_reasoning.run import LEVEL, N_SAMPLES, run  # noqa: E402

QUESTION = "What is the total price to replace the heating elements on both a DW-300 and a DW-480?"
SEQUENCE = [
    "Working through it...\nHLV-4471 (DW-300 heating element) is $38.50, and HLV-4472 (DW-480 "
    "heating element) is $41.00. $38.50 + $41.00 = $79.50.\nAnswer: 79.50",
    "Working through it...\n$38.50 + $41.00 = $79.50.\nAnswer: 79.50",
    "Working through it...\nRounding as I go: about $38.50 + $41.00 comes to $79.00.\nAnswer: 79.00",
    "Working through it...\n$38.50 + $41.00 = $79.50.\nAnswer: 79.50",
    "Working through it...\nCarried a digit wrong: $38.50 + $41.00 = $80.50.\nAnswer: 80.50",
]


def _sample(text: str) -> StubResponse:
    return StubResponse(text=f"Working through it...\nAnswer: {text}")


class InferenceTimeReasoningExampleTests(unittest.TestCase):
    def test_majority_answer_wins_over_two_dissenting_samples(self) -> None:
        # 38.50 + 41.00 = 79.50; three samples get it right, two slip in different directions
        model = StubModel([_sample("79.50"), _sample("79.50"), _sample("79.00"), _sample("79.50"), _sample("80.50")])
        tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer, n=5)
        self.assertIn("79.50", answer.text)
        self.assertIn("3/5", answer.text)

    def test_a_unanimous_vote_is_reported_as_five_of_five(self) -> None:
        model = StubModel([_sample("79.50")] * 5)
        tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer, n=5)
        self.assertIn("5/5", answer.text)

    def test_a_sample_with_no_answer_line_counts_as_no_answer_not_a_crash(self) -> None:
        model = StubModel(
            [_sample("79.50"), _sample("79.50"), StubResponse(text="I'm not sure, sorry."), _sample("79.50")]
        )
        tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer, n=4)
        self.assertIn("79.50", answer.text)
        self.assertIn("3/4", answer.text)

    def test_samples_the_model_exactly_n_times(self) -> None:
        model = StubModel([_sample("79.50")] * 3)
        tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id="stub-1")
        run(QUESTION, model, tracer, n=3)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 3)

    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel([_sample("79.50")] * N_SAMPLES)
        tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id="stub-1")
        run(QUESTION, model, tracer)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertTrue(tracer.steps)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))
        self.assertEqual(N_SAMPLES, 5)


class ScriptedCommandTests(unittest.TestCase):
    """The sequence `python -m examples.inference_time_reasoning --model stub:scripted` plays,
    run the same way the CLI runs it, plus the guard that keeps the two in step."""

    def test_the_scripted_sequence_s_majority_lands_on_the_correct_total(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="inference_time_reasoning", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer, n=5)
        self.assertIn("79.50", answer.text)
        self.assertIn("3/5", answer.text)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)


if __name__ == "__main__":
    unittest.main()
