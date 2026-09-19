# Bench Calibration and Fixture Verification Procedure

Orbeck Power Systems, document CP-0210. Revision 5, 07/31/2026. Revision 5 added section 5, the
fixture channel offset record, after the FIX-02 relay repair in June 2026.

## 1. Scope and Intervals

Two separate records, with separate intervals, are kept for the SRB-5030 production line.

| Item | Interval | Performed by | Record |
| --- | --- | --- | --- |
| MDN-4010, MDN-6100, TRN-2400, TRN-1102 | 12 months | outside calibration house | certificate on file |
| Fixture channel offsets, FIX-01 to FIX-04 | 3 months, and after any repair | test engineering | `fixture-cal.json` per fixture |

An instrument inside its interval and a fixture inside its interval are both required before a
production run. They are different records and one does not imply the other. Every fixture problem
this line has had was a fixture record problem, not an instrument record problem.

## 2. Reference Standards

The MDN-6100 is the bench transfer standard for DC volts. It is calibrated against a certified
10 V reference and is the meter every other DC voltage on the bench is verified against. Nothing
on this bench is calibrated against the MDN-4010's own readback, which is two orders of magnitude
coarser.

## 3. Instrument Verification Points

Verify at these points before sending an instrument out, so that a drift is caught here rather
than in a production yield.

| Instrument | Point | Tolerance |
| --- | --- | --- |
| MDN-4010, output | 5.000 V, 12.000 V, 24.000 V, 32.000 V at 1 A | +/-(0.05% + 10 mV) against the MDN-6100 |
| MDN-4010, current readback | 0.200 A, 1.000 A, 3.000 A | +/-(0.1% + 3 mA) against a 10 mohm shunt |
| MDN-6100, DC volts | 1.000 V, 5.000 V, 10.000 V | +/-(0.0035% + 50 uV) against the 10 V reference |
| TRN-2400, CC | 0.100 A, 1.000 A, 3.000 A | +/-(0.1% + 10 mA) against the same shunt |
| TRN-1102, vertical | 20 mV and 100 mV square wave | +/-2% of amplitude |

## 4. Procedure

1. Warm every instrument up for 30 minutes with its output or input off.
2. `*RST` and `*CLS` each instrument, then `*IDN?` and record the firmware version. A firmware
   version that has changed since the last record invalidates the record.
3. Work through section 3 in order. Record the measured value, not a pass or fail.
4. Read `SYST:ERR?` after every step. A verification with an error in the queue is void.
5. File the readings with the date, the technician and the ambient temperature.

## 5. Fixture Channel Offsets

Each fixture carries a relay multiplexer with two measurement channels wired to the MDN-6100:

| Channel | Path | Used by |
| --- | --- | --- |
| 1 | J2-1 to J2-2, two-wire, through the mux | step 1, R_OUT |
| 2 | TP2 to TP3, four-wire | step 3, VOUT |

To verify a channel: short the fixture's probe tips to each other, read the meter through that
channel, and record the reading as that channel's offset. Then apply 5.000 V from the MDN-4010
through a verified path and confirm the corrected reading is within 200 uV of the MDN-6100's
direct reading of the same node.

Offsets are stored per channel in the fixture's `fixture-cal.json` and are applied by the test
executive. A channel whose offset exceeds 5 mV is out of tolerance: repair the path rather than
storing a large offset.

**After any repair to a fixture, re-verify every channel on that fixture before it returns to
service, whether or not the repair touched that channel.** A relay replaced on channel 1 has, in
practice, twice been followed by a channel 2 offset entered from the wrong column of the previous
record. An offset entered wrong looks like a product problem: every board on that fixture reads
low by the same amount, and no other fixture does.

## 6. What a Stale Fixture Record Looks Like in the Data

A fixture offset error has a signature and it is worth recognizing before spending a day on it.

- Every board on the affected fixture is shifted by the same amount. The spread within the
  fixture is normal; only the mean has moved.
- Only measurements that read an absolute value through the affected channel are shifted. A
  measurement that is the difference of two readings through the same channel is unaffected,
  because a fixed offset cancels in a difference.
- The shift appears abruptly, dated to the repair, not gradually.
- Units that fail on the affected fixture pass on any other fixture, at a value consistent with
  the offset.

Group the measured values by fixture before anything else when a yield falls. It is one line of
work and it either rules the fixture out or finds the problem.
