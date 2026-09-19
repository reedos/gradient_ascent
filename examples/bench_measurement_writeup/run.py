"""Level 1: measurement writeup. One model call turns a lab notebook and a table of numbers code
already computed into a short characterization report a reviewer can read.

Nothing here asks the model for a number. `compute_figures` reads
`evals/bench/data/characterization-2026-09.csv`, the revision C characterization sweep, and
computes every figure the report might quote: the margin to the datasheet's output voltage
minimum at the corner where line, load and temperature all push it down together, for all five
boards; the expanded uncertainty behind the worst one's corner reading, from the same
`dc_voltage_budget` / `combined_uncertainty` / `expanded_uncertainty` functions every other
recipe on this bench uses; and the three-ambient line regulation figures and guardbanded verdict
for the one board whose margin is smaller than the measurement is worth
(`docs/THE-BENCH.md`, "Story A" and "Story B"). Those figures, formatted exactly as the model is
allowed to quote them, and the notebook's own prose (`characterization-notebook.md`), are what
the prompt hands over. The model's only job is to write the sentences around them.

`unsupported_numbers` is the check the page is built on: every numeric token in the model's draft
has to appear, character for character, among the figures code computed and handed over. It is
real code, not a description of one, and `tests/test_example_bench_measurement_writeup.py` shows
it both accepting a clean draft and rejecting one with a number code never produced. It is not a
retry loop: level 1 makes exactly one model call, and a draft the check rejects is not silently
patched or reshipped, it is handed to a person as a report that failed review, with the exact
tokens that failed named so the review does not start from scratch.
"""
from __future__ import annotations

import csv
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from evals.bench import CHARACTERIZATION_CSV, load_bench_documents
from examples.common.bench import (
    COVERAGE_FACTOR,
    LEAD_HALF_WIDTH_V,
    combined_uncertainty,
    dc_voltage_budget,
    expanded_uncertainty,
    guarded_verdict,
    margin_to_limit,
)
from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 1

#: srb5030-datasheet.md section 4: the output voltage window over the full line, load and
#: temperature range, and the line regulation maximum from the same table.
VOUT_MIN_V = 4.900
VOUT_MAX_V = 5.100
LINE_REG_MAX_PCT = 0.300
VOUT_NOM_V = 5.000
#: The 10 V DC range characterization-notebook.md section 2 says the meter was set to.
DC_RANGE_V = 10.0
#: The corner where line, load and temperature all push the output down at once: notebook
#: section 4, and docs/THE-BENCH.md's "Story A".
CORNER_TAMB_C = "70.0"
CORNER_VIN_V = "9.0"
CORNER_IOUT_A = "3.000"
CORNER_AMBIENT_TEXT = "70"
#: Board 5's line regulation is the uncertainty story: notebook sections 5 and 6, and
#: docs/THE-BENCH.md's "Story B".
MARGINAL_LINE_SERIAL = "SRB5030-2609-0005"
#: The point the notebook flags as unconfirmed: section 3, board 1's 12 V block.
UNCERTAIN_BLOCK_SERIAL = "SRB5030-2609-0001"
UNCERTAIN_BLOCK_VIN_TEXT = "12.0"

#: A numeric token: an optionally signed run of digits with at most one decimal point, not
#: touching a letter, an underscore, a hyphen or another digit's decimal point on either side.
#: The exclusion is what keeps a serial number ("SRB5030-2609-0003") from being read as three
#: numbers instead of an identifier: every digit inside one is preceded by a letter, a digit or a
#: hyphen, so nothing there ever starts a match. See the module docstring and this recipe's page
#: for what this check can and cannot catch.
NUMBER_RE = re.compile(r"(?<![\w.-])[+-]?\d[\d,]*(?:\.\d+)?(?![\w])")

SYSTEM_PROMPT = (
    "You write short characterization reports for Orbeck Power Systems engineers, from a lab "
    "notebook and a list of figures another program has already computed from the raw sweep "
    "data. Write plain prose a reviewer can read in under a minute: what the session found, what "
    "it means, and what is still open. Rules, with no exceptions:\n"
    "- Every number in your report must be copied character for character from the Figures list "
    "below. Never compute, round, average, convert or improve a number yourself, even one that "
    "looks easy, and never use a number from the notebook that is not also in the Figures list.\n"
    "- Say the label next to a figure exactly what it says next to it in the Figures list; do not "
    "reuse a figure's number for a different quantity.\n"
    "- Do not soften a 'cannot say' verdict into a pass, or a 'fail' into a marginal pass. Report "
    "a verdict exactly as given.\n"
    "- For anything not in the Figures list (how many boards, how many readings, which ambient is "
    "warmer than which), use words, not digits.\n"
    "- Carry forward every open item from the notebook that is still genuinely open; do not drop "
    "a caveat because it complicates the story."
)


