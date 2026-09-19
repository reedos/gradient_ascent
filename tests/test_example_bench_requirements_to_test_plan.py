"""Tests for examples/bench_requirements_to_test_plan: read the SRB-5030's datasheet
requirements, ask the model for one test per requirement, build the traceability table, and let
code -- never a model -- decide whether the table covers every requirement. Mirrors the shape of
tests/test_example_human_in_the_loop.py: `run` on a scripted StubModel, then a scripted reviewer
decision fed into `resume`.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.bench_requirements_to_test_plan.run import (  # noqa: E402
    BENCH_INSTRUMENTS,
    Blocked,
    PendingApproval,
    REQUIREMENTS,
    _requirements_for_revision,
    _stale_limit,
    check_coverage,
    resume,
    run,
    TestProposal,
    TraceRow,
)

#: A correct instrument for each requirement, chosen the way `docs/THE-BENCH.md` says to: the
#: ripple and switching-frequency requirements go to the scope, not the meter, since the meter's
#: AC volts function stops at 300 kHz.
_CORRECT_INSTRUMENT = {
    "REQ-VIN": "MDN-4010",
    "REQ-VOUT": "MDN-6100",
    "REQ-LINEREG": "MDN-6100",
    "REQ-LOADREG": "MDN-6100",
    "REQ-RIPPLE": "TRN-1102",
    "REQ-IQNL": "MDN-4010",
    "REQ-FSW": "TRN-1102",
    "REQ-ILIM": "TRN-2400",
}


def _correct_response(requirement) -> StubResponse:
    payload = {
        "requirement": requirement.id,
        "instrument": _CORRECT_INSTRUMENT[requirement.id],
        "measurement": f"read {requirement.parameter.lower()}",
        "lower": requirement.lower,
        "upper": requirement.effective_upper(),
        "unit": requirement.unit,
    }
    return StubResponse(text=json.dumps(payload))


def _responses(revision: str, overrides: dict[str, StubResponse] | None = None) -> list[StubResponse]:
    """One correct response per requirement, in the fixed call order, with any override swapped
    in by requirement id. `overrides` lets a test corrupt exactly one requirement's proposal."""
    overrides = overrides or {}
    out = []
    for requirement in _requirements_for_revision(revision):
        out.append(overrides.get(requirement.id, _correct_response(requirement)))
    return out


