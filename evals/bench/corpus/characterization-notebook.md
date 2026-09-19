# SRB-5030 Revision C Characterization Notebook

Orbeck Power Systems, engineering notebook extract. Entries from 09/13/2026 to 09/16/2026, in
date order, for the design verification sweep of the five revision C prototypes. Working notes,
not a controlled document: where this disagrees with the datasheet, the test specification or an
ECN, the controlled document is right. The readings themselves are in
`characterization-2026-09.csv`.

## 1. 09/13/2026, What Was Set Up

Five hand-built revision C boards, serials SRB5030-2609-0001 through 0005. Revision C is the
build with 63 V input capacitors from ECN-2608-04, so the whole point of the sweep is that these
boards are allowed back up to 36 V while the boards in the field are not. I swept to 32.0 V
anyway. The test specification's line regulation sweep is 9.0 V to 32.0 V and I wanted numbers
that could be compared against production, and the chamber and the supply were already set up for
it.

Bench, all four instruments from the production bench, all inside their calibration intervals:

| Instrument | Role | Connection |
| --- | --- | --- |
| MDN-4010 | input supply | J1-1 and J1-2, 16 AWG, 0.6 m |
| MDN-6100 | output voltage | TP2 and TP3, four-wire, lead set L4 |
| TRN-2400 | load, constant current | J2-1 and J2-2, 14 AWG, 0.4 m |
| Chamber | ambient | boards on a rack, thermocouple on the rack, not on a board |

No fixture: a bench harness with screw terminals, so nothing here goes through a fixture
channel and the offsets in `calibration-procedure.md` section 5 do not apply.

## 2. 09/13/2026, The Sweep

9.0, 12.0, 24.0 and 32.0 V in; 0.100, 1.000 and 3.000 A out; 25, 70 and 0 degC ambient; five
readings of the output at every point, 6 seconds apart, after a 30 second settle at each new
point. Input current is read off the supply at the same time. That is 900 readings.

Five readings a point rather than one because repeatability is the one line of an uncertainty
budget that is measured on the day rather than looked up, and it costs 24 extra seconds a point.

Output ripple is not in this session. It needs its own setup, and `bringup-notebook.md` section 2
is the reason not to do it casually alongside something else.

Meter: DC volts, 10 V range, selected once per board rather than per reading. Thirty minutes of
warm-up before the first reading of each day.

## 3. 09/14/2026, 25 degC

Room ambient, chamber door open, the whole sweep from 08:30 to 09:55.

Stepped away during board 1's 12 V block. When I came back the supply was reading 24 V, which is
where the previous block left it, and I could not tell from the screen whether the 12 V block had
run at 12 V or not. I let the sweep finish rather than stopping it. If one block on board 1 is
wrong it will be that one, and the input current will show it: at 12 V in and 3 A out this board
should draw about 1.31 A, and at 24 V in about 0.67 A. The output voltage will not show it,
because holding the output steady while the input moves is the entire job of the part.

Mid-sweep on board 3 I put the meter on the 100 V range by hand to look at the 32 V input rail,
and left it there. I noticed on board 4 and put it back. From the timestamps that is 09:12:30 to
09:29:54, sixty readings, the second half of board 3 and the first half of board 4. Those
readings are not wrong. They are just worth a quarter of the others: 5 ppm of range on the 10 V
range is 50 uV, and 6 ppm of range on the 100 V range is 600 uV, and the readings in that window
land on 100 uV steps because that is the resolution of that range.

I thought at first the noise was a settling problem and put a 2 second delay in front of every
reading for the rest of board 4. It changed nothing, which was the clue: a settling problem gets
better with a longer delay and a range problem does not.

Board 3 reads low everywhere. About 4.9585 V at 24 V in and 1 A out where the others are near
4.99. Inside the specification, and worth watching at the corners.

## 4. 09/15/2026, 70 degC

Chamber at 70 degC, the rated maximum ambient at full load, two hours of soak before the first
reading. Same sweep, 08:30 to 09:55 once it was stable.