@dataclass(frozen=True)
class Figure:
    """One number code computed, formatted exactly as the model is allowed to quote it.

    `label` is what the prompt calls it; `text` is the literal character sequence
    `unsupported_numbers` looks for in the model's draft. The check compares `text` as a string,
    not the number it represents, so "0.267" and "0.2670" are different figures as far as it is
    concerned. Code always formats a given number the same way once, here, rather than once in
    the prompt and again wherever the page quotes it, so the two cannot drift apart.
    """

    label: str
    text: str


@dataclass(frozen=True)
class Results:
    """Every number this recipe hands the model, already computed, and every function that
    produced one of them is either shared with the rest of the bench
    (`examples.common.bench`) or a subtraction over the raw CSV; nothing here is arithmetic a
    model did."""

    figures: tuple[Figure, ...]
    corner_margins_mv: dict[str, float]
    thin_serial: str
    corner_expanded_uncertainty_uv: float
    corner_verdict: str
    line_reg_pct: dict[str, float]
    line_reg_uncertainty_pct: float
    line_reg_verdicts: dict[str, str]


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with open(csv_path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _readings(rows: list[dict[str, str]], serial: str, tamb_c: str, vin_v: str, iout_a: str) -> list[float]:
    return [
        float(r["vout_v"])
        for r in rows
        if r["serial"] == serial and r["tamb_c"] == tamb_c and r["vin_v"] == vin_v and r["iout_a"] == iout_a
    ]


def line_regulation_pct(rows: list[dict[str, str]], serial: str, tamb_c: str) -> float:
    """(VOUT at 32.0 V - VOUT at 9.0 V) / 5.000, as a percentage, at 1.000 A. The same arithmetic
    `tests/test_bench_characterization.py` checks this session's own numbers against, over the
    same CSV `evals.bench.CHARACTERIZATION_CSV` names."""
    high = statistics.fmean(_readings(rows, serial, tamb_c, "32.0", "1.000"))
    low = statistics.fmean(_readings(rows, serial, tamb_c, "9.0", "1.000"))
    return 100.0 * (high - low) / VOUT_NOM_V


def compute_results(csv_path: Path = CHARACTERIZATION_CSV) -> Results:
    """Read the characterization sweep and compute the corner margins, one uncertainty budget
    and the line-regulation verdicts this report needs. Nothing here is a model's arithmetic, and
    nothing the model is handed lets it redo this arithmetic differently.
    """
    rows = _read_rows(csv_path)
    serials = sorted({r["serial"] for r in rows})

    figures: list[Figure] = [
        Figure("output voltage minimum (V)", f"{VOUT_MIN_V:.3f}"),
        Figure("line regulation limit (%)", f"{LINE_REG_MAX_PCT:.3f}"),
        Figure("coverage factor (k)", f"{COVERAGE_FACTOR:.0f}"),
        Figure("corner ambient (degC)", CORNER_AMBIENT_TEXT),
        Figure("corner input voltage (V)", CORNER_VIN_V),
        Figure("corner load current (A)", CORNER_IOUT_A),
        Figure("uncertain block input voltage (V)", UNCERTAIN_BLOCK_VIN_TEXT),
        Figure("lead and connection uncertainty assumption (uV)", f"{LEAD_HALF_WIDTH_V * 1e6:.0f}"),
    ]

    corner_margins_mv: dict[str, float] = {}
    for serial in serials:
        mean = statistics.fmean(_readings(rows, serial, CORNER_TAMB_C, CORNER_VIN_V, CORNER_IOUT_A))
        margin_v = margin_to_limit(mean, VOUT_MIN_V, side="lower")
        corner_margins_mv[serial] = 1000.0 * margin_v
        figures.append(Figure(f"{serial} corner output voltage (V)", f"{mean:.5f}"))
        figures.append(Figure(f"{serial} corner margin (mV)", f"{1000.0 * margin_v:.1f}"))

    thin_serial = min(corner_margins_mv, key=corner_margins_mv.get)
    corner_readings = _readings(rows, thin_serial, CORNER_TAMB_C, CORNER_VIN_V, CORNER_IOUT_A)
    corner_expanded_v = expanded_uncertainty(
        combined_uncertainty(dc_voltage_budget(corner_readings, range_v=DC_RANGE_V))
    )
    corner_expanded_uv = 1e6 * corner_expanded_v
    corner_verdict = guarded_verdict(
        statistics.fmean(corner_readings), corner_expanded_v, lower=VOUT_MIN_V, upper=VOUT_MAX_V
    )
    figures.append(Figure("thin-margin board corner expanded uncertainty (uV)", f"{corner_expanded_uv:.1f}"))

    line_reg_pct = {tamb: line_regulation_pct(rows, MARGINAL_LINE_SERIAL, tamb) for tamb in ("0.0", "25.0", "70.0")}
    reg_readings = _readings(rows, MARGINAL_LINE_SERIAL, "25.0", "32.0", "1.000")
    per_reading = combined_uncertainty(
        dc_voltage_budget(reg_readings, range_v=DC_RANGE_V, lead_half_width_v=None)
    )
    reg_expanded_v = expanded_uncertainty(per_reading * math.sqrt(2.0))
    line_reg_uncertainty_pct = 100.0 * reg_expanded_v / VOUT_NOM_V
    figures.append(
        Figure("marginal-line board regulation uncertainty (percentage points)", f"{line_reg_uncertainty_pct:.4f}")
    )
    line_reg_verdicts: dict[str, str] = {}
    for tamb, pct in line_reg_pct.items():
        figures.append(Figure(f"marginal-line board regulation at {tamb} degC (%)", f"{pct:.3f}"))
        line_reg_verdicts[tamb] = guarded_verdict(pct, line_reg_uncertainty_pct, upper=LINE_REG_MAX_PCT)

    return Results(
        figures=tuple(figures),
        corner_margins_mv=corner_margins_mv,
        thin_serial=thin_serial,
        corner_expanded_uncertainty_uv=corner_expanded_uv,
        corner_verdict=corner_verdict,
        line_reg_pct=line_reg_pct,
        line_reg_uncertainty_pct=line_reg_uncertainty_pct,
        line_reg_verdicts=line_reg_verdicts,
    )


def _figures_block(figures: Sequence[Figure]) -> str:
    return "\n".join(f"- {figure.label}: {figure.text}" for figure in figures)


def unsupported_numbers(draft: str, figures: Sequence[Figure]) -> tuple[str, ...]:
    """Every numeric token in `draft` that is not, character for character, one of `figures`'
    own text. Order-preserving and may repeat a token, so a report that leans on one bad number
    three times shows all three.

    This is the whole safety argument for making one model call write a report nobody re-derives
    by hand: it costs one regular-expression scan and a set lookup, and it is a pass or a fail,
    never a judgment call.
    """
    allowed = {figure.text for figure in figures}
    return tuple(token for token in NUMBER_RE.findall(draft) if token not in allowed)


@dataclass(frozen=True)
class Report:
    """What `run` hands back: the model's drafted prose, and what the check found in it.

    `text` is the model's draft whichever way the check comes out; deciding what happens to a
    draft the check rejects is a person's job, not this function's, so `unsupported` names the
    exact tokens that failed instead of the function silently discarding or "fixing" the draft.
    """

    text: str
    figures: tuple[Figure, ...]
    unsupported: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.unsupported


def run(
    notes: str,
    model: Model,
    tracer: Tracer,
    *,
    csv_path: Path = CHARACTERIZATION_CSV,
) -> Report:
    """One model call. `notes` is free text a requester may add (which finding to lead with, a
    house style note); it is appended to the prompt and never reaches the check, because it never
    contributes a number of its own.
    """
    results = compute_results(csv_path)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Compute the figures from the characterization data",
        detail=(
            f"{len(results.figures)} figures; thin-margin board {results.thin_serial} "
            f"({results.corner_margins_mv[results.thin_serial]:.1f} mV, {results.corner_verdict})"
        ),
    )

    notebook = load_bench_documents()["characterization-notebook"]
    tracer.record(kind="code", decided_by="code", title="Load the session notebook", detail=f"{len(notebook)} characters")

    user_parts = [
        f"Figures (use only these numbers, exactly as written):\n{_figures_block(results.figures)}",
        f"Notebook:\n{notebook}",
    ]
    if notes and notes.strip():
        user_parts.append(f"Additional guidance from the requester: {notes.strip()}")
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content="\n\n".join(user_parts)),
    ]
    tracer.record(
        kind="code",
        decided_by="code",
        title="Build the prompt with the figures and the notebook",
        detail=f"{len(results.figures)} figures, {len(notebook)}-character notebook",
    )

    completion = model.complete(messages, max_tokens=700)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model to draft the report",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )

    unsupported = unsupported_numbers(completion.text, results.figures)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check the draft's numbers against the figures",
        detail="every number is supported" if not unsupported else f"unsupported: {', '.join(unsupported)}",
    )
    return Report(text=completion.text, figures=results.figures, unsupported=unsupported)
