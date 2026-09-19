"""The simulated electronics test bench: one device under test, four instruments, one envelope.

Everything here is invented. Orbeck Power Systems, the SRB-5030 regulator board, Maridun
Instruments and Tarnley Test Systems are fictional, the way "Halvorsen" is fictional in
`evals/corpus/`. The physics is not: the numbers this module produces are computed from the
inductor, capacitor, switching frequency and loss terms written down in
`evals/bench/corpus/srb5030-datasheet.md`, and `docs/THE-BENCH.md` shows the arithmetic.

Three pieces:

1. `Dut` -- a model of one SRB-5030 board. Given an input voltage and a load current it returns
   the output voltage, the input current, the inductor ripple current and the output ripple. It
   is pure arithmetic and has no randomness: a board's unit-to-unit variation is carried in the
   fields (`vout_offset_v`, `cout_f`, `ilim_a`), so a caller that wants a population seeds the
   variation itself. `evals/bench/make_data.py` does exactly that, which is why the CSVs and the
   simulated instruments describe the same board.

2. Four instruments, each behind one `send(command: str) -> str` method: `PowerSupply`,
   `Multimeter`, `ElectronicLoad` and `Oscilloscope`. They implement the SCPI-style command set
   their programming manuals document and nothing else. An undocumented command returns the
   empty string and pushes the documented error onto the error queue, where `SYST:ERR?` reads it.
   Wiring is explicit: `Bench` connects the supply to the DUT input and the load to the DUT
   output, and every measurement is computed from the DUT model through that wiring.

3. `SafetyEnvelope`, `Approval` and `GuardedSupply` -- the code-side limits. The model never
   drives an instrument directly in any example on this site: it proposes a command, code checks
   it against the envelope, a person approves the output enable, and only then does the
   (simulated) instrument act. The envelope refuses negative and non-finite values, values over
   its ceiling by any margin at all, an output enable with no approval, an approval that does not
   match the set point it is being used for, a reused approval, and any message that tries to set
   two things at once.

Standard library only, deterministic, no network. `tests/test_bench.py` is the contract.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# The device under test
# ---------------------------------------------------------------------------

#: Every constant the DUT model uses, in SI units, as the datasheet states them.
VOUT_NOM_V = 5.000
VIN_MIN_V = 9.0
VIN_MAX_DATASHEET_V = 36.0  # Rev B datasheet, superseded for Rev A/B boards by ECN-2608-04
VIN_MAX_ECN_V = 32.0  # ECN-2608-04: input capacitor derating, Rev A and Rev B
VIN_ABS_MAX_V = 40.0
IOUT_MAX_A = 3.0
FSW_HZ = 500_000.0
L_H = 10.0e-6
COUT_F = 24.0e-6  # two 22 uF 25 V X7R parts, derated to about 12 uF each at 5 V bias
COUT_ESR_OHM = 0.0015
UVLO_RISING_V = 8.2
UVLO_FALLING_V = 7.8

#: Regulation coefficients. Line: volts of output shift per volt of input, referred to 24 V.
#: Load: volts of output droop per amp. Both are first order and both are what the datasheet's
#: line and load regulation figures are computed from; see docs/THE-BENCH.md.
LINE_COEFF_V_PER_V = 0.00025
LOAD_COEFF_V_PER_A = 0.00700

#: Loss terms. `R_LOSS_OHM` is the conduction path (inductor DCR plus the two FETs plus board
#: and connector resistance); `K_SW_W_PER_VA` is switching loss, which grows with both the input
#: voltage and the current; the quiescent terms are the control and gate-drive draw with no load.
R_LOSS_OHM = 0.065
K_SW_W_PER_VA = 0.005
IQ_A = 0.0040
IQ_PER_V_A = 0.00030

ILIM_NOM_A = 4.2

#: Switching-edge ringing the probe sees on top of the inductor-capacitor ripple. This is a
#: property of the measurement, not of the regulator, which is why it is a separate field: the
#: datasheet quotes both numbers and says which is which.
RINGING_V = 0.0125


@dataclass(frozen=True)
class Dut:
    """One Orbeck SRB-5030 step-down regulator board.

    Defaults describe a typical board. A population is made by varying the three fields that
    actually vary unit to unit: the feedback offset (reference tolerance and divider tolerance),
    the effective output capacitance (part tolerance and DC bias derating) and the current limit.
    """

    serial: str = "SRB5030-TYPICAL"
    vout_offset_v: float = 0.0
    cout_f: float = COUT_F
    ilim_a: float = ILIM_NOM_A
    r_loss_ohm: float = R_LOSS_OHM
    ringing_v: float = RINGING_V
    #: Set on a board whose output is dead: no output at any input voltage.
    dead: bool = False
    #: DC resistance the first test step measures, input to return and output to return. A good
    #: board looks like a discharged capacitor with a bleed path; a shorted one reads near zero.
    input_res_ohm: float = 47_000.0
    output_res_ohm: float = 3_300.0

    # -- operating point -------------------------------------------------

    def powered(self, vin_v: float) -> bool:
        """True when the input is above the undervoltage lockout threshold."""
        return not self.dead and vin_v >= UVLO_RISING_V

    def vout_v(self, vin_v: float, iout_a: float) -> float:
        """Output voltage at this input voltage and load current.

        Below the lockout threshold the output is off. Above the current limit the regulator
        folds back: the model holds output power at roughly the limit point, which is the
        behavior the overcurrent test step looks for, not a claim about the exact foldback curve.
        """
        if not self.powered(vin_v):
            return 0.0
        ideal = (
            VOUT_NOM_V
            + LINE_COEFF_V_PER_V * (vin_v - 24.0)
            - LOAD_COEFF_V_PER_A * iout_a
            + self.vout_offset_v
        )
        if iout_a > self.ilim_a:
            return max(0.0, ideal * self.ilim_a / iout_a)
        return ideal

    def loss_w(self, vin_v: float, iout_a: float) -> float:
        """Power lost in the board: quiescent, switching, and conduction."""
        if not self.powered(vin_v):
            return 0.0
        quiescent = vin_v * (IQ_A + IQ_PER_V_A * vin_v)
        switching = K_SW_W_PER_VA * vin_v * iout_a
        conduction = self.r_loss_ohm * iout_a * iout_a
        return quiescent + switching + conduction

    def iin_a(self, vin_v: float, iout_a: float) -> float:
        """Input current: output power plus losses, divided by the input voltage."""
        if not self.powered(vin_v) or vin_v <= 0.0:
            return 0.0
        pout = self.vout_v(vin_v, iout_a) * iout_a
        return (pout + self.loss_w(vin_v, iout_a)) / vin_v

    def efficiency_pct(self, vin_v: float, iout_a: float) -> float:
        """Output power over input power, as a percentage. The only definition this site uses."""
        pin = vin_v * self.iin_a(vin_v, iout_a)
        if pin <= 0.0:
            return 0.0
        return 100.0 * self.vout_v(vin_v, iout_a) * iout_a / pin

    # -- ripple ----------------------------------------------------------

    def inductor_ripple_a(self, vin_v: float, iout_a: float) -> float:
        """Peak-to-peak inductor current ripple, (Vin - Vout) * D / (L * fsw) with D = Vout/Vin."""
        vout = self.vout_v(vin_v, iout_a)
        if not self.powered(vin_v) or vin_v <= 0.0 or vout <= 0.0:
            return 0.0
        duty = vout / vin_v
        return (vin_v - vout) * duty / (L_H * FSW_HZ)

    def lc_ripple_v(self, vin_v: float, iout_a: float) -> float:
        """Output ripple from the inductor and capacitor alone: dI/(8*C*fsw) plus dI*ESR."""
        dil = self.inductor_ripple_a(vin_v, iout_a)
        if dil <= 0.0 or self.cout_f <= 0.0:
            return 0.0
        return dil / (8.0 * self.cout_f * FSW_HZ) + dil * COUT_ESR_OHM

    def measured_ripple_v(self, vin_v: float, iout_a: float) -> float:
        """What a scope reads at the output test point: the ripple above plus edge ringing."""
        if not self.powered(vin_v):
            return 0.0
        return self.lc_ripple_v(vin_v, iout_a) + self.ringing_v


# ---------------------------------------------------------------------------
# SCPI-style instruments
# ---------------------------------------------------------------------------

#: Error codes, as every programming manual in `evals/bench/corpus/` documents them. The negative
#: codes and their wording come from the SCPI standard's error list; positive codes are
#: device specific and none of these instruments define one.
NO_ERROR = '0,"No error"'
ERR_COMMAND = '-100,"Command error"'
ERR_PARAM_NOT_ALLOWED = '-108,"Parameter not allowed"'
ERR_MISSING_PARAM = '-109,"Missing parameter"'
ERR_UNDEFINED_HEADER = '-113,"Undefined header"'
ERR_SETTINGS_CONFLICT = '-221,"Settings conflict"'
ERR_OUT_OF_RANGE = '-222,"Data out of range"'
ERR_ILLEGAL_VALUE = '-224,"Illegal parameter value"'
ERR_QUEUE_OVERFLOW = '-350,"Queue overflow"'

ERROR_QUEUE_DEPTH = 10

#: Long form to short form, for every keyword these four instruments use. SCPI lets a program
#: spell a keyword either way; the manuals print the long form with the short form capitalized
#: (`VOLTage`), and this table is how the simulation honors both.
_KEYWORDS = {
    "VOLTAGE": "VOLT",
    "CURRENT": "CURR",
    "RESISTANCE": "RES",
    "OUTPUT": "OUTP",
    "INPUT": "INP",
    "MEASURE": "MEAS",
    "CONFIGURE": "CONF",
    "FUNCTION": "FUNC",
    "RANGE": "RANG",
    "SYSTEM": "SYST",
    "ERROR": "ERR",
    "CHANNEL": "CHAN",
    "TIMEBASE": "TIM",
    "SCALE": "SCAL",
    "COUPLING": "COUP",
    "BWLIMIT": "BWL",
    "SINGLE": "SING",
    "PROTECTION": "PROT",
    "STATE": "STAT",
    "TRANSIENT": "TRAN",
    "CHANNEL1": "CHAN1",
    "CHANNEL2": "CHAN2",
}

_NUMBER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
_ON_OFF = {"ON": True, "1": True, "OFF": False, "0": False}


def _normalize(header: str) -> str:
    """`MEASure:VOLTage:DC?` -> `MEAS:VOLT:DC?`. Case and long form both collapse here."""
    return _normalize_parts(header)[0]


def _normalize_parts(header: str) -> tuple[str, bool]:
    """Normalize a header, and say whether any node arrived in its long form.

    The second value matters because the two vendors on this bench do not agree about long
    forms: Maridun accepts either spelling, Tarnley accepts the short form only. That is the
    kind of difference two instruments that both claim SCPI compliance really do have, and the
    reason a script drafted from one manual cannot be pointed at the other instrument.
    """
    query = header.endswith("?")
    body = header[:-1] if query else header
    nodes = []
    long_form = False
    for node in body.split(":"):
        upper = node.strip().upper()
        short = _KEYWORDS.get(upper, upper)
        if short != upper:
            long_form = True
        nodes.append(short)
    return ":".join(nodes) + ("?" if query else ""), long_form


def parse_number(text: str) -> float:
    """Parse one SCPI numeric parameter, or raise ValueError.

    Rejects everything the manuals say is not a number, including the spellings Python's own
    `float()` accepts and an instrument does not: `nan`, `inf`, `infinity`, and hex or underscore
    forms. This is the first line of the safety story: a set point that is not a number must be
    refused before anything decides whether it is inside a limit, because every comparison
    against NaN is false.
    """
    stripped = text.strip()
    if not _NUMBER_RE.match(stripped):
        raise ValueError(f"not a numeric parameter: {text!r}")
    value = float(stripped)
    if not math.isfinite(value):
        raise ValueError(f"not a finite number: {text!r}")
    return value


class ScpiError(Exception):
    """Raised inside a handler to push one documented error onto the queue."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class Instrument:
    """Shared SCPI message handling: one command per message, an error queue, `*IDN?`, `*RST`.

    Subclasses declare `IDN`, fill `_handlers` with normalized headers, and implement `_reset`.

    Three class attributes carry the vendor differences the manuals document. They are not
    decoration: an example that drafts a command from the Maridun manual and sends it to the
    Tarnley load gets a documented error, which is exactly what happens on a real bench.
    """

    IDN = "GENERIC,INSTRUMENT,0,0.0"
    #: Maridun firmware accepts `VOLTage` and `VOLT` alike. Tarnley firmware accepts `VOLT` only.
    ACCEPTS_LONG_FORM = True
    #: Maridun accepts `ON`/`OFF` as well as `1`/`0` for a boolean. Tarnley accepts `1`/`0` only.
    ACCEPTS_ON_OFF_WORDS = True
    #: Tarnley query responses carry a unit suffix (`4.9930V`); Maridun's are bare numbers.
    UNIT_SUFFIX = False

    def __init__(self) -> None:
        self._errors: list[str] = []
        self._overflowed = False
        self._handlers: dict[str, object] = {}
        self._install()
        self._reset()

    # -- subclass hooks --------------------------------------------------

    def _install(self) -> None:  # pragma: no cover - overridden by every instrument
        raise NotImplementedError

    def _reset(self) -> None:  # pragma: no cover - overridden by every instrument
        raise NotImplementedError

    # -- error queue -----------------------------------------------------

    def _push_error(self, code: str) -> None:
        if len(self._errors) >= ERROR_QUEUE_DEPTH:
            self._overflowed = True
            return
        self._errors.append(code)

    def _pop_error(self) -> str:
        if self._errors:
            # The ten that were kept come out first, oldest first; the overflow marker follows
            # them, which is what the manuals say and is the order that lets a program tell
            # "ten errors" from "more than ten errors".
            return self._errors.pop(0)
        if self._overflowed:
            self._overflowed = False
            return ERR_QUEUE_OVERFLOW
        return NO_ERROR

    @property
    def error_queue(self) -> list[str]:
        """The queue as it stands, for a test or a log. Reading this does not drain it."""
        return list(self._errors)

    # -- the one public method -------------------------------------------

    def send(self, command: str) -> str:
        """Send one message. Returns the response for a query, the empty string otherwise.

        A message that the instrument cannot carry out never raises: it returns the empty string
        and leaves the documented error in the queue, which is what a real instrument does and
        what makes `SYST:ERR?` worth reading after every step.
        """
        if not isinstance(command, str):
            self._push_error(ERR_COMMAND)
            return ""
        message = command.strip()
        if not message:
            self._push_error(ERR_COMMAND)
            return ""
        if ";" in message:
            # One command per message: the manuals say so, and the envelope depends on it.
            self._push_error(ERR_PARAM_NOT_ALLOWED)
            return ""
        parts = message.split(None, 1)
        header, long_form = _normalize_parts(parts[0])
        if long_form and not self.ACCEPTS_LONG_FORM:
            self._push_error(ERR_UNDEFINED_HEADER)
            return ""
        argument = parts[1].strip() if len(parts) > 1 else None
        if argument is not None and "," in argument:
            self._push_error(ERR_PARAM_NOT_ALLOWED)
            return ""
        if argument is not None and len(argument.split()) > 1:
            self._push_error(ERR_PARAM_NOT_ALLOWED)
            return ""

        if header == "*IDN?":
            return self.IDN
        if header == "*RST":
            self._reset()
            return ""
        if header == "*CLS":
            self._errors.clear()
            self._overflowed = False
            return ""
        if header == "SYST:ERR?":
            return self._pop_error()

        handler = self._handlers.get(header)
        if handler is None:
            self._push_error(ERR_UNDEFINED_HEADER)
            return ""
        try:
            return handler(argument) or ""  # type: ignore[operator]
        except ScpiError as exc:
            self._push_error(exc.code)
            return ""

    # -- helpers for handlers ---------------------------------------------

    @staticmethod
    def _require(argument: str | None) -> str:
        if argument is None:
            raise ScpiError(ERR_MISSING_PARAM)
        return argument

    @staticmethod
    def _no_argument(argument: str | None) -> None:
        if argument is not None:
            raise ScpiError(ERR_PARAM_NOT_ALLOWED)

    @classmethod
    def _number(cls, argument: str | None, low: float, high: float) -> float:
        text = cls._require(argument)
        try:
            value = parse_number(text)
        except ValueError:
            raise ScpiError(ERR_ILLEGAL_VALUE) from None
        if value < low or value > high:
            raise ScpiError(ERR_OUT_OF_RANGE)
        return value

    @classmethod
    def _on_off(cls, argument: str | None) -> bool:
        text = cls._require(argument).upper()
        if text not in _ON_OFF:
            raise ScpiError(ERR_ILLEGAL_VALUE)
        if text in ("ON", "OFF") and not cls.ACCEPTS_ON_OFF_WORDS:
            raise ScpiError(ERR_ILLEGAL_VALUE)
        return _ON_OFF[text]

    @classmethod
    def _value(cls, text: str, unit: str) -> str:
        """Format one numeric response, with this vendor's unit suffix or without it."""
        return f"{text}{unit}" if cls.UNIT_SUFFIX else text


