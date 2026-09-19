"""Level 3: sort one failing SRB-5030 unit into a cause the failure analysis guide already
lists, then route it. The worked measurement is VOUT (test step 3), the one step Orbeck's own
guide already treats as ambiguous: "Retest once on another fixture, then failure analysis if it
fails again" (`evals/bench/corpus/failure-analysis-guide.md` section 1). Everything here narrows
that default, or leaves it alone; nothing here decides pass or fail, which the test executive
already did before this file ever runs.

Two causes never need the model. Grouping the run's VOUT failures by fixture finds a stale
calibration offset (guide section 7); the same grouping by lot would find a bad reel of output
capacitors for RIPPLE failures (section 4). Both are a count and a share, computed in
`_group_signature` before any note is read, the same argument `limits-without-a-model` makes for
the whole month of data.

What a count cannot see is a genuine one-off sitting inside a group's own pattern, or a unit with
nothing systemic behind it at all. The operator's note is the only signal left for those, and it
is exactly as uneven as `evals/bench/corpus/failure-analysis-guide.md` section 8 says: most
failures carry no note, and the ones that do range from a full diagnosis to a question mark.
`_classify_note` reads one note and sorts it into one of four causes the guide lists; it is
skipped outright when there is no note to read, since there is nothing for a model to add.

`_route` is the asymmetric-cost line the recipe page walks through: a `dead_board` claim
overrides even a matching group signature, because a dead board that gets waved through on "it's
just the fixture" is a defect that ships, and a `fixture_signature` claim with no group evidence
behind it is not enough, by itself, to skip failure analysis for the same reason in reverse. A
person confirms every route before it is acted on; see `confirm`.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from evals.bench import PRODUCTION_CSV
from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 3
MAX_RETRIES = 1
DEFAULT_MEASUREMENT = "VOUT"

#: A serial that did fail VOUT in the production log, for `scripts/record_trace.py`. `run` refuses
#: a serial it cannot find, which is right, so a recorder needs to be told one that exists.
SAMPLE_INPUT = "SRB5030-2608-0063"

#: The four causes this recipe sorts a VOUT failure's note into. Each is a cause
#: `evals/bench/corpus/failure-analysis-guide.md` already names: `dead_board` is section 2,
#: `fixture_signature` is section 7 (and section 3's "check the fixture before the board"),
#: `board_low_general` is section 3's feedback-divider suspect, and `no_information` is section 8's
#: own admission that most failures carry no usable note at all.
CAUSES = ("dead_board", "fixture_signature", "board_low_general", "no_information")

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "cause": {"type": "string", "enum": list(CAUSES)},
        "evidence": {"type": "string"},
    },
    "required": ["cause", "evidence"],
}
CLASSIFY_SYSTEM = (
    "An Orbeck SRB-5030 regulator board failed its VOUT test step. Read the operator's note and "
    "classify the likely cause as exactly one of four words from Orbeck's own failure analysis "
    "guide: 'dead_board' if the note describes no output at all or the controller not switching; "
    "'fixture_signature' if the note blames a fixture by name or number; 'board_low_general' if "
    "the note describes the board itself measuring low, with no fixture blamed; 'no_information' "
    "if the note adds no diagnosis beyond the measured value, or says nothing useful at all. "
    f"Reply as JSON matching this schema, nothing else: {json.dumps(CLASSIFY_SCHEMA)}. Quote the "
    "exact words from the note that support your answer in 'evidence', or leave it empty only "
    "for 'no_information'."
)

#: What each route means, for the disposition record a person reads before confirming it.
ROUTES = {
    "hold_check_fixture": "Hold the unit. Check this fixture's calibration record before touching the board.",
    "hold_check_lot": "Hold the unit. Check this lot's output capacitors before touching the board.",
    "failure_analysis": "Send to failure analysis directly; do not retest first.",
    "retest_other_fixture": "Retest once on another fixture, the guide's own default for an ungrouped VOUT failure.",
}


@dataclass(frozen=True)
class FailureRow:
    """One failing row of `production-run-2026-08.csv`, read but never altered here."""

    serial: str
    lot: str
    fixture: str
    measurement: str
    value: str
    unit: str
    lower_limit: str
    upper_limit: str
    note: str


@dataclass(frozen=True)
class Disposition:
    """What a person is asked to confirm. Nothing here is final until `confirm` records a
    decision: the route is a proposal, not a disposition, until then."""

    row: FailureRow
    group_signature: str  # "fixture" | "lot" | "none"
    cause: str
    evidence: str
    route: str


def load_failures(measurement: str, *, production_csv: Path = PRODUCTION_CSV) -> list[FailureRow]:
    """Every row that failed this measurement, in the order the CSV has them. Level 0: a filter,
    not a model, the same as the row's own PASS/FAIL verdict, which was decided at the fixture."""
    with production_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            FailureRow(
                serial=r["serial"], lot=r["lot"], fixture=r["fixture"], measurement=r["measurement"],
                value=r["value"], unit=r["unit"], lower_limit=r["lower_limit"], upper_limit=r["upper_limit"],
                note=r["notes"],
            )
            for r in reader
            if r["measurement"] == measurement and r["result"] == "FAIL"
        ]


