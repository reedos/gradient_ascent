"""Tests for examples/adaptation: builds a chat-format fine-tuning JSONL split from the site's
60-question set and checks it for leakage between train and validation. No model is called."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.adaptation.run import (  # noqa: E402
    Example,
    leaked_questions,
    load_examples,
    run,
    split,
)
from examples.common.trace import Tracer  # noqa: E402

QUESTIONS_PATH = ROOT / "evals" / "questions.json"


class AdaptationExampleTests(unittest.TestCase):
    def test_loads_all_60_questions_as_examples(self) -> None:
        examples = load_examples(QUESTIONS_PATH)
        self.assertEqual(len(examples), 60)
        self.assertTrue(all(ex.question and ex.answer for ex in examples))

    def test_unanswerable_questions_keep_their_plain_language_answer(self) -> None:
        examples = load_examples(QUESTIONS_PATH)
        unanswerable = [ex for ex in examples if ex.id.startswith("U")]
        self.assertEqual(len(unanswerable), 12)
        self.assertTrue(all(ex.answer for ex in unanswerable))

    def test_chat_record_has_system_user_assistant_in_order(self) -> None:
        ex = Example(id="X01", question="How many place settings?", answer="12.")
        record = ex.as_chat_record()
        roles = [m["role"] for m in record["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant"])
        self.assertEqual(record["messages"][1]["content"], ex.question)
        self.assertEqual(record["messages"][2]["content"], ex.answer)

    def test_split_is_a_clean_partition_with_no_overlap_and_no_loss(self) -> None:
        examples = load_examples(QUESTIONS_PATH)
        train, val = split(examples, val_fraction=0.2, seed=0)
        self.assertEqual(len(train) + len(val), len(examples))
        self.assertEqual(set(ex.id for ex in train) & set(ex.id for ex in val), set())
        self.assertEqual(len(val), 12)  # round(60 * 0.2)

    def test_split_is_deterministic_for_a_given_seed(self) -> None:
        examples = load_examples(QUESTIONS_PATH)
        train_a, val_a = split(examples, val_fraction=0.2, seed=7)
        train_b, val_b = split(examples, val_fraction=0.2, seed=7)
        self.assertEqual([ex.id for ex in train_a], [ex.id for ex in train_b])
        self.assertEqual([ex.id for ex in val_a], [ex.id for ex in val_b])

    def test_a_different_seed_can_produce_a_different_split(self) -> None:
        examples = load_examples(QUESTIONS_PATH)
        _, val_a = split(examples, val_fraction=0.2, seed=0)
        _, val_b = split(examples, val_fraction=0.2, seed=1)
        self.assertNotEqual([ex.id for ex in val_a], [ex.id for ex in val_b])

    def test_leaked_questions_is_empty_for_a_clean_partition(self) -> None:
        examples = load_examples(QUESTIONS_PATH)
        train, val = split(examples, val_fraction=0.2, seed=0)
        self.assertEqual(leaked_questions(train, val), [])

    def test_leaked_questions_catches_the_same_question_restyled_under_a_different_id(self) -> None:
        train = [Example(id="A01", question="How many place settings?", answer="12.")]
        val = [Example(id="A02", question="  HOW many   place settings?  ", answer="12.")]
        self.assertEqual(leaked_questions(train, val), ["A02"])

    def test_leaked_questions_catches_a_punctuation_only_difference(self) -> None:
        train = [Example(id="A01", question="How many place settings (DW-300)?", answer="12.")]
        val = [Example(id="A02", question="How many place settings, DW-300?", answer="12.")]
        self.assertEqual(leaked_questions(train, val), ["A02"])

    def test_leaked_questions_catches_punctuation_inside_a_word(self) -> None:
        # The case the docstring promised and the code missed: normalizing punctuation to a space
        # kept the word boundary, so "don't" became "don t" while "dont" stayed "dont", and a
        # leak that differed by one apostrophe was not reported.
        for left, right in (
            ("What doesn't the warranty cover?", "What doesnt the warranty cover?"),
            ("Is the DW-300 covered?", "Is the DW300 covered?"),
            ("HLV-2205 price", "HLV2205 price"),
        ):
            with self.subTest(left=left):
                train = [Example(id="A01", question=left, answer="x")]
                val = [Example(id="A02", question=right, answer="x")]
                self.assertEqual(leaked_questions(train, val), ["A02"])

    def test_the_real_question_set_has_no_leak_under_the_stricter_check(self) -> None:
        # The stricter normalization runs words together, so it can in principle collide two
        # different questions. It does not collide any two in the set this example ships with.
        examples = load_examples()
        train, val = split(examples, val_fraction=0.2, seed=0)
        self.assertEqual(leaked_questions(train, val), [])

    def test_leaked_questions_does_not_claim_to_catch_a_reworded_paraphrase(self) -> None:
        # The check is equality over normalized text, not similarity. A paraphrase in different
        # words slips through, which is why the page says an equality test is the floor.
        train = [Example(id="A01", question="How long is the warranty?", answer="Two years.")]
        val = [Example(id="A02", question="What is the warranty period?", answer="Two years.")]
        self.assertEqual(leaked_questions(train, val), [])

    def test_run_writes_two_jsonl_files_and_records_only_code_decided_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracer = Tracer(example="adaptation", level=1, model_id="none")
            result = run(tracer, questions_path=QUESTIONS_PATH, out_dir=Path(tmp), val_fraction=0.2, seed=0)

            self.assertTrue(result.train_path.exists())
            self.assertTrue(result.val_path.exists())
            self.assertEqual(result.leaked, [])

            train_lines = result.train_path.read_text(encoding="utf-8").splitlines()
            val_lines = result.val_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(train_lines), len(result.train))
            self.assertEqual(len(val_lines), len(result.val))
            for line in train_lines + val_lines:
                record = json.loads(line)
                self.assertEqual([m["role"] for m in record["messages"]], ["system", "user", "assistant"])

            self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
            self.assertEqual(tracer.model_decided_count(), 0)

    def test_declares_its_level(self) -> None:
        import examples.adaptation.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 1)

    def test_record_trace_still_finds_adaptation_unrecordable(self) -> None:
        # `run(tracer, *, questions_path=..., out_dir, val_fraction=0.2, seed=0)` processes the
        # whole 60-question set in one call, not one question, and this same `run` is what
        # fine-tuning.mdx's `<CodeFile func="run" />` shows -- adding a second, differently-
        # shaped `run` here would either collide with that name or silently change what the page
        # displays. Left unrecordable on purpose; see .local/page-requests/wave6-examples.md.
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("adaptation")
        self.assertFalse(rec.ok)
        self.assertIn("tracer", rec.reason)


if __name__ == "__main__":
    unittest.main()