@dataclass
class Wiring:
    """What is connected to what. The instruments read the DUT through this, not directly."""

    dut: Dut = field(default_factory=Dut)
    #: The supply drives the DUT input; set False for an instrument standing on its own.
    supply_drives_dut: bool = True
    #: A fixed offset the fixture's measurement path adds to a DMM DC volts reading, in volts.
    #: This is how a miscalibrated fixture channel is modeled; see `docs/THE-BENCH.md`.
    dmm_offset_v: float = 0.0
    #: The node voltages the meters read, recomputed by `Bench.refresh`.
    input_voltage_v: float = 0.0
    load_current_a: float = 0.0


class PowerSupply(Instrument):
    """Maridun Instruments MDN-4010, 0 to 40 V, 0 to 10 A, 200 W.

    Documented in `evals/bench/corpus/mdn4010-programming-manual.md`.
    """

    IDN = "MARIDUN,MDN-4010,MY26014477,2.14"
    MAX_VOLTAGE_V = 40.0
    MAX_CURRENT_A = 10.0

    def __init__(self, wiring: Wiring | None = None) -> None:
        self.wiring = wiring if wiring is not None else Wiring()
        super().__init__()

    def _reset(self) -> None:
        self.voltage_setpoint_v = 0.0
        self.current_limit_a = 0.1
        self.output_on = False

    def _install(self) -> None:
        self._handlers = {
            "VOLT": self._set_voltage,
            "VOLT?": self._get_voltage,
            "CURR": self._set_current,
            "CURR?": self._get_current,
            "OUTP": self._set_output,
            "OUTP?": self._get_output,
            "MEAS:VOLT?": self._meas_voltage,
            "MEAS:CURR?": self._meas_current,
        }

    # -- state -----------------------------------------------------------

    def _set_voltage(self, argument: str | None) -> None:
        self.voltage_setpoint_v = round(self._number(argument, 0.0, self.MAX_VOLTAGE_V), 3)

    def _get_voltage(self, argument: str | None) -> str:
        self._no_argument(argument)
        return f"{self.voltage_setpoint_v:.3f}"

    def _set_current(self, argument: str | None) -> None:
        self.current_limit_a = round(self._number(argument, 0.0, self.MAX_CURRENT_A), 3)

    def _get_current(self, argument: str | None) -> str:
        self._no_argument(argument)
        return f"{self.current_limit_a:.3f}"

    def _set_output(self, argument: str | None) -> None:
        self.output_on = self._on_off(argument)

    def _get_output(self, argument: str | None) -> str:
        self._no_argument(argument)
        return "1" if self.output_on else "0"

    # -- measurement -----------------------------------------------------

    def terminal_voltage_v(self) -> float:
        """What the supply's terminals actually sit at, current limit and all."""
        if not self.output_on:
            return 0.0
        if not self.wiring.supply_drives_dut:
            return self.voltage_setpoint_v
        draw = self.wiring.dut.iin_a(self.voltage_setpoint_v, self._load_current_a())
        if draw > self.current_limit_a:
            # In constant current the supply drops its voltage until the draw fits the limit.
            # The DUT then collapses; reporting zero is close enough for a fold-back that this
            # bench treats as a failure either way.
            return 0.0
        return self.voltage_setpoint_v

    def _load_current_a(self) -> float:
        return float(self.wiring.load_current_a)

    def _meas_voltage(self, argument: str | None) -> str:
        self._no_argument(argument)
        return f"{self.terminal_voltage_v():.4f}"

    def _meas_current(self, argument: str | None) -> str:
        self._no_argument(argument)
        if not self.output_on:
            return "0.0000"
        vin = self.terminal_voltage_v()
        if vin <= 0.0:
            return f"{self.current_limit_a:.4f}"
        return f"{self.wiring.dut.iin_a(vin, self._load_current_a()):.4f}"


