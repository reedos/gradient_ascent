"""Generate the revision C characterization data, byte for byte, from one seed.

One file lands in `evals/bench/data/`:

  characterization-2026-09.csv   five prototype boards, swept over line, load and temperature

This is the engineering-test half of the bench's data. `make_data.py` writes a production run:
two hundred units, eight fixed steps, a pass or a fail against limits. This writes what design
verification actually produces: a handful of boards, a sweep over every corner, several readings
at every point, and margins rather than verdicts. The two share the board model
(`examples.common.bench.Dut`) and nothing else, including the random stream. That is deliberate
and `tests/test_bench_data.py` depends on it: the three production CSVs must reproduce byte for
byte no matter what is added here, so this module has its own seed and never touches
`make_data`'s.

Five boards, four input voltages, three load currents, three ambients, five readings a point:
900 rows. Four stories are planted in it, `docs/THE-BENCH.md` is the answer key, and
`tests/test_bench_characterization.py` proves each one is there and that the things a reader
might otherwise blame are not:

1. One board holds a fifth of the margin the others hold, at one corner only, with no single
   parameter out of specification.
2. One board's line regulation lands inside its limit by less than the measurement uncertainty
   at one ambient, which is the case guardbanding exists for.
3. Sixty readings are noisier than the rest because the meter was left on the 100 V range. It
   follows the range column, not a board and not a corner.
4. One point is recorded at an input voltage it was not taken at. The input current says so.

    python -m evals.bench.make_characterization [output_dir]
"""
from __future__ import annotations

import csv
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from examples.common.bench import (
    LINE_COEFF_V_PER_V,
    LOAD_COEFF_V_PER_A,
    Dut,
    reading_resolution,
)
from evals.bench.make_data import _fmt, _round_half_up, write_csv

DATA_DIR = Path(__file__).resolve().parent / "data"

#: Its own seed, and nothing in this module ever draws from `make_data`'s generator.
SEED = 20260914

REVISION = "C"

#: The sweep. Four input voltages: the 9.0 V minimum, the 12.0 V and 24.0 V rails customers
#: actually run, and the 32.0 V ceiling ECN-2608-04 sets for boards in the field. Three load
#: currents and three ambients, the outer two of which are the datasheet's own recommended
#: operating limits.
VIN_V = (9.0, 12.0, 24.0, 32.0)
IOUT_A = (0.100, 1.000, 3.000)
#: Session order, not sorted order: one chamber setting per day, and the room-temperature day
#: first because it is the one that decides whether the sweep script works at all.
AMBIENTS_C = (25.0, 70.0, 0.0)
REPEATS = 5

#: One day per ambient, starting at 08:30 after the half hour of instrument warm-up
#: `calibration-procedure.md` section 4 requires.
SESSION_START = {
    25.0: datetime(2026, 9, 14, 8, 30, 0),
    70.0: datetime(2026, 9, 15, 8, 30, 0),
    0.0: datetime(2026, 9, 16, 8, 30, 0),
}
READING_INTERVAL_S = 6
POINT_SETTLE_S = 30
BOARD_CHANGE_S = 360

#: The meter range the sweep script selects, and the one it was left on for part of the first
#: day. Both are real ranges; nothing about the wrong one is an error, which is the point.
NOMINAL_RANGE_V = 10.0
SLIPPED_RANGE_V = 100.0

#: Reading noise, one standard deviation. The 100 V range is noisier in the same proportion its
#: specification is looser, and its least significant digit is ten times coarser.
NOISE_V = 60e-6
SLIPPED_NOISE_V = 400e-6
#: The supply's current readback resolves 0.1 mA and is specified to +/-(0.1% + 3 mA), so its
#: scatter is two orders of magnitude coarser than the meter's. Nothing here reports it as a
#: precise number.
NOISE_IIN_A = 0.0008


@dataclass(frozen=True)
class BoardSpec:
    """One hand-built revision C prototype: what makes this board different from the others.

    A production population varies around the design's typical numbers. Five prototypes do not:
    each one is its own set of coefficients, and the whole reason to characterize is that the
    typical board tells you nothing about the corners of the population.
    """

    serial: str
    vout_offset_v: float
    load_coeff_v_per_a: float = LOAD_COEFF_V_PER_A
    line_coeff_v_per_v: float = LINE_COEFF_V_PER_V
    #: Line coefficient by ambient, for the one board whose line regulation moves with
    #: temperature. Empty means the coefficient above holds at every ambient.
    line_coeff_by_c: tuple[tuple[float, float], ...] = field(default_factory=tuple)
    note: str = ""

    def dut(self, tamb_c: float) -> Dut:
        line = dict(self.line_coeff_by_c).get(tamb_c, self.line_coeff_v_per_v)
        return Dut(
            serial=self.serial,
            vout_offset_v=self.vout_offset_v,
            load_coeff_v_per_a=self.load_coeff_v_per_a,
            line_coeff_v_per_v=line,
        )


#: Board 3 is the margin story. Its output sits 30 mV low, its load coefficient is 11.5 mV/A
#: against the design's 7.0, and its line coefficient is 0.50 mV/V against 0.25. Not one of those
#: is out of specification on its own. At 9 V in, 3 A out and 70 degC they stack.
THIN_MARGIN_SERIAL = "SRB5030-2609-0003"

#: Board 5 is the uncertainty story. Its line regulation is close to the 0.300 percent limit and
#: moves with temperature: comfortably inside at 0 degC, inside by less than the measurement
#: uncertainty at 25 degC, and outside it at 70 degC.
MARGINAL_LINE_SERIAL = "SRB5030-2609-0005"

