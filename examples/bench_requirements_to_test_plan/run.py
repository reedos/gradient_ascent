"""Level 3: prompt chaining. Turn the SRB-5030's datasheet requirements into a production test
plan, four fixed steps, every run, in this order:

1. Read the requirements. They are already pulled from the datasheet below, each with the
   section it came from; one of them also carries the notice that supersedes it.
2. Ask the model to propose one test for each requirement, one call per requirement, in the same
   order every time. Each reply has to name the requirement it answers, an instrument, a
   measurement, a limit and a unit.
3. Build the traceability table from what came back, requirement by requirement.
4. Check the table in code: every requirement covered, every test naming a requirement, an
   instrument this bench actually has, a limit and a unit, and no limit copied from a source a
   later notice has superseded.

Code decides all four steps and their order never changes; the model only fills in step two, and
never twice the same way if the same requirement is asked again. `check_coverage` is a pass or
fail with no model in it: a bad or missing test fails the check, full stop. Nothing in this plan
is adopted before a person approves the traceability table -- `resume`, below, is that checkpoint,
built the same way `examples/human_in_the_loop/run.py` builds its own.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Literal

from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 3

# ---------------------------------------------------------------------------
# Requirements, read from the datasheet -- and, for one of them, the ECN that supersedes it
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    """One line of the datasheet's Recommended Operating Conditions or Electrical
    Characteristics table. `source` is the citation for the number as printed. `superseded_upper`
    and `superseded_by` are set only for the one requirement a later engineering change notice
    overrides; every other requirement's datasheet number is still the number in force."""

    id: str
    parameter: str
    condition: str
    lower: float | None
    upper: float | None
    unit: str
    source: str
    superseded_upper: float | None = None
    superseded_by: str | None = None

    def effective_upper(self) -> float | None:
        """The upper limit actually in force: the superseding notice's number if one applies to
        this requirement, the datasheet's own number otherwise."""
        return self.superseded_upper if self.superseded_upper is not None else self.upper


#: `srb5030-datasheet.md` sections 3 (Recommended Operating Conditions) and 4 (Electrical
#: Characteristics). REQ-FSW has no step in `srb5030-test-spec.md` section 4 at all -- the
#: production test plan simply does not cover it, which is exactly the kind of gap this recipe
#: exists to catch. REQ-VIN's datasheet figure, 36.0 V, is superseded to 32.0 V for revisions A
#: and B by `ecn-2608-04.md#1`; revision C is not affected, since revision C fits the 63 V input
#: capacitors the notice describes.
REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        id="REQ-VIN", parameter="Input voltage", condition="steady state",
        lower=9.0, upper=36.0, unit="V", source="srb5030-datasheet#3",
        superseded_upper=32.0, superseded_by="ecn-2608-04#1",
    ),
    Requirement(
        id="REQ-VOUT", parameter="Output voltage",
        condition="full line, load and temperature range",
        lower=4.900, upper=5.100, unit="V", source="srb5030-datasheet#4",
    ),
    Requirement(
        id="REQ-LINEREG", parameter="Line regulation", condition="9.0 V to 36.0 V in, 1.0 A out",
        lower=None, upper=0.30, unit="%", source="srb5030-datasheet#4",
    ),
    Requirement(
        id="REQ-LOADREG", parameter="Load regulation", condition="0.1 A to 3.0 A out, 24.0 V in",
        lower=None, upper=0.80, unit="%", source="srb5030-datasheet#4",
    ),
    Requirement(
        id="REQ-RIPPLE", parameter="Output ripple, peak to peak",
        condition="24.0 V in, 3.0 A out, 20 MHz bandwidth",
        lower=None, upper=50.0, unit="mV", source="srb5030-datasheet#4",
    ),
    Requirement(
        id="REQ-IQNL", parameter="No-load input current", condition="24.0 V in, output enabled",
        lower=None, upper=25.0, unit="mA", source="srb5030-datasheet#4",
    ),
    Requirement(
        id="REQ-FSW", parameter="Switching frequency", condition="24.0 V in, 1.0 A out",
        lower=450.0, upper=550.0, unit="kHz", source="srb5030-datasheet#4",
    ),
    Requirement(
        id="REQ-ILIM", parameter="Current limit, output leaves regulation",
        condition="24.0 V in", lower=3.70, upper=5.00, unit="A", source="srb5030-datasheet#4",
    ),
)

REQUIREMENTS_BY_ID = {r.id: r for r in REQUIREMENTS}

#: The four instruments this bench actually has, by the short designation the test spec's
#: Equipment table and every programming manual use. A proposed test naming anything else names
#: an instrument that is not here to run it. See `examples/common/bench.py`.
BENCH_INSTRUMENTS = frozenset({"MDN-4010", "MDN-6100", "TRN-2400", "TRN-1102"})