class Multimeter(Instrument):
    """Maridun Instruments MDN-6100, 6 1/2 digit DC volts, AC volts and resistance.

    Documented in `evals/bench/corpus/mdn6100-programming-manual.md`.
    """

    IDN = "MARIDUN,MDN-6100,MY26030912,1.08"
    DC_RANGES_V = (0.1, 1.0, 10.0, 100.0, 1000.0)
    RES_RANGES_OHM = (100.0, 1000.0, 1.0e4, 1.0e5, 1.0e6, 1.0e7, 1.0e8)

    def __init__(self, wiring: Wiring | None = None) -> None:
        self.wiring = wiring if wiring is not None else Wiring()
        #: Which node the leads are on: "vout", "vin", or "open".
        self.probe = "vout"
        super().__init__()

    def _reset(self) -> None:
        self.function = "VOLT:DC"
        self.dc_range_v = 10.0
        self.res_range_ohm = 1.0e5

    def _install(self) -> None:
        self._handlers = {
            "CONF:VOLT:DC": self._conf_dc,
            "CONF:VOLT:AC": self._conf_ac,
            "CONF:RES": self._conf_res,
            "FUNC?": self._get_function,
            "VOLT:DC:RANG": self._set_dc_range,
            "VOLT:DC:RANG?": self._get_dc_range,
            "READ?": self._read,
            "MEAS:VOLT:DC?": self._meas_dc,
            "MEAS:VOLT:AC?": self._meas_ac,
            "MEAS:RES?": self._meas_res,
        }

    # -- configuration ---------------------------------------------------

    def _conf_dc(self, argument: str | None) -> None:
        self.function = "VOLT:DC"
        if argument is not None:
            self._set_dc_range(argument)

    def _conf_ac(self, argument: str | None) -> None:
        self._no_argument(argument)
        self.function = "VOLT:AC"

    def _conf_res(self, argument: str | None) -> None:
        self.function = "RES"
        if argument is not None:
            value = self._number(argument, 0.0, max(self.RES_RANGES_OHM))
            self.res_range_ohm = min(r for r in self.RES_RANGES_OHM if r >= value)

    def _get_function(self, argument: str | None) -> str:
        self._no_argument(argument)
        return f'"{self.function}"'

    def _set_dc_range(self, argument: str | None) -> None:
        value = self._number(argument, 0.0, max(self.DC_RANGES_V))
        self.dc_range_v = min(r for r in self.DC_RANGES_V if r >= value)

    def _get_dc_range(self, argument: str | None) -> str:
        self._no_argument(argument)
        return f"{self.dc_range_v:.4f}"

    # -- measurement -----------------------------------------------------

    def node_voltage_v(self) -> float:
        """The DC voltage at whichever node the leads are on."""
        wiring = self.wiring
        vin = float(wiring.input_voltage_v)
        iout = float(wiring.load_current_a)
        if self.probe == "vin":
            return vin
        if self.probe == "vout":
            return wiring.dut.vout_v(vin, iout) + wiring.dmm_offset_v
        return 0.0

    def _reading(self) -> float:
        wiring = self.wiring
        if self.function == "VOLT:DC":
            return self.node_voltage_v()
        if self.function == "VOLT:AC":
            # AC volts on this meter is true RMS, AC coupled. For the triangular ripple a buck
            # produces, the RMS value is the peak-to-peak divided by 2*sqrt(3); the manual says
            # so. The test spec measures ripple on the scope instead, because this reading
            # excludes everything above the meter's 300 kHz AC bandwidth, which is most of what
            # makes production ripple bigger than the inductor and capacitor alone predict.
            vin = float(wiring.input_voltage_v)
            iout = float(wiring.load_current_a)
            return wiring.dut.lc_ripple_v(vin, iout) / (2.0 * math.sqrt(3.0))
        # Resistance, measured with the board unpowered: each node looks like a discharged
        # capacitor in parallel with its bleed path. A shorted board reads near zero, which is
        # what the first test step is for.
        if self.probe == "vin":
            return wiring.dut.input_res_ohm
        if self.probe == "vout":
            return wiring.dut.output_res_ohm
        return 1.0e9

    #: What this meter returns when the signal is bigger than the selected range. It is not an
    #: error and the error queue stays empty, which the manual says out loud: a program that only
    #: checks `SYST:ERR?` will take this number for a measurement.
    OVERLOAD = "+9.900000E+37"

    def _format(self, value: float) -> str:
        limit = self.dc_range_v if self.function.startswith("VOLT") else self.res_range_ohm
        if abs(value) > limit:
            return self.OVERLOAD
        return f"{value:+.6E}"

    def _read(self, argument: str | None) -> str:
        self._no_argument(argument)
        return self._format(self._reading())

    def _meas_dc(self, argument: str | None) -> str:
        if argument is not None:
            self._set_dc_range(argument)
        self.function = "VOLT:DC"
        return self._format(self._reading())

    def _meas_ac(self, argument: str | None) -> str:
        self._no_argument(argument)
        self.function = "VOLT:AC"
        return self._format(self._reading())

    def _meas_res(self, argument: str | None) -> str:
        self._no_argument(argument)
        self.function = "RES"
        return self._format(self._reading())


