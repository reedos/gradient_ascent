"""Level 3: pull the MDN-6100's DC volts accuracy table out of its programming manual and into
`AccuracySpec` rows, one per range per calibration interval, that
`examples/common/bench.py`'s shared functions can price a reading from.

`evals/bench/corpus/mdn6100-programming-manual.md` section 2 prints the table as two ranges by
three calibration intervals in prose plus a five-row temperature-coefficient table: 15 DC volts
rows in total. The model reads that text once and replies with all 15 as JSON matching
`AccuracySpec`'s own fields. Code checks three things it can check without already knowing what
the manual says: every row is shaped right, every one of the 15 (range, interval) combinations is
present exactly once, and for a fixed range the accuracy limit only gets looser from the 24 hour
row through the 90 day row to the 1 year row, never tighter. A reply that fails gets one retry
with the specific problem appended.

None of that catches the mistake this bench plants: a row can be shaped right, complete and
monotonic and still hold the wrong numbers, because a range's own accuracy generally gets looser
with the range too, the same direction monotonicity already expects. `_bad_response` below
answers with the 100 V row's numbers under the 10 V, 1 year label -- a plausible one-row slip
reading a five-column manual table -- and `_validate_table` finds nothing wrong with it. Only a
person reading `mdn6100-programming-manual.md` section 2 against the extracted table catches it,
which is why `run` never returns a table a caller may use: it returns a proposal, and
`confirm_table` is where a person's decision is actually recorded, the same shape as
`test-failure-triage`'s `confirm` and the bench's own `GuardedSupply.output_on`.

Once a table is confirmed, pricing a reading from it is arithmetic and calls no model again:
`price_reading` is `dc_voltage_budget` from `examples/common/bench.py`, rewritten to read a
freshly extracted table instead of the one already coded there, because a real instrument's table
is not already coded anywhere until a run like this one puts it there. The two settings that
choose which row applies, the calibration interval and the range, are never the model's either;
manual section 7 calls them out by name: "Two influences are settings and not contributions, and
both are in the user's hands." `interval_for_calibration` is that rule as three comparisons, and
the range a reading was actually taken on is a fact `price_reading` is handed, not one it guesses.
Getting either one wrong on an otherwise perfect table reproduces the manual's own two worked
examples: the 24 hour row used for a meter calibrated eleven months ago prices a 4.9930 V reading
at 79.9 uV against a true 224.8 uV, and the 100 V row used for a 10 V reading prices it at 824.7 uV
against the same 224.8 uV. `tests/test_example_bench_accuracy_specs_from_the_manual.py` reproduces
both.
"""
from __future__ import annotations

import json
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from evals.bench import load_bench_sections
from examples.common.bench import (
    AccuracySpec,
    CAL_BAND_24H_C,
    CAL_BAND_C,
    Contribution,
    Multimeter,
    combined_uncertainty,
    expanded_uncertainty,
    reading_resolution,
    repeatability_uncertainty,
    resolution_uncertainty,
    standard_uncertainty,
)
from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 3
MAX_RETRIES = 1

#: The only section this recipe ever reads. `scripts/record_trace.py` needs some value to pass
#: when it is given no `--question`, so this doubles as `SAMPLE_INPUT`, the pattern
#: `bench_test_failure_triage` uses for the same reason.
SECTION_ID = "mdn6100-programming-manual#2"
SAMPLE_INPUT = SECTION_ID

#: The five DC volts ranges and three calibration intervals the manual's table crosses.
RANGES_V: tuple[float, ...] = Multimeter.DC_RANGES_V
INTERVALS: tuple[str, ...] = ("24 hour", "90 day", "1 year")

ROW_SCHEMA = {
    "type": "object",
    "properties": {
        "range_value": {"type": "number"},
        "interval": {"type": "string", "enum": list(INTERVALS)},
        "ppm_of_reading": {"type": "number"},
        "ppm_of_range": {"type": "number"},
        "tempco_ppm_of_reading_per_c": {"type": "number"},
        "tempco_ppm_of_range_per_c": {"type": "number"},
    },
    "required": [
        "range_value",
        "interval",
        "ppm_of_reading",
        "ppm_of_range",
        "tempco_ppm_of_reading_per_c",
        "tempco_ppm_of_range_per_c",
    ],
}
TABLE_SCHEMA = {"type": "array", "items": ROW_SCHEMA}

EXTRACT_SYSTEM = (
    "Read the DC volts accuracy table in this excerpt of a multimeter's programming manual. "
    f"It crosses {len(RANGES_V)} ranges with {len(INTERVALS)} calibration intervals, plus one "
    "temperature coefficient per range that is the same for all three intervals of that range. "
    f"Reply with exactly {len(RANGES_V) * len(INTERVALS)} JSON objects, one per range per "
    "interval, as a JSON array matching this schema, nothing else: "
    f"{json.dumps(TABLE_SCHEMA)}. Copy every number from the row it actually belongs to; do not "
    "compute, round, or carry a number over from a neighboring range or interval."
)


