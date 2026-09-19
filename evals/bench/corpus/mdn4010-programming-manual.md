# Maridun MDN-4010 Programmable DC Power Supply: Programming Manual

Maridun Instruments. Firmware 2.14, manual revision D, 05/29/2026. Covers the MDN-4010 only. The
MDN-4010 is a single-output supply, 0 to 40 V and 0 to 10 A, with a maximum output power of 200 W.
The command set is SCPI style and follows IEEE 488.2 for the common commands.

## 1. Interface and Conventions

The instrument accepts commands over USB, LAN and GPIB. All three carry the same command set.
Terminate every message with a line feed. The response to a query is a single line, also
terminated with a line feed.

Keywords are shown with the short form capitalized: `VOLTage` means that both `VOLT` and `VOLTAGE`
are accepted, in any mix of upper and lower case. A query is the same keyword with `?` appended.
Send one command per message. A message containing a semicolon, a comma, or a second parameter is
rejected with error -108; this instrument does not accept compound messages.

Numeric parameters are decimal, with an optional sign and an optional exponent. Unit suffixes are
not accepted on input, and are not returned on output: a query answers with a bare number.

## 2. Ranges, Resolution and Accuracy

| Parameter | Range | Resolution | Accuracy, 1 year, 18 to 28 degC |
| --- | --- | --- | --- |
| Voltage programming | 0 to 40.000 V | 1 mV | +/-(0.05% of setting + 10 mV) |
| Current limit programming | 0 to 10.000 A | 1 mA | +/-(0.1% of setting + 5 mA) |
| Voltage readback | 0 to 40.000 V | 0.1 mV | +/-(0.05% of reading + 5 mV) |
| Current readback | 0 to 10.000 A | 0.1 mA | +/-(0.1% of reading + 3 mA) |
| Output power | 200 W maximum | | |

A programmed value outside its range is rejected with error -222 and the previous setting is kept.
The instrument does not clip a set point into range.

After a voltage or current step, allow 30 ms before taking a reading. The output settles to within
0.1 percent of the new value in that time with a resistive load.

## 3. Common Commands

| Command | Response | Effect |
| --- | --- | --- |
| `*IDN?` | `MARIDUN,MDN-4010,<serial>,<firmware>` | Identify. |
| `*RST` | none | Output off, voltage 0.000 V, current limit 0.100 A. |
| `*CLS` | none | Clear the error queue. |

`*RST` turns the output off before it changes the set points, so a board on the bench sees the
output drop rather than a new voltage.

## 4. Source Commands

| Command | Parameter | Response | Notes |
| --- | --- | --- | --- |
| `VOLTage <n>` | 0 to 40.000 | none | Set the output voltage in volts. |
| `VOLTage?` | | `24.000` | The set point, not a measurement. |
| `CURRent <n>` | 0 to 10.000 | none | Set the current limit in amps. |
| `CURRent?` | | `4.000` | The limit, not a measurement. |
| `OUTPut <state>` | `ON`, `OFF`, `1`, `0` | none | Enable or disable the output. |
| `OUTPut?` | | `1` or `0` | |

Setting a voltage or a current limit while the output is on takes effect immediately. There is no
separate apply step and no way to stage a set point.

## 5. Measurement Commands

| Command | Response | Notes |
| --- | --- | --- |
| `MEASure:VOLTage?` | `24.0000` | Volts at the output terminals. Reads 0.0000 with the output off. |
| `MEASure:CURRent?` | `0.2270` | Amps delivered. Reads 0.0000 with the output off. |

Both are live measurements at the terminals and are not the same as `VOLTage?` and `CURRent?`,
which report set points. A supply in current limit measures a terminal voltage below its set
point; comparing the two is how a program detects that condition.

## 6. Errors and the Error Queue

`SYSTem:ERRor?` removes the oldest error from the queue and returns it as `<code>,"<text>"`. When
the queue is empty it returns `0,"No error"`. The queue holds ten entries; an eleventh is
discarded and `-350,"Queue overflow"` is returned after the ten that were kept.

| Code | Text | Cause |
| --- | --- | --- |
| 0 | No error | Queue empty. |
| -100 | Command error | Message empty or unparsable. |
| -108 | Parameter not allowed | More than one parameter, or more than one command in a message. |
| -109 | Missing parameter | A set command with no value. |
| -113 | Undefined header | A command this instrument does not have. |
| -222 | Data out of range | A numeric parameter outside the range in section 2. |
| -224 | Illegal parameter value | A parameter that is not a number, or not a listed keyword. |
| -350 | Queue overflow | More than ten errors since the last read or `*CLS`. |

A rejected command changes nothing and returns nothing. It is not an error on the interface: the
program has to ask. Read `SYSTem:ERRor?` after any sequence that sets state, or a typo in a set
point will look exactly like a board that measured wrong.

## 7. Worked Example

Bring a board up at 24 V with a 1 A limit, read back the input current, and shut down.

    *RST                    -> (no response)
    VOLT 24.000             -> (no response)
    CURR 1.000              -> (no response)
    SYST:ERR?               -> 0,"No error"
    OUTP ON                 -> (no response)
    (wait 30 ms)
    MEAS:VOLT?              -> 24.0000
    MEAS:CURR?              -> 0.2270
    OUTP OFF                -> (no response)
    SYST:ERR?               -> 0,"No error"

The `SYSTem:ERRor?` before the output is enabled is the point of the sequence. Both set points are
confirmed accepted before anything is energized, and the second read confirms nothing was rejected
while the board was live.