class ElectronicLoad(Instrument):
    """Tarnley Test Systems TRN-2400, 0 to 60 V, 0 to 30 A, 300 W, CC/CR/CV.

    Documented in `evals/bench/corpus/trn2400-programming-manual.md`.
    """

    IDN = "TARNLEY,TRN-2400,TL26008145,3.02"
    ACCEPTS_LONG_FORM = False
    ACCEPTS_ON_OFF_WORDS = False
    UNIT_SUFFIX = True
    MAX_VOLTAGE_V = 60.0
    MAX_CURRENT_A = 30.0
    MAX_POWER_W = 300.0
    MODES = ("CC", "CR", "CV")

    def __init__(self, wiring: Wiring | None = None) -> None:
        self.wiring = wiring if wiring is not None else Wiring()
        super().__init__()

    def _reset(self) -> None:
        self.mode = "CC"
        self.current_setpoint_a = 0.0
        self.resistance_setpoint_ohm = 1000.0
        self.voltage_setpoint_v = 0.0
        self.input_on = False
        self._publish()

    def _install(self) -> None:
        self._handlers = {
            "MODE": self._set_mode,
            "MODE?": self._get_mode,
            "CURR": self._set_current,
            "CURR?": self._get_current,
            "RES": self._set_resistance,
            "RES?": self._get_resistance,
            "INP": self._set_input,
            "INP?": self._get_input,
            "MEAS:VOLT?": self._meas_voltage,
            "MEAS:CURR?": self._meas_current,
        }

    def _publish(self) -> None:
        """Tell the wiring how much current the load is pulling, so the other instruments see it."""
        self.wiring.load_current_a = self.actual_current_a()

    # -- state -----------------------------------------------------------

    def _set_mode(self, argument: str | None) -> None:
        text = self._require(argument).upper()
        if text not in self.MODES:
            raise ScpiError(ERR_ILLEGAL_VALUE)
        self.mode = text
        self._publish()

    def _get_mode(self, argument: str | None) -> str:
        self._no_argument(argument)
        return self.mode

    def _set_current(self, argument: str | None) -> None:
        self.current_setpoint_a = round(self._number(argument, 0.0, self.MAX_CURRENT_A), 4)
        self._publish()

    def _get_current(self, argument: str | None) -> str:
        self._no_argument(argument)
        return self._value(f"{self.current_setpoint_a:.4f}", "A")

    def _set_resistance(self, argument: str | None) -> None:
        self.resistance_setpoint_ohm = self._number(argument, 0.05, 10_000.0)
        self._publish()

    def _get_resistance(self, argument: str | None) -> str:
        self._no_argument(argument)
        return self._value(f"{self.resistance_setpoint_ohm:.4f}", "OHM")

    def _set_input(self, argument: str | None) -> None:
        self.input_on = self._on_off(argument)
        self._publish()

    def _get_input(self, argument: str | None) -> str:
        self._no_argument(argument)
        return "1" if self.input_on else "0"

    # -- measurement -----------------------------------------------------

    def actual_current_a(self) -> float:
        """The current the load is drawing right now: zero with the input off."""
        if not self.input_on:
            return 0.0
        if self.mode == "CC":
            return self.current_setpoint_a
        if self.mode == "CR":
            vin = float(self.wiring.input_voltage_v)
            vout = self.wiring.dut.vout_v(vin, 0.0)
            return vout / self.resistance_setpoint_ohm
        return 0.0

    def terminal_voltage_v(self) -> float:
        vin = float(self.wiring.input_voltage_v)
        return self.wiring.dut.vout_v(vin, self.actual_current_a())

    def _meas_voltage(self, argument: str | None) -> str:
        self._no_argument(argument)
        return self._value(f"{self.terminal_voltage_v():.4f}", "V")

    def _meas_current(self, argument: str | None) -> str:
        self._no_argument(argument)
        return self._value(f"{self.actual_current_a():.4f}", "A")


