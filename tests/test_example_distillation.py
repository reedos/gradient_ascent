"""Tests for examples/distillation: a teacher model answers exact-graded questions, the answers
are filtered by the site's own accept/require/reject contract, and what passes is written as a
chat-format student training file. No model beyond StubModel is ever called."""
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
from examples.distillation.run import (  # noqa: E402
    DistilledExample,
    Question,
    grade_exact,
    load_exact_questions,
    run,
)

QUESTIONS_PATH = ROOT / "evals" / "questions.json"

# The same 32 replies, in call order, as examples/distillation/__main__.py's SCRIPTED: one per
# exact-graded question in evals/questions.json (L01-L12, M01, M02, M08, M09, N01-N12, C01, C02,
# C09, C12), every one the question's own reference answer except L06 and N04, which are
# deliberately wrong so the filter has something real to drop.
SEQUENCE = [
    "12 place settings.",
    "44 dBA.",
    "7.8 cubic feet.",
    "A dedicated 240V, 30A circuit.",
    "Every 30 cycles.",
    "F4.",
    "30 minutes.",
    "$19.99.",
    "2 years from the original date of purchase.",
    "8 feet.",
    "It shuts off the water supply and stops the cycle immediately.",
    "110 lb.",
    (
        "The drain pump is part HLV-2205, priced at $52.00 in the parts list; the DW-480 owner's "
        "manual confirms HLV-2205 is the drain pump used in that model."
    ),
    (
        "Part HLV-7734, priced at $12.50 in the parts list; the DR-210 owner's manual confirms "
        "HLV-7734 is the door latch switch used on the DR-210."
    ),
    (
        "The Heavy cycle, run empty with a dishwasher-safe cleaner. On the DW-300 the Heavy cycle "
        "runs 130 minutes."
    ),
    "One Air Fluff cycle, which runs 20 minutes on the DR-520.",
    "32 gallons.",
    "$33.60 per year (240 kWh x $0.14/kWh).",
    "20 kWh (260 - 240).",
    "5 gallons ((3.2 - 3.0) x 20).",
    "$79.50 ($38.50 + $41.00).",
    "$66.75 ($57.00 + $9.75).",
    "10 minutes (140 - 130).",
    "104 minutes (42 x 2 + 20).",
    "$0.03 (3.0 gallons x $0.010/gallon).",
    "6 cycles (180 / 30).",
    "3 lb (128 - 125).",
    "$25.75 ($12.50 + $13.25).",
    (
        "25 feet, per Service Bulletin SB-2026-07 (2026-06-01), which supersedes the DR-520 "
        "owner's manual's 35-foot figure (revision 2024-03-01)."
    ),
    "3 elbows, per the 2026 service bulletin, which supersedes the manual's original figure of 4.",
    "10 feet (35 - 25).",
    "35 feet, with up to 4 elbows.",
]


def _write_questions(tmp_dir: Path, questions: list[dict]) -> Path:
    path = tmp_dir / "questions.json"
    path.write_text(json.dumps({"questions": questions}), encoding="utf-8")
    return path


