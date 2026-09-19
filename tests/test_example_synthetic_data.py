"""Tests for examples/synthetic_data: a model paraphrases seed questions, paraphrases are
deduplicated against the seeds and each other, and what survives is answered blind and graded by
the seed's own accept/require/reject contract before being kept. No model beyond StubModel is
ever called."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.synthetic_data.run import _normalize, all_question_texts, run  # noqa: E402


def _write_questions(tmp_dir: Path, questions: list[dict]) -> Path:
    path = tmp_dir / "questions.json"
    path.write_text(json.dumps({"questions": questions}), encoding="utf-8")
    return path


SEEDS = [
    {"id": "A1", "kind": "lookup", "question": "How many place settings does it hold?", "answer": "12.",
     "accept": ["12 place setting"], "require": [], "reject": [], "grading": "exact"},
    {"id": "A2", "kind": "numeric", "question": "What is the price of the filter?", "answer": "$19.99.",
     "accept": [], "require": ["\\$19\\.99"], "reject": [], "grading": "exact"},
    # A rubric question in the same file must never reach the pipeline as a seed -- but its text
    # still has to be off limits to a paraphrase, which is what AllQuestionTextsTests checks.
    {"id": "R1", "kind": "multi_hop", "question": "Why does it fail?", "answer": "Several reasons.",
     "grading": "rubric", "rubric": ["mentions the cause"]},
]


class NormalizeTests(unittest.TestCase):
    def test_case_and_punctuation_collapse_to_the_same_string(self) -> None:
        self.assertEqual(_normalize("How many place settings?"), _normalize("how many PLACE settings"))


class AllQuestionTextsTests(unittest.TestCase):
    def test_every_question_is_included_not_only_the_exact_graded_ones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_questions(Path(tmp), SEEDS)
            self.assertIn("Why does it fail?", all_question_texts(path))  # the rubric-graded one
            self.assertEqual(len(all_question_texts(path)), 3)

    def test_the_real_set_has_more_questions_than_the_exact_graded_subset(self) -> None:
        texts = all_question_texts(ROOT / "evals" / "questions.json")
        self.assertEqual(len(texts), 60)
        self.assertEqual(len(set(texts)), 60)


class RunTests(unittest.TestCase):
    def _responder(self, paraphrases: dict[str, str], answers: dict[str, str]):
        """paraphrases maps a seed's exact question text to the paraphrase text to return for it;
        answers maps a paraphrase text to the answer to return when that paraphrase is later
        asked as a question. Two lookups by exact message content, matching how `run` calls
        the model: first to paraphrase, then, for whatever came back, to answer."""

        def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
            asked = messages[-1].content
            if asked in paraphrases:
                return StubResponse(text=paraphrases[asked])
            return StubResponse(text=answers.get(asked, "I do not know."))

        return responder

    def test_a_verified_novel_paraphrase_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            paraphrases = {
                "How many place settings does it hold?": "How many place settings can it fit?",
                "What is the price of the filter?": "How much does the filter cost?",
            }
            answers = {
                "How many place settings can it fit?": "It fits 12 place settings.",
                "How much does the filter cost?": "The filter costs $19.99.",
            }
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)
            out_path = tmp_path / "out" / "questions.jsonl"

            result = run(tracer, model, questions_path=questions_path, out_path=out_path)

            self.assertEqual(sorted(g.source_id for g in result.kept), ["A1", "A2"])
            self.assertEqual(result.rejected, [])
            lines = out_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)

    def test_a_paraphrase_identical_to_the_seed_is_rejected_as_a_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            paraphrases = {
                "How many place settings does it hold?": "How many place settings does it hold?",  # unchanged
                "What is the price of the filter?": "How much does the filter cost?",
            }
            answers = {"How much does the filter cost?": "The filter costs $19.99."}
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            reasons = {r.source_id: r.reason for r in result.rejected}
            self.assertEqual(reasons.get("A1"), "duplicate")
            self.assertEqual([g.source_id for g in result.kept], ["A2"])

    def test_two_seeds_paraphrased_the_same_way_the_second_is_a_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            same_text = "Tell me about it."
            paraphrases = {
                "How many place settings does it hold?": same_text,
                "What is the price of the filter?": same_text,
            }
            model = StubModel(self._responder(paraphrases, {}))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            reasons = {r.source_id: r.reason for r in result.rejected}
            self.assertEqual(reasons.get("A2"), "duplicate")  # A1's paraphrase claimed the text first

    def test_a_paraphrase_whose_blind_answer_fails_grading_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            paraphrases = {"How many place settings does it hold?": "How many settings come with it?"}
            answers = {"How many settings come with it?": "I'm not sure how many."}  # wrong: no "12"
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(
                tracer,
                model,
                questions_path=_write_questions(tmp_path, [SEEDS[0]]),
                out_path=tmp_path / "q.jsonl",
            )

            self.assertEqual(result.kept, [])
            self.assertEqual(result.rejected[0].reason, "failed verification")

    # --- Attacks on the verification step. Each one is a paraphrase a careless generator could
    # produce, and the question is whether the check catches it.

    def test_a_paraphrase_that_changes_a_number_is_rejected(self) -> None:
        """The paraphrase reads like a rewording and asks about a different quantity, so the
        blind answer is well formed, plausible, and no longer the seed's answer."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, [SEEDS[0]])
            paraphrases = {"How many place settings does it hold?": "How many place settings does it hold with the top rack removed?"}
            answers = {"How many place settings does it hold with the top rack removed?": "It holds 10 place settings."}
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            self.assertEqual(result.kept, [])
            self.assertEqual([(r.source_id, r.reason) for r in result.rejected], [("A1", "failed verification")])

    def test_a_negated_paraphrase_whose_answer_changed_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, [SEEDS[1]])
            paraphrases = {"What is the price of the filter?": "What does the filter not cost?"}
            answers = {"What does the filter not cost?": "The filter does not cost $24.50."}
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            self.assertEqual(result.kept, [])
            self.assertEqual(result.rejected[0].reason, "failed verification")

    def test_a_negation_whose_answer_still_carries_the_pattern_is_kept_which_is_the_blind_spot(self) -> None:
        """The documented miss, pinned so it cannot quietly become a claim the checks do not
        support: the paraphrase asks the opposite question, the blind answer denies the seed's
        own fact, and the accept pattern still matches the text. Catching this needs a meaning
        check, which neither normalized equality nor a regex is."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, [SEEDS[0]])
            paraphrases = {"How many place settings does it hold?": "How many place settings does it not hold?"}
            answers = {"How many place settings does it not hold?": "It does not hold 12 place settings."}
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            self.assertEqual([g.source_id for g in result.kept], ["A1"])
            self.assertEqual(result.rejected, [])

    def test_a_paraphrase_that_is_another_seed_with_different_punctuation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            paraphrases = {
                "How many place settings does it hold?": "How many place settings can it fit?",
                "What is the price of the filter?": "how many place settings does it hold",  # A1, restyled
            }
            answers = {"How many place settings can it fit?": "It fits 12 place settings."}
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            self.assertEqual([(r.source_id, r.reason) for r in result.rejected], [("A2", "duplicate")])
            self.assertEqual([g.source_id for g in result.kept], ["A1"])

    def test_a_paraphrase_that_duplicates_a_rubric_graded_question_is_rejected(self) -> None:
        """R1 is never a seed -- the pipeline only generates from exact-graded questions -- but
        it is still a question the eval set asks, so a paraphrase that lands on it is a copy of
        a question, not a new one."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            paraphrases = {
                "How many place settings does it hold?": "why does it fail",  # R1, restyled
                "What is the price of the filter?": "How much does the filter cost?",
            }
            answers = {"How much does the filter cost?": "The filter costs $19.99."}
            model = StubModel(self._responder(paraphrases, answers))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            self.assertEqual([(r.source_id, r.reason) for r in result.rejected], [("A1", "duplicate")])
            self.assertEqual([g.source_id for g in result.kept], ["A2"])

    def test_run_only_calls_the_model_for_exact_graded_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            asked: list[str] = []

            def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
                asked.append(messages[-1].content)
                return StubResponse(text="something new " + str(len(asked)))

            model = StubModel(responder)
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)
            run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            self.assertNotIn("Why does it fail?", asked)  # the rubric-graded seed R1

    def test_run_records_only_code_decided_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = _write_questions(tmp_path, SEEDS)
            model = StubModel(lambda messages, tools: StubResponse(text="a fresh phrasing " + messages[-1].content[:5]))
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)
            run(tracer, model, questions_path=questions_path, out_path=tmp_path / "q.jsonl")

            self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
            self.assertEqual(tracer.model_decided_count(), 0)
            self.assertTrue(any(s.kind == "model" for s in tracer.steps))

    def test_declares_its_level(self) -> None:
        import examples.synthetic_data.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 1)

    def test_record_trace_still_finds_synthetic_data_unrecordable(self) -> None:
        # `run(tracer, model, *, questions_path=..., out_path)` processes the whole seed set in
        # one call, not one question, and this same `run` is what synthetic-data.mdx's
        # `<CodeFile func="run" />` shows -- adding a second, differently-shaped `run` here would
        # either collide with that name or silently change what the page displays. Left
        # unrecordable on purpose; see .local/page-requests/wave6-examples.md.
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("synthetic_data")
        self.assertFalse(rec.ok)
        self.assertIn("tracer", rec.reason)


if __name__ == "__main__":
    unittest.main()