class Oscilloscope(Instrument):
    """Tarnley Test Systems TRN-1102, two channels, 100 MHz, 1 GSa/s.

    Documented in `evals/bench/corpus/trn1102-programming-manual.md`. Only channel 1 is wired to
    anything on this bench: the output test point, through a 1:1 probe with a ground spring.
    """

    IDN = "TARNLEY,TRN-1102,TL26100233,5.41"
    ACCEPTS_LONG_FORM = False
    ACCEPTS_ON_OFF_WORDS = False
    UNIT_SUFFIX = True
    VERTICAL_SCALES_V = (
        0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0,
    )
    DIVISIONS = 8

    def __init__(self, wiring: Wiring | None = None) -> None:
        self.wiring = wiring if wiring is not None else Wiring()
        super().__init__()

    def _reset(self) -> None:
        self.coupling = {1: "DC", 2: "DC"}
        self.scale_v = {1: 1.0, 2: 1.0}
        self.bandwidth_limit = {1: False, 2: False}
        self.timebase_s = 1.0e-3
        self.acquired = False

    def _install(self) -> None:
        self._handlers = {
            "CHAN1:COUP": lambda a: self._set_coupling(1, a),
            "CHAN2:COUP": lambda a: self._set_coupling(2, a),
            "CHAN1:COUP?": lambda a: self._get_coupling(1, a),
            "CHAN2:COUP?": lambda a: self._get_coupling(2, a),
            "CHAN1:SCAL": lambda a: self._set_scale(1, a),
            "CHAN2:SCAL": lambda a: self._set_scale(2, a),
            "CHAN1:SCAL?": lambda a: self._get_scale(1, a),
            "CHAN2:SCAL?": lambda a: self._get_scale(2, a),
            "CHAN1:BWL": lambda a: self._set_bwl(1, a),
            "CHAN2:BWL": lambda a: self._set_bwl(2, a),
            "CHAN1:BWL?": lambda a: self._get_bwl(1, a),
            "CHAN2:BWL?": lambda a: self._get_bwl(2, a),
            "TIM:SCAL": self._set_timebase,
            "TIM:SCAL?": self._get_timebase,
            "SING": self._single,
            "MEAS:VPP?": self._meas_vpp,
        }

    # -- configuration ---------------------------------------------------

    def _set_coupling(self, channel: int, argument: str | None) -> None:
        text = self._require(argument).upper()
        if text not in ("AC", "DC", "GND"):
            raise ScpiError(ERR_ILLEGAL_VALUE)
        self.coupling[channel] = text

    def _get_coupling(self, channel: int, argument: str | None) -> str:
        self._no_argument(argument)
        return self.coupling[channel]

    def _set_scale(self, channel: int, argument: str | None) -> None:
        value = self._number(argument, min(self.VERTICAL_SCALES_V), max(self.VERTICAL_SCALES_V))
        self.scale_v[channel] = min(self.VERTICAL_SCALES_V, key=lambda s: abs(s - value))

    def _get_scale(self, channel: int, argument: str | None) -> str:
        self._no_argument(argument)
        return self._value(f"{self.scale_v[channel]:.4f}", "V")

    def _set_bwl(self, channel: int, argument: str | None) -> None:
        self.bandwidth_limit[channel] = self._on_off(argument)

    def _get_bwl(self, channel: int, argument: str | None) -> str:
        self._no_argument(argument)
        return "1" if self.bandwidth_limit[channel] else "0"

    def _set_timebase(self, argument: str | None) -> None:
        self.timebase_s = self._number(argument, 1.0e-9, 50.0)

    def _get_timebase(self, argument: str | None) -> str:
        self._no_argument(argument)
        return self._value(f"{self.timebase_s:.3E}", "S")

    def _single(self, argument: str | None) -> None:
        self._no_argument(argument)
        self.acquired = True

    # -- measurement -----------------------------------------------------

    def ripple_v(self) -> float:
        """Peak-to-peak output ripple as this channel would see it.

        Two settings change the number, and both are in the test spec for a reason: DC coupling
        puts the 5 V rail on screen, so the 8-bit digitizer cannot resolve a 20 mV ripple at all,
        and switching the 20 MHz bandwidth limit off lets the switching-edge ringing through,
        which roughly doubles the reading. That is a measurement difference, not a board
        difference, and it is the most common way two benches disagree about ripple.
        """
        wiring = self.wiring
        vin = float(wiring.input_voltage_v)
        iout = float(wiring.load_current_a)
        dut = wiring.dut
        if self.coupling[1] != "AC":
            return dut.vout_v(vin, iout)
        if self.bandwidth_limit[1]:
            return dut.measured_ripple_v(vin, iout)
        return dut.lc_ripple_v(vin, iout) + 2.6 * dut.ringing_v

    def _meas_vpp(self, argument: str | None) -> str:
        channel = _normalize(self._require(argument))
        if channel not in ("CHAN1", "CHAN2"):
            raise ScpiError(ERR_ILLEGAL_VALUE)
        if not self.acquired:
            raise ScpiError(ERR_SETTINGS_CONFLICT)
        if channel == "CHAN2":
            return self._value("0.0000E+00", "V")
        value = self.ripple_v()
        full_scale = self.scale_v[1] * self.DIVISIONS
        if value > full_scale:
            # Off screen. A real scope reports the clipped span; the test spec's setup step
            # exists so this cannot happen quietly.
            value = full_scale
        return self._value(f"{value:.4E}", "V")


