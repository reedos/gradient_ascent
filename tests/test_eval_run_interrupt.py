"""A stopped run must leave something a person can read.

`docs/FIRST-LIVE-RUN.md` tells the owner that Ctrl+C is safe at any point. It was safe for his
wallet (every answer is cached by model id and prompt hash, so a resume re-pays only for the
question in flight) but not for his time: the runner held every finished question in memory and
wrote the result file only after the last one, so Ctrl+C at question 55 of 60 threw away 54
graded answers and printed a traceback. Now the partial result is written, marked
`"interrupted": true`, and the runner stops instead of rolling on to the next example.

These tests raise `KeyboardInterrupt` from inside a scripted model, which is where a real Ctrl+C
lands during a run: in the middle of a `complete` call waiting on a model.
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import eval_run  # noqa: E402
from examples.common.model import Completion, Message, StubEmbedder  # noqa: E402

_STDOUT: contextlib.AbstractContextManager | None = None


def setUpModule() -> None:
    global _STDOUT
    _STDOUT = contextlib.redirect_stdout(io.StringIO())
    _STDOUT.__enter__()


def tearDownModule() -> None:
    if _STDOUT is not None:
        _STDOUT.__exit__(None, None, None)


def _questions(n: int) -> list[dict]:
    """n questions the stub answers correctly, so any shortfall in `questions_run` is the
    interrupt and not a grading result. The wording differs per question on purpose: `main` wraps
    the model in `CachingModel`, which keys on the prompt, so identical questions would be
    answered once and served from cache five times and the scripted interrupt would never fire."""
    return [
        {
            "id": f"K{i}",
            "kind": "lookup",
            "question": f"On unit {i}, how often should the DW-300's filter be cleaned?",
            "answer": "Every 30 cycles.",
            "accept": ["every 30 cycles"],
            "grading": "exact",
        }
        for i in range(n)
    ]


class InterruptAfter:
    """A model that answers `n` calls and then raises KeyboardInterrupt, the way a real Ctrl+C
    arrives: inside the call the runner is waiting on."""

    model_id = "interrupting-stub"

    def __init__(self, n: int) -> None:
        self.n = n
        self.calls = 0

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[dict] | None = None,
        schema: dict | None = None,
        max_tokens: int = 1024,
    ) -> Completion:
        self.calls += 1
        if self.calls > self.n:
            raise KeyboardInterrupt
        return Completion(
            text="Every 30 cycles.",
            tool_calls=[],
            tokens_in=10,
            tokens_out=5,
            ms=0.0,
            model_id=self.model_id,
        )


class InterruptedRunTest(unittest.TestCase):
    def test_the_questions_already_answered_survive_the_interrupt(self) -> None:
        summary = eval_run.run_example(
            "one_call",
            model=InterruptAfter(3),
            embedder=StubEmbedder(),
            grader=None,
            questions=_questions(10),
            stub=False,
            dry=False,
        )
        self.assertTrue(summary["interrupted"])
        self.assertTrue(summary["partial"], "an interrupted run is by definition incomplete")
        self.assertEqual(summary["questions_run"], 3)
        self.assertEqual(summary["questions_total"], 10)
        # The three that finished are graded and readable, which is the whole point.
        self.assertEqual(summary["score_overall"], 1.0)
        self.assertEqual(len(summary["questions"]), 3)

    def test_a_run_that_finishes_is_not_marked_interrupted(self) -> None:
        summary = eval_run.run_example(
            "one_call",
            model=InterruptAfter(99),
            embedder=StubEmbedder(),
            grader=None,
            questions=_questions(4),
            stub=False,
            dry=False,
        )
        self.assertFalse(summary["interrupted"])
        self.assertFalse(summary["partial"])
        self.assertEqual(summary["questions_run"], 4)

    def test_an_interrupt_on_the_first_question_still_writes_a_readable_file(self) -> None:
        summary = eval_run.run_example(
            "one_call",
            model=InterruptAfter(0),
            embedder=StubEmbedder(),
            grader=None,
            questions=_questions(5),
            stub=False,
            dry=False,
        )
        self.assertTrue(summary["interrupted"])
        self.assertEqual(summary["questions_run"], 0)
        # No score to report, and it must say None rather than a zero that reads as a bad model.
        self.assertIsNone(summary["score_overall"])


class InterruptedMainTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self._cache = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._cache, ignore_errors=True)

    def _run_main(self, extra: list[str]) -> int:
        with tempfile.TemporaryDirectory() as questions_dir:
            questions_path = Path(questions_dir) / "questions.json"
            questions_path.write_text(json.dumps({"questions": _questions(6)}), encoding="utf-8")
            return eval_run.main(
                [
                    "--example", "one_call", "--model", "stub", "--questions", str(questions_path),
                    "--out", str(self._tmp), "--cache-dir", str(self._cache),
                ]
                + extra
            )

    def test_main_writes_the_partial_file_and_exits_130(self) -> None:
        original = eval_run.generic_stub_model
        eval_run.generic_stub_model = lambda: InterruptAfter(2)  # type: ignore[assignment]
        self.addCleanup(setattr, eval_run, "generic_stub_model", original)

        code = self._run_main(["--allow-stub"])

        self.assertEqual(code, 130, "130 is the shell's code for a process killed by Ctrl+C")
        written = [p for p in self._tmp.glob("one_call/*.json") if not p.name.endswith(".review.json")]
        self.assertEqual(len(written), 1, "the partial result must be on disk to be read")
        data = json.loads(written[0].read_text(encoding="utf-8"))
        self.assertTrue(data["interrupted"])
        self.assertTrue(data["partial"])
        self.assertEqual(data["questions_run"], 2)
        self.assertEqual(data["questions_total"], 6)

    def test_an_interrupt_stops_the_run_instead_of_starting_the_next_example(self) -> None:
        # `--example all` walks EXAMPLE_NAMES in order. Ctrl+C during the first one must not be
        # read as "skip this one", which is what a swallowed interrupt would have looked like.
        original = eval_run.generic_stub_model
        eval_run.generic_stub_model = lambda: InterruptAfter(1)  # type: ignore[assignment]
        self.addCleanup(setattr, eval_run, "generic_stub_model", original)
        original_names = list(eval_run.EXAMPLE_NAMES)
        eval_run.EXAMPLE_NAMES = ["one_call", "rag"]  # type: ignore[assignment]
        self.addCleanup(setattr, eval_run, "EXAMPLE_NAMES", original_names)

        with tempfile.TemporaryDirectory() as questions_dir:
            questions_path = Path(questions_dir) / "questions.json"
            questions_path.write_text(json.dumps({"questions": _questions(6)}), encoding="utf-8")
            code = eval_run.main(
                [
                    "--example", "all", "--model", "stub", "--questions", str(questions_path),
                    "--out", str(self._tmp), "--cache-dir", str(self._cache), "--allow-stub",
                ]
            )

        self.assertEqual(code, 130)
        self.assertEqual(sorted(p.parent.name for p in self._tmp.glob("*/*.json")), ["one_call"])


class StubRefusalTest(unittest.TestCase):
    """`stub_refusal` is pinned by name on the evals page. Keep it honest in both directions."""

    def test_a_stub_run_is_refused_a_result_file(self) -> None:
        message = eval_run.stub_refusal("rag", is_stub=True, allow_stub=False)
        self.assertIsNotNone(message)
        self.assertIn("--allow-stub", message or "")

    def test_allow_stub_lets_it_through_and_a_real_model_is_never_refused(self) -> None:
        self.assertIsNone(eval_run.stub_refusal("rag", is_stub=True, allow_stub=True))
        self.assertIsNone(eval_run.stub_refusal("rag", is_stub=False, allow_stub=False))


if __name__ == "__main__":
    unittest.main()
