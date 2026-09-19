# Maridun MDN-6100 Digital Multimeter: Programming Manual

Maridun Instruments. Firmware 1.08, manual revision C, 04/12/2026. The MDN-6100 is a 6 1/2 digit
bench multimeter measuring DC volts, AC volts and resistance. Its command set follows the same
conventions as the MDN-4010: long or short keyword form, bare numeric responses, one command per
message.

## 1. Functions and Ranges

| Function | Ranges | Resolution on the lowest range |
| --- | --- | --- |
| DC volts | 100 mV, 1 V, 10 V, 100 V, 1000 V | 100 nV |
| AC volts, true RMS, AC coupled | 100 mV, 1 V, 10 V, 100 V, 750 V | 100 nV |
| Resistance, two-wire or four-wire | 100 ohm to 100 Mohm in decades | 100 uohm |

AC volts bandwidth is 20 Hz to 300 kHz. Content above 300 kHz is not measured. A switching
regulator's output ripple is mostly above that, which is why ripple is a scope measurement and not
an AC volts measurement.

## 2. Accuracy

DC volts accuracy is stated as +/-(ppm of reading + ppm of range), per range, per calibration
interval, after a 30 minute warm-up and with the ambient inside the stated band. Parts per million
and percent are the same specification written two ways: 35 ppm of reading is 0.0035 percent of
reading, and 5 ppm of range is 0.0005 percent of range.

| Range | 24 hour, 23 +/-1 degC | 90 day, 18 to 28 degC | 1 year, 18 to 28 degC |
| --- | --- | --- | --- |
| 100 mV | 15 + 30 | 25 + 35 | 40 + 35 |
| 1 V | 10 + 3 | 20 + 5 | 30 + 5 |
| 10 V | 12 + 2 | 25 + 4 | 35 + 5 |
| 100 V | 15 + 3 | 30 + 5 | 45 + 6 |
| 1000 V | 20 + 3 | 35 + 5 | 50 + 6 |

Outside 18 to 28 degC, add the temperature coefficient for every degree outside the band. It is
one tenth of the one year specification per degree, and it applies to the number of degrees
outside the band, not to the ambient itself.

| Range | Temperature coefficient, per degC outside the band |
| --- | --- |
| 100 mV | 4.0 ppm of reading + 3.5 ppm of range |
| 1 V | 3.0 + 0.5 |
| 10 V | 3.5 + 0.5 |
| 100 V | 4.5 + 0.6 |
| 1000 V | 5.0 + 0.6 |

Displayed resolution is the range divided by 1 000 000: 100 nV on the 100 mV range, 10 uV on the
10 V range, 100 uV on the 100 V range.

Two consequences are worth stating in the manual rather than leaving to the user.

**The range term does not scale with the reading.** On the 10 V range, one year, 5 ppm of range is
50 uV whatever is being measured. A 4.9930 V reading is therefore good to
`35 ppm x 4.9930 V + 5 ppm x 10 V = 174.8 uV + 50 uV = 224.8 uV`. The same reading taken on the
100 V range is good to `45 ppm x 4.9930 V + 6 ppm x 100 V = 224.7 uV + 600 uV = 824.7 uV`: 3.7
times worse, and all of the difference is in the range term, which grew twelvefold while the
reading term did not move.

**The interval is part of the specification.** The same 4.9930 V reading is good to 79.9 uV on the
24 hour specification, 164.8 uV on the 90 day and 224.8 uV on the one year. Quoting the 24 hour
figure for a meter calibrated eleven months ago is not a tighter measurement; it is a wrong one.

Accuracy for the other two functions is stated per range in the same form. The rows the SRB-5030
bench uses:

| Function | Range | 1 year, 18 to 28 degC |
| --- | --- | --- |
| AC volts, 1 kHz | 10 V | +/-(0.06% of reading + 0.03% of range) |
| Resistance | 100 kohm | +/-(0.010% of reading + 0.001% of range) |

## 3. Common Commands

| Command | Response | Effect |
| --- | --- | --- |
| `*IDN?` | `MARIDUN,MDN-6100,<serial>,<firmware>` | Identify. |
| `*RST` | none | DC volts, 10 V range. |
| `*CLS` | none | Clear the error queue. |

## 4. Configuration and Reading

| Command | Parameter | Response | Notes |
| --- | --- | --- | --- |
| `CONFigure:VOLTage:DC [<range>]` | volts | none | Select DC volts. The range is optional. |
| `CONFigure:VOLTage:AC` | | none | Select AC volts. |
| `CONFigure:RESistance [<range>]` | ohms | none | Select resistance. |
| `FUNCtion?` | | `"VOLT:DC"` | The selected function, in quotes. |
| `VOLTage:DC:RANGe <n>` | volts | none | Select the smallest range that holds `<n>`. |
| `VOLTage:DC:RANGe?` | | `10.0000` | |
| `READ?` | | `+4.993000E+00` | Take one reading in the selected function. |
| `MEASure:VOLTage:DC? [<range>]` | volts | `+4.993000E+00` | Configure and read in one message. |
| `MEASure:VOLTage:AC?` | | `+2.720000E-03` | |
| `MEASure:RESistance?` | | `+3.288300E+03` | |

A range parameter selects the smallest range that will hold the given value: `VOLT:DC:RANG 5`
selects the 10 V range. Readings are returned in scientific notation with a sign, always in the
base unit: volts, or ohms. There is no unit suffix.

