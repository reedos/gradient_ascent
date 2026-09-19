"""Generate the SRB-5030 production test data, byte for byte, from one seed.

Three files land in `evals/bench/data/`:

  production-run-2026-08.csv  about 200 units x 8 test steps, the main run
  soak-2026-08-27.csv         three units held at full load for 90 minutes
  retest-2026-08-31.csv       a short retest export with two defects of its own

The board model is `examples.common.bench.Dut`, the same one the simulated instruments answer
from. That is deliberate: an example that queries the instruments and an example that reads these
CSVs are looking at the same regulator, with the same regulation coefficients, the same loss
terms and the same ripple arithmetic. Unit-to-unit variation is seeded here, not there, because a
`Dut` is one board and this script makes a population of them.

Six stories are planted in the data. `docs/THE-BENCH.md` is the answer key, and
`tests/test_bench_data.py` proves each one is really present, and that rerunning this script
reproduces all three files byte for byte.

    python -m evals.bench.make_data [output_dir]
"""
from __future__ import annotations

import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from examples.common.bench import Dut

DATA_DIR = Path(__file__).resolve().parent / "data"

SEED = 20260824
UNIT_COUNT = 200
LOTS = ("L2608A", "L2608B", "L2608C", "L2608D")
FIXTURES = ("FIX-01", "FIX-02", "FIX-03", "FIX-04")

#: The lot whose output capacitors are 16 V X5R parts instead of the 25 V X7R on the bill of
#: materials. At 5 V bias they derate to roughly 3.3 uF each instead of roughly 12 uF, so the
#: effective output capacitance falls from about 24 uF to about 6.6 uF and the ripple roughly
#: doubles. Most units still pass; the capability index does not.
MARGINAL_LOT = "L2608B"
MARGINAL_COUT_F = 6.6e-6
MARGINAL_COUT_SD_F = 0.8e-6
NORMAL_COUT_F = 24.0e-6
NORMAL_COUT_SD_F = 1.6e-6

#: The fixture whose DMM channel 2 carries a stale calibration offset after a relay repair. It
#: shifts every absolute DC voltage reading on that path by -25 mV. Only the VOUT step reads an
#: absolute voltage through it; the two regulation steps are differences, and a fixed offset
#: cancels in a difference, which is why exactly one step looks wrong.
OFFSET_FIXTURE = "FIX-03"
FIXTURE_OFFSET_V = -0.030

#: Boards with a planted defect, by unit index (1-based, matching the serial number).
SHORTED_UNITS = (37, 154)  # solder bridge at the output terminal: step 1 fails, run aborts
DEAD_UNITS = (63, 178)  # no output at all
HIGH_IQ_UNIT = 92  # leaky bootstrap capacitor
HIGH_LOSS_UNIT = 121  # cold solder joint at the inductor: efficiency fails, board runs hot

#: Four days, two shifts a day, 25 units a shift. Lot, fixture, day and shift are deliberately
#: crossed rather than nested: the fixture changes every unit and the lot every four, so each
#: lot gets each fixture an equal number of times and neither one can stand in for the other.
#: Grouping by lot finds the capacitor problem, grouping by fixture finds the calibration
#: problem, and grouping by day or by shift finds nothing, which is the answer a yield
#: investigation needs to be able to give as much as the other two.
FIRST_DAY = datetime(2026, 8, 24)
UNITS_PER_SHIFT = 25
SHIFT_START_HOUR = {"A": 7, "B": 15}
SHIFT_START_MINUTE = 12
MINUTES_PER_UNIT = 7

#: Step number, measurement name, unit, lower limit, upper limit, decimal places. These are the
#: limits in `evals/bench/corpus/srb5030-test-spec.md` section 4, and nothing else may set them.
STEPS = (
    (1, "R_OUT", "ohm", 500.0, None, 1),
    (2, "IQ_NL", "mA", None, 25.0, 2),
    (3, "VOUT", "V", 4.950, 5.050, 4),
    (4, "LINE_REG", "%", None, 0.30, 3),
    (5, "LOAD_REG", "%", None, 0.80, 3),
    (6, "EFF_FL", "%", 88.0, None, 2),
    (7, "RIPPLE", "mV", None, 50.0, 1),
    (8, "I_LIM", "A", 3.70, 5.00, 2),
)

HEADER = [
    "serial",
    "lot",
    "fixture",
    "shift",
    "timestamp",
    "step",
    "measurement",
    "value",
    "unit",
    "lower_limit",
    "upper_limit",
    "result",
    "notes",
]

