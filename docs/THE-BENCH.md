# The bench

Every general example on this site runs on one synthetic world: "Halvorsen," a fictional appliance
brand, in `evals/corpus/`. The engineering examples run on a second one, described here. It is a
small electronics test bench: one circuit board, four instruments, a production test specification,
a month of test data and the documents an engineer actually works from.

This file is the design of that bench and the answer key to the data hidden in it. It is written
to be read, by the people writing the engineering recipe pages and by anyone who wants to check
that the numbers hold up.

## Everything here is invented

Orbeck Power Systems, the SRB-5030 regulator board, Maridun Instruments, Tarnley Test Systems, the
MDN-4010, the MDN-6100, the TRN-2400, the TRN-1102 and every internal part number of the form
`OPS-nnnn` are invented for this site. No real company, product or part number is used as if it
were ours.

Each of those names was searched on the open web before it was used, and none of them returned a
company, a product or a part with that name. The searches were run in September 2026. Short
alphanumeric strings collide with something somewhere, so the check is on the full designation:
"Orbeck SRB-5030," "Maridun MDN-4010," "Tarnley TRN-2400," "Tarnley TRN-1102." Internal part
numbers only ever appear inside Orbeck's own documents, where they are Orbeck's internal numbers
by definition.

What is not invented is the engineering. SCPI, IEEE 488.2, the buck converter ripple equations,
Ohm's law, capacitance derating under DC bias and the standard formula for Cpk are all real, are
used correctly, and are used because an engineer reading these pages will check them. Every figure
below is computed from the constants in `examples/common/bench.py` rather than chosen to look
plausible, and the arithmetic is shown so it can be rechecked.

## The device under test: Orbeck SRB-5030

A small synchronous buck regulator board: wide DC input, fixed 5 V output, 3 A.

| Parameter | Value |
| --- | --- |
| Input voltage | 9.0 V to 36.0 V (32.0 V on revisions A and B, see the ECN below) |
| Absolute maximum input | 40.0 V |
| Output voltage | 5.000 V, +/-2% over line, load and temperature |
| Output current | 0 to 3.0 A |
| Switching frequency | 500 kHz |
| Inductor | 10 uH, 4.5 A saturation, 28 mohm DCR |
| Output capacitance | two 22 uF 25 V X7R parts, about 24 uF effective at 5 V bias |
| Line regulation | 0.14% typical over 9 V to 36 V at 1 A, 0.30% max |
| Load regulation | 0.41% typical over 0.1 A to 3.0 A at 24 V, 0.80% max |
| Output ripple | 22 mV peak to peak typical at 24 V in, 3 A out, 50 mV max |
| Efficiency | 92.5% at 24 V in, 3 A out; 95.8% peak at 12 V in, 1 A out |
| Thermal | 42 degC/W junction to ambient, 125 degC junction max, shutdown at 145 degC |
| Revisions | A (pilot), B (production), C (in qualification) |

The full document is `evals/bench/corpus/srb5030-datasheet.md`.

### Where the numbers come from

The output voltage is set by a 0.800 V reference and a 105 kohm / 20.0 kohm divider:
`0.800 * (1 + 105/20) = 5.000 V` exactly. Both values are E96, so the nominal needs no trim.

Efficiency is output power over input power at the terminals, and the datasheet prints both
currents so it can be checked rather than believed. At 24 V in and 3 A out the board draws
0.6730 A, so `Pin = 16.151 W`, `Pout = 4.979 * 3 = 14.937 W`, and `14.937 / 16.151 = 92.5%`.
Efficiency is higher at 12 V in than at 24 V in because switching loss grows with input voltage
while the duty cycle falls, and it drops at light load because the fixed quiescent draw is a bigger
share of a smaller output. The loss model behind the whole table is three terms: quiescent
(`Vin * (4.0 mA + 0.30 mA/V * Vin)`), switching (`0.005 W/VA * Vin * Iout`) and conduction
(`0.065 ohm * Iout^2`).

Ripple is computed, not assumed. At 24 V in and 3 A out the duty cycle is `4.979 / 24 = 0.207` and
the peak-to-peak inductor ripple current is

    dIL = (24.0 - 4.979) * 0.207 / (10 uH * 500 kHz) = 0.79 A