class RowsNotConfirmed(Exception):
    """Raised by `confirm_table` when a person rejects the table, and by `price_reading` if it is
    ever handed something that did not come back from `confirm_table`. Passing validation is not
    the same as being right; that is the entire reason this exception exists."""


@dataclass(frozen=True)
class ExtractionResult:
    """What `run` returns: a proposal, not a usable table. `raw` is what the model actually said,
    kept so a person reviewing the table can see it next to the manual without re-running
    anything."""

    section: str
    rows: dict[tuple[str, float], AccuracySpec]
    raw: tuple[dict, ...]


def _validate_table(rows: object) -> list[str]:
    """Shape, completeness and monotonicity: everything code can check without already knowing
    what the manual says. It cannot check that a row's numbers came from the cell they claim to,
    only that the 15 cells are all present once each, hold plausible numbers, and get no tighter
    from the 24 hour row to the 1 year row of the same range -- and a range's own numbers usually
    get looser with the range too, which is exactly why a row copied from the next range up still
    passes this last check.
    """
    if not isinstance(rows, list):
        return ["the extraction must be a JSON array of rows"]

    problems: list[str] = []
    clean: dict[tuple[str, float], dict] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"row {i}: not an object")
            continue
        interval = row.get("interval")
        range_value = row.get("range_value")
        row_ok = True
        if interval not in INTERVALS:
            problems.append(f"row {i}: interval must be one of {INTERVALS}, got {interval!r}")
            row_ok = False
        if range_value not in RANGES_V:
            problems.append(f"row {i}: range_value must be one of {RANGES_V}, got {range_value!r}")
            row_ok = False
        for name in (
            "ppm_of_reading",
            "ppm_of_range",
            "tempco_ppm_of_reading_per_c",
            "tempco_ppm_of_range_per_c",
        ):
            value = row.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                problems.append(f"row {i}: {name} must be a non-negative number, got {value!r}")
                row_ok = False
        if not row_ok:
            continue
        key = (interval, float(range_value))
        if key in clean:
            problems.append(f"row {i}: duplicate row for interval={interval!r} range_value={range_value!r}")
            continue
        clean[key] = row

    expected = {(interval, range_value) for interval in INTERVALS for range_value in RANGES_V}
    missing = expected - set(clean)
    if missing:
        problems.append(f"missing rows: {sorted(missing)}")

    for range_value in RANGES_V:
        if not all((interval, range_value) in clean for interval in INTERVALS):
            continue  # already reported above
        for name in ("ppm_of_reading", "ppm_of_range"):
            values = [float(clean[(interval, range_value)][name]) for interval in INTERVALS]
            if any(a > b for a, b in zip(values, values[1:])):
                problems.append(
                    f"{range_value:g} V: {name} does not increase from 24 hour through 1 year: {values}"
                )
    return problems


def _rows_to_table(rows: list[dict]) -> dict[tuple[str, float], AccuracySpec]:
    """Build real `AccuracySpec` rows from a validated extraction. Only called once
    `_validate_table` has returned no problems, so every field is present and typed."""
    table: dict[tuple[str, float], AccuracySpec] = {}
    for row in rows:
        interval = row["interval"]
        range_value = float(row["range_value"])
        band = CAL_BAND_24H_C if interval == "24 hour" else CAL_BAND_C
        table[(interval, range_value)] = AccuracySpec(
            range_value=range_value,
            ppm_of_reading=float(row["ppm_of_reading"]),
            ppm_of_range=float(row["ppm_of_range"]),
            tempco_ppm_of_reading_per_c=float(row["tempco_ppm_of_reading_per_c"]),
            tempco_ppm_of_range_per_c=float(row["tempco_ppm_of_range_per_c"]),
            interval=interval,
            band_c=band,
        )
    return table


def run(
    section: str,
    model: Model,
    tracer: Tracer,
    *,
    sections: dict | None = None,
) -> ExtractionResult:
    sections = sections if sections is not None else load_bench_sections()
    if section not in sections:
        raise ValueError(f"{section!r} is not a section of the bench corpus")
    manual_text = sections[section].text
    tracer.record(kind="code", decided_by="code", title="Read the manual section", detail=section)

    messages = [
        Message(role="system", content=EXTRACT_SYSTEM),
        Message(role="user", content=manual_text),
    ]
    rows: list = []
    problems: list[str] = ["no attempt made"]
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=TABLE_SCHEMA, max_tokens=1400)
        tracer.record(
            kind="model",
            decided_by="code",
            title="Extract the accuracy table" if attempt == 0 else "Extract again with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            rows = json.loads(completion.text)
            problems = _validate_table(rows)
        except json.JSONDecodeError as exc:
            rows, problems = [], [f"invalid JSON: {exc}"]
        tracer.record(
            kind="code",
            decided_by="code",
            title="Validate shape, completeness and monotonicity",
            detail=(
                "; ".join(problems)
                if problems
                else f"{len(rows)} rows, every range and interval present once, ppm increases 24 hour through 1 year"
            ),
        )
        if not problems:
            break
        if attempt < MAX_RETRIES:
            messages.append(
                Message(
                    role="user",
                    content=f"That did not validate: {'; '.join(problems)}. Reply again with the corrected JSON array only.",
                )
            )

    if problems:
        tracer.record(
            kind="code",
            decided_by="code",
            title="Stop: the table never validated",
            detail=(
                f"gave up after {MAX_RETRIES} retry(ies): {'; '.join(problems)}; nothing for a "
                f"person to check, so nothing is returned to price a reading from"
            ),
        )
        raw = tuple(rows) if isinstance(rows, list) else ()
        return ExtractionResult(section=section, rows={}, raw=raw)

    table = _rows_to_table(rows)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Hold the table for a person's row-by-row check against the manual",
        detail=(
            f"{len(table)} rows; validation cannot see a row whose numbers came from the wrong "
            f"range or the wrong interval, only a person reading {section} can"
        ),
    )
    return ExtractionResult(section=section, rows=table, raw=tuple(rows))


