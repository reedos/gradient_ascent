# SRB-5030 Bring-Up Notebook

Orbeck Power Systems, engineering notebook extract. Entries from 03/04/2026 to 08/28/2026, in
date order. This is working notes, not a controlled document. Nothing here supersedes the
datasheet, the test specification or an ECN; where it disagrees with one of those, the controlled
document is right and this file is a record of what somebody thought at the time.

## 1. 03/04/2026, first power-up, revision A

Board 4 of the pilot build. Bench supply current limit at 0.2 A, input ramped from 0 V by hand.
Output came up at 8.3 V in, which matches the 8.2 V lockout. 5.001 V at no load on the MDN-6100.
Input current 11 mA at 24 V with nothing on the output, which is where I expected it.

Switch node on TP4 is clean at 500 kHz, about 495 kHz on the counter. Duty cycle at 24 V in reads
21 percent; 4.98 / 24 is 20.8 percent, so that is right.

No smoke, no heat. Left it running at 1 A for an hour and the inductor was warm but not hot.

## 2. 03/09/2026, ripple, and a measurement that was wrong

Measured 46 mV of ripple at 3 A and spent most of a morning on it before realizing the probe
ground lead was 15 cm of wire. Swapped to a ground spring on the probe tip and the same board
reads 22 mV. Bandwidth limit on, AC coupled, 10 mV per division.

The arithmetic says the inductor and capacitor alone give about 9 mV: 0.79 A of ripple current
into 24 uF at 500 kHz is 8.2 mV, plus 1.2 mV of ESR. The remaining 13 mV is switching edge, and
how much of it you see depends entirely on the probe and the bandwidth limit.

Wrote this up for the test spec because the number is meaningless without the setup. Two people
measuring the same board with different probe grounds will disagree by a factor of two and both
will be sure the other one's board is bad.

## 3. 04/22/2026, efficiency sweep

Swept 12 V and 24 V in, 0.5 A to 3 A out, reading input current on the MDN-4010 and output current
on the TRN-2400, output voltage at the load terminals.

Peak is 95.8 percent at 12 V in, 1 A out. At 24 V in, 3 A out it is 92.5 percent, so 1.21 W lost.
Inductor DCR is 28 mohm, so 0.25 W of that is the inductor and the rest is the controller and the
FETs.

Efficiency at 24 V is lower than at 12 V across the whole sweep. That is expected: switching loss
scales with input voltage and the duty cycle is lower.

## 4. 06/12/2026, thermal, revision B

Three boards at 24 V in, 3 A out, still air, thermocouple on the controller case. All three
settled between 59 and 62 degC case at 24 degC ambient after about 45 minutes. Consistent with
42 degC/W junction to ambient and about 1 W in the controller.

Held one at 70 degC ambient in the chamber for two hours. Case 108 degC, no shutdown, output held
at 4.978 V. Thermal shutdown is at 145 degC so there is real margin, but this is still air with
the pour intact. A board with a cut pour or a blocked enclosure is a different measurement.

## 5. 08/11/2026, revision C design review, input capacitor

Went through the derating rules for revision C and C1/C2 do not pass DR-14. They are 50 V parts on
a rail the datasheet says goes to 36 V, and 50/36 is 1.39, under the 1.5 the rule requires.

Nobody caught this on revision A or B. Checked the field data: no returns, no failures, and the
customers we know about are all on a 24 V nominal rail. But the datasheet sold a 36 V input and
the board as built does not meet our own derating rule at 36 V.

Raised ECN-2608-04. Revision C moves to 63 V parts. Revisions A and B get a 32 V ceiling, which is
50/1.5 rounded down, and the test spec drops the line regulation sweep from 36 V to 32 V.

## 6. 08/28/2026, lot L2608B ripple, and a soak

Ripple is up on L2608B. Mean is about 44 mV against about 21 mV on the other three lots this
month, and four units are over the 50 mV limit. Grouping the ripple readings by lot makes it
obvious; grouping by fixture or by shift shows nothing.

Pulled three boards from L2608B and measured the output capacitors in circuit at 5 V bias: about
3.3 uF each instead of about 12 uF. The reel is 16 V X5R, not the 25 V X7R on the bill of
materials, so they derate far harder at bias. Working back from the 44 mV: 0.79 A into about
6.6 uF at 500 kHz gives about 30 mV of capacitor ripple, plus the usual 12 or 13 mV of edge, which
is what we are seeing.

Separately, soaked three boards at 3 A for 90 minutes. Two settled at about 60 degC case with the
output flat to a couple of millivolts. The third, serial SRB5030-2608-0121, walked down about
75 mV over the 90 minutes and its case kept climbing past 90 degC without settling. That one had
already failed efficiency in production at 79.6 percent. Both readings point the same way: a
resistive joint that heats, and heats further as it heats. Sent it to failure analysis rather than
guessing; see `failure-analysis-guide.md` section 5.
