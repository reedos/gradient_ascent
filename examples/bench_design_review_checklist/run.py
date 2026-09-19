"""Level 3: check a bill of materials and a netlist summary against DR-0100, Orbeck's design
review rules, rule by rule.

DR-0100 (`evals/bench/corpus/design-review-rules.md`) has seven numbered rules. Four of them --
DR-10 (inductor saturation margin), DR-12 (semiconductor voltage derating), DR-14 (ceramic
capacitor voltage derating) and DR-16 (resistor and capacitor power derating) -- plus DR-20's
placement thresholds are a number compared with a number: a voltage rating divided by a factor,
a distance in millimeters, a ratio against a saturation current. Code computes every one of
those directly from the bill of materials and the netlist summary, with no model in the loop, the
same way `limits-without-a-model` does for a production limit check.

Two rules are not arithmetic. DR-24 (thermal) and DR-30 (test access and markings) ask whether
the *evidence* submitted for the review actually supports what it claims, which needs reading,
not a comparison. Those two go through two model passes: one drafts a finding from the rule text
and the evidence, a second checks that drafted finding against the rule's own full text before it
is allowed to reach a person. See `_merge_judgment_findings`: a finding the second pass rejects is
not corrected and reshipped, it is recorded as not met, per DR-0100 rule 1, and a person redoes
it.

Every step here is `decided_by: "code"`: the two model calls always happen, in this order, and
code always merges their output the same way regardless of what came back. Nothing about which
finding survives is the model's call; the checker's own verdict is data the code reads, not a
decision the code hands control to.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from evals.bench import load_bench_sections
from examples.common.bench import Dut, IOUT_MAX_A, VIN_MAX_DATASHEET_V, VIN_MAX_ECN_V
from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 3

Status = Literal["met", "not met", "not applicable"]

#: The rules this example checks by reading rather than by arithmetic: DR-24's own text
#: explicitly disclaims one common wrong reason to call it met, and DR-30 needs the evidence read
#: against several named clauses at once. Every other rule below is computed.
JUDGMENT_RULES = ["DR-24", "DR-30"]

#: C1, C2: OPS-3105, 10 uF, 50 V, X7R, input rail (srb5030-bom.md section 1).
C1C2_RATING_V = 50.0
#: L1: OPS-2210, 4.5 A saturation (srb5030-bom.md section 1; docs/THE-BENCH.md shows the ripple
#: arithmetic this reuses `Dut` for, so it cannot drift from the datasheet).
INDUCTOR_SAT_A = 4.5
DERATE_FACTOR = 1.5  # DR-12 and DR-14 both use this factor
DR10_MARGIN_MIN = 1.3

#: A netlist summary's placement data: ref, what it decouples, distance to the pin (mm), via to
#: plane (mm). Invented for this example -- no such file exists in evals/bench/corpus/ yet; see
#: .local/page-requests/w7-design-review-checklist.md.
DECOUPLING = [
    ("C5", "100 nF bootstrap cap, U1 BOOT pin", 2.1, 0.7),
    ("C6", "100 nF decoupling, U1 VCC pin", 2.6, 0.9),
    ("C7", "100 nF decoupling, U1 VIN pin", 2.4, 0.6),
]
BULK_CAPS = [("C1, C2", "input bulk, VIN pin", 6.0), ("C3, C4", "output bulk, VOUT pin", 5.0)]
DR20_MAX_PIN_MM = 3.0
DR20_MAX_VIA_MM = 1.0
DR20_MAX_BULK_MM = 10.0
LOOP_AREA_NOTE = "closed on layer 2, return plane beneath, 145 mm^2, recorded in the review packet"

#: What a reviewer submitted for the two rules that need reading. DR24_EVIDENCE deliberately
#: reasons the way an engineer glancing at "thermal shutdown, 145 degC" sometimes does: it leads
#: with the protection, which DR-24's own text says is not a reason the rule is met.
DR24_EVIDENCE = (
    "Board dissipates 1.21 W at 24.0 V in, 3.0 A out, from the datasheet's own efficiency table "
    "(Pin - Pout). About 0.96 W of that is in the controller and its FETs; the rest is the "
    "inductor's own DCR loss on a separate thermal path. Rth junction to ambient is 42 degC/W. "
    "At the 70 degC maximum rated ambient: Tj = 70 + 42 * 0.96 = 110.3 degC. Thermal shutdown "
    "engages at 145 degC, well above, so the part is protected even if this calculation is "
    "optimistic."
)
DR30_EVIDENCE = (
    "TP1 (VIN), TP2 (VOUT) and TP3 (RTN) are loop test points sized for a fixture probe. TP4 is "
    "the switch node; the datasheet marks it for scope use only and it is not populated as a "
    "fixture contact. The silkscreen carries a revision character next to J1, and the assembly "
    "number OPS-9001-B ends in that same character, B."
)

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"},
                    "status": {"type": "string", "enum": ["met", "not met", "not applicable"]},
                    "evidence": {"type": "string"},
                },
                "required": ["rule", "status", "evidence"],
            },
        },
    },
    "required": ["findings"],
}
CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["confirm", "reject"]},
                    "reason": {"type": "string"},
                },
                "required": ["rule", "verdict", "reason"],
            },
        },
    },
    "required": ["verdicts"],
}
DRAFT_SYSTEM = (
    "Draft one design review finding per rule below: 'met', 'not met' or 'not applicable', and "
    "the evidence for it, from the rule text and the submitted evidence only. Reply as JSON "
    "matching the schema and nothing else."
)
CHECK_SYSTEM = (
    "Check one drafted finding at a time against the FULL text of the rule it names. Reject a "
    "finding whose stated reasoning is not actually what that rule says, even when you agree "
    "with its status; confirm a finding the rule text actually supports. Reply as JSON matching "
    "the schema and nothing else."
)

_DR_ID_RE = re.compile(r"\bDR-\d+\b")


@dataclass(frozen=True)
class Finding:
    rule: str
    status: Status
    evidence: str
    checked_by: Literal["code", "model"]


@dataclass(frozen=True)
class ReviewReport:
    board: str
    findings: tuple[Finding, ...]

    @property
    def text(self) -> str:
        return "\n".join(f"{f.rule}: {f.status} ({f.checked_by}) - {f.evidence}" for f in self.findings)

    @property
    def citations(self) -> list[str]:
        return [f.rule for f in self.findings]


def _rule_sections() -> dict[str, str]:
    """DR-0100's rules, keyed by their DR-id ("DR-14") rather than by section number, so the rest
    of this module never has to know which numbered section a rule happens to be today."""
    out: dict[str, str] = {}
    for cite, section in load_bench_sections().items():
        if not cite.startswith("design-review-rules#"):
            continue
        match = _DR_ID_RE.search(section.title)
        if match:
            out[match.group(0)] = f"{section.title}\n\n{section.text}"
    return out


# ---------------------------------------------------------------------------
# The numeric rules: code computes these, no model reads them.
# ---------------------------------------------------------------------------


def _check_capacitor_derating(rating_v: float, max_rail_v: float, *, ref: str) -> Finding:
    """DR-14: a ceramic on a DC rail must be rated at least 1.5 times the maximum steady-state
    rail voltage. This is the same arithmetic ECN-2608-04 uses to justify lowering the SRB-5030's
    input ceiling: a 50 V part supports 50 / 1.5 = 33.3 V, not the datasheet's superseded 36.0 V.
    """
    supported_v = rating_v / DERATE_FACTOR
    met = supported_v >= max_rail_v
    evidence = (
        f"{ref} is rated {rating_v:.1f} V; at the {DERATE_FACTOR}x factor DR-14 requires that "
        f"supports up to {supported_v:.1f} V, against a {max_rail_v:.1f} V maximum rail."
    )
    return Finding(rule="DR-14", status="met" if met else "not met", evidence=evidence, checked_by="code")


def _check_inductor_margin(dut: Dut, *, vin_v: float, iout_a: float) -> Finding:
    """DR-10: saturation current at least 1.3 times the peak inductor current at maximum rated
    load, where peak current is the DC output current plus half the peak-to-peak ripple current.
    `Dut.inductor_ripple_a` is the bench's own model, already checked against the datasheet in
    `tests/test_bench.py`, reused here rather than recomputed."""
    ripple_a = dut.inductor_ripple_a(vin_v, iout_a)
    peak_a = iout_a + ripple_a / 2.0
    margin = INDUCTOR_SAT_A / peak_a
    met = margin >= DR10_MARGIN_MIN
    evidence = (
        f"L1 ripple current is {ripple_a:.2f} A at {vin_v:.1f} V in, {iout_a:.1f} A out; peak "
        f"inductor current is {peak_a:.2f} A. Against the {INDUCTOR_SAT_A:.1f} A saturation "
        f"rating that is a margin of {margin:.2f}, against the {DR10_MARGIN_MIN}x DR-10 requires."
    )
    return Finding(rule="DR-10", status="met" if met else "not met", evidence=evidence, checked_by="code")


def _check_decoupling(entries, bulk) -> Finding:
    """DR-20: every decoupling pin within 3 mm with a via to plane within 1 mm, bulk capacitance
    within 10 mm. Three numeric thresholds against a netlist summary's own measurements."""
    problems = []
    for ref, _desc, pin_mm, via_mm in entries:
        if pin_mm > DR20_MAX_PIN_MM:
            problems.append(f"{ref} is {pin_mm:.1f} mm from its pin, over {DR20_MAX_PIN_MM:.0f} mm")
        if via_mm > DR20_MAX_VIA_MM:
            problems.append(f"{ref}'s via is {via_mm:.1f} mm from the plane, over {DR20_MAX_VIA_MM:.0f} mm")
    for ref, _desc, dist_mm in bulk:
        if dist_mm > DR20_MAX_BULK_MM:
            problems.append(f"{ref} bulk capacitance is {dist_mm:.1f} mm away, over {DR20_MAX_BULK_MM:.0f} mm")
    if problems:
        return Finding(rule="DR-20", status="not met", evidence="; ".join(problems), checked_by="code")
    evidence = (
        f"Every decoupling cap is within {DR20_MAX_PIN_MM:.0f} mm of its pin with a via within "
        f"{DR20_MAX_VIA_MM:.0f} mm of the plane; bulk capacitance is within {DR20_MAX_BULK_MM:.0f} mm. "
        f"Switching loop: {LOOP_AREA_NOTE}."
    )
    return Finding(rule="DR-20", status="met", evidence=evidence, checked_by="code")