def confirm_table(
    result: ExtractionResult,
    approved: bool,
    tracer: Tracer,
    *,
    note: str = "",
) -> dict[tuple[str, float], AccuracySpec]:
    """A person's decision on one proposed table. Never automatic, and never skipped: `run`
    returns a proposal, and this is where it becomes something `price_reading` may use, the same
    shape as `bench_test_failure_triage.confirm`."""
    tracer.record(
        kind="code",
        decided_by="code",
        title="Person confirms the table against the manual",
        detail=f"approved={approved} section={result.section}" + (f" note={note!r}" if note else ""),
    )
    if not approved:
        raise RowsNotConfirmed(note or "rejected: at least one row did not match the manual")
    return result.rows


def interval_for_calibration(days_since_cal: float) -> str:
    """Which calibration interval applies, from how long ago the meter was calibrated. Level 0,
    three comparisons, no model: manual section 7, "use the row for the interval since the last
    calibration, not the tightest row in the table." A meter calibrated eleven months ago is
    about 335 days out, which lands on the 1 year row, not the 24 hour or the 90 day row, however
    much smaller those numbers look.
    """
    if days_since_cal < 0:
        raise ValueError("days_since_cal is not negative")
    if days_since_cal <= 1.0:
        return "24 hour"
    if days_since_cal <= 90.0:
        return "90 day"
    return "1 year"


@dataclass(frozen=True)
class PricedReading:
    interval: str
    range_v: float
    mean_v: float
    contributions: tuple[Contribution, ...]
    combined_v: float
    expanded_v: float


def price_reading(
    table: dict[tuple[str, float], AccuracySpec],
    readings_v: Sequence[float],
    *,
    range_v: float,
    days_since_cal: float,
    ambient_c: float = 23.0,
    lead_half_width_v: float | None = None,
) -> PricedReading:
    """The same four-line budget `examples.common.bench.dc_voltage_budget` computes, read from
    this extraction's own confirmed table instead of the one already coded in
    `examples/common/bench.py` -- a real instrument's table is not already coded anywhere until a
    run like this one puts it there. `range_v` and `days_since_cal` are facts about how the
    reading was actually taken, not choices this function makes: pass the wrong one and this
    returns a real number from a real row of the table, priced for a measurement that was not
    actually taken that way. Level 0 throughout; no model runs past `confirm_table`.
    """
    interval = interval_for_calibration(days_since_cal)
    try:
        spec = table[(interval, range_v)]
    except KeyError:
        raise ValueError(
            f"the confirmed table has no row for interval={interval!r} range_value={range_v!r}"
        ) from None

    values = [float(v) for v in readings_v]
    if not values:
        raise ValueError("price_reading needs at least one reading")
    mean_v = statistics.fmean(values)

    contributions = [
        Contribution(
            "meter accuracy",
            standard_uncertainty(spec.limit(mean_v, ambient_c)),
            f"{spec.interval} specification, {spec.range_value:g} V range, {ambient_c:g} degC",
        ),
        Contribution(
            "resolution",
            resolution_uncertainty(range_v),
            f"{reading_resolution(range_v) * 1e6:g} uV per count",
        ),
    ]
    if len(values) > 1:
        contributions.append(
            Contribution("repeatability", repeatability_uncertainty(values), f"{len(values)} readings")
        )
    if lead_half_width_v:
        contributions.append(
            Contribution(
                "leads and connections",
                standard_uncertainty(lead_half_width_v),
                f"+/-{lead_half_width_v * 1e6:g} uV, from the fixture record",
            )
        )

    combined = combined_uncertainty(contributions)
    expanded = expanded_uncertainty(combined)
    return PricedReading(
        interval=interval,
        range_v=range_v,
        mean_v=mean_v,
        contributions=tuple(contributions),
        combined_v=combined,
        expanded_v=expanded,
    )