Resistance readings across a board with output capacitance rise while the capacitors charge
through the meter's test current. Allow two seconds before reading, or the number is a measure of
how quickly the program asked, not of the board.

## 5. Errors

`SYSTem:ERRor?` behaves exactly as on the MDN-4010: oldest first, `0,"No error"` when empty, a
ten-entry queue, `-350,"Queue overflow"` beyond that. The codes in section 6 of
`mdn4010-programming-manual.md` are the same codes this instrument returns.

The one behavior worth calling out: selecting a range too small for the signal is not an error.
The meter returns `+9.900000E+37`, the overload reading, and the error queue stays empty. A
program that only checks the error queue will accept that number as a measurement.

## 6. Worked Example

Read the output of a board on the 10 V range, then check the board's output-to-return resistance
with the source off.

    *RST                       -> (no response)
    CONF:VOLT:DC 10            -> (no response)
    READ?                      -> +4.993000E+00
    CONF:RES 100000            -> (no response)
    (wait 2 s)
    READ?                      -> +3.288300E+03
    SYST:ERR?                  -> 0,"No error"

`MEASure:VOLTage:DC? 10` would replace the first three lines. Use the long form when the range has
to be set once and read many times, and the `MEASure` form for a single reading.

## 7. Measurement Uncertainty

The accuracy table above is a limit on the meter alone. A measurement is the meter plus everything
else in the path, and it is reported as a value, an uncertainty, the range and the calibration
interval it was taken under. Maridun recommends the standard treatment, which is four steps and no
judgment.

1. **Reduce every influence to a standard uncertainty.** An accuracy specification is a limit and
   says nothing about where inside it this instrument sits, so treat it as a rectangular
   distribution: a half-width of `a` becomes `a / sqrt(3)`. Display resolution is the same shape:
   one count spans the resolution, so the half-width is half a count.
2. **Measure the repeatability rather than looking it up.** Take n readings, compute their sample
   standard deviation s, and use `s / sqrt(n)`. This is the only line in the budget that gets
   smaller by taking more readings, and it is the only one measured on the day.
3. **Combine by root sum of squares.** Squares, so the largest line is most of the answer and a
   line half the size of another contributes a quarter as much.
4. **Expand.** Multiply the combined standard uncertainty by a coverage factor, k = 2 for about 95
   percent, and state the k alongside the number. An expanded uncertainty quoted without its k is
   ambiguous by a factor of two.

Four influences cover most bench DC measurements with this meter: the meter's accuracy at the
value being measured, the display resolution, the repeatability of the readings, and whatever the
test leads, connections and thermal EMFs in the user's own path contribute. The last is not
Maridun's to specify. It is usually the line that decides the answer.

Two influences are settings and not contributions, and both are in the user's hands:

- **The range.** The range term is fixed, so a reading low on its range is priced mostly by a
  range it never used. Select the smallest range that holds the signal.
- **The interval.** Use the row for the interval since the last calibration, not the tightest row
  in the table.

Once a measurement has an expanded uncertainty, a limit check has three outcomes rather than two.
Guardband the limit by the expanded uncertainty: for an upper limit the acceptance limit is
`limit - U`, for a lower limit `limit + U`. A value inside the acceptance limit passes. A value
outside the limit by more than U fails. A value between the two has not been decided by this
measurement, and the answer is that it cannot be said, which is a result and not a failure of the
procedure.

## 8. Worked Example: an Uncertainty Budget

Ten readings of a nominal 5 V rail on the 10 V range, DC volts, meter calibrated eleven months ago
(so the one year row), ambient 23 degC, mean 4.9930 V, sample standard deviation 60 uV. The user's
fixture record allows +/-200 uV for the lead and connection path.

| Contribution | Value | Distribution | Standard uncertainty |
| --- | --- | --- | --- |
| Meter accuracy, 1 year, 10 V range | +/-224.8 uV | rectangular, /sqrt(3) | 129.8 uV |
| Resolution, 10 uV per count | +/-5.0 uV | rectangular, /sqrt(3) | 2.9 uV |
| Repeatability, 10 readings | s = 60 uV | s/sqrt(n) | 19.0 uV |
| Leads and connections | +/-200 uV | rectangular, /sqrt(3) | 115.5 uV |
| **Combined** | | root sum of squares | **174.8 uV** |
| **Expanded, k = 2** | | | **349.5 uV** |

Report it as 4.9930 V +/-0.00035 V, k = 2, 10 V range, one year specification. Against limits of
4.9500 V and 5.0500 V the guardbanded acceptance band is 4.95035 V to 5.04965 V, and this reading
passes with room to spare.

The budget also says what to fix. The meter and the leads are the two lines that matter, they are
comparable in size, and the meter's own accuracy is not the largest one. Taking a hundred readings
instead of ten would move the total by less than 2 uV.

Two variations on the same reading, for comparison:

- **On the 100 V range instead of the 10 V range**: the meter line becomes 476.1 uV, the
  resolution line 28.9 uV, and the expanded uncertainty 982.3 uV instead of 349.5 uV. The reading
  is the same. The measurement is 2.8 times worse, and the error queue says nothing.
- **At 35 degC instead of 23 degC**: seven degrees outside the band adds
  `7 x (3.5 ppm x 4.9930 V + 0.5 ppm x 10 V) = 157.3 uV` to the meter's limit, taking it from
  224.8 uV to 382.1 uV.
