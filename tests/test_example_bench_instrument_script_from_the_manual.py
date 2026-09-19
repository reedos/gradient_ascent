"""Tests for examples/bench_instrument_script_from_the_manual: level 3, draft an instrument
script from its manual and check it against the simulated instrument before a person ever sees
it. Mirrors the shape of tests/test_example_evaluator_optimizer.py: run end to end on a scripted
StubModel and check both the trace's decided_by pattern and the loop's own behavior.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.bench import Approval, SafetyEnvelope, SafetyRefusal  # noqa: E402
from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.bench_instrument_script_from_the_manual.__main__ import SCRIPTED  # noqa: E402
from examples.bench_instrument_script_from_the_manual.run import (  # noqa: E402
    LEVEL,
    TASK,
    parse_reading,
    run,
)

# A draft written as if the TRN-2400 were a Maridun instrument: a long-form keyword ("CURRent")
# and the ON/OFF words Maridun accepts and Tarnley does not. Both are documented mistakes in
# evals/bench/corpus/trn2400-programming-manual.md section 2.
BAD_DRAFT = "MODE CC\nCURRent 1.000\nINP ON\nMEAS:VOLT?\nMEAS:CURR?\nINP OFF"
GOOD_DRAFT = "MODE CC\nCURR 1.000\nINP 1\nMEAS:VOLT?\nMEAS:CURR?\nINP 0"
#: BAD_DRAFT with only the keyword fixed: a plausible half-correction that leaves the boolean
#: words wrong. The command's own scripted sequence draft, revise, revise again, matching
#: SCRIPTED in examples/bench_instrument_script_from_the_manual/__main__.py.
PARTIAL_DRAFT = "MODE CC\nCURR 1.000\nINP ON\nMEAS:VOLT?\nMEAS:CURR?\nINP OFF"
SEQUENCE = [BAD_DRAFT, PARTIAL_DRAFT, GOOD_DRAFT]


def make_tracer() -> Tracer:
    return Tracer(example="bench_instrument_script_from_the_manual", level=LEVEL, model_id="stub-1")


class InstrumentScriptExampleTests(unittest.TestCase):
    def test_a_clean_draft_needs_no_revision(self) -> None:
        model = StubModel([StubResponse(text=GOOD_DRAFT)])
        tracer = make_tracer()
        result = run(TASK, model, tracer)
        self.assertEqual(len(result.attempts), 1)
        self.assertEqual(result.attempts[0].errors, [])
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)

    def test_a_maridun_style_draft_is_rejected_and_fixed_within_the_cap(self) -> None:
        model = StubModel([StubResponse(text=BAD_DRAFT), StubResponse(text=GOOD_DRAFT)])
        tracer = make_tracer()
        result = run(TASK, model, tracer)

        self.assertEqual(len(result.attempts), 2)
        first_codes = {error.split(",", 1)[0] for _, error in result.attempts[0].errors}
        self.assertEqual(first_codes, {"-113", "-224"}, "the manual's own two dialect mistakes")
        self.assertEqual(result.attempts[1].errors, [])
        self.assertEqual(result.final_commands, GOOD_DRAFT.splitlines())

        # Level 3: the model is called, but code decides every branch -- whether to revise, what
        # feedback to send, and when to stop. tests/common/trace.py is the single definition.
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "draft + one revision")

    def test_the_checked_script_reads_the_manuals_own_worked_numbers(self) -> None:
        """evals/bench/corpus/trn2400-programming-manual.md's worked example reads 4.9930V and
        1.0000A at 24 V in, 1.000 A load; the DUT model in examples/common/bench.py computes the
        same two numbers, so this is a real cross-check and not a coincidence of wording."""
        model = StubModel([StubResponse(text=GOOD_DRAFT)])
        tracer = make_tracer()
        result = run(TASK, model, tracer)
        self.assertAlmostEqual(result.readings["vout_v"], 4.9930, places=4)
        self.assertAlmostEqual(result.readings["iout_a"], 1.0000, places=4)
        self.assertEqual(result.approver, "the test engineer")

    def test_a_draft_that_never_clears_stops_at_the_cap_with_no_readings(self) -> None:
        model = StubModel([StubResponse(text=BAD_DRAFT) for _ in range(4)])
        tracer = make_tracer()
        result = run(TASK, model, tracer, max_revisions=1)
        self.assertEqual(len(result.attempts), 2, "the first draft plus exactly one revision")
        self.assertEqual(result.readings, {})
        stop_steps = [s for s in tracer.steps if s.title == "Stop: revision cap reached"]
        self.assertEqual(len(stop_steps), 1)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))

    def test_enabling_the_load_on_an_approval_for_another_set_point_is_refused(self) -> None:
        # The gate is GuardedLoad.input_on in examples/common/bench.py: the board comes up at
        # 24.0 V and the script sets the load to 1.000 A, so an approval naming 4.5 A does not
        # fit the enable it is being used for.
        model = StubModel([StubResponse(text=GOOD_DRAFT)])
        tracer = make_tracer()
        with self.assertRaises(SafetyRefusal):
            run(TASK, model, tracer, approval_load=Approval("the test engineer", 24.0, 4.5, reason="wrong set point"))

    def test_enabling_the_load_on_something_that_is_not_an_approval_is_refused(self) -> None:
        model = StubModel([StubResponse(text=GOOD_DRAFT)])
        tracer = make_tracer()
        with self.assertRaises(SafetyRefusal):
            run(TASK, model, tracer, approval_load="the test engineer said it was fine")  # type: ignore[arg-type]

    def test_a_load_current_over_the_envelope_never_reaches_the_instrument(self) -> None:
        over_limit = GOOD_DRAFT.replace("CURR 1.000", "CURR 4.600")
        model = StubModel([StubResponse(text=over_limit)])
        tracer = make_tracer()
        with self.assertRaises(SafetyRefusal):
            run(TASK, model, tracer, envelope=SafetyEnvelope())

    def test_parse_reading_strips_a_tarnley_unit_suffix_a_bare_maridun_reply_does_not_have(self) -> None:
        self.assertEqual(parse_reading("4.9930V"), 4.9930)
        self.assertEqual(parse_reading("1.0000A"), 1.0000)
        self.assertEqual(parse_reading("1000.0000OHM"), 1000.0)
        self.assertEqual(parse_reading("24.0000"), 24.0)
        with self.assertRaises(ValueError):
            float("4.9930V")  # the naive call this function exists to not make

    def test_the_recipe_pages_token_figures_are_what_a_run_actually_counts(self) -> None:
        """The cost section states ~760 tokens for a clean draft and ~1,575 for one with a single
        dialect mistake in it, and the low-volume line reuses the second figure as the whole model
        cost of an afternoon's characterization script. Both are counted by
        `examples/common/model.py`'s deterministic estimator over the manual excerpt this example
        actually sends, not by a provider's tokenizer, so they move whenever the excerpt does.
        """
        for responses, expected in (
            ([StubResponse(text=GOOD_DRAFT)], 760),
            ([StubResponse(text=BAD_DRAFT), StubResponse(text=GOOD_DRAFT)], 1575),
        ):
            with self.subTest(total=expected):
                tracer = make_tracer()
                run(TASK, StubModel(responses), tracer)
                total = sum((s.tokens_in or 0) + (s.tokens_out or 0) for s in tracer.steps)
                self.assertEqual(total, expected)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.bench_instrument_script_from_the_manual.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 3)


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)

    def test_the_scripted_sequence_needs_both_revisions_and_then_runs_clean(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = make_tracer()
        result = run(TASK, model, tracer)
        self.assertEqual(len(result.attempts), 3)
        first_codes = {error.split(",", 1)[0] for _, error in result.attempts[0].errors}
        self.assertEqual(first_codes, {"-113", "-224"})
        second_codes = {error.split(",", 1)[0] for _, error in result.attempts[1].errors}
        self.assertEqual(second_codes, {"-224"}, "the keyword is fixed; only the booleans are still wrong")
        self.assertEqual(result.attempts[2].errors, [])
        self.assertEqual(result.final_commands, GOOD_DRAFT.splitlines())
        self.assertTrue(result.readings)


if __name__ == "__main__":
    unittest.main()
