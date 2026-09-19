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

One year, 18 to 28 degC, after a 30 minute warm-up.

| Function | Range | Accuracy |
| --- | --- | --- |
| DC volts | 10 V | +/-(0.0035% of reading + 0.0005% of range) |
| DC volts | 100 V | +/-(0.0045% of reading + 0.0006% of range) |
| AC volts | 10 V, 1 kHz | +/-(0.06% of reading + 0.03% of range) |
| Resistance | 100 kohm | +/-(0.010% of reading + 0.001% of range) |

On the 10 V range, 0.0005 percent of range is 50 uV. A 5 V reading is therefore good to about
225 uV, which is two orders of magnitude finer than the 100 mV window the production test applies
to it. The meter is not the limiting term in that measurement; the fixture path is.

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
