"""Tests for scripts/record_trace.py's discovery, `classify`, `--list` and `--dry-run`.

Recording itself (writing trace.json, the stub refusal rule) is tests/test_record_trace.py; this
module is about the part that replaced the old hard-coded `EXAMPLE_NAMES` list: every example
directory is found on disk, each one is classified by reading its own `run.py`, and `--dry-run`
never calls a model.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import record_trace  # noqa: E402

_STDOUT: contextlib.AbstractContextManager | None = None


def setUpModule() -> None:
    global _STDOUT
    _STDOUT = contextlib.redirect_stdout(io.StringIO())
    _STDOUT.__enter__()


def tearDownModule() -> None:
    if _STDOUT is not None:
        _STDOUT.__exit__(None, None, None)


class DiscoveryTests(unittest.TestCase):
    def test_every_example_directory_on_disk_is_discovered(self) -> None:
        # Computed independently of record_trace.discover_examples(), the same way a reader
        # would list them by hand, so this actually checks discovery rather than repeating it.
        examples_dir = ROOT / "examples"
        on_disk = sorted(
            entry.name
            for entry in examples_dir.iterdir()
            if entry.is_dir() and entry.name not in {"common", "__pycache__"} and (entry / "run.py").exists()
        )
        self.assertEqual(record_trace.EXAMPLE_NAMES, on_disk)
        # A stale hard-coded list is exactly the bug this script no longer has; pin roughly where
        # the count should be without hard-coding the exact number the repo happens to be at.
        self.assertGreaterEqual(len(on_disk), 40)

    def test_discover_examples_excludes_the_shared_common_package(self) -> None:
        self.assertNotIn("common", record_trace.EXAMPLE_NAMES)

    def test_discover_examples_is_sorted(self) -> None:
        self.assertEqual(record_trace.EXAMPLE_NAMES, sorted(record_trace.EXAMPLE_NAMES))


class ClassifyTests(unittest.TestCase):
    def test_rag_is_recordable_and_takes_an_embedder(self) -> None:
        rec = record_trace.classify("rag")
        self.assertTrue(rec.ok, rec.reason)
        self.assertTrue(rec.takes_embedder)
        self.assertEqual(rec.level, 2)

    def test_structured_output_is_recordable_without_an_embedder(self) -> None:
        rec = record_trace.classify("structured_output")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)

    def test_examples_that_gained_a_run_wrapper_are_now_recordable(self) -> None:
        # wave 6 (.local/page-requests/wave6-examples.md) gave each of these a `run` that fits
        # the shared convention: agent_teammates, embodied, long_horizon and organizations_swarms
        # gained a thin wrapper around their differently-named or differently-shaped real entry
        # point (run_tick, run_step, run_session, coordinate -- all still there, unchanged); ops,
        # observability, ai_gateways and local_inference had no run() at all and gained one that
        # calls no model, since none of the four ever did.
        for example in (
            "agent_teammates", "embodied", "long_horizon", "organizations_swarms",
            "ops", "observability", "ai_gateways", "local_inference",
        ):
            rec = record_trace.classify(example)
            self.assertTrue(rec.ok, f"{example}: {rec.reason}")

    def test_examples_that_gained_a_default_are_now_recordable(self) -> None:
        # multimodal's `image` and prompt_engineering's `structured` used to be required
        # keyword-only arguments with no default, so one --question could not supply a complete
        # call; both now default (a label-only synthetic image, and structured=True).
        for example in ("multimodal", "prompt_engineering"):
            rec = record_trace.classify(example)
            self.assertTrue(rec.ok, f"{example}: {rec.reason}")

    def test_examples_that_keep_a_different_run_shape_stay_unrecordable(self) -> None:
        # reviewing's run(answer, sections, tracer) is what reviewing.mdx's own <CodeFile
        # func="run" /> shows; adaptation, distillation, synthetic_data and prompt_optimization
        # each process the whole question set in one call under a `run` their own pages pin the
        # same way. Reshaping any of them, or adding a second `run` under the same name, would
        # collide with the pin or change what the page displays -- left unrecordable on purpose;
        # see .local/page-requests/wave6-examples.md.
        for example in ("reviewing", "adaptation", "distillation", "synthetic_data", "prompt_optimization"):
            rec = record_trace.classify(example)
            self.assertFalse(rec.ok, example)

    def test_recordable_examples_are_a_subset_of_discovered_examples(self) -> None:
        recordable = record_trace.recordable_examples()
        self.assertTrue(set(recordable).issubset(set(record_trace.EXAMPLE_NAMES)))
        self.assertGreater(len(recordable), 0)
        self.assertLess(len(recordable), len(record_trace.EXAMPLE_NAMES))
        for example in recordable:
            self.assertTrue(record_trace.classify(example).ok)


class ListStatusTests(unittest.TestCase):
    def test_list_status_covers_every_discovered_example_exactly_once(self) -> None:
        rows = record_trace.list_status()
        names = [r["example"] for r in rows]
        self.assertEqual(names, record_trace.EXAMPLE_NAMES)
        self.assertEqual(len(names), len(set(names)))

    def test_list_status_is_stable_across_calls(self) -> None:
        self.assertEqual(record_trace.list_status(), record_trace.list_status())

    def test_list_status_marks_a_known_recordable_and_a_known_unrecordable_example(self) -> None:
        rows = {r["example"]: r for r in record_trace.list_status()}
        self.assertTrue(rows["rag"]["recordable"])
        self.assertEqual(rows["rag"]["reason"], "")
        self.assertFalse(rows["adaptation"]["recordable"])
        self.assertTrue(rows["adaptation"]["reason"])

    def test_main_list_exits_zero_and_names_every_example(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = record_trace.main(["--list"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("rag", output)
        self.assertIn("adaptation", output)
        self.assertIn("recordable", output)

    def test_list_needs_no_example_question_or_model(self) -> None:
        code = record_trace.main(["--list"])
        self.assertEqual(code, 0)


class DryRunTests(unittest.TestCase):
    def test_dry_run_never_builds_a_real_model(self) -> None:
        """`--dry-run` must not construct a real backend at all -- not just avoid calling
        `.complete()` on one. Patching `build_model` to raise is a stronger guarantee than
        patching `.complete`, because it catches the mistake of constructing a `ClaudeModel` or
        `OllamaModel` (which, per examples/common/model.py, do no I/O on construction, but would
        still mean a real backend's config -- an API key, a host -- is on the hook) merely to
        read its `model_id`.
        """

        def _raise(*args, **kwargs):
            raise AssertionError("dry-run must not call build_model")

        original = record_trace.build_model
        record_trace.build_model = _raise
        try:
            code = record_trace.main(
                [
                    "--example", "rag", "--question", "What is the DW-480's warranty?",
                    "--model", "claude:claude-sonnet-5", "--dry-run",
                ]
            )
        finally:
            record_trace.build_model = original
        self.assertEqual(code, 0)

    def test_dry_run_writes_nothing(self) -> None:
        import shutil
        import tempfile

        tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)
        out_path = tmp_dir / "would-be-trace.json"
        summary = record_trace.project("rag", "What is the DW-480's warranty?", "ollama:llama3.1", out_path=out_path)
        self.assertFalse(out_path.exists(), "--dry-run must not write a trace file")
        self.assertEqual(summary["would_write"], str(out_path))

    def test_dry_run_reports_model_id_tokens_and_destination(self) -> None:
        summary = record_trace.project(
            "rag", "What is the DW-480's warranty, and what voids it?", "ollama:llama3.1", out_path=Path("examples/rag/trace.json")
        )
        self.assertEqual(summary["example"], "rag")
        self.assertEqual(summary["model_id"], "ollama:llama3.1")
        self.assertGreater(summary["tokens_in"], 0)
        self.assertGreater(summary["tokens_out"], 0)
        self.assertGreater(summary["steps"], 0)
        self.assertTrue(summary["would_write"].endswith("trace.json"))

    def test_dry_run_works_without_an_embedder_shaped_example(self) -> None:
        summary = record_trace.project(
            "structured_output", "What is the DW-300's warranty?", "ollama:llama3.1", out_path=Path("x")
        )
        self.assertEqual(summary["example"], "structured_output")

    def test_dry_run_refuses_an_unrecordable_example(self) -> None:
        with self.assertRaises(ValueError):
            record_trace.project("adaptation", "anything", "ollama:llama3.1", out_path=Path("x"))

    def test_main_dry_run_prints_no_model_was_called(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = record_trace.main(
                [
                    "--example", "rag", "--question", "What is the DW-480's warranty?",
                    "--model", "ollama:llama3.1", "--dry-run",
                ]
            )
        self.assertEqual(code, 0)
        self.assertIn("no model was called", buf.getvalue())


class EmbedderFlagTests(unittest.TestCase):
    """`--embedder` lets the chat model and embedder specs differ, since `build_embedder` has no
    `claude:` branch (examples/common/model.py) -- a metered chat model needs a local embedder
    paired in explicitly, rather than the same spec used for both, which is what every example
    did before this flag existed."""

    def test_embedder_defaults_to_none_so_it_falls_back_to_model(self) -> None:
        args = record_trace.build_args(["--example", "rag", "--question", "x"])
        self.assertIsNone(args.embedder)

    def test_embedder_can_be_set_independently_of_model(self) -> None:
        args = record_trace.build_args(
            ["--example", "rag", "--question", "x", "--model", "claude:claude-sonnet-5", "--embedder", "ollama:nomic-embed-text"]
        )
        self.assertEqual(args.model, "claude:claude-sonnet-5")
        self.assertEqual(args.embedder, "ollama:nomic-embed-text")


if __name__ == "__main__":
    unittest.main()
