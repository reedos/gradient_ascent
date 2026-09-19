# Tarnley TRN-1102 Digital Oscilloscope: Programming Manual

Tarnley Test Systems. Firmware 5.41, manual revision A, 02/20/2026. Two channels, 100 MHz
bandwidth, 1 GSa/s, 8-bit vertical resolution, 8 vertical divisions and 10 horizontal divisions.
The syntax conventions are Tarnley's, the same three as the TRN-2400: short keyword form only,
`1` and `0` rather than `ON` and `OFF`, and a unit suffix on numeric responses.

## 1. Vertical and Horizontal Settings

| Setting | Values |
| --- | --- |
| Vertical scale, per division | 1, 2, 5, 10, 20, 50, 100, 200, 500 mV and 1, 2, 5 V |
| Coupling | `AC`, `DC`, `GND` |
| Bandwidth limit | 20 MHz, on or off |
| Timebase, per division | 1 ns to 50 s in a 1-2-5 sequence |

At 8 bits over 8 divisions, one least significant bit is the vertical scale divided by 32. On the
10 mV per division setting that is 312 uV, which resolves a 20 mV ripple well. On a 1 V per
division setting, the same ripple is one third of one bit and is not measurable at all. This is
why ripple is measured AC coupled: DC coupling puts the whole 5 V rail on screen and forces a
scale that cannot see the ripple.

## 2. Commands

| Command | Parameter | Response | Notes |
| --- | --- | --- | --- |
| `*IDN?` | | `TARNLEY,TRN-1102,<serial>,<firmware>` | |
| `*RST` | | none | Both channels DC, 1 V/div, bandwidth limit off, 1 ms/div. |
| `*CLS` | | none | Clear the error queue. |
| `CHAN1:COUP <c>` | `AC`, `DC`, `GND` | none | Channel 1 coupling. `CHAN2:COUP` likewise. |
| `CHAN1:COUP?` | | `AC` | |
| `CHAN1:SCAL <n>` | volts per division | none | Snapped to the nearest listed value. |
| `CHAN1:SCAL?` | | `0.0100V` | |
| `CHAN1:BWL <state>` | `1`, `0` | none | 20 MHz bandwidth limit. |
| `CHAN1:BWL?` | | `1` or `0` | |
| `TIM:SCAL <n>` | seconds per division | none | |
| `TIM:SCAL?` | | `2.000E-06S` | |
| `SING` | | none | Arm and take one acquisition. |
| `MEAS:VPP? <source>` | `CHAN1`, `CHAN2` | `2.1924E-02V` | Peak to peak of the last acquisition. |

`CHANnel1` is not accepted; `CHAN1` is the only spelling. `MEAS:VPP?` requires its source
parameter: without one it returns `-109,"Missing parameter"`.

## 3. Acquisition

`MEAS:VPP?` measures the acquisition that is already in memory. It does not trigger one. Sending
it before any `SING` returns `-221,"Settings conflict"` rather than a stale number, which is the
one place this firmware is friendlier than most.

Send `SING`, then read. Reading twice without a second `SING` returns the same number twice: that
is not noise-free measurement, it is the same acquisition.

## 4. Measuring Ripple on a Switching Regulator

Four settings, all four of which change the number:

1. `CHAN1:COUP AC`. DC coupling cannot resolve a 20 mV ripple on a 5 V rail.
2. `CHAN1:BWL 1`. With the 20 MHz limit off, switching-edge ringing roughly doubles the reading on
   a board like the SRB-5030. Both numbers are real; they are answers to different questions.
3. `CHAN1:SCAL 0.01`. Ten millivolts per division puts a 20 mV ripple across two divisions.
4. `TIM:SCAL 2e-6`. Two microseconds per division shows ten switching cycles at 500 kHz.

Probe the output test point with a 1:1 probe and a ground spring, not a ground lead. A 15 cm
ground lead is an antenna at the frequencies in a switching edge and will add ringing that is not
present on the board.

## 5. Worked Example

Measure output ripple to the production test specification.

    *RST                    -> (no response)
    CHAN1:COUP AC           -> (no response)
    CHAN1:BWL 1             -> (no response)
    CHAN1:SCAL 0.01         -> (no response)
    TIM:SCAL 2e-6           -> (no response)
    SYST:ERR?               -> 0,"No error"
    SING                    -> (no response)
    MEAS:VPP? CHAN1         -> 2.1924E-02V

The response is 21.924 mV. Strip the `V`, convert to millivolts, and compare against the 50 mV
limit in `srb5030-test-spec.md` section 4. Do not compare the volts figure against the millivolt
limit; a factor of a thousand in the passing direction is the easiest error in this whole sequence
to make and the hardest to notice.
