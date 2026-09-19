"""Every example's own command, run.

`--model stub:scripted` (`examples/common/cli.py`) plays a sequence of replies, one per model
call, written down in the example's own `__main__.py` as `SCRIPTED`: in call order, or matched
against each call's prompt where the example calls the model from a thread pool and there is no
call order to script against. This file is the guard that keeps the sequence and the example
together: it runs every example's demo command against its own `SCRIPTED` and fails if the run
asks for a reply the sequence does not have, if the command exits nonzero, or if it prints
nothing.

That is the failure that matters. A sequence kept anywhere other than beside the example drifts
from it silently, and the first symptom is a "Run it" command on a published page that prints a
truncated demo of something the page does not claim. Here an example that grows a model call
fails on the next test run, naming the call number, in `ScriptExhausted`.

Two more things are checked:

- Every example has either a `SCRIPTED` or an entry in `NO_SCRIPT` saying why it needs none, so a
  new example cannot be added without deciding which it is.
- No example calls a model or a network here. `stub:scripted` is a fixture, the same as
  `--model stub`; `tests/test_common.py` holds the unit tests for both.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.cli import SCRIPTED_SPEC, WhenAsked  # noqa: E402
from examples.common.model import StubResponse  # noqa: E402

EXAMPLES_DIR = ROOT / "examples"

# An example that never calls a model has nothing to script, and saying so here is how that stays
# a decision rather than an oversight. Every other example must export SCRIPTED.
NO_SCRIPT = {
    "adaptation": "it writes a fine-tuning set out of the corpus by code; nothing here calls a model",
    "ai_gateways": "the demo is two hard-coded providers, so the gateway's fallback is visible without a script",
    "bench_characterize_a_design": "level 0: the whole point is that no model is called",
    "bench_limits_without_a_model": "level 0: the whole point is that no model is called",
    "embeddings_search": "level 2 retrieval only: it embeds and ranks, and calls no model",
    "household_paperwork": "level 0: the renewal and bill dates are read and sorted by code",
    "knowledge_graphs": "its command plays a transcribed extraction of its own, so --model never reaches a stub",
    "local_inference": "the command sizes a model in memory: arithmetic, no call",
    "observability": "the command reads recorded traces; nothing in it calls a model",
    "ops": "the command costs recorded traces out; nothing in it calls a model",
    "order_zero": "level 0: the whole point is that no model is called",
    "reviewing": "it checks an answer's figures and citations against the sources, by code",
}


def example_names() -> list[str]:
    return sorted(
        entry.name
        for entry in EXAMPLES_DIR.iterdir()
        if entry.is_dir()
        and entry.name not in {"common", "__pycache__"}
        and (entry / "__main__.py").exists()
    )


def load_main(example: str):
    return importlib.import_module(f"examples.{example}.__main__")


def demo_argv(module, tmpdir: str = "") -> list[str]:
    """The arguments the example's documented demo command passes besides `--model`. Most
    examples need none, because their `__main__` defaults `--question` to the input the sequence
    was written for.

    An example that writes a file writes `{tmpdir}` into its `DEMO_ARGV` where the path goes, so
    running the suite leaves nothing behind in the repository. The command a page prints names a
    real path instead; the arguments are otherwise the same.
    """
    return [arg.replace("{tmpdir}", tmpdir) for arg in getattr(module, "DEMO_ARGV", [])]


def run_demo(example: str) -> tuple[int, str]:
    """Run one example's demo command exactly as a reader would, and capture what they see."""
    module = load_main(example)
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as tmpdir:
        with contextlib.redirect_stdout(out):
            code = module.main(["--model", SCRIPTED_SPEC, *demo_argv(module, tmpdir)])
    return code, out.getvalue()


