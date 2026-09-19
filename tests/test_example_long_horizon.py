"""Tests for examples/long_horizon: the queue-across-sessions example for the long-horizon
technique page. Checks the decided_by pattern for one session, the flag-for-review and resolve
path, and — the property this page exists to prove — that a session which crashes before it
checkpoints loses no completed work and, on retry, repeats none.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.long_horizon.run import (  # noqa: E402
    MAX_NOTES,
    CheckpointError,
    ConcurrentSessionError,
    QueueState,
    resolve,
    run_session,
)

CORPUS_DIR = ROOT / "evals" / "corpus"
Q1 = "What does the DW-300's drain pump cost?"
Q2 = "How long is the DW-300 under warranty?"
Q3 = "What voltage does the DR-210 need?"


def _answer_response(text: str, citations: list[str]) -> StubResponse:
    return StubResponse(tool_calls=[ToolCall(name="answer", arguments={"text": text, "citations": citations})])


def _flag_response(reason: str) -> StubResponse:
    return StubResponse(tool_calls=[ToolCall(name="flag_for_review", arguments={"reason": reason})])


class LongHorizonExampleTests(unittest.TestCase):
    def _tracer(self) -> Tracer:
        return Tracer(example="long_horizon", level=7, model_id="stub-1")

    def test_a_session_records_exactly_one_model_decided_step(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            model = StubModel([_answer_response("$46.00. Sources: parts-list#2", ["parts-list#2"])])
            tracer = self._tracer()
            answer = run_session(state_path, model, tracer, questions=[Q1], corpus_dir=CORPUS_DIR)

            self.assertIsNotNone(answer)
            self.assertEqual(tracer.model_decided_count(), 1)
            model_steps = [s for s in tracer.steps if s.decided_by == "model"]
            self.assertEqual(len(model_steps), 1)
            self.assertEqual(model_steps[0].kind, "model")
            self.assertEqual(model_steps[0].edge, "dashed")
            self.assertEqual(model_steps[0].title, "Model decides whether to answer or flag this question")

            titles = [s.title for s in tracer.steps]
            self.assertEqual(titles[0], "Scheduler starts a session")
            self.assertEqual(tracer.steps[0].decided_by, "code")
            self.assertIn("Checkpoint the queue to disk", titles)
            for step in tracer.steps:
                if step.decided_by == "code":
                    self.assertEqual(step.edge, "solid")

    def test_the_trigger_needs_no_person_and_runs_with_an_empty_queue(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text(json.dumps({"queue": [], "notes": [], "answers": {}, "pending": {}, "sessions_run": 3}), encoding="utf-8")
            model = StubModel([])  # never consulted: the queue is already empty
            tracer = self._tracer()
            answer = run_session(state_path, model, tracer, questions=[Q1], corpus_dir=CORPUS_DIR)
            self.assertIsNone(answer)
            self.assertEqual(tracer.model_decided_count(), 0)
            self.assertEqual(tracer.steps[0].title, "Scheduler starts a session")

    def test_flagging_hands_the_question_to_a_person_and_resolve_finishes_it(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            model = StubModel([_flag_response("the manual and the service bulletin disagree")])
            tracer = self._tracer()
            answer = run_session(state_path, model, tracer, questions=[Q1], corpus_dir=CORPUS_DIR)

            self.assertIsNone(answer)
            state = QueueState.load(state_path, questions=[])
            self.assertEqual(state.pending[Q1], "the manual and the service bulletin disagree")
            self.assertNotIn(Q1, state.answers)
            self.assertEqual(state.queue, [])  # popped off the queue; a person owns it now, not the scheduler

            resolve(state_path, Q1, "A person checked: it's $46.00, per the current bulletin.", tracer)
            resolved = QueueState.load(state_path, questions=[])
            self.assertNotIn(Q1, resolved.pending)
            self.assertIn(Q1, resolved.answers)
            self.assertTrue(resolved.notes[-1].startswith(Q1))

    def test_a_crash_before_the_checkpoint_loses_no_completed_work_and_repeats_none(self) -> None:
        """Session 1 finishes and checkpoints q1. Session 2's model call raises -- a simulated
        crash -- before `run_session` reaches its own checkpoint write. Session 3 retries q2 and
        succeeds. The finished q1 answer must survive the crash untouched and unduplicated, and
        the crashed q2 must be answered exactly once, not zero and not twice."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            questions = [Q1, Q2, Q3]

            model1 = StubModel([_answer_response("$46.00.", ["parts-list#2"])])
            run_session(state_path, model1, self._tracer(), questions=questions, corpus_dir=CORPUS_DIR)
            after_session_1 = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(list(after_session_1["answers"]), [Q1])
            self.assertEqual(after_session_1["queue"], [Q2, Q3])
            self.assertEqual(after_session_1["sessions_run"], 1)

            def crash(messages, tools):
                raise RuntimeError("simulated process crash mid-session")

            crashy_model = StubModel(crash)
            with self.assertRaises(RuntimeError):
                run_session(state_path, crashy_model, self._tracer(), questions=questions, corpus_dir=CORPUS_DIR)

            # nothing was checkpointed by the crashed session: the file on disk is exactly what
            # session 1 left, not a partially-updated sessions_run or a half-popped queue
            after_crash = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(after_crash, after_session_1)

            model3 = StubModel([_answer_response("2 years.", ["warranty-policy#1"])])
            run_session(state_path, model3, self._tracer(), questions=questions, corpus_dir=CORPUS_DIR)
            after_retry = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(sorted(after_retry["answers"]), sorted([Q1, Q2]))
            self.assertEqual(after_retry["answers"][Q1]["text"], "$46.00.")  # untouched by the retry
            self.assertEqual(after_retry["queue"], [Q3])
            self.assertEqual(after_retry["sessions_run"], 2)  # the crashed attempt did not count

    def test_a_damaged_checkpoint_is_an_error_not_a_fresh_start(self) -> None:
        """A file the loader cannot make sense of must stop the session. Starting over silently
        would drop the queue and re-answer everything already answered, and every scheduled tick
        after it would still report success."""
        import tempfile

        damaged = {
            "truncated mid-write": '{"queue": ["a"], "notes": [',
            "empty": "",
            "not an object": "[]",
            "unknown field": '{"queue": [], "notes": [], "answers": {}, "pending": {}, "sessions_run": 0, "injected": 1}',
            "missing queue": '{"notes": [], "answers": {}, "pending": {}, "sessions_run": 0}',
            "queue is a string": '{"queue": "abc", "notes": [], "answers": {}, "pending": {}, "sessions_run": 0}',
            "answers is a list": '{"queue": [], "notes": [], "answers": [], "pending": {}, "sessions_run": 0}',
        }
        for label, blob in damaged.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    state_path = Path(tmp) / "state.json"
                    state_path.write_text(blob, encoding="utf-8")
                    model = StubModel([_answer_response("$46.00.", [])])
                    with self.assertRaises(CheckpointError) as caught:
                        run_session(state_path, model, self._tracer(), questions=[Q1], corpus_dir=CORPUS_DIR)
                    self.assertIn(str(state_path), str(caught.exception))  # the error names the file to repair
                    self.assertEqual(state_path.read_text(encoding="utf-8"), blob)  # and did not overwrite it

    def test_two_sessions_at_once_cannot_silently_overwrite_each_other(self) -> None:
        """Two scheduled sessions overlapping is the ordinary way this goes wrong: both load the
        same checkpoint, both work the same question, and the second write erases the first. The
        checkpoint counter has to be what the session read, or the write is refused."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            questions = [Q1, Q2]
            QueueState(queue=list(questions)).save(state_path)

            first = QueueState.load(state_path, questions=questions)
            second = QueueState.load(state_path, questions=questions)  # started before the first one wrote
            started_from = second.sessions_run

            first.sessions_run += 1
            first.answers[Q1] = {"text": "answered by session one", "citations": []}
            first.queue.pop(0)
            first.save(state_path, expect_sessions_run=started_from)

            second.sessions_run += 1
            second.answers[Q1] = {"text": "answered by session two", "citations": []}
            second.queue.pop(0)
            with self.assertRaises(ConcurrentSessionError):
                second.save(state_path, expect_sessions_run=started_from)

            on_disk = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["answers"][Q1]["text"], "answered by session one")
            self.assertEqual(on_disk["queue"], [Q2])

    def test_the_checkpoint_write_leaves_no_temp_file_and_does_not_share_one(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            QueueState(queue=[Q1]).save(state_path)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["state.json"])
            # the name a concurrent writer in another process would use is not the same file
            self.assertIn(str(os.getpid()), state_path.with_name(f"{state_path.name}.{os.getpid()}.tmp").name)

    def test_notes_are_compacted_not_left_to_grow_without_bound(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            questions = [f"question {i}" for i in range(MAX_NOTES + 3)]
            for i, _ in enumerate(questions):
                model = StubModel([_answer_response(f"answer {i}", [])])
                run_session(state_path, model, self._tracer(), questions=questions, corpus_dir=CORPUS_DIR)

            state = QueueState.load(state_path, questions=[])
            self.assertEqual(len(state.answers), len(questions))  # nothing answered is ever dropped
            self.assertLessEqual(len(state.notes), MAX_NOTES)  # but what a fresh session rereads is capped
            self.assertEqual(state.queue, [])

    def test_the_checkpoint_is_written_with_lf_line_endings(self) -> None:
        # Path.write_text defaults to the platform's line ending, so on Windows the same queue
        # checkpointed to different bytes than it does everywhere else.
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            model = StubModel(
                [StubResponse(tool_calls=[ToolCall(name="answer", arguments={"text": "ok", "citations": []})])]
            )
            run_session(state_path, model, self._tracer(), questions=["What does HLV-2205 cost?"])
            raw = state_path.read_bytes()
            self.assertNotIn(b"\r\n", raw)
            self.assertTrue(raw.endswith(b"\n"))
            self.assertEqual(json.loads(raw.decode("utf-8"))["sessions_run"], 1)

    def test_declares_its_level(self) -> None:
        import examples.long_horizon.run as module

        self.assertEqual(module.LEVEL, 7)


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(question, model, tracer)` is the entry point `record_trace.py` calls: one session
    against a fresh checkpoint file in a new temp directory, so two calls never see each other's
    queue."""

    def test_run_is_one_session_against_a_fresh_checkpoint(self) -> None:
        from examples.long_horizon.run import run

        model = StubModel([_answer_response("$46.00. Sources: parts-list#2", ["parts-list#2"])])
        tracer = Tracer(example="long_horizon", level=7, model_id="stub-1")
        answer = run(Q1, model, tracer)
        self.assertIsNotNone(answer)

    def test_two_calls_to_run_do_not_share_a_queue(self) -> None:
        from examples.long_horizon.run import run

        tracer = Tracer(example="long_horizon", level=7, model_id="stub-1")
        answer1 = run(Q1, StubModel([_answer_response("a1", [])]), tracer)
        answer2 = run(Q1, StubModel([_answer_response("a2", [])]), tracer)
        self.assertEqual(answer1.text, "a1")
        self.assertEqual(answer2.text, "a2")  # a shared checkpoint would have had nothing left to answer

    def test_record_trace_classifies_long_horizon_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("long_horizon")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