# ---------------------------------------------------------------------------
# The bench: four instruments wired to one board
# ---------------------------------------------------------------------------


class Bench:
    """One DUT and the four instruments connected to it, sharing one `Wiring`.

    `bench.supply.send(...)`, `bench.dmm.send(...)` and so on are the only way in. Nothing here
    reads the DUT model directly except through an instrument, which is the point: an example
    that drives this bench is written exactly the way it would be written against real hardware,
    and swapping `send` for a PyVISA `write`/`query` pair is the whole port.
    """

    def __init__(self, dut: Dut | None = None, *, dmm_offset_v: float = 0.0) -> None:
        self.wiring = Wiring(dut=dut if dut is not None else Dut(), dmm_offset_v=dmm_offset_v)
        self.supply = PowerSupply(self.wiring)
        self.dmm = Multimeter(self.wiring)
        self.load = ElectronicLoad(self.wiring)
        self.scope = Oscilloscope(self.wiring)

    @property
    def dut(self) -> Dut:
        return self.wiring.dut

    def refresh(self) -> None:
        """Recompute the node voltages the meters read from the supply and load state.

        Call it after any command that changes an output state. `GuardedSupply` and the example
        packages call it for you; a bare `supply.send("OUTP ON")` does not, which is deliberate:
        the bench models the settling a real one needs, and the test spec's settle delays are
        where that shows up.
        """
        vin = self.supply.voltage_setpoint_v if self.supply.output_on else 0.0
        self.wiring.input_voltage_v = vin
        self.wiring.load_current_a = self.load.actual_current_a()


