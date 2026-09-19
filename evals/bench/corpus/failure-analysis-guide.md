# SRB-5030 Failure Analysis Guide

Orbeck Power Systems, document FA-5030. Revision 4, 08/29/2026. Revision 4 added section 7 after
the FIX-03 offset in August 2026. This guide maps what a failing unit does to what is usually
wrong with it. It is a starting point for an investigation, not a verdict: every cause here has to
be confirmed on the board before it is recorded.

## 1. Routing a Failure

| First failing step | Route to |
| --- | --- |
| 1, R_OUT | Failure analysis. Do not retest, do not power. |
| 2, IQ_NL | Failure analysis. |
| 3, VOUT | Retest once on another fixture, then failure analysis if it fails again. |
| 4 or 5, regulation | Failure analysis. |
| 6, EFF_FL | Failure analysis, with a thermal check. |
| 7, RIPPLE | Hold the unit and check the lot before touching the board. |
| 8, I_LIM | Failure analysis. |

Before any board is opened, check whether the failure is one unit or a group. Group the month's
readings for the failing measurement by lot, by fixture, by day and by shift. A unit problem needs
a board on a bench; a group problem does not, and taking a group problem to the bench costs a day
and finds nothing.

## 2. No Output at All

Symptom: VOUT reads near zero, or negative by a few tens of millivolts on a fixture with a channel
offset. Regulation steps pass, because the difference of two readings of zero is zero. Efficiency
reads zero. The current limit step reports its lowest value, because the output is below the
threshold at the first current tried.

Likely causes, most common first:

1. U1 not switching. Check for activity on TP4 with the input applied. No activity means the
   controller, the enable pull-up R3, or the bootstrap capacitor C5.
2. Open inductor or an unsoldered L1 pad. Continuity from the switch node to the output.
3. Feedback divider open. R1 open pulls the feedback low and the part runs to its limit; R2 open
   pulls it high and the part stops. Measure both in circuit.

A unit that passes the regulation steps and fails VOUT is not a regulation problem. It is a dead
board that the regulation steps cannot see, which is why step 3 comes first.

## 3. Output Low But Alive

Symptom: VOUT below 4.950 V but within a few tens of millivolts of nominal. Everything else
passes.

Check the fixture before the board. See section 7. If the unit reads low on one fixture and normal
on another, the board is fine and the fixture is not.

If the unit reads low on every fixture: the feedback divider is the first suspect. A 1 percent
resistor fitted where a 0.1 percent part belongs shifts the output by up to three times the
expected spread; a wrong value shifts it much further. Measure R1 and R2 and compute
`0.800 * (1 + R1/R2)`.

## 4. Ripple Over the Limit

Symptom: RIPPLE over 50 mV, usually between 40 and 60 mV, with every other step passing.

Before opening anything, group the month's ripple readings by lot. Output ripple is set by the
output capacitance, and output capacitance is a purchased part: a ripple problem that is real is
almost always a whole reel, not one board.

If one lot's mean has moved and the others have not, measure C3 and C4 in circuit at 5 V bias on
three units from that lot and compare against the 12 uF each the design assumes. A 22 uF part in a
lower voltage rating or a lower-grade dielectric measures far less at bias, has the same marking
and the same footprint, and will pass an incoming check that only reads the marked value. See
`srb5030-bom.md` section 3.

If the ripple is high on a single board with no lot signal, check the probe ground before the
board: a ground lead instead of a ground spring reads roughly double. See
`trn1102-programming-manual.md` section 4.

## 5. Efficiency Low, Board Hot

Symptom: EFF_FL below 88 percent, often well below. The board works, regulates and passes ripple.
Held at load it gets hot, and the output walks down as it heats.

This is a resistive joint, and the two readings are the same reading: the loss is `I squared R`,
so the joint heats, and a heated joint is more resistive, so it heats further. The output droop
follows the same resistance.

Confirm with a soak: hold the board at 24 V in and 3 A out for at least 60 minutes with a
thermocouple on the case, and sample the output voltage every five minutes. A healthy board
settles within about 45 minutes, at a case temperature in the high 50s or low 60s Celsius at room
ambient, with the output flat to a few millivolts. A board with a resistive joint does not settle:
the case keeps climbing and the output keeps falling for as long as you watch it.

The joint is usually L1, which carries the full output current across two large pads that sink
heat away from the iron during reflow. Reflow the inductor and re-measure before replacing
anything.

## 6. Thermal Shutdown in Normal Use

Thermal shutdown at 145 degC junction is a protection. A board that reaches it inside the rated
operating envelope has a defect, and the defect is one of: a resistive joint as in section 5, a
cut or blocked ground pour, or an ambient above the 70 degC the board is rated for. Establish
which before replacing the controller. A controller replaced on a board with a cut pour fails the
same way.

## 7. When the Fixture Is the Failure

Two fixture faults have produced board-shaped symptoms on this line, and both were found by
grouping rather than by probing.

**A stale channel offset.** Every board on one fixture reads low, or high, by the same amount on
one measurement. The spread within the fixture is normal; only the mean has moved. Only
measurements that read an absolute value through the affected channel move, because a fixed offset
cancels in the difference the regulation steps take. Units that fail on that fixture pass on any
other. Cause: a channel offset entered wrong after a repair, per `calibration-procedure.md`
section 5. Fix the record, then re-run the held units.

**An open sense connection.** The four-wire sense on channel 2 loses one lead, so the measurement
includes the drop in the force lead and reads low by an amount that grows with load current. This
one does not cancel in a difference, so the regulation steps move too, and that is how it is told
apart from a stale offset: a fixed offset moves one step, an open sense moves three.

## 8. Reading Operator Notes

The `notes` column is free text and nothing automatic reads it. It is still the fastest source of
a hypothesis on this line, and it is unreliable in specific ways worth knowing.

- Notes are written on the step the operator was looking at, which is not always the step that
  failed. A note about ripple has appeared on a passing VOUT row more than once.
- Notes name fixtures informally: "fix3", "fixture 3" and "FIX-03" all appear.
- A note may record a number that disagrees with the logged value, usually because the operator
  wrote down what the screen said before the final settled reading.
- Most failures have no note at all, and "FAIL" and "?" are both common.

Treat a note as a lead to check against the logged numbers, never as a record of what happened.
The logged value, the limits and the result are the record.