which is 26% of the 3 A rating, in the usual 20% to 40% range, and puts the peak inductor current
at 3.39 A. Against the 4.5 A saturation rating that is a margin of 1.33, which clears the 1.3 the
design rules require and does not clear it by much. That ripple current into 24 uF gives
`0.79 / (8 * 24 uF * 500 kHz) = 8.2 mV`, plus `0.79 * 1.5 mohm = 1.2 mV` of ESR: about 9.4 mV of
inductor-and-capacitor ripple.

The 22 mV typical figure is larger because a probe at the output test point also sees
switching-edge ringing. Both numbers are in the datasheet, labeled, because the difference between
them is the single most common reason two benches disagree about a ripple measurement.

### The conflict the site needs

`ecn-2608-04.md` contradicts the datasheet on exactly one number. The datasheet says the maximum
input voltage is 36.0 V. The ECN says 32.0 V, for revisions A and B only.

The reason is a derating rule. The input capacitors are 50 V X7R parts, and design rule DR-14
requires a ceramic on a DC rail to be rated at least 1.5 times the maximum steady-state rail
voltage. `50 / 1.5 = 33.3 V`, so a 50 V part supports a 33.3 V rail and not a 36 V one. Revision C
fits 63 V parts (`63 / 1.5 = 42 V`) and restores 36 V.

So "what is the maximum input voltage of an SRB-5030" has no single right answer. It has a right
answer per revision, and a reader who does not notice the ECN gets it wrong for the boards that are
actually in the field. The test specification already followed the ECN: revision 3 changed the line
regulation sweep from 36 V to 32 V. The datasheet has not been reissued. That is what a real
document set looks like, and it is what `ask-the-datasheet` exists to teach.

## The instruments

Four, from two invented vendors, each behind one `send(command) -> str` method in
`examples/common/bench.py`. Each has a programming manual in the corpus, and the simulation
implements what the manual documents and nothing else: an undocumented command returns nothing and
leaves `-113,"Undefined header"` in the error queue.

| Instrument | Role | Range | Resolution | Accuracy |
| --- | --- | --- | --- | --- |
| Maridun MDN-4010 | programmable DC supply | 0 to 40 V, 0 to 10 A, 200 W | 1 mV, 1 mA programming | +/-(0.05% + 10 mV), +/-(0.1% + 5 mA) |
| Maridun MDN-6100 | 6 1/2 digit multimeter | 100 mV to 1000 V DC, 100 ohm to 100 Mohm | 100 nV on the lowest range | +/-(0.0035% of reading + 0.0005% of range) on 10 V DC |
| Tarnley TRN-2400 | electronic load | 0 to 60 V, 0 to 30 A, 300 W | 1 mA CC | +/-(0.1% + 10 mA) CC |
| Tarnley TRN-1102 | oscilloscope | 100 MHz, 1 GSa/s, 8 bit | vertical scale / 32 per bit | +/-2% of amplitude |

The scope is here because ripple is a scope measurement. The MDN-6100's AC volts function stops at
300 kHz, and most of what makes a switching regulator's measured ripple bigger than its computed
ripple is above that. Using the meter instead would be the wrong instrument, stated confidently,
which is exactly the kind of thing an engineer notices.

### The command set

| Command | Supply | Meter | Load | Scope |
| --- | --- | --- | --- | --- |
| `*IDN?`, `*RST`, `*CLS`, `SYST:ERR?` | yes | yes | yes | yes |
| `VOLT <n>` / `VOLT?` | yes | | | |
| `CURR <n>` / `CURR?` | yes | | yes | |
| `OUTP <state>` / `OUTP?` | yes | | | |
| `INP <state>` / `INP?` | | | yes | |
| `MODE <cc\|cr\|cv>` / `MODE?` | | | yes | |
| `RES <n>` / `RES?` | | | yes | |
| `MEAS:VOLT?`, `MEAS:CURR?` | yes | | yes | |
| `CONF:VOLT:DC`, `CONF:VOLT:AC`, `CONF:RES`, `FUNC?` | | yes | | |
| `VOLT:DC:RANG <n>` / `VOLT:DC:RANG?`, `READ?` | | yes | | |
| `MEAS:VOLT:DC?`, `MEAS:VOLT:AC?`, `MEAS:RES?` | | yes | | |
| `CHAN1:COUP`, `CHAN1:SCAL`, `CHAN1:BWL`, `TIM:SCAL` | | | | yes |
| `SING`, `MEAS:VPP? <source>` | | | | yes |

Error codes are the standard SCPI ones: `0,"No error"`, `-100`, `-108`, `-109`, `-113`, `-221`,
`-222`, `-224`, `-350`. Every instrument keeps a ten-deep queue read oldest first with
`SYST:ERR?`, and a rejected command changes nothing, returns nothing and reports nothing until the
program asks.