# ---------------------------------------------------------------------------
# The safety envelope
# ---------------------------------------------------------------------------


#: Every header on this bench that only reads. A query never changes the state of an instrument
#: or the board, so an agent may run one of these without asking anybody. Everything else sets
#: something: a voltage, a current, a range, an output state. Those go through `SafetyEnvelope`,
#: and the two that energize a board (`OUTP` on the supply, `INP` on the load) additionally need
#: a person's `Approval`. The recipes on this site draw the line in exactly this place, and
#: `is_read_only` is where the line is written down once rather than per example.
READ_ONLY_HEADERS = frozenset(
    {
        "*IDN?",
        "SYST:ERR?",
        "VOLT?",
        "CURR?",
        "RES?",
        "OUTP?",
        "INP?",
        "MODE?",
        "FUNC?",
        "VOLT:DC:RANG?",
        "READ?",
        "MEAS:VOLT?",
        "MEAS:CURR?",
        "MEAS:VOLT:DC?",
        "MEAS:VOLT:AC?",
        "MEAS:RES?",
        "MEAS:VPP?",
        "CHAN1:COUP?",
        "CHAN2:COUP?",
        "CHAN1:SCAL?",
        "CHAN2:SCAL?",
        "CHAN1:BWL?",
        "CHAN2:BWL?",
        "TIM:SCAL?",
    }
)

_CHANNEL_SELECTORS = frozenset({"CHAN1", "CHAN2"})


def is_read_only(command: str) -> bool:
    """True when this message only reads: safe to run without an approval, on any instrument.

    `*RST` and `*CLS` are not read-only even though they measure nothing: `*RST` drops an output
    and a range, which can change what the next reading means, and on a powered board that is a
    state change like any other.
    """
    if not isinstance(command, str) or ";" in command:
        return False
    parts = command.strip().split(None, 1)
    if not parts:
        return False
    header = _normalize(parts[0])
    if header not in READ_ONLY_HEADERS:
        return False
    if len(parts) == 1:
        return True
    # A query with an argument is not read-only just because its header is. `MEAS:VOLT:DC? 0.1`
    # sets the meter's range before it reads, the range stays set for every later query, and the
    # error queue says nothing about it. The one argument that only selects what to read is the
    # oscilloscope's channel, so that is the one argument allowed.
    return header == "MEAS:VPP?" and parts[1].strip().upper() in _CHANNEL_SELECTORS


class SafetyRefusal(Exception):
    """Raised when the envelope refuses a set point, an enable, or an approval.

    It is an exception and not a return code on purpose: a refusal must stop the sequence, and a
    caller that wants to continue has to say so in as many words.
    """