def _requirements_for_revision(revision: str) -> tuple[Requirement, ...]:
    """The requirements as they actually stand for one board revision. Only REQ-VIN moves: the
    ECN's 32.0 V ceiling covers revisions A and B; revision C's 63 V input capacitors restore the
    datasheet's original 36.0 V, per `ecn-2608-04.md` section 3."""
    rev = revision.strip().upper()
    if rev not in ("A", "B", "C"):
        raise ValueError(f"unknown board revision: {revision!r}; expected 'A', 'B' or 'C'")
    if rev != "C":
        return REQUIREMENTS
    unsuperseded = dataclasses.replace(
        REQUIREMENTS_BY_ID["REQ-VIN"], superseded_upper=None, superseded_by=None
    )
    return tuple(unsuperseded if r.id == "REQ-VIN" else r for r in REQUIREMENTS)


# ---------------------------------------------------------------------------
# Step 2: the model proposes one test per requirement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestProposal:
    """What the model proposed for one requirement. `requirement_id` is the model's own claim
    about which requirement this answers -- code checks it against the requirement actually
    asked about, rather than assuming the two always agree."""

    requirement_id: str
    instrument: str
    measurement: str
    lower: float | None
    upper: float | None
    unit: str


PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "requirement": {"type": "string"},
        "instrument": {"type": "string"},
        "measurement": {"type": "string"},
        "lower": {"type": ["number", "null"]},
        "upper": {"type": ["number", "null"]},
        "unit": {"type": "string"},
    },
    "required": ["requirement", "instrument", "measurement", "unit"],
}

PROPOSE_SYSTEM = (
    "You are drafting one production test for one requirement of an SRB-5030 regulator board. "
    "Reply with a single line of JSON matching this schema and nothing else: "
    f"{json.dumps(PROPOSAL_SCHEMA)}. Name the instrument by its short designation from the "
    "equipment list, for example MDN-6100. If no test can be proposed for this requirement, "
    "reply with the single word SKIP instead of JSON."
)


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _propose_test(requirement: Requirement, model: Model, tracer: Tracer) -> TestProposal | None:
    lower, upper = requirement.lower, requirement.effective_upper()
    prompt = (
        f"Requirement {requirement.id}: {requirement.parameter}, {requirement.condition}. "
        f"Limit: lower={lower} upper={upper} {requirement.unit}, per {requirement.source}."
    )
    completion = model.complete(
        [Message(role="system", content=PROPOSE_SYSTEM), Message(role="user", content=prompt)],
        schema=PROPOSAL_SCHEMA,
        max_tokens=150,
    )
    tracer.record(
        kind="model",
        decided_by="code",
        title=f"Propose a test for {requirement.id}",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    text = completion.text.strip()
    if not text or text.upper() == "SKIP":
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "requirement" not in data or "instrument" not in data:
        return None
    return TestProposal(
        requirement_id=str(data["requirement"]).strip(),
        instrument=str(data.get("instrument", "")).strip(),
        measurement=str(data.get("measurement", "")).strip(),
        lower=_as_float(data.get("lower")),
        upper=_as_float(data.get("upper")),
        unit=str(data.get("unit", "")).strip(),
    )


# ---------------------------------------------------------------------------
# Step 3: the traceability table
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceRow:
    """One line of the traceability table: the requirement as asked, and whatever the model
    proposed for it, in that order -- `None` when nothing usable came back."""

    requirement: Requirement
    proposal: TestProposal | None


def _build_traceability(
    requirements: tuple[Requirement, ...], proposals: list[TestProposal | None], tracer: Tracer
) -> list[TraceRow]:
    rows = [TraceRow(requirement=r, proposal=p) for r, p in zip(requirements, proposals)]
    covered = sum(1 for row in rows if row.proposal is not None)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Build the traceability table",
        detail=f"{covered}/{len(rows)} requirements have a proposed test",
    )
    return rows


# ---------------------------------------------------------------------------
# Step 4: the coverage check -- pass or fail, never a model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoverageProblem:
    requirement_id: str
    reason: str


@dataclass(frozen=True)
class CoverageResult:
    ok: bool
    problems: list[CoverageProblem] = field(default_factory=list)


def _stale_limit(requirement: Requirement, proposal: TestProposal) -> str | None:
    """`None` when the proposed upper limit is the one actually in force. A reason when the
    proposal copied the datasheet's own number for a requirement a later notice has superseded --
    the trap `ecn-2608-04.md` exists to teach: the datasheet has not been reissued, so its number
    is still sitting there to be copied."""
    if requirement.superseded_upper is None:
        return None
    if proposal.upper is not None and abs(proposal.upper - requirement.upper) < 1e-9:
        return (
            f"upper limit {proposal.upper:g}{requirement.unit} is {requirement.source}'s figure; "
            f"{requirement.superseded_by} supersedes it to "
            f"{requirement.superseded_upper:g}{requirement.unit}"
        )
    return None