def _numeric_findings(revision: str) -> list[Finding]:
    max_rail_v = VIN_MAX_ECN_V if revision in ("A", "B") else VIN_MAX_DATASHEET_V
    return [
        _check_capacitor_derating(C1C2_RATING_V, max_rail_v, ref="C1, C2 (OPS-3105, 50 V X7R)"),
        _check_inductor_margin(Dut(), vin_v=24.0, iout_a=IOUT_MAX_A),
        _check_decoupling(DECOUPLING, BULK_CAPS),
        Finding(
            rule="DR-12",
            status="not applicable",
            evidence=(
                "The bill of materials lists no discrete MOSFET or diode on a DC rail; U1's "
                "FETs are integrated into the controller and carry no separate rail rating here."
            ),
            checked_by="code",
        ),
        Finding(
            rule="DR-16",
            status="not met",
            evidence=(
                "The bill of materials gives values, tolerances and voltage or package ratings, "
                "but no power rating for R1-R3 or ripple-current rating for C1-C8; rule 1 "
                "records that as not met until the documents say otherwise."
            ),
            checked_by="code",
        ),
    ]


# ---------------------------------------------------------------------------
# The rules that need reading: two model passes, draft then check.
# ---------------------------------------------------------------------------


def _draft_findings(rule_texts: dict[str, str], evidence: dict[str, str], model: Model, tracer: Tracer) -> list[dict]:
    prompt = "\n\n".join(
        f"{rule_id}\n{text}\n\nEvidence submitted for {rule_id}:\n{evidence[rule_id]}"
        for rule_id, text in rule_texts.items()
    )
    completion = model.complete(
        [Message(role="system", content=DRAFT_SYSTEM), Message(role="user", content=prompt)],
        schema=DRAFT_SCHEMA,
        max_tokens=600,
    )
    tracer.record(
        kind="model",
        decided_by="code",
        title="Draft findings for the rules that need reading",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    try:
        return json.loads(completion.text)["findings"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _check_findings(drafts: list[dict], rule_texts: dict[str, str], model: Model, tracer: Tracer) -> dict[str, dict]:
    prompt = "\n\n".join(
        f"Drafted finding for {d['rule']}: {d['status']} - {d['evidence']}\n\n"
        f"Full text of {d['rule']}:\n{rule_texts.get(d['rule'], '(rule not found)')}"
        for d in drafts
    )
    completion = model.complete(
        [Message(role="system", content=CHECK_SYSTEM), Message(role="user", content=prompt)],
        schema=CHECK_SCHEMA,
        max_tokens=600,
    )
    tracer.record(
        kind="model",
        decided_by="code",
        title="Check each finding against the rule text it cites",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    try:
        verdicts = json.loads(completion.text)["verdicts"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}
    return {v["rule"]: v for v in verdicts if "rule" in v}


def _merge_judgment_findings(drafts: list[dict], verdicts: dict[str, dict]) -> list[Finding]:
    """A confirmed finding ships as drafted. A rejected or unverified one does not ship as a
    finding at all: it is recorded as not met, per DR-0100 rule 1 (unclear counts as not met
    until the documents say otherwise), with the checker's own reason attached, so a person
    redoes it instead of a wrong 'met' quietly reaching the review record."""
    findings = []
    for d in drafts:
        verdict = verdicts.get(d.get("rule", ""))
        if verdict is not None and verdict.get("verdict") == "confirm":
            findings.append(Finding(rule=d["rule"], status=d["status"], evidence=d["evidence"], checked_by="model"))
            continue
        reason = verdict["reason"] if verdict is not None else "the second pass returned no verdict for this rule"
        findings.append(
            Finding(
                rule=d.get("rule", "?"),
                status="not met",
                evidence=f"Pass 2 rejected the drafted citation: {reason}",
                checked_by="model",
            )
        )
    return findings


def run(board_revision: str, model: Model, tracer: Tracer) -> ReviewReport:
    revision = (board_revision or "B").strip().upper() or "B"
    rules = _rule_sections()
    tracer.record(kind="code", decided_by="code", title="Load DR-0100", detail=f"{len(rules)} numbered rules")

    numeric = _numeric_findings(revision)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Compute the numeric rules",
        detail=", ".join(f"{f.rule}: {f.status}" for f in numeric),
    )

    rule_texts = {rid: rules[rid] for rid in JUDGMENT_RULES if rid in rules}
    evidence = {"DR-24": DR24_EVIDENCE, "DR-30": DR30_EVIDENCE}
    drafts = _draft_findings(rule_texts, evidence, model, tracer)
    verdicts = _check_findings(drafts, rule_texts, model, tracer)
    judged = _merge_judgment_findings(drafts, verdicts)

    findings = tuple(numeric + judged)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Assemble the review record",
        detail=f"{len(findings)} findings for SRB-5030 revision {revision}",
    )
    return ReviewReport(board=f"SRB-5030 revision {revision}", findings=findings)
