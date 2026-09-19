"""End-to-end tests for the design review checklist example.

Three things are being pinned here, matching the recipe's own claim.

- **The numeric rules are arithmetic a test can recompute independently.** DR-14's derating
  figure (a capacitor's rating divided by 1.5) and DR-10's saturation margin are checked against
  numbers computed here directly, not against whatever `run.py` happens to print, so the two
  cannot drift together.
- **DR-14 flips with the ceiling it is checked against.** The same 50 V rating supports 32.0 V
  (the ECN's ceiling for revisions A and B) but not 36.0 V (the datasheet's superseded figure),
  which is the whole reason ECN-2608-04 exists.
- **The second pass catches a finding whose citation does not say what it claims**, and the
  rejected finding is recorded as not met rather than reshipped with the wrong reasoning intact.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.bench_design_review_checklist.run import (  # noqa: E402
    C1C2_RATING_V,
    DERATE_FACTOR,
    INDUCTOR_SAT_A,
    LEVEL,
    _check_capacitor_derating,
    _check_inductor_margin,
    run,
)
from examples.common.bench import Dut, VIN_MAX_DATASHEET_V, VIN_MAX_ECN_V  # noqa: E402
from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

# A drafted finding for DR-24 that reasons the way DR-24's own text explicitly disclaims: it
# calls the board compliant because thermal shutdown protects it, not because the computed
# junction temperature is under the limit.
DRAFT_RESPONSE = json.dumps(
    {
        "findings": [
            {
                "rule": "DR-24",
                "status": "met",
                "evidence": (
                    "Thermal shutdown at 145 degC protects the design, so the junction "
                    "temperature requirement is satisfied."
                ),
            },
            {
                "rule": "DR-30",
                "status": "met",
                "evidence": (
                    "TP1, TP2 and TP3 are sized for a fixture probe; TP4 is marked for scope "
                    "use only and is not a fixture contact; the silkscreen revision character "
                    "matches the last character of the assembly number."
                ),
            },
        ]
    }
)
CHECK_RESPONSE = json.dumps(
    {
        "verdicts": [
            {
                "rule": "DR-24",
                "verdict": "reject",
                "reason": (
                    "DR-24 says a design whose junction temperature reaches the shutdown "
                    "threshold in any rated operating condition does not meet this rule, "
                    "whatever the protection does; citing the shutdown as the reason it is met "
                    "is the opposite of what the rule says."
                ),
            },
            {
                "rule": "DR-30",
                "verdict": "confirm",
                "reason": "Every clause DR-30 lists is addressed by name in the evidence.",
            },
        ]
    }
)


def _scripted_model() -> StubModel:
    return StubModel([StubResponse(text=DRAFT_RESPONSE), StubResponse(text=CHECK_RESPONSE)])


class DesignReviewChecklistExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))

    def test_dr14_derating_figure_is_the_rule_arithmetic(self) -> None:
        """50 V / 1.5 = 33.3 V: the same number ECN-2608-04 uses to justify a 32.0 V ceiling."""
        supported_v = C1C2_RATING_V / DERATE_FACTOR
        self.assertAlmostEqual(supported_v, 33.333333, places=5)
        self.assertEqual(round(supported_v, 1), 33.3)

    def test_dr14_is_met_under_the_ecn_ceiling_and_not_met_under_the_superseded_one(self) -> None:
        under_ecn = _check_capacitor_derating(C1C2_RATING_V, VIN_MAX_ECN_V, ref="C1, C2")
        under_datasheet = _check_capacitor_derating(C1C2_RATING_V, VIN_MAX_DATASHEET_V, ref="C1, C2")
        self.assertEqual(under_ecn.status, "met")
        self.assertEqual(under_datasheet.status, "not met")
        self.assertEqual(under_ecn.checked_by, "code")

    def test_dr10_margin_matches_the_bench_model(self) -> None:
        dut = Dut()
        ripple_a = dut.inductor_ripple_a(24.0, 3.0)
        peak_a = 3.0 + ripple_a / 2.0
        expected_margin = INDUCTOR_SAT_A / peak_a
        finding = _check_inductor_margin(dut, vin_v=24.0, iout_a=3.0)
        self.assertIn(f"{expected_margin:.2f}", finding.evidence)
        self.assertGreaterEqual(expected_margin, 1.3, "the board should clear DR-10, narrowly")
        self.assertEqual(finding.status, "met")

    def test_full_run_covers_all_seven_rules_with_the_right_split(self) -> None:
        model = _scripted_model()
        tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        report = run("B", model, tracer)
        by_rule = {f.rule: f for f in report.findings}
        self.assertEqual(set(by_rule), {"DR-10", "DR-12", "DR-14", "DR-16", "DR-20", "DR-24", "DR-30"})
        code_checked = {"DR-10", "DR-12", "DR-14", "DR-16", "DR-20"}
        model_checked = {"DR-24", "DR-30"}
        for rule in code_checked:
            self.assertEqual(by_rule[rule].checked_by, "code", rule)
        for rule in model_checked:
            self.assertEqual(by_rule[rule].checked_by, "model", rule)

    def test_second_pass_drops_a_finding_that_cites_a_rule_it_does_not_say(self) -> None:
        model = _scripted_model()
        tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        report = run("B", model, tracer)
        by_rule = {f.rule: f for f in report.findings}
        # Pass 1 drafted "met"; pass 2 must have overridden it, not passed it through.
        self.assertEqual(by_rule["DR-24"].status, "not met")
        self.assertIn("Pass 2 rejected", by_rule["DR-24"].evidence)
        self.assertIn("whatever the protection does", by_rule["DR-24"].evidence)

    def test_second_pass_confirms_a_finding_the_rule_text_actually_supports(self) -> None:
        model = _scripted_model()
        tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        report = run("B", model, tracer)
        by_rule = {f.rule: f for f in report.findings}
        self.assertEqual(by_rule["DR-30"].status, "met")
        self.assertNotIn("Pass 2 rejected", by_rule["DR-30"].evidence)

    def test_every_step_is_decided_by_code(self) -> None:
        model = _scripted_model()
        tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        run("B", model, tracer)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "draft, then check")

    def test_revision_a_and_b_use_the_ecn_ceiling_revision_c_uses_the_datasheet(self) -> None:
        model_b = _scripted_model()
        tracer_b = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        report_b = run("B", model_b, tracer_b)
        model_c = _scripted_model()
        tracer_c = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        report_c = run("C", model_c, tracer_c)
        dr14_b = next(f for f in report_b.findings if f.rule == "DR-14")
        dr14_c = next(f for f in report_c.findings if f.rule == "DR-14")
        self.assertEqual(dr14_b.status, "met", "50 V caps clear the 32.0 V ECN ceiling")
        self.assertEqual(dr14_c.status, "not met", "the same 50 V rating does not clear 36.0 V")

    def test_malformed_model_output_does_not_crash_and_drops_no_numeric_finding(self) -> None:
        model = StubModel([StubResponse(text="not json"), StubResponse(text="also not json")])
        tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        report = run("B", model, tracer)
        rules = {f.rule for f in report.findings}
        self.assertEqual(rules, {"DR-10", "DR-12", "DR-14", "DR-16", "DR-20"})

    def test_report_text_and_citations_are_readable(self) -> None:
        model = _scripted_model()
        tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id="stub-1")
        report = run("B", model, tracer)
        self.assertIn("SRB-5030 revision B", report.board)
        self.assertIn("DR-14", report.text)
        self.assertEqual(len(report.citations), 7)


if __name__ == "__main__":
    unittest.main()
