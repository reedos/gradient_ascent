# Tarnley TRN-2400 Programmable Electronic Load: Programming Manual

Tarnley Test Systems. Firmware 3.02, manual revision B, 07/08/2026. The TRN-2400 is a single-input
electronic load, 0 to 60 V, 0 to 30 A, 300 W, with constant current, constant resistance and
constant voltage modes.

Read section 2 before writing anything against this instrument. Tarnley firmware is SCPI style but
is not interchangeable with Maridun firmware, and the three differences below are the ones that
break a script that was written against a Maridun manual and pointed at this load.

## 1. Ranges, Resolution and Accuracy

| Parameter | Range | Resolution | Accuracy, 1 year |
| --- | --- | --- | --- |
| Input voltage | 0 to 60.00 V | 1 mV | +/-(0.05% of reading + 5 mV) |
| Constant current | 0 to 30.000 A | 1 mA | +/-(0.1% of setting + 10 mA) |
| Current readback | 0 to 30.000 A | 0.1 mA | +/-(0.1% of reading + 5 mA) |
| Constant resistance | 0.05 to 10000 ohm | 4 digits | +/-(0.5% of setting + 20 mohm) |
| Input power | 300 W maximum | | |
| Slew rate, CC mode | 0.1 to 2.5 A/us | | |

The load needs at least 1.2 V across its terminals to sink its full current. Below that it sinks
less than the set point, silently. A test that loads a 5 V rail is well clear of this.

## 2. Syntax: Three Differences From Maridun Firmware

**Short keyword form only.** This instrument accepts `CURR` and rejects `CURRENT` with
`-113,"Undefined header"`. There is no long form. The keyword table in section 3 is the whole
vocabulary.

**Booleans are 1 and 0, never ON and OFF.** `INP 1` enables the input. `INP ON` is rejected with
`-224,"Illegal parameter value"`. This is the single most common mistake made against this
instrument.

**Responses carry a unit suffix.** `MEAS:VOLT?` answers `4.9930V`, not `4.9930`. `MEAS:CURR?`
answers `1.0000A`. `RES?` answers `1000.0000OHM`. A program that calls `float()` on the response
raises rather than returning a wrong number, which is the good case; a program that slices a fixed
number of characters does return a wrong number.

One command per message, as on every instrument on this bench. A semicolon or a second parameter
is rejected with `-108,"Parameter not allowed"`.

## 3. Commands

| Command | Parameter | Response | Notes |
| --- | --- | --- | --- |
| `*IDN?` | | `TARNLEY,TRN-2400,<serial>,<firmware>` | |
| `*RST` | | none | Input off, CC mode, 0.0000 A. |
| `*CLS` | | none | Clear the error queue. |
| `MODE <mode>` | `CC`, `CR`, `CV` | none | Select the regulation mode. |
| `MODE?` | | `CC` | No unit suffix: this one is a keyword. |
| `CURR <n>` | 0 to 30.000 | none | Constant current set point, amps. |
| `CURR?` | | `1.0000A` | The set point. |
| `RES <n>` | 0.05 to 10000 | none | Constant resistance set point, ohms. |
| `RES?` | | `1000.0000OHM` | |
| `INP <state>` | `1`, `0` | none | Enable or disable the input. |
| `INP?` | | `1` or `0` | No suffix. |
| `MEAS:VOLT?` | | `4.9930V` | Terminal voltage. |
| `MEAS:CURR?` | | `1.0000A` | Current being sunk. Reads `0.0000A` with the input off. |

`CURR` sets the constant-current set point whether or not CC mode is selected, and whether or not
the input is enabled. Setting the current does not enable the input; `INP 1` does that, and it is
the command that actually puts a load on a board.

## 4. Errors

`SYST:ERR?` returns `<code>,"<text>"`, oldest first, `0,"No error"` when the queue is empty, ten
entries deep. The codes are the standard ones; see section 6 of `mdn4010-programming-manual.md`
for the list, which this firmware follows exactly.

Note that `-113` here means either a command this instrument does not have or a long keyword form
it does not accept. The two cases are not distinguished in the message text.

## 5. Sequencing a Load Step

The order matters and is not interchangeable.

1. `MODE CC`
2. `CURR <amps>`
3. `INP 1`
4. Wait 100 ms for the board and the load to settle.
5. Read.

To change the load current with the input already on, send `CURR <amps>` and wait 100 ms again.
Do not disable and re-enable the input to change a set point: the board sees a load dump and a
reapplication, and the transient is not what the test is measuring.

Always disable the load input before the source output at the end of a sequence. Removing the
input voltage while the load is still sinking current pulls the board's output capacitors down
through the load and stresses the output stage.

## 6. Worked Example

Load a board at 1.000 A and read its terminal voltage and the actual current.

    *RST                    -> (no response)
    MODE CC                 -> (no response)
    CURR 1.0000             -> (no response)
    SYST:ERR?               -> 0,"No error"
    INP 1                   -> (no response)
    (wait 100 ms)
    MEAS:VOLT?              -> 4.9930V
    MEAS:CURR?              -> 1.0000A
    INP 0                   -> (no response)

The two readings come back as `4.9930V` and `1.0000A`. Strip the suffix before comparing either
one against a limit. A limit check against the string is a limit check against nothing.
