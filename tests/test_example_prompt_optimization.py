"""Tests for examples/prompt_optimization: candidate instructions are scored on a development
split, the best-scoring one is selected, and only the selected candidate is then scored on a
held-out split. No model beyond StubModel is ever called."""
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
from examples.prompt_optimization.run import run, split_dev_held_out  # noqa: E402
from examples.distillation.run import load_exact_questions  # noqa: E402
from examples.prompt_optimization.__main__ import DEMO_QUESTIONS, SCRIPTED  # noqa: E402

QUESTIONS_PATH = ROOT / "evals" / "questions.json"

# The same 14 replies examples/prompt_optimization/__main__.py scripts for `--model
# stub:scripted --demo-subset`: three candidates scored on 4 development questions (12 calls,
# only the middle candidate answering correctly), then that winner scored on 2 held-out questions.
_WRONG = "I have no idea."
SEQUENCE = [
    _WRONG, _WRONG, _WRONG, _WRONG,
    "44 dBA.", "12 place settings.", "F2.", "A dedicated 240V, 30A circuit.",
    _WRONG, _WRONG, _WRONG, _WRONG,
    "Every 30 cycles.", "7.8 cubic feet.",
]


def _write_questions(tmp_dir: Path, questions: list[dict]) -> Path:
    path = tmp_dir / "questions.json"
    path.write_text(json.dumps({"questions": questions}), encoding="utf-8")
    return path


QUESTIONS = [
    {"id": f"A{i}", "kind": "lookup", "question": f"Question number {i}?", "answer": "x",
     "accept": [f"answer{i}"], "require": [], "reject": [], "grading": "exact"}
    for i in range(1, 9)
]


class SplitDevHeldOutTests(unittest.TestCase):
    def test_split_is_a_clean_partition(self) -> None:
        questions = load_exact_questions(QUESTIONS_PATH)
        dev, held_out = split_dev_held_out(questions, held_out_fraction=0.25, seed=0)
        self.assertEqual(len(dev) + len(held_out), len(questions))
        self.assertEqual(set(q.id for q in dev) & set(q.id for q in held_out), set())

    def test_split_is_deterministic_for_a_given_seed(self) -> None:
        questions = load_exact_questions(QUESTIONS_PATH)
        dev_a, held_a = split_dev_held_out(questions, held_out_fraction=0.25, seed=3)
        dev_b, held_b = split_dev_held_out(questions, held_out_fraction=0.25, seed=3)
        self.assertEqual([q.id for q in dev_a], [q.id for q in dev_b])
        self.assertEqual([q.id for q in held_a], [q.id for q in held_b])

    def test_a_different_seed_still_partitions_cleanly(self) -> None:
        questions = load_exact_questions(QUESTIONS_PATH)
        all_ids = {q.id for q in questions}
        for seed in (0, 1, 7, 42):
            dev, held_out = split_dev_held_out(questions, held_out_fraction=0.25, seed=seed)
            dev_ids, held_ids = {q.id for q in dev}, {q.id for q in held_out}
            self.assertEqual(dev_ids | held_ids, all_ids)
            self.assertEqual(dev_ids & held_ids, set())

    def test_the_held_out_split_is_never_empty(self) -> None:
        questions = load_exact_questions(QUESTIONS_PATH)
        _, held_out = split_dev_held_out(questions, held_out_fraction=0.0, seed=0)
        self.assertEqual(len(held_out), 1)  # rounding down to nothing would leave no check at all