class GradeExactTests(unittest.TestCase):
    def test_a_matching_accept_pattern_passes_with_no_require_or_reject(self) -> None:
        q = Question(id="Q1", text="How many place settings?", accept=["12 place setting"], require=[], reject=[])
        self.assertTrue(grade_exact("It holds 12 place settings.", q))

    def test_missing_every_accept_pattern_fails(self) -> None:
        q = Question(id="Q1", text="How many place settings?", accept=["12 place setting"], require=[], reject=[])
        self.assertFalse(grade_exact("It holds a lot of dishes.", q))

    def test_accept_is_alternatives_any_one_matches(self) -> None:
        q = Question(id="Q1", text="x", accept=["7\\.8 cubic (foot|feet)"], require=[], reject=[])
        self.assertTrue(grade_exact("The capacity is 7.8 cubic feet.", q))
        self.assertTrue(grade_exact("The capacity is 7.8 cubic foot.", q))

    def test_require_is_conjunction_every_pattern_must_match(self) -> None:
        # The docs/EVALS.md example: naming the part without its price does not pass.
        q = Question(id="M01", text="x", accept=["HLV-2205"], require=["\\$52\\.00"], reject=[])
        self.assertTrue(grade_exact("The part is HLV-2205 and it costs $52.00.", q))
        self.assertFalse(grade_exact("The part is HLV-2205.", q))

    def test_a_matched_reject_pattern_fails_even_when_accept_also_matches(self) -> None:
        q = Question(id="U01", text="x", accept=["not stated"], require=[], reject=["\\bblue\\b"])
        self.assertFalse(grade_exact("Not stated in the documents, but it looks blue to me.", q))

    def test_grading_is_case_insensitive(self) -> None:
        q = Question(id="Q1", text="x", accept=["HLV-2205"], require=[], reject=[])
        self.assertTrue(grade_exact("the part number is hlv-2205.", q))

    def test_no_accept_patterns_means_nothing_to_fail_on_that_axis(self) -> None:
        q = Question(id="Q1", text="x", accept=[], require=["ok"], reject=[])
        self.assertTrue(grade_exact("everything is ok here", q))


class LoadExactQuestionsTests(unittest.TestCase):
    def test_loads_only_the_exact_graded_subset_of_the_real_set(self) -> None:
        questions = load_exact_questions(QUESTIONS_PATH)
        self.assertEqual(len(questions), 32)
        all_data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
        exact_ids = {q["id"] for q in all_data["questions"] if q["grading"] == "exact"}
        self.assertEqual({q.id for q in questions}, exact_ids)

    def test_a_question_with_no_require_or_reject_gets_empty_lists_not_none(self) -> None:
        questions = load_exact_questions(QUESTIONS_PATH)
        lookup = next(q for q in questions if q.id == "L01")
        self.assertEqual(lookup.require, [])
        self.assertEqual(lookup.reject, [])


class DistilledExampleTests(unittest.TestCase):
    def test_as_chat_record_carries_the_teachers_own_text_not_an_answer_key(self) -> None:
        ex = DistilledExample(id="Q1", question="How long is the warranty?", answer="Two years from delivery.")
        record = ex.as_chat_record()
        roles = [m["role"] for m in record["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant"])
        self.assertEqual(record["messages"][2]["content"], "Two years from delivery.")