def check_coverage(rows: list[TraceRow]) -> CoverageResult:
    """Pass or fail. Every requirement needs at least one proposed test, and every proposed test
    has to name the requirement it answers, an instrument this bench actually has, and a limit
    with a unit. This function never calls a model and never reads one's output as anything but
    data to check: the decision is arithmetic and string comparison, the same as every pass/fail
    decision this site makes."""
    problems: list[CoverageProblem] = []
    for row in rows:
        requirement, proposal = row.requirement, row.proposal
        if proposal is None:
            problems.append(CoverageProblem(requirement.id, "no test was proposed for this requirement"))
            continue
        if proposal.requirement_id != requirement.id:
            problems.append(
                CoverageProblem(
                    requirement.id,
                    f"the proposed test names {proposal.requirement_id!r}, not this requirement",
                )
            )
        if proposal.instrument not in BENCH_INSTRUMENTS:
            problems.append(
                CoverageProblem(
                    requirement.id,
                    f"names {proposal.instrument!r}, which is not one of the four instruments on this bench",
                )
            )
        if proposal.lower is None and proposal.upper is None:
            problems.append(CoverageProblem(requirement.id, "the proposed test carries no limit"))
        if not proposal.unit:
            problems.append(CoverageProblem(requirement.id, "the proposed test carries no unit"))
        stale = _stale_limit(requirement, proposal)
        if stale is not None:
            problems.append(CoverageProblem(requirement.id, stale))
    return CoverageResult(ok=not problems, problems=problems)


# ---------------------------------------------------------------------------
# The chain, and the approval checkpoint
# ---------------------------------------------------------------------------

Decision = Literal["approve", "reject"]


@dataclass(frozen=True)
class Blocked:
    """The coverage check failed. There is nothing yet for a person to approve: the chain stops
    here, in code, and reports exactly which requirements have a problem and what it is."""

    rows: list[TraceRow]
    coverage: CoverageResult


@dataclass(frozen=True)
class PendingApproval:
    """A traceability table that cleared the coverage check and is waiting on a person. Nothing
    downstream may treat this plan as adopted until `resume` records a decision."""

    rows: list[TraceRow]
    coverage: CoverageResult


def run(revision: str, model: Model, tracer: Tracer) -> Blocked | PendingApproval:
    requirements = _requirements_for_revision(revision)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Read the requirements",
        detail=f"{len(requirements)} requirements, board revision {revision.strip().upper()}",
    )
    proposals = [_propose_test(r, model, tracer) for r in requirements]
    rows = _build_traceability(requirements, proposals, tracer)
    coverage = check_coverage(rows)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check coverage",
        detail="pass" if coverage.ok else f"fail: {len(coverage.problems)} problem(s)",
    )
    if not coverage.ok:
        return Blocked(rows=rows, coverage=coverage)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Hold for a person's approval",
        detail="the plan cleared the coverage check; nothing is adopted before resume() records a decision",
    )
    return PendingApproval(rows=rows, coverage=coverage)


def _render_plan(rows: list[TraceRow]) -> str:
    lines = ["requirement,parameter,test,instrument,lower,upper,unit,source"]
    for row in rows:
        requirement, proposal = row.requirement, row.proposal
        assert proposal is not None  # a PendingApproval only reaches resume() after coverage.ok
        lines.append(
            f"{requirement.id},{requirement.parameter},{proposal.measurement},"
            f"{proposal.instrument},{proposal.lower},{proposal.upper},{proposal.unit},"
            f"{requirement.source}"
        )
    return "\n".join(lines)


def _citations(rows: list[TraceRow]) -> list[str]:
    cites: set[str] = set()
    for row in rows:
        cites.add(row.requirement.source)
        if row.requirement.superseded_by:
            cites.add(row.requirement.superseded_by)
    return sorted(cites)


def resume(pending: PendingApproval, decision: Decision, tracer: Tracer, *, note: str = "") -> Answer:
    """A person's decision on a plan that already cleared the coverage check. Approving adopts
    the traceability table as it stands; rejecting adopts nothing. There is no `edit` here, unlike
    `examples/human_in_the_loop/run.py`'s checkpoint: a reviewer who wants a different test sends
    the requirement back through step two, since a hand-typed correction to a traceability table
    is exactly the kind of change that itself needs a citation."""
    tracer.record(
        kind="code",
        decided_by="code",
        title="Resume from checkpoint with the reviewer's decision",
        detail=f"decision={decision}" + (f" note={note!r}" if note else ""),
    )
    if decision == "reject":
        return Answer(text="The reviewer rejected this plan; it is not adopted.", citations=[])
    return Answer(text=_render_plan(pending.rows), citations=_citations(pending.rows))