Board 3 at 9 V in and 3 A out is the lowest reading of the whole session. Its margin to the
4.900 V datasheet minimum is about 20 mV where the other four hold 58 to 78 mV. Nothing about
board 3 is out of specification on its own. Its output is low, its load regulation is the worst
of the five, and its line regulation is the second worst, and at the corner where all three push
the same way there is not much left.

Board 5's line regulation at 70 degC is 0.334 percent against a 0.300 percent maximum. That one
is over, not marginal, and it is over by far more than the measurement is worth.

## 5. 09/16/2026, 0 degC

Chamber at 0 degC, same soak, same sweep. Nothing new: every board is higher at the cold end, as
expected, and the highest reading of the session is about 5.011 V against a 5.100 V maximum.

Board 5's line regulation at 0 degC is 0.267 percent, comfortably inside the limit. At 25 degC it
is 0.299 percent. So the number moves with temperature by about a third of the margin the limit
allows, and there is one ambient where it sits inside the limit by less than the measurement is
worth. See section 6.

## 6. The Uncertainty I Am Quoting

Per the MDN-6100 manual's own method, for one output voltage on the 10 V range, one year
specification, five readings. The ambient in the specification is the meter's, and the meter sits
on the bench at about 23 degC on all three days; it is the boards that are in the chamber:

| Contribution | Value | Standard uncertainty |
| --- | --- | --- |
| Meter accuracy at 5 V | +/-224.8 uV | 129.8 uV |
| Resolution, 10 uV | +/-5 uV | 2.9 uV |
| Repeatability, 5 readings | about 60 uV spread | 26.8 uV |
| Leads and connections | +/-200 uV | 115.5 uV |
| Combined | | 175.8 uV |
| Expanded, k = 2 | | 351.6 uV |

The 200 uV on the lead and connection line is borrowed from `calibration-procedure.md` section 5,
where it is what a verified fixture path has to agree to. This harness is not a fixture path. The
figure is the right order of magnitude for a four-wire lead set on screw terminals and it has not
been checked on this harness, so it is an assumption and it is the second largest line in the
budget. Somebody should put a shorting link across the lead set and read it.

So an output voltage from this session is good to about +/-0.35 mV. Against a 20 mV margin that
is nothing, which is why board 3's corner is a real finding and not a measurement artifact.

Line and load regulation are differences of two readings through the same leads, so the lead
contribution cancels and drops out, leaving 132.5 uV per reading. Two readings and k = 2
gives 374.9 uV, which is 0.0075 percentage points of a figure quoted against 5.000 V.

Board 5 at 25 degC reads 0.299 percent against a 0.300 percent limit. The margin is 0.0006
points and the measurement is worth 0.0075 points. Guardbanded, the acceptance limit is 0.2925
percent and this is over it: the honest statement is that this measurement does not say whether
that board meets its line regulation limit at 25 degC. It is not a pass and it is not a fail.
Either measure it better, with a longer average and a measured lead contribution, or hold the
board against the 70 degC result, which is unambiguous.

The input current, and therefore efficiency, is a different story. It comes off the supply's own
readback, which is specified to +/-(0.1 percent of reading + 3 mA), so at 3 A it is worth about
6 mA: roughly 0.2 percent of the reading, against 45 ppm for the output voltage. Efficiency from
this session is a percent-level number no matter how many digits the arithmetic produces, and
nothing in this notebook should be quoted to a tenth of a percent.

## 7. What Is Still Open

- Board 1's 12 V, 3 A block at 25 degC. Check the input current before using it. If it is the
  24 V number, throw the block out and re-run it; do not correct it.
- Board 5's line regulation. One measurement that cannot say, one that fails. Design should look
  at the feedforward before anybody re-measures.
- Board 3's stack of three marginal parameters. This is a design margin question and not a board
  question: if the pilot build has boards like this one, the corner is thinner than the datasheet
  suggests.
- The lead and connection contribution is assumed, not measured. Everything above moves if that
  200 uV is wrong.
- Ripple, which this session did not measure at all.
