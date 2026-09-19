# Orbeck SRB-5030 Step-Down Regulator Board

Orbeck Power Systems. Datasheet revision B, 06/18/2026. Covers board revisions A and B. Revision
C is in qualification and is not covered here. Some figures in this datasheet are superseded for
revision A and revision B boards by ECN-2608-04; see `ecn-2608-04.md`.

## 1. Description

The SRB-5030 is a synchronous buck (step-down) regulator board that converts a wide DC input to a
fixed 5.000 V output at up to 3.0 A. It is built around the OPS-1147 40 V synchronous buck
controller switching at 500 kHz, with a 10 uH inductor and ceramic output capacitors. The board is
38 mm by 25 mm, four layers, with screw terminals at each end and four test points.

It is intended as a point-of-load regulator on a 24 V industrial rail. It has no enable sequencing,
no power-good output and no remote sense. Boards leave the line configured for 5.000 V; the output
voltage is set by fixed resistors and is not adjustable.

## 2. Absolute Maximum Ratings

Exceeding any of these damages the board. They are not operating conditions.

| Parameter | Min | Max | Unit |
| --- | --- | --- | --- |
| Input voltage, VIN to RTN | -0.3 | 40.0 | V |
| Output voltage forced externally | -0.3 | 6.0 | V |
| Output current, continuous | | 4.0 | A |
| Junction temperature, TJ | -40 | 125 | degC |
| Storage temperature | -55 | 150 | degC |
| Terminal torque, J1 and J2 | | 0.25 | N m |

## 3. Recommended Operating Conditions

| Parameter | Min | Typ | Max | Unit |
| --- | --- | --- | --- | --- |
| Input voltage, VIN | 9.0 | 24.0 | 36.0 | V |
| Output current, IOUT | 0 | | 3.0 | A |
| Ambient temperature, full load | -40 | 25 | 70 | degC |
| Input source impedance | | | 0.5 | ohm |

The 36.0 V maximum in this table is superseded for revision A and revision B boards. See
`ecn-2608-04.md`.

Above 70 degC ambient, derate the output current linearly from 3.0 A at 70 degC to 1.5 A at
85 degC.

## 4. Electrical Characteristics

VIN = 24.0 V, IOUT = 1.0 A, TA = 25 degC unless a row says otherwise.

| Parameter | Conditions | Min | Typ | Max | Unit |
| --- | --- | --- | --- | --- | --- |
| Output voltage | full line, load and temperature range | 4.900 | 5.000 | 5.100 | V |
| Output voltage | 24.0 V in, 1.0 A, 25 degC | 4.950 | 4.993 | 5.050 | V |
| Line regulation | 9.0 V to 36.0 V, IOUT = 1.0 A | | 0.14 | 0.30 | % |
| Load regulation | IOUT 0.1 A to 3.0 A, VIN = 24.0 V | | 0.41 | 0.80 | % |
| Output ripple, peak to peak | 24.0 V in, 3.0 A, 20 MHz bandwidth | | 22 | 50 | mV |
| No-load input current | 24.0 V in, output enabled | | 11.2 | 25.0 | mA |
| Switching frequency | | 450 | 500 | 550 | kHz |
| Undervoltage lockout, rising | | | 8.2 | | V |
| Undervoltage lockout, falling | | | 7.8 | | V |
| Soft-start time | 0 V to 5.000 V, no load | | 4 | | ms |
| Current limit, output leaves regulation | VIN = 24.0 V | 3.70 | 4.30 | 5.00 | A |
| Thermal shutdown | junction temperature | | 145 | | degC |
| Thermal shutdown recovery | junction temperature | | 125 | | degC |

Line regulation and load regulation are stated as the change in output voltage across the stated
range, divided by the 5.000 V nominal output, as a percentage.

## 5. Typical Performance: Efficiency

Efficiency is output power divided by input power, measured at the terminals. Both currents are
given so the figure can be checked rather than taken on trust.