### The three dialect differences

Instruments that all claim SCPI compliance still diverge, and a script drafted from one manual and
pointed at another instrument fails in ways that look like hardware faults. Three differences are
built into this bench on purpose, documented in the manuals, and enforced by the simulation:

1. **Keyword form.** Maridun firmware accepts `VOLTage` and `VOLT` alike. Tarnley firmware accepts
   the short form only and answers a long form with `-113,"Undefined header"`.
2. **Booleans.** Maridun accepts `ON`, `OFF`, `1` and `0`. Tarnley accepts `1` and `0` only, and
   answers `INP ON` with `-224,"Illegal parameter value"`.
3. **Unit suffixes.** Tarnley query responses carry a unit: `MEAS:VOLT?` answers `4.9930V`,
   `RES?` answers `1000.0000OHM`, `TIM:SCAL?` answers `2.000E-06S`. Maridun responses are bare
   numbers. A program that calls `float()` on a Tarnley response raises, which is the good case.

The lesson for `instrument-script-from-the-manual` is not "SCPI is a mess." It is that every
command has to be checked against the manual for the instrument it is going to, and that checking
it is code's job, not the model's.

## Read-only commands and commands that set state

The line this site draws through an instrument's command set, written down once in
`examples/common/bench.py` as `READ_ONLY_HEADERS` and `is_read_only()`:

| Class | Commands | Who may run it |
| --- | --- | --- |
| Read only | `*IDN?`, `SYST:ERR?`, every `?` query: `MEAS:*?`, `READ?`, `VOLT?`, `CURR?`, `OUTP?`, `INP?`, `MODE?`, `FUNC?`, `CHAN1:*?`, `TIM:SCAL?` | An agent, without asking. A query changes nothing. |
| Sets state | `VOLT`, `CURR`, `RES`, `MODE`, `CONF:*`, `VOLT:DC:RANG`, `CHAN1:*`, `TIM:SCAL`, `SING`, `*RST`, `*CLS` | Code, after the value clears the safety envelope. |
| Energizes a board | `OUTP ON` on the supply, `INP 1` on the load | Code, after the envelope, and only with a person's approval that names the set point. |

`*RST` is in the second class and not the first. It measures nothing, but it drops an output and
resets a range, and on a powered board that is a state change like any other.

### The safety envelope

`SafetyEnvelope` in `examples/common/bench.py` holds the limits for this board, not the limits of
the instrument: 32.0 V (the ECN ceiling for the revisions in the field), a 4.0 A supply current
limit (above the 3.0 A rating, below the 4.5 A the inductor saturates at) and a 4.5 A load ceiling.
The MDN-4010 will happily do 40 V and 10 A. The envelope is about what is safe for the board in
the fixture.

It refuses, and `tests/test_bench.py` proves each one:

- a negative voltage or current
- `float("nan")` and `float("inf")`, and the strings `"nan"`, `"inf"` and `"1e400"`
- a value that is not a number at all, including `None`, a list and a boolean
- a set point over the ceiling by any margin: 32.001 V is refused, with no tolerance band
- an output enable with no approval
- an approval that names a different set point than the supply is actually at
- an approval that has already been used once
- `OUTP ON` sent as a command string, which cannot carry an approval
- any message that sets two things at once (`VOLT 24;CURR 1`)
- any set command the envelope does not know how to check, rather than passing it through

The order is always the same: the model proposes, code checks the value against the envelope, a
person approves the enable, and only then does the instrument act. On this bench the instrument is
simulated, so the whole thing is a rehearsal. The point of rehearsing it is that the same code runs
when it is not.

## The production test

Eight steps, in order, on one of four fixtures. Full text in
`evals/bench/corpus/srb5030-test-spec.md`.

| Step | Measurement | Conditions | Lower | Upper | Unit | Typical |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | R_OUT | source off, output to return | 500 | | ohm | 3288 |
| 2 | IQ_NL | 24.0 V in, no load | | 25.00 | mA | 11.20 |
| 3 | VOUT | 24.0 V in, 1.000 A | 4.9500 | 5.0500 | V | 4.9930 |
| 4 | LINE_REG | 9.0 V to 32.0 V at 1.000 A | | 0.300 | % | 0.115 |
| 5 | LOAD_REG | 0.100 A to 3.000 A at 24.0 V | | 0.800 | % | 0.406 |
| 6 | EFF_FL | 24.0 V in, 3.000 A | 88.00 | | % | 92.45 |
| 7 | RIPPLE | 24.0 V in, 3.000 A, AC, 20 MHz limit | | 50.0 | mV | 22.5 |
| 8 | I_LIM | 24.0 V in, load ramped in 50 mA steps | 3.70 | 5.00 | A | 4.30 |

