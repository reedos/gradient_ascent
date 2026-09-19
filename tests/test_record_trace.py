"""Tests for scripts/record_trace.py: the stub refusal rule and the written trace shape.

Discovery, `--list` and `--dry-run` have their own module, tests/test_record_trace_discovery.py,
so this file stays about what recording actually writes.
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

import record_trace  # noqa: E402

# These tests drive command-line entry points, which print what they did. Capturing stdout for
# the module keeps a real failure readable: without it one run of the suite buries its assertion
# messages under several screens of corpus text and "wrote ..." lines. stderr is left alone, so a
# traceback still reaches the terminal.
_STDOUT: contextlib.AbstractContextManager | None = None


def setUpModule() -> None:
    global _STDOUT
    _STDOUT = contextlib.redirect_stdout(io.StringIO())
    _STDOUT.__enter__()


def tearDownModule() -> None:
    if _STDOUT is not None:
        _STDOUT.__exit__(None, None, None)


class RecordTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_refuses_to_write_a_stub_trace_without_allow_stub(self) -> None:
        out_path = self._tmp / "trace.json"
        code = record_trace.main(
            ["--example", "order_zero", "--question", "How often should the DW-300 filter be cleaned?", "--model", "stub", "--out", str(out_path)]
        )
        self.assertEqual(code, 1)
        self.assertFalse(out_path.exists())

    def test_writes_a_stub_trace_with_allow_stub(self) -> None:
        out_path = self._tmp / "trace.json"
        code = record_trace.main(
            [
                "--example", "order_zero", "--question", "How often should the DW-300 filter be cleaned?",
                "--model", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(out_path.exists())
        data = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(data["example"], "order_zero")
        self.assertEqual(data["level"], 0)
        self.assertFalse(data["illustrative"])
        self.assertIn("recorded_at", data)
        self.assertTrue(data["steps"])
        self.assertTrue(all(step["decided_by"] == "code" for step in data["steps"]))

    def test_trace_file_is_lf_only(self) -> None:
        out_path = self._tmp / "trace.json"
        record_trace.main(
            [
                "--example", "one_call", "--question", "What voltage does a DR-210 need?",
                "--model", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        raw = out_path.read_bytes()
        self.assertNotIn(b"\r", raw)

    def test_every_recordable_example_records_a_stub_trace_without_running_out_of_responses(self) -> None:
        # prompt chaining calls the model twice and the agent loop calls it as often as it
        # likes; a fixed one-response stub raised IndexError part-way through the run. This
        # covers every example record_trace.py discovers as recordable, not a fixed list, so a
        # future example that follows the shared run() convention is exercised automatically.
        examples = record_trace.recordable_examples()
        self.assertGreaterEqual(len(examples), 35, "expected most discovered examples to be recordable")
        for example in examples:
            out_path = self._tmp / f"{example}.json"
            code = record_trace.main(
                [
                    "--example", example, "--question", "What is the maximum vent run for a DR-520?",
                    "--model", "stub", "--allow-stub", "--out", str(out_path),
                ]
            )
            self.assertEqual(code, 0, f"{example} failed to record")
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertTrue(data["steps"], f"{example} recorded no steps")
            self.assertEqual(data["example"], example)

    def test_a_stub_trace_is_marked_stub_so_the_site_can_refuse_it(self) -> None:
        out_path = self._tmp / "trace.json"
        record_trace.main(
            [
                "--example", "rag", "--question", "What voltage does a DR-210 need?",
                "--model", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        data = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertTrue(data["stub"])
        self.assertFalse(data["illustrative"])
        self.assertIn("model_decided_steps", data)

    def test_function_calling_trace_records_a_model_decided_step(self) -> None:
        out_path = self._tmp / "trace.json"
        record_trace.main(
            [
                "--example", "function_calling", "--question", "What does part HLV-2205 cost?",
                "--model", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        data = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(data["level"], 4)
        # the generic interactive-style stub used by record_trace never calls a tool, so the
        # single completion is still the model's choice not to call one
        model_steps = [s for s in data["steps"] if s["decided_by"] == "model"]
        self.assertEqual(len(model_steps), 1)

    def test_an_example_with_no_embedder_in_its_signature_records_fine(self) -> None:
        # structured_output and inference_time_reasoning take (question, model, tracer): no
        # embedder. record_trace.py must not try to build or pass one for these.
        out_path = self._tmp / "trace.json"
        code = record_trace.main(
            [
                "--example", "structured_output", "--question", "What is the DW-300's warranty?",
                "--model", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        self.assertEqual(code, 0)
        data = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertTrue(data["steps"])

    def test_a_pendingreview_result_is_described_without_crashing(self) -> None:
        # human_in_the_loop's run() can return PendingReview instead of Answer; PendingReview has
        # no .text attribute (it has .draft_text). The generic stub answer never clears the
        # confidence threshold, so this exercises that path on every run.
        out_path = self._tmp / "trace.json"
        code = record_trace.main(
            [
                "--example", "human_in_the_loop", "--question", "What is the maximum vent run for a DR-520?",
                "--model", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(out_path.exists())

    def test_unrecordable_example_is_refused_with_its_reason_and_exit_code_two(self) -> None:
        # adaptation processes the whole question set in one call, not one question, and stays
        # unrecordable on purpose -- see .local/page-requests/wave6-examples.md.
        out_path = self._tmp / "trace.json"
        code = record_trace.main(
            ["--example", "adaptation", "--question", "anything", "--model", "stub", "--allow-stub", "--out", str(out_path)]
        )
        self.assertEqual(code, 2)
        self.assertFalse(out_path.exists())

    def test_unknown_example_name_is_refused(self) -> None:
        code = record_trace.main(["--example", "not-a-real-example", "--question", "x", "--model", "stub", "--allow-stub"])
        self.assertEqual(code, 2)

    def test_missing_question_is_refused(self) -> None:
        code = record_trace.main(["--example", "rag", "--model", "stub", "--allow-stub"])
        self.assertEqual(code, 2)

    def test_an_explicit_embedder_spec_still_records_an_embedder_shaped_example(self) -> None:
        # rag's run() takes an embedder; passing --embedder explicitly (rather than leaving it to
        # default from --model) must not change that recording still works.
        out_path = self._tmp / "trace.json"
        code = record_trace.main(
            [
                "--example", "rag", "--question", "What is the DW-480's warranty?",
                "--model", "stub", "--embedder", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(out_path.exists())


class TraceShapeMatchesSiteVocabularyTests(unittest.TestCase):
    """`examples/common/trace.py` is not this agent's file to change, but its output feeds the
    site eventually (see site/src/components/islands/RunDiagram.tsx: `RunEdge.by` and the node
    kinds are `'code' | 'model'`-shaped vocabulary). These tests pin the vocabulary
    record_trace.py writes so a future converter has something stable to read.
    """

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_step_fields_use_the_site_s_code_model_vocabulary(self) -> None:
        out_path = self._tmp / "trace.json"
        record_trace.main(
            [
                "--example", "function_calling", "--question", "What does part HLV-2205 cost?",
                "--model", "stub", "--allow-stub", "--out", str(out_path),
            ]
        )
        data = json.loads(out_path.read_text(encoding="utf-8"))
        for step in data["steps"]:
            self.assertIn(step["kind"], ("code", "model"))
            self.assertIn(step["decided_by"], ("code", "model"))
            self.assertIn(step["edge"], ("solid", "dashed"))
            # dashed iff the model decided, same rule RunDiagram's legend documents
            self.assertEqual(step["edge"] == "dashed", step["decided_by"] == "model")
            for field in ("i", "title", "detail", "tokens_in", "tokens_out", "ms"):
                self.assertIn(field, step)


if __name__ == "__main__":
    unittest.main()
