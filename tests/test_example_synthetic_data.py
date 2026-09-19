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

# The same 61 replies, in call order, as examples/synthetic_data/__main__.py's SCRIPTED: up to two
# per exact-graded seed in evals/questions.json (L01-L12, M01, M02, M08, M09, N01-N12, C01, C02,
# C09, C12). L06, N07 and C09 paraphrase to their own seed text unchanged (rejected as duplicates,
# so neither gets a second call); N04 paraphrases to something novel but answers wrong (rejected
# as a failed verification); every other seed paraphrases to something novel and answers with the
# seed's own reference answer (kept).
SEQUENCE = [
    "What is the DW-300 dishwasher's place setting capacity?",
    "12 place settings.",
    "During its Normal cycle, how loud is the DW-480 dishwasher rated?",
    "44 dBA.",
    "What is the drum capacity, in cubic feet, of the DR-520 dryer?",
    "7.8 cubic feet.",
    "Which electrical circuit is required to install a DR-210 dryer?",
    "A dedicated 240V, 30A circuit.",
    "What is the recommended cleaning interval for the DW-300's fine filter?",
    "Every 30 cycles.",
    "Which dryer error code indicates the thermal fuse has opened?",
    "What is the duration of the DW-300's Quick Wash cycle?",
    "30 minutes.",
    "How much does part HLV-9002, the universal dryer vent cleaning kit, cost?",
    "$19.99.",
    "What is the duration of Halvorsen's full parts-and-labor warranty on its dishwashers and dryers?",
    "2 years from the original date of purchase.",
    "For a dishwasher installation, what is the longest a drain hose is allowed to be?",
    "8 feet.",
    "When the DW-480's leak cutoff trips, what happens?",
    "It shuts off the water supply and stops the cycle immediately.",
    "How much does an empty DR-210 dryer weigh?",
    "110 lb.",
    "What is the price of the DW-480's drain pump, and which document verifies that part is used in the DW-480?",
    (
        "The drain pump is part HLV-2205, priced at $52.00 in the parts list; the DW-480 owner's "
        "manual confirms HLV-2205 is the drain pump used in that model."
    ),
    "How much is the DR-210's door latch switch, and which manual verifies it fits that model?",
    (
        "Part HLV-7734, priced at $12.50 in the parts list; the DR-210 owner's manual confirms "
        "HLV-7734 is the door latch switch used on the DR-210."
    ),
    "Which cycle does the care and cleaning guide prescribe for the monthly dishwasher deep clean, and what is its runtime on a DW-300?",
    (
        "The Heavy cycle, run empty with a dishwasher-safe cleaner. On the DW-300 the Heavy cycle "
        "runs 130 minutes."
    ),
    "Before regular use, the installation guide requires running one cycle on a new dryer. Which cycle is it and how long does it take on a DR-520?",
    "One Air Fluff cycle, which runs 20 minutes on the DR-520.",
    "Over 10 Normal cycles, how much water, in gallons, does a DW-300 use?",
    "32 gallons.",
    "Based on the rate assumption in the specifications comparison, what does the DW-480 cost to run per year in electricity?",
    "$33.60 per year (240 kWh x $0.14/kWh).",
    "In kWh, how much more estimated annual energy does the DW-300 use than the DW-480?",
    "20 kWh (260 - 240).",
    "Running 20 Normal cycles on each, how many extra gallons does the DW-300 use compared to the DW-480?",
    "About 5 gallons more, judging from the cycle specifications.",
    "If you replaced the heating elements on both a DW-300 and a DW-480, what would the combined price be?",
    "$79.50 ($38.50 + $41.00).",
    "Combined, what do a DR-210 heating element and a DR-210 drive belt cost?",
    "$66.75 ($57.00 + $9.75).",
    "How many minutes longer is the DW-480's Heavy cycle than the DW-300's Heavy cycle?",
    "If a DR-520 runs its 42-minute Normal cycle twice and its 20-minute Steam Refresh cycle once in a day, what is the total cycle time in minutes?",
    "104 minutes (42 x 2 + 20).",
    "Based on the specifications comparison's rate assumption, how much does one DW-480 Normal cycle cost in water?",
    "$0.03 (3.0 gallons x $0.010/gallon).",
    "Back-to-back, how many 30-minute DW-300 Quick Wash cycles fit inside a 180-minute window?",
    "6 cycles (180 / 30).",
    "How much heavier is the gas version of the DR-520 than the electric version?",
    "3 lb (128 - 125).",
    "Combined, what does it cost to replace the door latch switch on a DR-210 and a DR-520?",
    "$25.75 ($12.50 + $13.25).",
    "For a DR-520 installation, what is the longest vent run allowed?",
    (
        "25 feet, per Service Bulletin SB-2026-07 (2026-06-01), which supersedes the DR-520 "
        "owner's manual's 35-foot figure (revision 2024-03-01)."
    ),
    "At the maximum vent run length, how many elbows does a DR-520 installation currently allow?",
    "3 elbows, per the 2026 service bulletin, which supersedes the manual's original figure of 4.",
    "What is the difference, in feet, between the DR-520 manual's original maximum vent run and the figure in Service Bulletin SB-2026-07?",
    "Before the 2026 revision, what did the DR-520's original owner's manual state as the maximum vent run?",
    "35 feet, with up to 4 elbows.",
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


class ScriptedCommandTests(unittest.TestCase):
    """End-to-end: the exact sequence examples/synthetic_data/__main__.py's SCRIPTED plays
    against the real 32-seed exact-graded set, not the small fixture the tests above use."""

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        from examples.synthetic_data.__main__ import SCRIPTED

        self.assertEqual(SCRIPTED, SEQUENCE)

    def test_the_scripted_run_keeps_most_and_rejects_the_three_duplicates_and_one_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = StubModel([StubResponse(text=t) for t in SEQUENCE])
            tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)
            out_path = Path(tmp) / "questions.jsonl"

            result = run(tracer, model, out_path=out_path)

            self.assertEqual(len(result.kept), 28)
            reasons = {r.source_id: r.reason for r in result.rejected}
            self.assertEqual(reasons, {"L06": "duplicate", "N07": "duplicate", "C09": "duplicate", "N04": "failed verification"})
            self.assertEqual(len(out_path.read_text(encoding="utf-8").splitlines()), 28)


if __name__ == "__main__":
    unittest.main()
