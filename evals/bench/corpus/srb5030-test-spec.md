# SRB-5030 Production Test Specification

Orbeck Power Systems, document TS-5030. Revision 3, 08/17/2026. Revision 3 changed step 4 from a
9.0 V to 36.0 V sweep to a 9.0 V to 32.0 V sweep, per ECN-2608-04. This specification governs the
final electrical test of every SRB-5030 board before it is shipped.

## 1. Scope

Eight steps, run in order, on one of four fixtures. Every step compares a measured number against a
fixed limit. No step involves judgment, and no step may be waived by the operator. A unit that
fails any step is marked FAIL, removed from the line and routed per
`failure-analysis-guide.md` section 1.

The pass or fail decision is arithmetic: a comparison of a measured value against the limits in
section 4 of this document. Nothing else decides it.

## 2. Equipment

| Role | Instrument | Manual |
| --- | --- | --- |
| DC source | Maridun MDN-4010 | `mdn4010-programming-manual.md` |
| Precision meter | Maridun MDN-6100 | `mdn6100-programming-manual.md` |
| Load | Tarnley TRN-2400 | `trn2400-programming-manual.md` |
| Ripple | Tarnley TRN-1102 | `trn1102-programming-manual.md` |

All four instruments must be within their calibration interval; see `calibration-procedure.md`.
The fixture's own channel offsets must be within their interval as well, which is a separate
record from the instruments'.

## 3. Setup and Safety

1. Fixture power off. Seat the board in the fixture and close the lid. The lid interlock must be
   closed before the source output can be enabled.
2. Set the MDN-4010 to 0.000 V and a 4.000 A current limit before enabling the output, never
   after. A board seated wrong will draw whatever the limit allows.
3. Enable the source output only after the current limit is set and the interlock is closed.
4. Allow 250 ms after any input voltage change and 100 ms after any load current change before
   taking a reading. Readings taken sooner are not valid.
5. Disable the load input before disabling the source output at the end of the sequence.

Step 1 runs with the source output disabled. A board that fails step 1 is never powered: the
sequence stops and the remaining seven steps are not run, so a failed unit has one record in the
log and a passing unit has eight.

## 4. Test Steps and Limits

| Step | Measurement | Conditions | Lower | Upper | Unit |
| --- | --- | --- | --- | --- | --- |
| 1 | R_OUT | source off, J2-1 to J2-2 | 500 | | ohm |
| 2 | IQ_NL | VIN 24.0 V, no load | | 25.00 | mA |
| 3 | VOUT | VIN 24.0 V, IOUT 1.000 A | 4.9500 | 5.0500 | V |
| 4 | LINE_REG | VIN 9.0 V to 32.0 V, IOUT 1.000 A | | 0.300 | % |
| 5 | LOAD_REG | VIN 24.0 V, IOUT 0.100 A to 3.000 A | | 0.800 | % |
| 6 | EFF_FL | VIN 24.0 V, IOUT 3.000 A | 88.00 | | % |
| 7 | RIPPLE | VIN 24.0 V, IOUT 3.000 A | | 50.0 | mV |
| 8 | I_LIM | VIN 24.0 V, load ramped | 3.70 | 5.00 | A |

Step 4 swept to 36.0 V before revision 3 of this specification. It now stops at 32.0 V. The reason
is in `ecn-2608-04.md`; the datasheet still prints the older figure.

## 5. Step Detail

**Step 1, R_OUT.** Source output disabled. MDN-6100 in resistance, 100 kohm range, on fixture
channel 1 across J2. Wait 2 s for the output capacitors to settle before reading. Below 500 ohm is
a short: stop, do not power the board.

**Step 2, IQ_NL.** Set 24.000 V, load input off. Read the source's own current with `MEAS:CURR?`.
The MDN-4010's current readback resolves to 1 mA, which is enough for a 25 mA limit and is why no
separate shunt is fitted.

**Step 3, VOUT.** Set 24.000 V, load to 1.000 A constant current, load input on. Read the
MDN-6100 on fixture channel 2, four-wire, 10 V range. This is the only step that reads an absolute
output voltage through channel 2. Steps 4 and 5 are differences of two readings, so any fixed
offset in the path cancels; step 6 reads the output voltage from the load's own terminals.

**Step 4, LINE_REG.** At 1.000 A, read VOUT at 9.0 V in and again at 32.0 V in. Report
`|V(32) - V(9)| / 5.000 * 100`, as a percentage of the nominal output, not of the reading.

**Step 5, LOAD_REG.** At 24.0 V in, read VOUT at 0.100 A and again at 3.000 A. Report
`|V(0.1) - V(3.0)| / 5.000 * 100`.

**Step 6, EFF_FL.** At 24.0 V in and 3.000 A out, read the load's terminal voltage and current and
the source's current. Report `(VOUT * IOUT) / (VIN * IIN) * 100`.

**Step 7, RIPPLE.** At 24.0 V in and 3.000 A out, TRN-1102 channel 1 on TP2 with a 1:1 probe and a
ground spring. AC coupling, 20 MHz bandwidth limit on, 10 mV per division, 2 us per division.
Single acquisition, then `MEAS:VPP? CHAN1`. All four settings are part of the limit: the 50 mV
limit does not apply to a reading taken any other way.

**Step 8, I_LIM.** At 24.0 V in, raise the load current in 50 mA steps from 3.500 A. Report the
first current at which VOUT falls below 4.900 V. Stop at 6.000 A and report 6.00 if the output has
not fallen by then.

## 6. Log Format

One row per step, written to the day's CSV. Columns, in order: `serial`, `lot`, `fixture`,
`shift`, `timestamp`, `step`, `measurement`, `value`, `unit`, `lower_limit`, `upper_limit`,
`result`, `notes`.

`value` is in the unit named in the `unit` column, and the limits are in that same unit. An empty
limit column means that limit is not applied. `result` is PASS or FAIL and is computed from the
value and the limits, never entered by hand. `notes` is free text the operator may leave and is
not read by anything automatic.

## 7. Fixture and Shift Records

Four fixtures, FIX-01 through FIX-04, run in parallel. Boards are assigned to fixtures in
rotation, so a fixture effect and a lot effect can be told apart afterward. Shift A runs from
07:00 and shift B from 15:00; both are recorded.

Any investigation into yield groups the measured values by lot, by fixture, by day and by shift
before anything else is done. A shift in the mean of one group, with no unit in that group failing,
is the normal early sign of both of the problems this line has had: a component change shows in the
lot grouping and a fixture problem shows in the fixture grouping.

## 8. Retest Rules

A unit that fails may be retested once, on a different fixture, with the reason recorded. A retest
that passes does not replace the original record: both records are kept, and the unit is shipped
only after the reason for the first failure is understood. A unit that fails step 1 is never
retested; it goes to failure analysis.

Retest exports are written by the fixture's own tool and are not the same file format as the
production log. Check the column headers and the magnitude of the values before merging a retest
export with a production log.