class RequirementsToTestPlanTests(unittest.TestCase):
    # -- the happy path --------------------------------------------------

    def test_a_fully_covered_plan_clears_coverage_and_pends_approval(self) -> None:
        model = StubModel(_responses("B"))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        result = run("B", model, tracer)
        self.assertIsInstance(result, PendingApproval)
        self.assertTrue(result.coverage.ok)
        self.assertEqual(result.coverage.problems, [])
        self.assertEqual(len(result.rows), len(REQUIREMENTS))
        self.assertTrue(all(row.proposal is not None for row in result.rows))

    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel(_responses("B"))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        run("B", model, tracer)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        # one model-kind step per requirement, plus the fixed code steps
        model_steps = [s for s in tracer.steps if s.kind == "model"]
        self.assertEqual(len(model_steps), len(REQUIREMENTS))

    def test_resume_approve_adopts_the_plan_with_every_source_cited(self) -> None:
        model = StubModel(_responses("B"))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        pending = run("B", model, tracer)
        answer = resume(pending, "approve", tracer)
        self.assertIn("REQ-VIN", answer.text)
        self.assertIn("REQ-ILIM", answer.text)
        self.assertIn("srb5030-datasheet#3", answer.citations)
        self.assertIn("srb5030-datasheet#4", answer.citations)
        self.assertIn("ecn-2608-04#1", answer.citations)

    def test_resume_reject_adopts_nothing(self) -> None:
        model = StubModel(_responses("B"))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        pending = run("B", model, tracer)
        answer = resume(pending, "reject", tracer)
        self.assertEqual(answer.citations, [])
        self.assertIn("not adopted", answer.text)

    # -- the three failure modes this recipe exists to catch -------------

    def test_coverage_catches_a_requirement_silently_dropped(self) -> None:
        """The model is asked about REQ-FSW -- switching frequency, which the eight-step test
        spec never tests at all -- and declines. Nothing else stops the run; only the coverage
        check catches the gap."""
        model = StubModel(_responses("B", {"REQ-FSW": StubResponse(text="SKIP")}))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        result = run("B", model, tracer)
        self.assertIsInstance(result, Blocked)
        self.assertFalse(result.coverage.ok)
        reasons = {p.requirement_id: p.reason for p in result.coverage.problems}
        self.assertIn("REQ-FSW", reasons)
        self.assertIn("no test was proposed", reasons["REQ-FSW"])
        # every other requirement is still fine
        other_ids = {p.requirement_id for p in result.coverage.problems}
        self.assertEqual(other_ids, {"REQ-FSW"})

    def test_coverage_catches_an_instrument_not_on_this_bench(self) -> None:
        """TRN-2500 does not exist; the load on this bench is the TRN-2400."""
        bad = json.dumps({
            "requirement": "REQ-ILIM", "instrument": "TRN-2500",
            "measurement": "ramp load current until VOUT falls below 4.900 V",
            "lower": 3.70, "upper": 5.00, "unit": "A",
        })
        model = StubModel(_responses("B", {"REQ-ILIM": StubResponse(text=bad)}))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        result = run("B", model, tracer)
        self.assertIsInstance(result, Blocked)
        reasons = {p.requirement_id: p.reason for p in result.coverage.problems}
        self.assertIn("REQ-ILIM", reasons)
        self.assertIn("TRN-2500", reasons["REQ-ILIM"])
        self.assertIn("not one of the four instruments", reasons["REQ-ILIM"])
        self.assertNotIn("TRN-2500", BENCH_INSTRUMENTS)

    def test_coverage_catches_a_limit_the_ecn_superseded(self) -> None:
        """REQ-VIN's proposal copies the datasheet's own 36.0 V instead of the ECN's 32.0 V, for
        a revision B board -- the exact trap ecn-2608-04.md exists to teach."""
        stale = json.dumps({
            "requirement": "REQ-VIN", "instrument": "MDN-4010",
            "measurement": "verify regulation holds up to the input ceiling",
            "lower": 9.0, "upper": 36.0, "unit": "V",
        })
        model = StubModel(_responses("B", {"REQ-VIN": StubResponse(text=stale)}))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        result = run("B", model, tracer)
        self.assertIsInstance(result, Blocked)
        reasons = {p.requirement_id: p.reason for p in result.coverage.problems}
        self.assertIn("REQ-VIN", reasons)
        self.assertIn("ecn-2608-04#1", reasons["REQ-VIN"])
        self.assertIn("32", reasons["REQ-VIN"])

    def test_the_same_stale_datasheet_figure_is_correct_for_revision_c(self) -> None:
        """Revision C is not covered by the ECN: 36.0 V is its real ceiling, so the same number
        that is stale for revision B must not be flagged here."""
        correct_for_c = json.dumps({
            "requirement": "REQ-VIN", "instrument": "MDN-4010",
            "measurement": "verify regulation holds up to the input ceiling",
            "lower": 9.0, "upper": 36.0, "unit": "V",
        })
        model = StubModel(_responses("C", {"REQ-VIN": StubResponse(text=correct_for_c)}))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        result = run("C", model, tracer)
        self.assertIsInstance(result, PendingApproval)
        self.assertTrue(result.coverage.ok)

    def test_all_three_failure_modes_together_are_all_reported_at_once(self) -> None:
        bad_instrument = json.dumps({
            "requirement": "REQ-ILIM", "instrument": "TRN-2500",
            "measurement": "ramp load current", "lower": 3.70, "upper": 5.00, "unit": "A",
        })
        stale_limit = json.dumps({
            "requirement": "REQ-VIN", "instrument": "MDN-4010",
            "measurement": "verify regulation at the ceiling", "lower": 9.0, "upper": 36.0, "unit": "V",
        })
        overrides = {
            "REQ-FSW": StubResponse(text="SKIP"),
            "REQ-ILIM": StubResponse(text=bad_instrument),
            "REQ-VIN": StubResponse(text=stale_limit),
        }
        model = StubModel(_responses("B", overrides))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        result = run("B", model, tracer)
        self.assertIsInstance(result, Blocked)
        flagged = {p.requirement_id for p in result.coverage.problems}
        self.assertEqual(flagged, {"REQ-FSW", "REQ-ILIM", "REQ-VIN"})

    # -- the other two parts of "every test names a requirement, an instrument, a limit, a unit" --

    def test_coverage_catches_a_test_that_names_the_wrong_requirement(self) -> None:
        row = TraceRow(
            requirement=REQUIREMENTS[1],  # REQ-VOUT
            proposal=TestProposal(
                requirement_id="REQ-ILIM", instrument="MDN-6100", measurement="read VOUT",
                lower=4.900, upper=5.100, unit="V",
            ),
        )
        result = check_coverage([row])
        self.assertFalse(result.ok)
        self.assertTrue(any("not this requirement" in p.reason for p in result.problems))

    def test_coverage_catches_a_test_with_no_limit_or_no_unit(self) -> None:
        requirement = REQUIREMENTS[1]  # REQ-VOUT
        no_limit = TraceRow(
            requirement=requirement,
            proposal=TestProposal(
                requirement_id=requirement.id, instrument="MDN-6100", measurement="read VOUT",
                lower=None, upper=None, unit="V",
            ),
        )
        no_unit = TraceRow(
            requirement=requirement,
            proposal=TestProposal(
                requirement_id=requirement.id, instrument="MDN-6100", measurement="read VOUT",
                lower=4.900, upper=5.100, unit="",
            ),
        )
        self.assertFalse(check_coverage([no_limit]).ok)
        self.assertFalse(check_coverage([no_unit]).ok)

    # -- revision handling -------------------------------------------------

    def test_an_unknown_revision_is_refused(self) -> None:
        model = StubModel([])
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        with self.assertRaises(ValueError):
            run("D", model, tracer)
        with self.assertRaises(ValueError):
            run("a test plan for revision D boards", model, tracer)

    def test_the_revision_is_read_out_of_a_sentence_and_defaults_to_the_stricter_limit(self) -> None:
        from examples.bench_requirements_to_test_plan.run import _revision_from

        self.assertEqual(_revision_from("C"), "C")
        self.assertEqual(_revision_from("rev b"), "b")
        self.assertEqual(_revision_from("Write the test plan for Revision C boards"), "C")
        # names no revision: revision A, whose 32.0 V ceiling is the stricter of the two
        self.assertEqual(_revision_from("What is the maximum vent run for a DR-520?"), "A")
        self.assertEqual(_revision_from("   "), "A", "an empty request names no revision either")

    def test_the_line_regulation_sweep_stops_at_the_ceiling_in_force(self) -> None:
        """ECN-2608-04 section 4: production may not apply 36.0 V to a revision A or B board,
        including during test, and `srb5030-test-spec.md` step 4 already sweeps to 32.0 V. A plan
        drafted for those revisions must not hand the model the datasheet's 36.0 V sweep."""
        by_id = {r.id: r for r in _requirements_for_revision("B")}
        self.assertEqual(by_id["REQ-LINEREG"].effective_condition(), "9.0 V to 32.0 V in, 1.0 A out")
        self.assertEqual(by_id["REQ-LINEREG"].superseded_by, "ecn-2608-04#4")
        # the limit itself is untouched: only the conditions moved
        self.assertEqual(by_id["REQ-LINEREG"].upper, 0.30)
        self.assertEqual(by_id["REQ-LINEREG"].effective_upper(), 0.30)
        for_c = {r.id: r for r in _requirements_for_revision("C")}
        self.assertEqual(for_c["REQ-LINEREG"].effective_condition(), "9.0 V to 36.0 V in, 1.0 A out")
        self.assertEqual(for_c["REQ-VIN"].effective_upper(), 36.0)

    def test_the_prompt_carries_the_superseded_condition_not_the_datasheets(self) -> None:
        scripted = _responses("B")
        seen: list[str] = []

        def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
            del tools
            seen.append(messages[-1].content)
            return scripted[len(seen) - 1]

        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        run("B", StubModel(responder), tracer)
        prompts = [p for p in seen if "REQ-LINEREG" in p]
        self.assertEqual(len(prompts), 1)
        self.assertIn("9.0 V to 32.0 V in", prompts[0])
        self.assertNotIn("36.0 V", prompts[0])
        self.assertIn("ecn-2608-04#4", prompts[0])

    def test_stale_limit_helper_is_none_when_the_proposal_already_uses_the_current_limit(self) -> None:
        requirement = REQUIREMENTS[0]  # REQ-VIN
        proposal = TestProposal(
            requirement_id="REQ-VIN", instrument="MDN-4010", measurement="x",
            lower=9.0, upper=32.0, unit="V",
        )
        self.assertIsNone(_stale_limit(requirement, proposal))

    def test_the_token_counts_the_page_quotes(self) -> None:
        """The recipe page's cost strip quotes these totals; pin them so the page cannot drift
        from the code. Counted by `count_tokens` over the eight prompts the example builds and the
        eight scripted replies, the same way every stub-model token count on this site is."""
        model = StubModel(_responses("B"))
        tracer = Tracer(example="bench_requirements_to_test_plan", level=3, model_id="stub-1")
        run("B", model, tracer)
        self.assertEqual(tracer.tokens_in_total(), 1608)
        self.assertEqual(tracer.tokens_out_total(), 283)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.bench_requirements_to_test_plan.run as module

        self.assertTrue(callable(module.run))
        self.assertTrue(callable(module.resume))
        self.assertTrue(callable(module.check_coverage))
        self.assertEqual(module.LEVEL, 3)


if __name__ == "__main__":
    unittest.main()