@dataclass(frozen=True)
class SafetyEnvelope:
    """The limits code enforces before any instrument acts, whatever the model proposed.

    The defaults are this bench's: 32 V is the input ceiling ECN-2608-04 sets for Rev A and Rev B
    boards, and 4.0 A is the supply current limit ceiling, above the SRB-5030's 3.0 A rating and
    below the 4.5 A the inductor saturates at. They are deliberately not the instrument's own
    limits, which are 40 V and 10 A: the envelope is about what is safe for this board, not what
    the supply can do.
    """

    max_voltage_v: float = 32.0
    max_current_limit_a: float = 4.0
    max_load_current_a: float = 4.5

    def check_voltage(self, volts: object) -> float:
        return self._check(volts, self.max_voltage_v, "voltage", "V")

    def check_current_limit(self, amps: object) -> float:
        return self._check(amps, self.max_current_limit_a, "current limit", "A")

    def check_load_current(self, amps: object) -> float:
        return self._check(amps, self.max_load_current_a, "load current", "A")

    @staticmethod
    def _check(value: object, ceiling: float, what: str, unit: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise SafetyRefusal(f"{what} is not a number: {value!r}")
        if isinstance(value, str):
            try:
                number = parse_number(value)
            except ValueError as exc:
                raise SafetyRefusal(f"{what} is not a number: {value!r}") from exc
        else:
            number = float(value)
        if not math.isfinite(number):
            raise SafetyRefusal(f"{what} is not finite: {value!r}")
        if number < 0.0:
            raise SafetyRefusal(f"{what} is negative: {number}{unit}")
        if number > ceiling:
            # No tolerance band. A set point 1 mV over the ceiling is over the ceiling.
            raise SafetyRefusal(f"{what} {number}{unit} is over the {ceiling}{unit} envelope")
        return number


@dataclass
class Approval:
    """A person's approval to energize the board at one named set point, good for one enable.

    It names the voltage and the current limit it was granted for. Code re-checks the supply's
    actual set point against those numbers at the moment of the enable, so an approval obtained
    for 12 V cannot energize a board at 32 V, and an approval already spent cannot be replayed.
    """

    approver: str
    voltage_v: float
    current_limit_a: float
    reason: str = ""
    used: bool = False

    def matches(self, voltage_v: float, current_limit_a: float) -> bool:
        return (
            abs(self.voltage_v - voltage_v) <= 1e-9
            and abs(self.current_limit_a - current_limit_a) <= 1e-9
        )


class GuardedSupply:
    """The supply, with the envelope in front of it. Nothing else in an example touches `supply`.

    Every set point goes through the envelope. The output enable additionally needs an unused
    `Approval` that names the set point the supply is actually at. `send` is kept, so a model's
    proposed command can be run through the same door as a hand-written one, and it refuses the
    commands that would go around the envelope rather than passing them along.
    """

    GUARDED_HEADERS = {"VOLT", "CURR", "OUTP"}

    def __init__(self, bench: Bench, envelope: SafetyEnvelope | None = None) -> None:
        self.bench = bench
        self.envelope = envelope if envelope is not None else SafetyEnvelope()
        self.log: list[str] = []

    # -- the checked operations -------------------------------------------

    def set_voltage(self, volts: object) -> float:
        checked = self.envelope.check_voltage(volts)
        self.bench.supply.send(f"VOLT {checked:.3f}")
        self._require_no_error()
        self.log.append(f"VOLT {checked:.3f}")
        self.bench.refresh()
        return checked

    def set_current_limit(self, amps: object) -> float:
        checked = self.envelope.check_current_limit(amps)
        self.bench.supply.send(f"CURR {checked:.3f}")
        self._require_no_error()
        self.log.append(f"CURR {checked:.3f}")
        self.bench.refresh()
        return checked

    def output_on(self, approval: object) -> None:
        if not isinstance(approval, Approval):
            raise SafetyRefusal("output enable needs an Approval; none was given")
        if approval.used:
            raise SafetyRefusal(f"approval from {approval.approver} has already been used")
        supply = self.bench.supply
        if not approval.matches(supply.voltage_setpoint_v, supply.current_limit_a):
            raise SafetyRefusal(
                f"approval is for {approval.voltage_v} V / {approval.current_limit_a} A; "
                f"the supply is set to {supply.voltage_setpoint_v} V / {supply.current_limit_a} A"
            )
        # Re-check the set points themselves: an approval is permission, not an override.
        self.envelope.check_voltage(supply.voltage_setpoint_v)
        self.envelope.check_current_limit(supply.current_limit_a)
        approval.used = True
        supply.send("OUTP ON")
        self._require_no_error()
        self.log.append("OUTP ON")
        self.bench.refresh()

    def output_off(self) -> None:
        self.bench.supply.send("OUTP OFF")
        self.log.append("OUTP OFF")
        self.bench.refresh()

    # -- the door a model's proposed command comes through ------------------

    def send(self, command: str) -> str:
        """Run one proposed command, refusing anything that would step around the envelope.

        A query passes straight through. A guarded set command is re-routed through the checked
        method above. `OUTP ON` is refused outright here: enabling the output is the one thing
        that needs a person, and a command string cannot carry an approval.
        """
        if not isinstance(command, str):
            raise SafetyRefusal(f"not a command: {command!r}")
        if ";" in command:
            raise SafetyRefusal(f"refusing a message that sets two things at once: {command!r}")
        parts = command.strip().split(None, 1)
        if not parts:
            raise SafetyRefusal("refusing an empty command")
        header = _normalize(parts[0])
        argument = parts[1].strip() if len(parts) > 1 else None
        if header.endswith("?"):
            return self.bench.supply.send(command)
        if header not in self.GUARDED_HEADERS:
            # Not a set point this envelope knows how to check, and not a query: refuse rather
            # than pass an unknown write through to the hardware.
            raise SafetyRefusal(f"refusing an unchecked command: {command!r}")
        if argument is None:
            raise SafetyRefusal(f"refusing a set command with no value: {command!r}")
        if header == "VOLT":
            self.set_voltage(argument)
            return ""
        if header == "CURR":
            self.set_current_limit(argument)
            return ""
        if argument.upper() in ("OFF", "0"):
            self.output_off()
            return ""
        raise SafetyRefusal("output enable requires an approved Approval, not a command string")

    def _require_no_error(self) -> None:
        """A checked value the instrument still rejected means the two disagree. Stop."""
        error = self.bench.supply.send("SYST:ERR?")
        if error != NO_ERROR:
            raise SafetyRefusal(f"the supply rejected a checked set point: {error}")


class GuardedLoad:
    """The electronic load, with the same envelope in front of its current set point.

    Note `INP 1` rather than `INP ON`: the TRN-2400 does not accept the word, and its manual says
    so. This class is where that difference is absorbed, once, instead of in every example.
    """

    def __init__(self, bench: Bench, envelope: SafetyEnvelope | None = None) -> None:
        self.bench = bench
        self.envelope = envelope if envelope is not None else SafetyEnvelope()

    def set_current(self, amps: object) -> float:
        checked = self.envelope.check_load_current(amps)
        self.bench.load.send("MODE CC")
        self.bench.load.send(f"CURR {checked:.4f}")
        self.bench.refresh()
        return checked

    def input_on(self) -> None:
        self.bench.load.send("INP 1")
        self.bench.refresh()

    def input_off(self) -> None:
        self.bench.load.send("INP 0")
        self.bench.refresh()


__all__ = [
    "Approval",
    "Bench",
    "Dut",
    "ElectronicLoad",
    "GuardedLoad",
    "GuardedSupply",
    "Instrument",
    "Multimeter",
    "Oscilloscope",
    "PowerSupply",
    "READ_ONLY_HEADERS",
    "SafetyEnvelope",
    "SafetyRefusal",
    "ScpiError",
    "Wiring",
    "is_read_only",
    "parse_number",
]