A unit that fails step 1 is never powered, so it has one row in the log instead of eight.

Two steps are worth noticing because of what they cannot see. Steps 4 and 5 are differences of two
readings, so a fixed offset anywhere in the measurement path cancels. That is a feature when the
fixture has an offset and a trap when the board is dead: a board with no output reads zero at both
points, scores a regulation of about zero, and passes. Step 3 measures the absolute voltage, which
is why it comes first.

## The data, and the six stories in it

`evals/bench/make_data.py` writes three files into `evals/bench/data/` from seed 20260824. Rerun
it and the bytes are identical; `tests/test_bench_data.py` proves that by generating into a
temporary directory and comparing.

| File | Rows | Contents |
| --- | --- | --- |
| `production-run-2026-08.csv` | 1586 | 200 units, 8 steps each, less the two that aborted at step 1 |
| `soak-2026-08-27.csv` | 57 | three units at full load, sampled every 5 minutes for 90 minutes |
| `retest-2026-08-31.csv` | 18 | a retest export written by a different tool |

The run covers four days, two shifts a day, four lots and four fixtures. The fixture changes every
unit and the lot every four units, so each lot gets each fixture an equal number of times. Lot and
fixture are crossed, not nested: neither can stand in for the other, and a grouping that blames one
of them is saying something real.

First-pass yield is 184 of 200, or 92.0%.

### Story 1: a lot with marginal ripple

Lot L2608B. Grouping the RIPPLE readings by lot:

| Lot | n | Mean (mV) | SD (mV) | Cpk | Over 50 mV |
| --- | --- | --- | --- | --- | --- |
| L2608A | 52 | 21.21 | 3.40 | 2.82 | 0 |
| L2608B | 51 | 44.41 | 3.76 | 0.50 | 4 |
| L2608C | 47 | 21.50 | 1.36 | 6.97 | 0 |
| L2608D | 48 | 21.67 | 3.54 | 2.67 | 0 |

Cpk here is the one-sided form, `(USL - mean) / (3 * sigma)`, because the ripple limit is one
sided. The whole-population Cpk is 0.72, which is itself a signal: a capable process split by a
bad lot reads as one incapable process.

The cause is in the bill of materials. The output capacitors in that reel are 16 V X5R parts, not
the 25 V X7R the BOM calls for. At 5 V DC bias they measure about 3.3 uF each instead of about
12 uF, so effective output capacitance falls from about 24 uF to about 6.6 uF, and
`0.79 / (8 * 6.6 uF * 500 kHz) = 29.9 mV` of capacitor ripple plus the usual edge ringing lands
right where the data does.

Notice what this story is not. Yield by lot is 96.2%, 90.4%, 89.6% and 91.7%: L2608B is not even
the worst. A lot problem this size shows up in the mean and the Cpk of the measurement long before
it shows up in a yield number, which is the argument for charting measurements rather than counting
failures.

### Story 2: a fixture that reads low on one step

FIX-03. Grouping the VOUT readings by fixture, with the two dead boards excluded:

| Fixture | n | Mean (V) | SD (V) | Cpk | Failures |
| --- | --- | --- | --- | --- | --- |
| FIX-01 | 49 | 4.9892 | 0.0120 | 1.09 | 0 |
| FIX-02 | 48 | 4.9922 | 0.0129 | 1.09 | 0 |
| FIX-03 | 49 | 4.9640 | 0.0105 | 0.44 | 5 |
| FIX-04 | 50 | 4.9906 | 0.0124 | 1.09 | 1 |

FIX-03 reads 30 mV low. The spread is normal; only the mean has moved. Yield by fixture is 96%,
94%, 86% and 92%.

The cause is a stale calibration constant on that fixture's DMM channel 2, entered from the wrong
column after a relay repair. Only step 3 reads an absolute voltage through channel 2, so only step
3 is affected: steps 4 and 5 are differences and the offset cancels, and step 6 reads the output
voltage at the load's own terminals. One step moving and three not moving is the signature that
tells a stale offset apart from an open sense lead, which would move all of them.