#: Operator notes, of the quality operator notes actually have. Index into this by the failure
#: kind; `None` means the operator wrote nothing, which is the most common case.
NOTES = {
    "short": ["no continuity check, reads 0.4 ohm out to gnd - bridge at J2?", "shorted"],
    "dead": ["dead. no vout at all, u1 not switching", "?"],
    "iq": ["draws 31ma with nothing on the output. boot cap?"],
    "ripple": ["ripple 52mv", "FAIL", "over on ripple, 3rd one from this reel"],
    "vout_fixture": [
        "low again on fix3, thats 3 today",
        None,
        "4.94 on fixture 3, moved to fixture 1 and it passed",
        None,
        "fix3",
    ],
    "vout_low": ["vout 4.943, below limit", None],
    "eff": ["eff 80pct, L1 hot to touch after 30s"],
}

#: Notes on units that passed, which is where half the noise in real notes lives.
PASSING_NOTES = {
    18: "retested, first run aborted when the operator bumped the lid",
    77: "ripple 44mv, passed but marginal",
    145: "beeps",
}


def _round_half_up(value: float, places: int) -> float:
    """Round the way a test executive writes a number to a report, not the way Python does.

    Python rounds a tie to even, so 4.9985 at four places is 4.998 in one build and could be
    4.9985 -> 4.999 under a different float. Doing it explicitly keeps the CSV stable.
    """
    factor = 10.0**places
    scaled = value * factor
    return (int(scaled + 0.5) if scaled >= 0 else -int(-scaled + 0.5)) / factor


def _fmt(value: float, places: int) -> str:
    return f"{_round_half_up(value, places):.{places}f}"


def _limit(value: float | None, places: int) -> str:
    return "" if value is None else f"{value:.{places}f}"


def _verdict(value: float, low: float | None, high: float | None) -> str:
    if low is not None and value < low:
        return "FAIL"
    if high is not None and value > high:
        return "FAIL"
    return "PASS"