class RunTests(unittest.TestCase):
    def _questions(self, tmp_dir: Path) -> Path:
        return _write_questions(
            tmp_dir,
            [
                {"id": "A1", "kind": "lookup", "question": "How many settings?", "answer": "12.",
                 "accept": ["12 setting"], "require": [], "reject": [], "grading": "exact"},
                {"id": "A2", "kind": "numeric", "question": "What is the price?", "answer": "$19.99.",
                 "accept": [], "require": ["\\$19\\.99"], "reject": [], "grading": "exact"},
                {"id": "A3", "kind": "unanswerable", "question": "What color is it?", "answer": "Not stated.",
                 "accept": ["not stated"], "require": [], "reject": ["\\bblue\\b"], "grading": "exact"},
                # A rubric question in the same file must be skipped entirely, not graded loosely.
                {"id": "R1", "kind": "multi_hop", "question": "Why does it fail?", "answer": "Several reasons.",
                 "grading": "rubric", "rubric": ["mentions the cause"]},
            ],
        )

    def test_run_keeps_passing_answers_and_drops_failing_ones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = self._questions(tmp_path)

            answers = {
                "How many settings?": "It has 12 settings in total.",  # passes
                "What is the price?": "It costs about twenty dollars.",  # fails: no $19.99
                "What color is it?": "Not stated, but I'd guess it's blue.",  # fails: reject hits
            }

            def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
                question = messages[-1].content
                return StubResponse(text=answers[question])

            teacher = StubModel(responder, model_id="fake-teacher")
            tracer = Tracer(example="distillation", level=1, model_id=teacher.model_id)
            out_path = tmp_path / "out" / "student.jsonl"

            result = run(tracer, teacher, questions_path=questions_path, out_path=out_path)

            self.assertEqual([ex.id for ex in result.kept], ["A1"])
            self.assertEqual(result.dropped, ["A2", "A3"])
            self.assertTrue(out_path.exists())

            lines = out_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["messages"][1]["content"], "How many settings?")
            self.assertEqual(record["messages"][2]["content"], "It has 12 settings in total.")

    def test_run_writes_an_empty_file_when_nothing_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = self._questions(tmp_path)
            teacher = StubModel(lambda messages, tools: StubResponse(text="I have no idea."))
            tracer = Tracer(example="distillation", level=1, model_id=teacher.model_id)
            out_path = tmp_path / "student.jsonl"

            result = run(tracer, teacher, questions_path=questions_path, out_path=out_path)

            self.assertEqual(result.kept, [])
            self.assertEqual(sorted(result.dropped), ["A1", "A2", "A3"])
            self.assertEqual(out_path.read_text(encoding="utf-8"), "")

    def test_run_only_calls_the_teacher_for_exact_graded_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = self._questions(tmp_path)
            calls: list[str] = []

            def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
                calls.append(messages[-1].content)
                return StubResponse(text="whatever")

            teacher = StubModel(responder)
            tracer = Tracer(example="distillation", level=1, model_id=teacher.model_id)
            run(tracer, teacher, questions_path=questions_path, out_path=tmp_path / "student.jsonl")

            self.assertEqual(len(calls), 3)  # not 4: the rubric question R1 is skipped
            self.assertNotIn("Why does it fail?", calls)

    def test_run_records_only_code_decided_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            questions_path = self._questions(tmp_path)
            teacher = StubModel(lambda messages, tools: StubResponse(text="It has 12 settings."))
            tracer = Tracer(example="distillation", level=1, model_id=teacher.model_id)
            run(tracer, teacher, questions_path=questions_path, out_path=tmp_path / "student.jsonl")

            self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
            self.assertEqual(tracer.model_decided_count(), 0)
            self.assertTrue(any(s.kind == "model" for s in tracer.steps))

    def test_declares_its_level(self) -> None:
        import examples.distillation.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 1)

    def test_record_trace_still_finds_distillation_unrecordable(self) -> None:
        # `run(tracer, teacher, *, questions_path=..., out_path)` processes the whole
        # exact-graded question set in one call, not one question, and this same `run` is what
        # distillation.mdx's `<CodeFile func="run" />` shows -- adding a second, differently-
        # shaped `run` here would either collide with that name or silently change what the page
        # displays. Left unrecordable on purpose; see .local/page-requests/wave6-examples.md.
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("distillation")
        self.assertFalse(rec.ok)
        self.assertIn("tracer", rec.reason)


class ScriptedCommandTests(unittest.TestCase):
    """End-to-end: the exact sequence examples/distillation/__main__.py's SCRIPTED plays against
    the real 32-question exact-graded set, not the small fixture the tests above use."""

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        from examples.distillation.__main__ import SCRIPTED

        self.assertEqual(SCRIPTED, SEQUENCE)

    def test_the_scripted_run_keeps_thirty_and_drops_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            teacher = StubModel([StubResponse(text=t) for t in SEQUENCE])
            tracer = Tracer(example="distillation", level=1, model_id=teacher.model_id)
            out_path = Path(tmp) / "student.jsonl"

            result = run(tracer, teacher, out_path=out_path)

            self.assertEqual(len(result.kept), 30)
            self.assertEqual(result.dropped, ["L06", "N04"])
            self.assertEqual(len(out_path.read_text(encoding="utf-8").splitlines()), 30)


if __name__ == "__main__":
    unittest.main()