def _group_signature(failures: list[FailureRow], row: FailureRow, *, min_count: int = 3, min_share: float = 0.5) -> str:
    """Level 0: does this row's fixture, or its lot, already account for most of the run's
    failures on this measurement? A `GROUP BY` and a count, nothing else -- see
    `evals/bench/corpus/failure-analysis-guide.md` section 7 (fixture) and section 4 (lot), and
    `docs/THE-BENCH.md`'s Story 1 and Story 2 for the numbers this threshold is checked against.
    `min_count` keeps one or two coincidental failures on the same fixture from reading as a
    pattern; `min_share` requires that fixture or lot to be most of the failures, not merely more
    than any other single one.
    """
    total = len(failures)
    if total == 0:
        return "none"
    fixture_count = sum(1 for f in failures if f.fixture == row.fixture)
    if fixture_count >= min_count and fixture_count / total > min_share:
        return "fixture"
    lot_count = sum(1 for f in failures if f.lot == row.lot)
    if lot_count >= min_count and lot_count / total > min_share:
        return "lot"
    return "none"


def _validate(record: dict) -> list[str]:
    problems = []
    cause = record.get("cause")
    if cause not in CAUSES:
        problems.append(f"cause must be one of {CAUSES}, got {cause!r}")
    evidence = record.get("evidence")
    if not isinstance(evidence, str):
        problems.append("evidence must be a string")
    elif cause is not None and cause != "no_information" and not evidence.strip():
        # A cause with no quoted evidence is an unsupported guess, not a reading of the note.
        problems.append(f"cause {cause!r} needs a quoted 'evidence' string, or the cause should be 'no_information'")
    return problems


def _classify_note(note: str, model: Model, tracer: Tracer) -> tuple[str, str]:
    if not note.strip():
        tracer.record(kind="code", decided_by="code", title="No operator note to read", detail="cause=no_information, no model call")
        return "no_information", ""

    messages = [Message(role="system", content=CLASSIFY_SYSTEM), Message(role="user", content=f"Note: {note!r}")]
    record: dict = {}
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=CLASSIFY_SCHEMA, max_tokens=120)
        tracer.record(
            kind="model",
            decided_by="code",
            title="Classify the note" if attempt == 0 else "Classify again with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            record, problems = json.loads(completion.text), None
            problems = _validate(record)
        except json.JSONDecodeError as exc:
            record, problems = {}, [f"invalid JSON: {exc}"]
        tracer.record(kind="code", decided_by="code", title="Validate against the schema", detail="; ".join(problems) or "valid")
        if not problems:
            return record["cause"], record["evidence"]
        if attempt < MAX_RETRIES:
            messages.append(Message(role="user", content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only."))
    tracer.record(kind="code", decided_by="code", title="Gave up after one retry; treated as no information", detail=str(record))
    return "no_information", ""


def _route(group_signature: str, cause: str) -> str:
    """Code, always: the note's label never decides where a unit goes by itself.

    `dead_board` outranks a group signature on purpose: a fixture offset of a few tens of
    millivolts cannot produce zero output, so a dead-board claim is never explained by the
    fixture, whatever the count says. Below that, the group signature outranks the note, because
    a board that merely reads low is exactly what a fixture offset also produces (guide section
    3). An uncorroborated `fixture_signature` -- one note, no group pattern behind it -- is not
    enough on its own to skip failure analysis, for the same reason in reverse: trusting it wrongly
    lets a real defect through on a guess, where the group check would have caught a real fixture
    fault for free. See the recipe page for the cost each direction of that mistake carries.
    """
    if cause == "dead_board":
        return "failure_analysis"
    if group_signature == "fixture":
        return "hold_check_fixture"
    if group_signature == "lot":
        return "hold_check_lot"
    if cause == "board_low_general":
        return "failure_analysis"
    return "retest_other_fixture"


def run(
    serial: str,
    model: Model,
    tracer: Tracer,
    *,
    measurement: str = DEFAULT_MEASUREMENT,
    production_csv: Path = PRODUCTION_CSV,
) -> Disposition:
    failures = load_failures(measurement, production_csv=production_csv)
    tracer.record(kind="code", decided_by="code", title=f"Load the run's {measurement} failures", detail=f"{len(failures)} rows")

    row = next((f for f in failures if f.serial == serial), None)
    if row is None:
        raise ValueError(f"{serial!r} did not fail {measurement} in {production_csv}")

    signature = _group_signature(failures, row)
    tracer.record(kind="code", decided_by="code", title="Group failures by fixture and by lot", detail=f"signature={signature}")

    cause, evidence = _classify_note(row.note, model, tracer)

    route = _route(signature, cause)
    tracer.record(kind="code", decided_by="code", title="Route from the cause and the group signature", detail=f"route={route}")

    disposition = Disposition(row=row, group_signature=signature, cause=cause, evidence=evidence, route=route)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Hold for a person's confirmation",
        detail="every disposition needs one before anything is scrapped, reworked, or held",
    )
    return disposition


def confirm(disposition: Disposition, approved: bool, tracer: Tracer, *, note: str = "") -> str:
    """A person's decision on one proposed disposition. Never automatic, and never skipped: see
    `run`'s last step. Returns the route that was actually acted on."""
    tracer.record(
        kind="code",
        decided_by="code",
        title="Person confirms the disposition",
        detail=f"approved={approved} route={disposition.route}" + (f" note={note!r}" if note else ""),
    )
    if approved:
        return disposition.route
    return f"overridden_by_person: {note or 'no reason given'}"