class Unit:
    """One board on the line: its serial, its lot, its fixture, and the model of the board."""

    def __init__(self, index: int, rng: random.Random) -> None:
        self.index = index
        self.serial = f"SRB5030-2608-{index:04d}"
        self.lot = LOTS[((index - 1) // 4) % 4]
        self.fixture = FIXTURES[(index - 1) % 4]
        self.day = (index - 1) // (2 * UNITS_PER_SHIFT)
        self.shift = "A" if ((index - 1) // UNITS_PER_SHIFT) % 2 == 0 else "B"
        self.shorted = index in SHORTED_UNITS
        self.dead = index in DEAD_UNITS

        cout_mean = MARGINAL_COUT_F if self.lot == MARGINAL_LOT else NORMAL_COUT_F
        cout_sd = MARGINAL_COUT_SD_F if self.lot == MARGINAL_LOT else NORMAL_COUT_SD_F
        # Every random draw happens here, in this order, for every unit: the seed then fixes the
        # whole run no matter which branches a unit takes later.
        self.vout_offset_v = rng.gauss(0.0, 0.012)
        self.cout_f = max(1.0e-6, rng.gauss(cout_mean, cout_sd))
        self.ilim_a = rng.gauss(4.20, 0.12)
        self.ringing_v = max(0.004, rng.gauss(0.0125, 0.0012))
        self.r_loss_ohm = max(0.03, rng.gauss(0.065, 0.0025))
        self.noise = [rng.gauss(0.0, 1.0) for _ in range(8)]

        if index == HIGH_LOSS_UNIT:
            self.r_loss_ohm = 0.350
        self.dut = Dut(
            serial=self.serial,
            vout_offset_v=self.vout_offset_v,
            cout_f=self.cout_f,
            ilim_a=self.ilim_a,
            r_loss_ohm=self.r_loss_ohm,
            ringing_v=self.ringing_v,
            dead=self.dead,
            output_res_ohm=0.4 if self.shorted else 3300.0,
        )

    @property
    def dmm_offset_v(self) -> float:
        return FIXTURE_OFFSET_V if self.fixture == OFFSET_FIXTURE else 0.0

    def timestamp(self, step: int) -> str:
        position = (self.index - 1) % UNITS_PER_SHIFT
        start = (
            FIRST_DAY
            + timedelta(days=self.day)
            + timedelta(hours=SHIFT_START_HOUR[self.shift], minutes=SHIFT_START_MINUTE)
            + timedelta(minutes=MINUTES_PER_UNIT * position)
        )
        return (start + timedelta(seconds=7 * (step - 1))).strftime("%Y-%m-%dT%H:%M:%S")

    # -- the eight measured values -----------------------------------------

    def r_out_ohm(self) -> float:
        return self.dut.output_res_ohm * (1.0 + 0.03 * self.noise[0])

    def iq_nl_ma(self) -> float:
        if self.index == HIGH_IQ_UNIT:
            return 31.4 + 0.4 * self.noise[1]
        if self.dead:
            return 0.62 + 0.05 * self.noise[1]
        return self.dut.iin_a(24.0, 0.0) * 1000.0 + 0.4 * self.noise[1]

    def vout_v(self) -> float:
        return self.dut.vout_v(24.0, 1.0) + self.dmm_offset_v + 0.0008 * self.noise[2]

    def line_reg_pct(self) -> float:
        """Regulation is a difference of two readings, so a fixed channel offset cancels here.

        A dead board reads zero at both input voltages and so scores near zero, which passes.
        That is not a bug in the generator: a difference-based limit cannot tell a perfectly
        regulated board from a board with no output, which is why step 3 measures the absolute
        voltage first and why the test spec runs the steps in the order it does.
        """
        low = self.dut.vout_v(9.0, 1.0) + 0.0008 * self.noise[3]
        high = self.dut.vout_v(32.0, 1.0) + 0.0008 * self.noise[2]
        return abs(high - low) / 5.000 * 100.0

    def load_reg_pct(self) -> float:
        light = self.dut.vout_v(24.0, 0.1) + 0.0008 * self.noise[4]
        heavy = self.dut.vout_v(24.0, 3.0) + 0.0008 * self.noise[3]
        return abs(light - heavy) / 5.000 * 100.0

    def eff_fl_pct(self) -> float:
        return max(0.0, self.dut.efficiency_pct(24.0, 3.0) + 0.25 * self.noise[5])

    def ripple_mv(self) -> float:
        return max(0.0, self.dut.measured_ripple_v(24.0, 3.0) * 1000.0 + 1.2 * self.noise[6])

    def i_lim_a(self) -> float:
        """The lowest load current, in 50 mA steps, at which the output falls below 4.900 V."""
        current = 3.50
        while current < 6.00:
            if self.dut.vout_v(24.0, current) < 4.900:
                return current
            current = round(current + 0.05, 2)
        return 6.00

    def value(self, step: int) -> float:
        return {
            1: self.r_out_ohm,
            2: self.iq_nl_ma,
            3: self.vout_v,
            4: self.line_reg_pct,
            5: self.load_reg_pct,
            6: self.eff_fl_pct,
            7: self.ripple_mv,
            8: self.i_lim_a,
        }[step]()


def _note_for(unit: Unit, step: int, result: str, counters: dict[str, int]) -> str:
    if result == "PASS":
        return PASSING_NOTES.get(unit.index, "") if step == 3 else ""
    kind = None
    if step == 1:
        kind = "short"
    elif step == 2:
        kind = "iq"
    elif step == 3:
        if unit.dead:
            kind = "dead"
        elif unit.fixture == OFFSET_FIXTURE:
            kind = "vout_fixture"
        else:
            kind = "vout_low"
    elif step == 6:
        kind = "eff" if unit.index == HIGH_LOSS_UNIT else None
    elif step == 7:
        kind = "ripple"
    if kind is None:
        return ""
    pool = NOTES[kind]
    index = counters.get(kind, 0)
    counters[kind] = index + 1
    note = pool[index % len(pool)]
    return note or ""


def build_production_rows() -> list[list[str]]:
    rng = random.Random(SEED)
    rows: list[list[str]] = []
    counters: dict[str, int] = {}
    for index in range(1, UNIT_COUNT + 1):
        unit = Unit(index, rng)
        for step, name, unit_label, low, high, places in STEPS:
            value = unit.value(step)
            result = _verdict(_round_half_up(value, places), low, high)
            rows.append(
                [
                    unit.serial,
                    unit.lot,
                    unit.fixture,
                    unit.shift,
                    unit.timestamp(step),
                    str(step),
                    name,
                    _fmt(value, places),
                    unit_label,
                    _limit(low, places),
                    _limit(high, places),
                    result,
                    _note_for(unit, step, result, counters),
                ]
            )
            if step == 1 and result == "FAIL":
                # A board that reads a short at the output is never powered: the sequence stops
                # here, which is why two serials have one row and not eight.
                break
    return rows


# ---------------------------------------------------------------------------
# Soak test
# ---------------------------------------------------------------------------

SOAK_HEADER = ["serial", "timestamp", "elapsed_min", "vin_v", "iout_a", "vout_v", "tcase_c"]
SOAK_START = datetime(2026, 8, 27, 9, 0, 0)
SOAK_MINUTES = 90
SOAK_INTERVAL_MIN = 5
SOAK_UNITS = ("SRB5030-2608-0044", "SRB5030-2608-0121", "SRB5030-2608-0166")
#: The middle serial is the one with the cold solder joint at the inductor. It is the unit whose
#: output walks down and whose case temperature keeps climbing after the other two have settled.
SOAK_DRIFTER = "SRB5030-2608-0121"


def build_soak_rows() -> list[list[str]]:
    rng = random.Random(SEED + 1)
    rows: list[list[str]] = []
    for serial in SOAK_UNITS:
        drifts = serial == SOAK_DRIFTER
        offset = rng.gauss(0.0, 0.010)
        for minute in range(0, SOAK_MINUTES + 1, SOAK_INTERVAL_MIN):
            settle = 1.0 - 2.718281828459045 ** (-minute / 12.0)
            if drifts:
                # Rising junction temperature at a resistive joint: the drop grows as it heats,
                # and the case temperature never settles the way the other two do.
                vout = 4.979 + offset - 0.065 * settle - 0.00012 * minute
                tcase = 24.5 + 52.0 * settle + 0.17 * minute
            else:
                vout = 4.979 + offset - 0.0012 * settle
                tcase = 24.5 + 36.0 * settle
            vout += 0.0006 * rng.gauss(0.0, 1.0)
            tcase += 0.15 * rng.gauss(0.0, 1.0)
            rows.append(
                [
                    serial,
                    (SOAK_START + timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%S"),
                    str(minute),
                    "24.000",
                    "3.000",
                    _fmt(vout, 4),
                    _fmt(tcase, 1),
                ]
            )
    return rows


# ---------------------------------------------------------------------------
# Retest export
# ---------------------------------------------------------------------------

RETEST_HEADER = ["serial", "lot", "fixture", "timestamp", "measurement", "value_v", "result"]
RETEST_START = datetime(2026, 8, 31, 13, 40, 0)
#: The serial the retest export files under a lot it is not in. Whoever pasted the sheet
#: together took the lot from the row above it.
MIXED_UP_SERIAL = "SRB5030-2608-0142"
MIXED_UP_LOT = "L2608A"
#: Passing units pulled into the retest as a control group, by serial number.
RETEST_CONTROLS = (9, 23, 61, 88, 104, 142, 150, 163, 187, 199)


def build_retest_rows(production: list[list[str]]) -> list[list[str]]:
    """Retest of every unit that failed step 3, plus a few that passed, on fixture FIX-01.

    Two things are wrong with this file, and both are the kind of thing that is wrong with a real
    one. The `value_v` column holds millivolts. And one serial is filed under a lot it is not in.
    """
    rng = random.Random(SEED + 2)
    failures = [r for r in production if r[6] == "VOUT" and r[11] == "FAIL"]
    controls = {f"SRB5030-2608-{i:04d}" for i in RETEST_CONTROLS}
    passers = [
        r for r in production if r[6] == "VOUT" and r[11] == "PASS" and r[0] in controls
    ]
    sample = failures + passers
    rows: list[list[str]] = []
    for offset_min, row in enumerate(sample):
        serial, lot = row[0], row[1]
        if serial == MIXED_UP_SERIAL:
            lot = MIXED_UP_LOT
        # Retested on FIX-01, which has no channel offset, so a unit that failed only because of
        # the fixture reads normally here. A genuinely dead board still reads zero.
        original = float(row[7])
        if original == 0.0:
            millivolts = 0.0
        else:
            corrected = original + (0.025 if row[2] == OFFSET_FIXTURE else 0.0)
            millivolts = (corrected + 0.0009 * rng.gauss(0.0, 1.0)) * 1000.0
        result = "PASS" if 4950.0 <= millivolts <= 5050.0 else "FAIL"
        rows.append(
            [
                serial,
                lot,
                "FIX-01",
                (RETEST_START + timedelta(minutes=3 * offset_min)).strftime("%Y-%m-%dT%H:%M:%S"),
                "VOUT",
                _fmt(millivolts, 1),
                result,
            ]
        )
    return rows


# ---------------------------------------------------------------------------


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write one file with LF line endings and no trailing blank line, on any platform."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def generate(out_dir: Path = DATA_DIR) -> dict[str, int]:
    """Write all three files. Returns the row count of each, not counting the header."""
    production = build_production_rows()
    soak = build_soak_rows()
    retest = build_retest_rows(production)
    write_csv(out_dir / "production-run-2026-08.csv", HEADER, production)
    write_csv(out_dir / "soak-2026-08-27.csv", SOAK_HEADER, soak)
    write_csv(out_dir / "retest-2026-08-31.csv", RETEST_HEADER, retest)
    return {
        "production-run-2026-08.csv": len(production),
        "soak-2026-08-27.csv": len(soak),
        "retest-2026-08-31.csv": len(retest),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    out_dir = Path(args[0]).resolve() if args else DATA_DIR
    counts = generate(out_dir)
    for name, count in counts.items():
        print(f"{name}: {count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