class ScriptedSequenceTests(unittest.TestCase):
    def test_every_example_either_scripts_its_command_or_says_why_it_needs_none(self) -> None:
        unscripted = {name for name in example_names() if not getattr(load_main(name), "SCRIPTED", None)}
        self.assertEqual(
            unscripted,
            set(NO_SCRIPT),
            "an example with no SCRIPTED has no command that demonstrates what its page claims; "
            "add one, or add the example to NO_SCRIPT with the reason it calls no model",
        )

    def test_a_scripted_sequence_is_replies_in_call_order_or_matched_on_the_prompt(self) -> None:
        for name in example_names():
            script = getattr(load_main(name), "SCRIPTED", None)
            if script is None:
                continue
            with self.subTest(example=name):
                self.assertIsInstance(script, list, "SCRIPTED must be a list, one entry per call")
                self.assertTrue(script, "an empty SCRIPTED is the same as having none")
                for entry in script:
                    self.assertIsInstance(entry, (str, StubResponse, WhenAsked))
                keyed = [e for e in script if isinstance(e, WhenAsked)]
                self.assertIn(
                    len(keyed),
                    (0, len(script)),
                    "a sequence is either all ordered or all matched on the prompt, never half of each",
                )
                # A `when` that also appears in another entry's prompt would pair a call with the
                # wrong reply on some runs, which is the defect this form exists to prevent.
                self.assertEqual(len({e.when for e in keyed}), len(keyed), "two entries share a `when`")

    def test_every_sequence_is_asserted_against_by_the_example_s_own_tests(self) -> None:
        """The other half of the guard. This file proves a sequence still *runs*; the example's
        own test file proves it is still the sequence that test says the example needs, by
        asserting on `SCRIPTED` directly. Without that line, a reply could be edited into
        something the example's behavior tests never cover and nothing would notice."""
        for name in example_names():
            if name in NO_SCRIPT:
                continue
            with self.subTest(example=name):
                path = ROOT / "tests" / f"test_example_{name}.py"
                if not path.exists():
                    # one_call, order_zero and rag have no test file of their own
                    path = ROOT / "tests" / "test_examples.py"
                asserted = [
                    line
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if "SCRIPTED" in line and "assert" in line
                ]
                self.assertTrue(
                    asserted,
                    f"{path.name} never asserts on {name}'s SCRIPTED, so the sequence its command "
                    f"plays and the sequence this file scripts can drift apart silently",
                )


class DemoCommandTests(unittest.TestCase):
    """The real check: run each example's own command and look at what came out."""

    def test_every_scripted_command_runs_to_the_end_and_prints_something(self) -> None:
        for name in example_names():
            if name in NO_SCRIPT:
                continue
            with self.subTest(example=name):
                code, printed = run_demo(name)
                self.assertEqual(code, 0, f"{name} exited {code}")
                self.assertTrue(printed.strip(), f"{name} printed nothing")

    def test_every_unscripted_command_still_runs(self) -> None:
        # They call no model, so --model stub:scripted has nothing to play; the generic stub is
        # still the documented way to run them and must keep working.
        for name in NO_SCRIPT:
            with self.subTest(example=name):
                module = load_main(name)
                out = io.StringIO()
                with tempfile.TemporaryDirectory() as tmpdir:
                    with contextlib.redirect_stdout(out):
                        code = module.main(["--model", "stub", *demo_argv(module, tmpdir)])
                self.assertEqual(code, 0)
                self.assertTrue(out.getvalue().strip())

    def test_the_scripted_run_shows_something_the_echo_stub_cannot(self) -> None:
        # If both stubs print the same thing, the sequence is not reaching the output and the
        # command demonstrates no more than it did before.
        for name in example_names():
            if name in NO_SCRIPT:
                continue
            with self.subTest(example=name):
                module = load_main(name)
                _, scripted = run_demo(name)
                echo = io.StringIO()
                with tempfile.TemporaryDirectory() as tmpdir:
                    with contextlib.redirect_stdout(echo):
                        # The echo stub is allowed to fail here: several examples cannot complete
                        # a run on an echoed reply at all, which is the defect this mode exists
                        # for.
                        with contextlib.suppress(Exception, SystemExit):
                            module.main(["--model", "stub", *demo_argv(module, tmpdir)])
                self.assertNotEqual(
                    scripted.strip(),
                    echo.getvalue().strip(),
                    f"{name}: the scripted replies never reach what the command prints",
                )


if __name__ == "__main__":
    unittest.main()