BOARDS = (
    BoardSpec("SRB5030-2609-0001", 0.0042, note="typical"),
    BoardSpec("SRB5030-2609-0002", -0.0115, note="typical"),
    BoardSpec(
        THIN_MARGIN_SERIAL,
        -0.0300,
        load_coeff_v_per_a=0.01150,
        line_coeff_v_per_v=0.00050,
        note="low output, high load and line coefficients, all inside their own limits",
    ),
    BoardSpec("SRB5030-2609-0004", 0.0088, note="typical"),
    BoardSpec(
        MARGINAL_LINE_SERIAL,
        0.0021,
        line_coeff_by_c=((0.0, 0.000580), (25.0, 0.000653), (70.0, 0.000725)),
        note="line regulation close to its limit, and temperature dependent",
    ),
)

#: The point recorded at a condition it was not taken at: board 1, 25 degC, the 12.0 V row at
#: 3.000 A. The supply was still at 24.0 V from the block before it. The output voltage barely
#: notices, because that is what a regulator is for; the input current halves.
WRONG_CONDITION = (25.0, "SRB5030-2609-0001", 12.0, 3.000)
WRONG_CONDITION_ACTUAL_VIN_V = 24.0

#: The block the meter spent on the 100 V range: from the middle of the third board's 25 degC
#: sweep to the middle of the fourth board's. It crosses a board boundary on purpose. A window
#: that sat inside one board would be indistinguishable from a board with a noise problem, and
#: the lesson of this story is that the scatter belongs to the measurement and not to any board.
SLIPPED_AMBIENT_C = 25.0
SLIPPED_FROM = (2, 30)  # (board index, reading index within that board's sweep), inclusive
SLIPPED_TO = (3, 29)  # inclusive

HEADER = [
    "serial",
    "revision",
    "tamb_c",
    "vin_v",
    "iout_a",
    "reading_n",
    "timestamp",
    "meter_range_v",
    "vout_v",
    "iin_a",
]

READINGS_PER_BOARD = len(VIN_V) * len(IOUT_A) * REPEATS


def _on_slipped_range(tamb_c: float, board_index: int, reading_index: int) -> bool:
    """True for the readings taken while the meter was left on the 100 V range."""
    if tamb_c != SLIPPED_AMBIENT_C:
        return False
    position = (board_index, reading_index)
    return SLIPPED_FROM <= position <= SLIPPED_TO


def _quantize(value: float, range_v: float) -> float:
    """Round a reading to the meter's least significant digit on this range.

    The 100 V range resolves 100 uV, so every reading taken on it ends in a zero in the fifth
    decimal place. That is visible in the file, and it is the cheapest clue to the story.
    """
    resolution = reading_resolution(range_v)
    return _round_half_up(value / resolution, 0) * resolution


def build_rows() -> list[list[str]]:
    rng = random.Random(SEED)
    rows: list[list[str]] = []
    for tamb_c in AMBIENTS_C:
        clock = SESSION_START[tamb_c]
        for board_index, board in enumerate(BOARDS):
            if board_index:
                clock += timedelta(seconds=BOARD_CHANGE_S)
            dut = board.dut(tamb_c)
            reading_index = 0
            for vin_v in VIN_V:
                for iout_a in IOUT_A:
                    clock += timedelta(seconds=POINT_SETTLE_S)
                    labelled = (tamb_c, board.serial, vin_v, iout_a)
                    actual_vin_v = (
                        WRONG_CONDITION_ACTUAL_VIN_V if labelled == WRONG_CONDITION else vin_v
                    )
                    for repeat in range(1, REPEATS + 1):
                        slipped = _on_slipped_range(tamb_c, board_index, reading_index)
                        range_v = SLIPPED_RANGE_V if slipped else NOMINAL_RANGE_V
                        noise_v = SLIPPED_NOISE_V if slipped else NOISE_V
                        # Both draws happen for every row, in this order, whatever the row is:
                        # the seed then fixes the whole file no matter which branches a row takes.
                        vout_noise = rng.gauss(0.0, 1.0)
                        iin_noise = rng.gauss(0.0, 1.0)
                        vout = dut.vout_at_c(actual_vin_v, iout_a, tamb_c) + noise_v * vout_noise
                        iin = dut.iin_at_c(actual_vin_v, iout_a, tamb_c) + NOISE_IIN_A * iin_noise
                        rows.append(
                            [
                                board.serial,
                                REVISION,
                                _fmt(tamb_c, 1),
                                _fmt(vin_v, 1),
                                _fmt(iout_a, 3),
                                str(repeat),
                                clock.strftime("%Y-%m-%dT%H:%M:%S"),
                                _fmt(range_v, 1),
                                _fmt(_quantize(vout, range_v), 5),
                                _fmt(max(0.0, iin), 4),
                            ]
                        )
                        clock += timedelta(seconds=READING_INTERVAL_S)
                        reading_index += 1
    return rows


def generate(out_dir: Path = DATA_DIR) -> dict[str, int]:
    """Write the characterization file. Returns its row count, not counting the header."""
    rows = build_rows()
    write_csv(out_dir / "characterization-2026-09.csv", HEADER, rows)
    return {"characterization-2026-09.csv": len(rows)}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    out_dir = Path(args[0]).resolve() if args else DATA_DIR
    for name, count in generate(out_dir).items():
        print(f"{name}: {count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