class RunTests(unittest.TestCase):
    def _model_that_answers(self, correct_instruction: str):
        """A stub that answers questions correctly only when asked under one specific
        instruction (the system message), and wrong under every other one -- so the optimizer
        has a real, checkable reason to prefer that candidate."""

        def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
            system = messages[0].content
            question = messages[-1].content
            if system == correct_instruction:
                # "Question number 3?" -> "answer3", matching that question's accept pattern
                n = question.split()[-1].rstrip("?")
                return StubResponse(text=f"answer{n}")
            return StubResponse(text="I have no idea.")

        return responder

    def test_the_best_candidate_on_dev_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            winner = "You are a Halvorsen appliance support assistant. Answer in one or two plain sentences, with no citations and no hedging."
            model = StubModel(self._model_that_answers(winner))
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)

            result = run(tracer, model, questions_path=questions_path, held_out_fraction=0.25, seed=0)

            self.assertEqual(result.selected, winner)
            self.assertGreater(result.held_out_score, 0.0)  # the winner also gets the held-out right

    def test_selection_never_sees_the_held_out_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            questions = load_exact_questions(questions_path)
            dev, held_out = split_dev_held_out(questions, held_out_fraction=0.25, seed=0)
            held_out_texts = {q.text for q in held_out}

            calls: list[tuple[str, str]] = []  # (instruction, question_text), in call order

            def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
                calls.append((messages[0].content, messages[-1].content))
                return StubResponse(text="answer1")  # only ever satisfies A1's own pattern

            model = StubModel(responder)
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
            result = run(tracer, model, questions_path=questions_path, held_out_fraction=0.25, seed=0)

            from examples.prompt_optimization.run import CANDIDATE_INSTRUCTIONS

            n_candidates = len(CANDIDATE_INSTRUCTIONS)
            # Every held-out question is asked exactly once, and only under the selected
            # instruction -- never while candidates were still being compared.
            held_out_calls = [c for c in calls if c[1] in held_out_texts]
            self.assertEqual(len(held_out_calls), len(held_out))
            self.assertTrue(all(instr == result.selected for instr, _ in held_out_calls))

            # Every development question is asked once per candidate, all under selection.
            dev_texts = {q.text for q in dev}
            dev_calls = [c for c in calls if c[1] in dev_texts]
            self.assertEqual(len(dev_calls), len(dev) * n_candidates)

    def test_no_held_out_question_is_asked_before_selection_is_finished(self) -> None:
        """Order, not just instruction: a held-out question scored while candidates were still
        being compared would leak even if it were later re-scored under the winner."""
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            questions = load_exact_questions(questions_path)
            dev, held_out = split_dev_held_out(questions, held_out_fraction=0.25, seed=0)
            dev_texts = {q.text for q in dev}
            held_out_texts = {q.text for q in held_out}
            asked: list[str] = []

            def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
                asked.append(messages[-1].content)
                return StubResponse(text="answer1")

            model = StubModel(responder)
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
            run(tracer, model, questions_path=questions_path, held_out_fraction=0.25, seed=0)

            last_dev = max(i for i, q in enumerate(asked) if q in dev_texts)
            first_held = min(i for i, q in enumerate(asked) if q in held_out_texts)
            self.assertLess(last_dev, first_held)

    def test_every_candidate_is_scored_on_the_same_development_questions(self) -> None:
        """A candidate scored on a different slice would make the comparison meaningless without
        changing anything a reader of the scores could see."""
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            seen: dict[str, list[str]] = {}

            def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
                seen.setdefault(messages[0].content, []).append(messages[-1].content)
                return StubResponse(text="nope")

            model = StubModel(responder)
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
            result = run(tracer, model, questions_path=questions_path, held_out_fraction=0.25, seed=0)

            questions = load_exact_questions(questions_path)
            dev, held_out = split_dev_held_out(questions, held_out_fraction=0.25, seed=0)
            for instruction, asked in seen.items():
                dev_asked = [q for q in asked if q not in {h.text for h in held_out}]
                self.assertEqual(sorted(dev_asked), sorted(q.text for q in dev), instruction)
            self.assertEqual(len(result.candidates), len(seen))

    def test_a_tie_resolves_to_the_first_candidate_and_does_so_every_time(self) -> None:
        """Every candidate scoring the same means the search chose nothing; what comes back is
        list order. Pinned because the page says exactly this about the stub run."""
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            instructions = ["first candidate", "second candidate", "third candidate"]
            selected = []
            for _ in range(2):
                model = StubModel(lambda messages, tools: StubResponse(text="no idea at all"))
                tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
                result = run(
                    tracer,
                    model,
                    questions_path=questions_path,
                    instructions=instructions,
                    held_out_fraction=0.25,
                    seed=0,
                )
                self.assertEqual({c.dev_correct for c in result.candidates}, {0})
                selected.append(result.selected)
            self.assertEqual(selected, ["first candidate", "first candidate"])

    def test_an_empty_development_split_is_refused_rather_than_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            model = StubModel(lambda messages, tools: StubResponse(text="nope"))
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
            with self.assertRaises(ValueError):
                run(tracer, model, questions_path=questions_path, held_out_fraction=1.0, seed=0)

    def test_a_dev_question_is_asked_once_per_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            asked_count: dict[str, int] = {}

            def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
                q = messages[-1].content
                asked_count[q] = asked_count.get(q, 0) + 1
                return StubResponse(text="nope")

            model = StubModel(responder)
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
            run(tracer, model, questions_path=questions_path, held_out_fraction=0.25, seed=0)

            questions = load_exact_questions(questions_path)
            dev, held_out = split_dev_held_out(questions, held_out_fraction=0.25, seed=0)
            from examples.prompt_optimization.run import CANDIDATE_INSTRUCTIONS

            for q in dev:
                self.assertEqual(asked_count[q.text], len(CANDIDATE_INSTRUCTIONS))
            for q in held_out:
                self.assertEqual(asked_count[q.text], 1)  # only the winner, once

    def test_run_records_only_code_decided_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), QUESTIONS)
            model = StubModel(lambda messages, tools: StubResponse(text="nope"))
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
            run(tracer, model, questions_path=questions_path, held_out_fraction=0.25, seed=0)

            self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
            self.assertEqual(tracer.model_decided_count(), 0)
            self.assertTrue(any(s.kind == "model" for s in tracer.steps))

    def test_declares_its_level(self) -> None:
        import examples.prompt_optimization.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 1)

    def test_record_trace_still_finds_prompt_optimization_unrecordable(self) -> None:
        # `run(tracer, model, *, questions_path=..., instructions=None, ...)` searches over the
        # whole candidate list against the question set in one call, not one question, and this
        # same `run` is what prompt-optimization.mdx's `<CodeFile func="run" />` shows -- adding
        # a second, differently-shaped `run` here would either collide with that name or
        # silently change what the page displays. Left unrecordable on purpose; see
        # .local/page-requests/wave6-examples.md.
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("prompt_optimization")
        self.assertFalse(rec.ok)
        self.assertIn("tracer", rec.reason)


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)

    def test_the_scripted_sequence_selects_the_real_winner_and_confirms_it_on_held_out(self) -> None:
        # DEMO_QUESTIONS is the small, real subset --demo-subset writes to disk; write it here
        # the same way and run the exact sequence SCRIPTED plays, to prove the 14-call demo
        # actually shows a search finding a winner, not a tie the way --model stub alone does.
        with tempfile.TemporaryDirectory() as tmp:
            questions_path = _write_questions(Path(tmp), DEMO_QUESTIONS["questions"])
            model = StubModel([StubResponse(text=t) for t in SEQUENCE])
            tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)
            result = run(tracer, model, questions_path=questions_path)

            winner = "You are a Halvorsen appliance support assistant. Answer in one or two plain sentences, with no citations and no hedging."
            self.assertEqual(result.selected, winner)
            by_instruction = {c.instruction: (c.dev_correct, c.dev_total) for c in result.candidates}
            self.assertEqual(by_instruction[winner], (4, 4))
            self.assertEqual(result.held_out_correct, 2)
            self.assertEqual(result.held_out_total, 2)


if __name__ == "__main__":
    unittest.main()