Until you group by fixture this looks like a board problem, and five boards fail for it. The
retest file closes the loop: every one of those five passes on FIX-01.

Grouping by day and by shift finds nothing. Yield by day is 90%, 92%, 96%, 90%; by shift it is 90%
and 94%. Being able to say that nothing is there is part of the same half hour of work.

### Story 3: a unit that drifts under soak

`soak-2026-08-27.csv`, serial SRB5030-2608-0121, held at 24 V in and 3 A out for 90 minutes.

| Serial | VOUT start | VOUT end | Drop | Case start | Case end |
| --- | --- | --- | --- | --- | --- |
| SRB5030-2608-0044 | 4.9923 V | 4.9898 V | 2.5 mV | 24.6 degC | 60.3 degC |
| SRB5030-2608-0121 | 4.9910 V | 4.9155 V | 75.5 mV | 24.6 degC | 91.7 degC |
| SRB5030-2608-0166 | 4.9918 V | 4.9906 V | 1.2 mV | 24.4 degC | 60.5 degC |

The two healthy boards settle in about 45 minutes. The third does not settle at all: the case
keeps climbing and the output keeps falling, which is what a resistive joint does, because
`I squared R` heats the joint and a hotter joint is more resistive.

The same unit failed EFF_FL in production at 79.6%, the only genuine efficiency failure in the run.
Both readings have one cause. That is deliberate: a reader who finds the soak drift and the
efficiency failure separately and then connects them has done the actual work of failure analysis.
A run chart of `vout_v` against `elapsed_min`, per serial, shows it in one picture.

### Story 4: a column in millivolts under a header that says volts

`retest-2026-08-31.csv` has a column named `value_v` whose values are `4973.5`, `4944.9`, `-6.1`.
Those are millivolts. The export was written by the fixture's own tool, which works in millivolts,
and the header was written by hand.

Nothing about the file is malformed. It parses, the numbers are numbers, and a merge with the
production log produces a table where some rows say a 5 V rail measured 4973.5 volts. Read
literally, every retested unit passes a 4.95 V lower limit by a factor of a thousand.

This is the trap `test-data-by-conversation` exists for. The check that catches it is not clever:
it is knowing that the rail is 5 V and noticing that the numbers are not near 5.

### Story 5: a serial filed under the wrong lot

In the same retest file, SRB5030-2608-0142 is filed under lot L2608A. In the production log that
serial is in lot L2608D. Whoever assembled the retest sheet took the lot from the row above.

One row, no error message, and it silently moves a unit between the groups that a lot analysis
depends on. Joining the two files on serial and comparing the lot columns finds it in one line.

### Story 6: operator notes of varying quality

Seventeen rows carry a free-text note. They are what operator notes really look like:

- specific and useful: `no continuity check, reads 0.4 ohm out to gnd - bridge at J2?`
- specific and useful: `draws 31ma with nothing on the output. boot cap?`
- useful but informal about the fixture: `low again on fix3, thats 3 today`, `fix3`
- an answer that is already the whole investigation: `4.94 on fixture 3, moved to fixture 1 and it passed`
- almost content free: `FAIL`, `?`, `beeps`, `shorted`
- on the wrong row: `ripple 44mv, passed but marginal` sits on a VOUT row that passed
- about something else entirely: `retested, first run aborted when the operator bumped the lid`

Notes are a source of hypotheses, never a record. The logged value, the limits and the result are
the record. `test-failure-triage` is the recipe that turns these into causes, and its first job is
to be honest about how often the note says nothing.

## What this bench is for

Two claims run through every engineering page built on it.

**Most of test automation is level 0.** A limit check is a comparison. A Cpk is arithmetic. A
sequencer is a loop. A control chart is a mean, a standard deviation and a plot. Grouping a
measurement by lot and by fixture is a `GROUP BY`. All six stories above are findable with no model
anywhere: four of them by grouping, one by a run chart, one by looking at the magnitude of a
number. The recipe that teaches this leads the engineering list, and every recipe above it in
level says plainly which part of the job actually needed the model.

**The pass or fail decision never involves a model.** Not as a check, not as a tie-breaker, not as
a summarizer of a borderline reading. A wrong pass ships a bad unit, and a model that is right 99
times in 100 is a defect rate of one percent added to a line that measures its defect rate in parts
per million. The model's place on this bench is reading a manual, triaging free text, drafting a
script that code then checks, and exploring data conversationally after the dashboard has run out
of answers.
