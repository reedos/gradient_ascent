"""Tests for examples/bench_test_failure_triage: sort a failing SRB-5030 unit's operator note
into a cause the failure analysis guide already lists, then route it.

Every case below runs against the real `evals/bench/data/production-run-2026-08.csv`, the same
file `docs/THE-BENCH.md` Story 2 describes: FIX-03 carries a stale calibration offset and accounts
for most of the month's VOUT failures, and two of those failures are boards that are actually
dead. The point of these tests is that dead-board serial: a group signature and a genuine defect
sitting on the very same fixture, which is exactly the case a rule that only ever trusted the
group count would get wrong.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import PRODUCTION_CSV  # noqa: E402
from examples.bench_test_failure_triage.run import (  # noqa: E402
    LEVEL,
    SAMPLE_INPUT,
    FailureRow,
    _group_signature,
    _route,
    _validate,
    confirm,
    load_failures,
    run,
)
from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

# Real serials from evals/bench/data/production-run-2026-08.csv, confirmed against the file
# before writing these tests (see the docstrings on each test for what makes each one worth it).
FIXTURE_FAULT_SERIAL = "SRB5030-2608-0011"  # FIX-03, note blames the fixture by name
DEAD_ON_OFFSET_FIXTURE_SERIAL = "SRB5030-2608-0063"  # FIX-03, but the note says the board is dead
UNGROUPED_SERIAL = "SRB5030-2608-0052"  # FIX-04, the only VOUT failure on that fixture that day
NO_NOTE_ON_OFFSET_FIXTURE_SERIAL = "SRB5030-2608-0015"  # FIX-03, notes column is empty


def _tracer() -> Tracer:
    return Tracer(example="bench_test_failure_triage", level=LEVEL, model_id="stub-1")


def _cause_model(cause: str, evidence: str = "quoted words") -> StubModel:
    return StubModel([StubResponse(text=json.dumps({"cause": cause, "evidence": evidence}))])


class LoadFailuresTests(unittest.TestCase):
    def test_reads_only_failing_vout_rows(self) -> None:
        failures = load_failures("VOUT")
        self.assertTrue(failures)
        self.assertTrue(all(f.measurement == "VOUT" for f in failures))
        serials = {f.serial for f in failures}
        self.assertIn(DEAD_ON_OFFSET_FIXTURE_SERIAL, serials)

    def test_a_measurement_with_no_failures_returns_an_empty_list(self) -> None:
        # R_OUT (step 1) only fails on the two shorted units, which never reach VOUT; asking for
        # a measurement that never failed at all should not raise.
        failures = load_failures("NOT_A_REAL_MEASUREMENT")
        self.assertEqual(failures, [])


class GroupSignatureTests(unittest.TestCase):
    def test_fix03_is_flagged_a_fixture_signature(self) -> None:
        # docs/THE-BENCH.md Story 2: FIX-03 carries 6 of the month's 8 VOUT failures.
        failures = load_failures("VOUT")
        row = next(f for f in failures if f.serial == FIXTURE_FAULT_SERIAL)
        self.assertEqual(row.fixture, "FIX-03")
        self.assertEqual(_group_signature(failures, row), "fixture")

    def test_a_lone_failure_on_a_fixture_is_not_a_signature(self) -> None:
        failures = load_failures("VOUT")
        row = next(f for f in failures if f.serial == UNGROUPED_SERIAL)
        self.assertEqual(row.fixture, "FIX-04")
        self.assertEqual(_group_signature(failures, row), "none")

    def test_an_empty_failure_list_is_not_a_signature(self) -> None:
        row = FailureRow(
            serial="X", lot="L1", fixture="FIX-01", measurement="VOUT", value="4.90",
            unit="V", lower_limit="4.9500", upper_limit="5.0500", note="",
        )
        self.assertEqual(_group_signature([], row), "none")


class ValidateTests(unittest.TestCase):
    def test_a_named_cause_needs_quoted_evidence(self) -> None:
        problems = _validate({"cause": "dead_board", "evidence": ""})
        self.assertTrue(problems)

    def test_no_information_needs_no_evidence(self) -> None:
        self.assertEqual(_validate({"cause": "no_information", "evidence": ""}), [])

    def test_an_unknown_cause_is_rejected(self) -> None:
        problems = _validate({"cause": "wiring_fault", "evidence": "smells burnt"})
        self.assertTrue(any("cause" in p for p in problems))


class RouteTests(unittest.TestCase):
    def test_dead_board_wins_over_a_fixture_signature(self) -> None:
        self.assertEqual(_route("fixture", "dead_board"), "failure_analysis")

    def test_a_fixture_signature_routes_to_a_fixture_check(self) -> None:
        self.assertEqual(_route("fixture", "board_low_general"), "hold_check_fixture")

    def test_a_lot_signature_routes_to_a_lot_check(self) -> None:
        self.assertEqual(_route("lot", "no_information"), "hold_check_lot")

    def test_board_low_general_with_no_group_signature_goes_to_failure_analysis(self) -> None:
        self.assertEqual(_route("none", "board_low_general"), "failure_analysis")

    def test_an_uncorroborated_fixture_claim_does_not_skip_failure_analysis(self) -> None:
        # The asymmetric-cost line: one note blaming a fixture, with no group pattern behind it,
        # is not enough on its own to route away from the guide's own default.
        self.assertEqual(_route("none", "fixture_signature"), "retest_other_fixture")

    def test_no_information_with_no_group_signature_uses_the_guides_default(self) -> None:
        self.assertEqual(_route("none", "no_information"), "retest_other_fixture")


class RunTests(unittest.TestCase):
    def test_unknown_serial_raises(self) -> None:
        with self.assertRaises(ValueError):
            run("NOT-A-REAL-SERIAL", _cause_model("no_information"), _tracer())

    def test_a_dead_board_on_the_offset_fixture_overrides_the_group_signature(self) -> None:
        model = _cause_model("dead_board", "no vout at all, u1 not switching")
        tracer = _tracer()
        disposition = run(DEAD_ON_OFFSET_FIXTURE_SERIAL, model, tracer)
        self.assertEqual(disposition.group_signature, "fixture")
        self.assertEqual(disposition.cause, "dead_board")
        self.assertEqual(disposition.route, "failure_analysis")

    def test_a_fixture_signature_case_routes_to_the_fixture_check_regardless_of_the_note(self) -> None:
        model = _cause_model("fixture_signature", "fix3")
        tracer = _tracer()
        disposition = run(FIXTURE_FAULT_SERIAL, model, tracer)
        self.assertEqual(disposition.group_signature, "fixture")
        self.assertEqual(disposition.route, "hold_check_fixture")

    def test_an_empty_note_never_calls_the_model(self) -> None:
        model = _cause_model("dead_board")  # would raise IndexError if actually called
        tracer = _tracer()
        disposition = run(NO_NOTE_ON_OFFSET_FIXTURE_SERIAL, model, tracer)
        self.assertEqual(disposition.row.note, "")
        self.assertEqual(disposition.cause, "no_information")
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 0)
        # Still routed on the group signature alone.
        self.assertEqual(disposition.route, "hold_check_fixture")

    def test_the_classify_calls_token_count_on_one_note(self) -> None:
        # The recipe page's cost line quotes this call's tokens; pin it here so the page cannot
        # drift from the code silently. Counted by `count_tokens` over the real system prompt and
        # the note text, the same way every stub-model token count on this site is counted.
        model = _cause_model("dead_board", "no vout at all, u1 not switching")
        tracer = _tracer()
        run(DEAD_ON_OFFSET_FIXTURE_SERIAL, model, tracer)
        classify_steps = [s for s in tracer.steps if s.title == "Classify the note"]
        self.assertEqual(len(classify_steps), 1)
        self.assertEqual(classify_steps[0].tokens_in, 244)
        self.assertEqual(classify_steps[0].tokens_out, 18)

    def test_an_invalid_reply_retries_once_then_succeeds(self) -> None:
        model = StubModel(
            [
                StubResponse(text=json.dumps({"cause": "dead_board", "evidence": ""})),  # missing evidence
                StubResponse(text=json.dumps({"cause": "dead_board", "evidence": "u1 not switching"})),
            ]
        )
        tracer = _tracer()
        disposition = run(DEAD_ON_OFFSET_FIXTURE_SERIAL, model, tracer)
        self.assertEqual(disposition.cause, "dead_board")
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)

    def test_still_invalid_after_the_retry_falls_back_to_no_information(self) -> None:
        model = StubModel([StubResponse(text="not json"), StubResponse(text="still not json")])
        tracer = _tracer()
        disposition = run(FIXTURE_FAULT_SERIAL, model, tracer)
        self.assertEqual(disposition.cause, "no_information")
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)

    def test_every_step_is_decided_by_code(self) -> None:
        model = _cause_model("dead_board", "u1 not switching")
        tracer = _tracer()
        run(DEAD_ON_OFFSET_FIXTURE_SERIAL, model, tracer)
        self.assertTrue(tracer.steps)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps), "level 3 must record no model-decided steps")
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_the_pass_fail_result_is_never_part_of_the_return_value(self) -> None:
        # Disposition carries the measured value and the route; it has no result/verdict field,
        # because the label this recipe produces never changes a pass or fail.
        disposition = run(DEAD_ON_OFFSET_FIXTURE_SERIAL, _cause_model("dead_board", "u1"), _tracer())
        self.assertNotIn("result", disposition.__dataclass_fields__)
        self.assertNotIn("verdict", disposition.__dataclass_fields__)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))


class ConfirmTests(unittest.TestCase):
    def test_an_approved_disposition_returns_its_route(self) -> None:
        tracer = _tracer()
        disposition = run(DEAD_ON_OFFSET_FIXTURE_SERIAL, _cause_model("dead_board", "u1"), tracer)
        self.assertEqual(confirm(disposition, True, tracer), "failure_analysis")

    def test_a_rejected_disposition_is_not_acted_on(self) -> None:
        tracer = _tracer()
        disposition = run(FIXTURE_FAULT_SERIAL, _cause_model("fixture_signature", "fix3"), tracer)
        result = confirm(disposition, False, tracer, note="already reworked, close it out")
        self.assertNotEqual(result, disposition.route)
        self.assertIn("already reworked", result)

    def test_confirmation_is_recorded_on_the_tracer(self) -> None:
        tracer = _tracer()
        disposition = run(FIXTURE_FAULT_SERIAL, _cause_model("fixture_signature", "fix3"), tracer)
        confirm(disposition, True, tracer)
        self.assertTrue(any("confirms" in s.title.lower() for s in tracer.steps))


class BenchFileConsistencyTests(unittest.TestCase):
    """These serials and fixture assignments are load-bearing for the recipe page and the tests
    above; if `evals/bench/make_data.py` ever regenerates the data differently, this is where
    that would show up first."""

    def test_production_csv_exists(self) -> None:
        self.assertTrue(PRODUCTION_CSV.exists())

    def test_the_recorder_sample_is_a_serial_that_really_failed(self) -> None:
        """`scripts/record_trace.py` runs this example with `SAMPLE_INPUT` when it is given no
        `--question`, and `run` refuses a serial that did not fail. So the sample has to be a real
        failing serial in the production log, not a plausible-looking one."""
        self.assertEqual(SAMPLE_INPUT, DEAD_ON_OFFSET_FIXTURE_SERIAL)
        self.assertIn(SAMPLE_INPUT, {f.serial for f in load_failures("VOUT")})
        disposition = run(SAMPLE_INPUT, _cause_model("dead_board", "u1 not switching"), _tracer())
        self.assertEqual(disposition.route, "failure_analysis")

    def test_the_named_serials_still_carry_the_notes_the_tests_assume(self) -> None:
        failures = load_failures("VOUT")
        by_serial = {f.serial: f for f in failures}
        self.assertIn("u1 not switching", by_serial[DEAD_ON_OFFSET_FIXTURE_SERIAL].note)
        self.assertEqual(by_serial[NO_NOTE_ON_OFFSET_FIXTURE_SERIAL].note, "")
        self.assertEqual(by_serial[FIXTURE_FAULT_SERIAL].fixture, "FIX-03")
        self.assertEqual(by_serial[UNGROUPED_SERIAL].fixture, "FIX-04")


if __name__ == "__main__":
    unittest.main()