| VIN (V) | IOUT (A) | VOUT (V) | IIN (A) | POUT (W) | PIN (W) | Efficiency (%) |
| --- | --- | --- | --- | --- | --- | --- |
| 12.0 | 0.5 | 4.9935 | 0.2195 | 2.497 | 2.634 | 94.8 |
| 12.0 | 1.0 | 4.9900 | 0.4339 | 4.990 | 5.206 | 95.8 |
| 12.0 | 2.0 | 4.9830 | 0.8698 | 9.966 | 10.437 | 95.5 |
| 12.0 | 3.0 | 4.9760 | 1.3154 | 14.928 | 15.784 | 94.6 |
| 24.0 | 0.5 | 4.9965 | 0.1185 | 2.498 | 2.843 | 87.9 |
| 24.0 | 1.0 | 4.9930 | 0.2270 | 4.993 | 5.447 | 91.7 |
| 24.0 | 2.0 | 4.9860 | 0.4475 | 9.972 | 10.741 | 92.8 |
| 24.0 | 3.0 | 4.9790 | 0.6730 | 14.937 | 16.151 | 92.5 |

Efficiency is higher at 12 V in than at 24 V in because the duty cycle is higher and the switching
loss, which grows with input voltage, is lower. Efficiency falls at light load because the fixed
quiescent and gate-drive loss is a larger share of a smaller output.

## 6. Typical Performance: Ripple

At VIN = 24.0 V and IOUT = 3.0 A the duty cycle is 4.979 / 24.0 = 0.207 and the peak-to-peak
inductor ripple current is

    dIL = (VIN - VOUT) * D / (L * fSW) = (24.0 - 4.979) * 0.207 / (10 uH * 500 kHz) = 0.79 A

which is 26 percent of the 3.0 A rating. Peak inductor current is 3.0 + 0.79/2 = 3.39 A.

That ripple current across the output capacitance produces

    dVC  = dIL / (8 * COUT * fSW) = 0.79 / (8 * 24 uF * 500 kHz) = 8.2 mV
    dVESR = dIL * ESR = 0.79 * 1.5 mohm = 1.2 mV

for about 9.4 mV peak to peak of inductor-and-capacitor ripple. COUT is 24 uF: two 22 uF 25 V X7R
parts, each derating to about 12 uF at 5 V DC bias.

The 22 mV typical figure in section 4 is a measured number and is larger than 9.4 mV because a
probe at the output test point also sees switching-edge ringing. Measure ripple AC coupled, with
the 20 MHz bandwidth limit on, using a short ground spring rather than a ground lead. With the
bandwidth limit off, the same board reads roughly twice as much, and the difference is in the
measurement, not the board.

## 7. Thermal

Board thermal resistance, junction to ambient, is 42 degC/W in still air on a four-layer board with
the pour intact.

At VIN = 24.0 V and IOUT = 3.0 A the board dissipates 16.151 - 14.937 = 1.21 W. About 0.25 W of
that is inductor DCR loss (28 mohm at 3 A), leaving about 0.96 W in the controller and its FETs, so
the junction runs roughly 40 degC above ambient. At the 70 degC maximum ambient that is about
110 degC, inside the 125 degC limit with margin for airflow that is worse than assumed.

Thermal shutdown is a protection, not an operating mode. A board that reaches it in normal use has
a defect; see `failure-analysis-guide.md` section 6.

## 8. Board Revisions

| Revision | Released | Change |
| --- | --- | --- |
| A | 03/02/2026 | Pilot build, 40 boards. Not sold. |
| B | 06/01/2026 | Production. Output terminal block changed to a 5.08 mm pitch part; inductor pad widened. Electrically identical to revision A. |
| C | not released | Input capacitors changed to 63 V parts per ECN-2608-04. In qualification. |

The revision is printed on the silkscreen next to J1 and is the last character of the assembly
number, OPS-9001-x.

## 9. Test Points and Connections

| Designator | Function |
| --- | --- |
| J1-1 | VIN |
| J1-2 | RTN |
| J2-1 | VOUT |
| J2-2 | RTN |
| TP1 | VIN, sense |
| TP2 | VOUT, sense |
| TP3 | RTN, sense |
| TP4 | switch node, for scope use only |

TP4 is a bare switch node. It swings the full input voltage at 500 kHz. Do not connect a meter or
a load to it.

## 10. Ordering and Marking

The label carries the assembly number, the board revision and a serial number of the form
`SRB5030-YYMM-NNNN`, where `YYMM` is the year and month the lot was built and `NNNN` is the unit
number within that lot. Lot codes are of the form `L2608A`: year 26, month 08, and a letter for the
reel set the lot was built from.
