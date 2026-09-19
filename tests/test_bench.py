"""Tests for the simulated bench: the board model, the four instruments, and the envelope.

Three things are being pinned here, and they are different kinds of claim.

- **The board model agrees with its own datasheet.** Every figure in
  `evals/bench/corpus/srb5030-datasheet.md` is recomputed from `Dut` and compared. If somebody
  edits a constant in `examples/common/bench.py`, the datasheet stops being true and these tests
  say so, which is the only way a synthetic datasheet stays trustworthy.
- **The instruments implement their manuals and nothing else.** Including the three ways the two
  vendors differ, because an example that drafts a command from the wrong manual has to fail here
  the way it would fail on a bench.
- **The envelope refuses what `docs/THE-BENCH.md` says it refuses.** Each refusal is its own test
  and each one is a thing somebody has actually done to a power supply.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.bench import (  # noqa: E402
    COUT_F,
    ERR_ILLEGAL_VALUE,
    ERR_MISSING_PARAM,
    ERR_OUT_OF_RANGE,
    ERR_PARAM_NOT_ALLOWED,
    ERR_QUEUE_OVERFLOW,
    ERR_SETTINGS_CONFLICT,
    ERR_UNDEFINED_HEADER,
    FSW_HZ,
    L_H,
    NO_ERROR,
    READ_ONLY_HEADERS,
    Approval,
    Bench,
    Dut,
    ElectronicLoad,
    GuardedLoad,
    GuardedSupply,
    Multimeter,
    Oscilloscope,
    PowerSupply,
    SafetyEnvelope,
    SafetyRefusal,
    is_read_only,
    parse_number,
)


class TestDutAgreesWithDatasheet(unittest.TestCase):
    """Every number in the datasheet, recomputed from the model."""

    def setUp(self) -> None:
        self.dut = Dut()

    def test_output_voltage_at_the_production_test_point(self) -> None:
        # srb5030-datasheet.md section 4: 4.993 V at 24.0 V in, 1.0 A, 25 degC.
        self.assertAlmostEqual(self.dut.vout_v(24.0, 1.0), 4.993, places=3)

    def test_output_voltage_stays_inside_the_datasheet_window(self) -> None:
        # Section 4: 4.900 V to 5.100 V over the full line and load range.
        for vin in (9.0, 12.0, 24.0, 32.0, 36.0):
            for iout in (0.0, 0.5, 1.0, 2.0, 3.0):
                vout = self.dut.vout_v(vin, iout)
                self.assertGreaterEqual(vout, 4.900, f"{vin} V, {iout} A")
                self.assertLessEqual(vout, 5.100, f"{vin} V, {iout} A")

    def test_efficiency_is_output_power_over_input_power(self) -> None:
        """The definition, not an approximation of it."""
        for vin in (12.0, 24.0):
            for iout in (0.5, 1.0, 2.0, 3.0):
                pout = self.dut.vout_v(vin, iout) * iout
                pin = vin * self.dut.iin_a(vin, iout)
                self.assertAlmostEqual(
                    self.dut.efficiency_pct(vin, iout), 100.0 * pout / pin, places=9
                )

    def test_efficiency_table(self) -> None:
        # srb5030-datasheet.md section 5, to the tenth of a percent it is printed to.
        expected = {
            (12.0, 0.5): 94.8,
            (12.0, 1.0): 95.8,
            (12.0, 2.0): 95.5,
            (12.0, 3.0): 94.6,
            (24.0, 0.5): 87.9,
            (24.0, 1.0): 91.7,
            (24.0, 2.0): 92.8,
            (24.0, 3.0): 92.5,
        }
        for (vin, iout), pct in expected.items():
            self.assertAlmostEqual(self.dut.efficiency_pct(vin, iout), pct, places=1)

    def test_efficiency_table_input_currents(self) -> None:
        # The datasheet prints IIN so the efficiency can be checked; the two must agree.
        expected = {
            (12.0, 0.5): 0.2195,
            (12.0, 3.0): 1.3154,
            (24.0, 1.0): 0.2270,
            (24.0, 3.0): 0.6730,
        }
        for (vin, iout), iin in expected.items():
            self.assertAlmostEqual(self.dut.iin_a(vin, iout), iin, places=4)

    def test_no_load_input_current_is_inside_the_limit(self) -> None:
        # Section 4: 11.2 mA typical, 25.0 mA max, at 24 V.
        self.assertAlmostEqual(self.dut.iin_a(24.0, 0.0) * 1000.0, 11.2, places=1)

    def test_line_regulation(self) -> None:
        # Section 4: 0.14% typical over 9.0 V to 36.0 V at 1.0 A, 0.30% max.
        delta = abs(self.dut.vout_v(36.0, 1.0) - self.dut.vout_v(9.0, 1.0))
        self.assertAlmostEqual(100.0 * delta / 5.000, 0.14, places=2)
        self.assertLess(100.0 * delta / 5.000, 0.30)

    def test_load_regulation(self) -> None:
        # Section 4: 0.41% typical over 0.1 A to 3.0 A at 24 V, 0.80% max.
        delta = abs(self.dut.vout_v(24.0, 0.1) - self.dut.vout_v(24.0, 3.0))
        self.assertAlmostEqual(100.0 * delta / 5.000, 0.41, places=2)
        self.assertLess(100.0 * delta / 5.000, 0.80)

    def test_inductor_ripple_current_matches_the_stated_formula(self) -> None:
        # Section 6: dIL = (VIN - VOUT) * D / (L * fSW), about 0.79 A at 24 V and 3 A.
        vout = self.dut.vout_v(24.0, 3.0)
        expected = (24.0 - vout) * (vout / 24.0) / (L_H * FSW_HZ)
        self.assertAlmostEqual(self.dut.inductor_ripple_a(24.0, 3.0), expected, places=9)
        self.assertAlmostEqual(self.dut.inductor_ripple_a(24.0, 3.0), 0.79, places=2)

    def test_peak_inductor_current_clears_the_saturation_rule(self) -> None:
        # design-review-rules.md DR-10: Isat >= 1.3 * peak. The inductor is rated 4.5 A.
        peak = 3.0 + self.dut.inductor_ripple_a(24.0, 3.0) / 2.0
        self.assertAlmostEqual(peak, 3.39, places=2)
        self.assertGreaterEqual(4.5 / peak, 1.3)

    def test_capacitor_ripple_terms(self) -> None:
        # Section 6: 8.2 mV of capacitive ripple, 1.2 mV of ESR, about 9.4 mV together.
        dil = self.dut.inductor_ripple_a(24.0, 3.0)
        self.assertAlmostEqual(1000.0 * dil / (8.0 * COUT_F * FSW_HZ), 8.2, places=1)
        self.assertAlmostEqual(1000.0 * self.dut.lc_ripple_v(24.0, 3.0), 9.4, places=1)

    def test_measured_ripple_is_the_typical_in_the_datasheet(self) -> None:
        # Section 4: 22 mV typical at 24 V in, 3 A out, 20 MHz bandwidth limit.
        self.assertAlmostEqual(1000.0 * self.dut.measured_ripple_v(24.0, 3.0), 22.0, delta=0.5)

    def test_loss_at_full_load(self) -> None:
        # Section 7: 16.151 W in, 14.937 W out, 1.21 W dissipated.
        self.assertAlmostEqual(self.dut.loss_w(24.0, 3.0), 1.21, places=2)

    def test_undervoltage_lockout(self) -> None:
        self.assertEqual(self.dut.vout_v(8.0, 1.0), 0.0)
        self.assertGreater(self.dut.vout_v(8.3, 1.0), 4.9)

    def test_current_limit_folds_the_output_back(self) -> None:
        # Section 4: the output leaves regulation at 4.30 A typical, limits 3.70 to 5.00 A.
        current = 3.50
        while self.dut.vout_v(24.0, current) >= 4.900:
            current = round(current + 0.05, 2)
        self.assertAlmostEqual(current, 4.30, places=2)

    def test_a_dead_board_reads_zero_everywhere(self) -> None:
        dead = Dut(dead=True)
        self.assertEqual(dead.vout_v(24.0, 1.0), 0.0)
        self.assertEqual(dead.iin_a(24.0, 1.0), 0.0)
        self.assertEqual(dead.measured_ripple_v(24.0, 3.0), 0.0)

    def test_a_marginal_capacitor_lot_roughly_doubles_the_ripple(self) -> None:
        """The lot story in the data, as arithmetic rather than as generated numbers."""
        marginal = Dut(cout_f=6.6e-6)
        # docs/THE-BENCH.md: 0.79 / (8 * 6.6 uF * 500 kHz) = 29.9 mV of capacitor ripple, plus
        # the ESR term and the usual edge ringing.
        self.assertAlmostEqual(1000.0 * marginal.lc_ripple_v(24.0, 3.0), 31.1, delta=0.2)
        self.assertAlmostEqual(1000.0 * marginal.measured_ripple_v(24.0, 3.0), 43.6, delta=0.5)


class TestParseNumber(unittest.TestCase):
    def test_accepts_the_forms_a_manual_documents(self) -> None:
        for text, value in (("5", 5.0), ("5.0", 5.0), ("-2.5", -2.5), ("2e-6", 2e-6), (" 24.000 ", 24.0)):
            self.assertEqual(parse_number(text), value)

    def test_rejects_the_forms_python_accepts_and_an_instrument_does_not(self) -> None:
        for text in ("nan", "inf", "-inf", "infinity", "0x10", "1_000", "", "on", "5V", "5,0"):
            with self.assertRaises(ValueError, msg=text):
                parse_number(text)

    def test_rejects_an_overflowing_literal(self) -> None:
        with self.assertRaises(ValueError):
            parse_number("1e400")


class TestPowerSupply(unittest.TestCase):
    def setUp(self) -> None:
        self.supply = PowerSupply()

    def test_identify(self) -> None:
        self.assertEqual(self.supply.send("*IDN?"), "MARIDUN,MDN-4010,MY26014477,2.14")

    def test_reset_defaults(self) -> None:
        self.supply.send("VOLT 24")
        self.supply.send("OUTP ON")
        self.supply.send("*RST")
        self.assertEqual(self.supply.send("VOLT?"), "0.000")
        self.assertEqual(self.supply.send("CURR?"), "0.100")
        self.assertEqual(self.supply.send("OUTP?"), "0")

    def test_set_and_query_round_trip(self) -> None:
        self.supply.send("VOLT 24.000")
        self.supply.send("CURR 1.000")
        self.assertEqual(self.supply.send("VOLT?"), "24.000")
        self.assertEqual(self.supply.send("CURR?"), "1.000")
        self.assertEqual(self.supply.send("SYST:ERR?"), NO_ERROR)

    def test_maridun_accepts_the_long_keyword_form(self) -> None:
        self.supply.send("VOLTage 12.5")
        self.assertEqual(self.supply.send("VOLTage?"), "12.500")
        self.assertEqual(self.supply.send("SYST:ERR?"), NO_ERROR)

    def test_maridun_accepts_on_and_off_as_words(self) -> None:
        self.supply.send("OUTP ON")
        self.assertEqual(self.supply.send("OUTP?"), "1")
        self.supply.send("OUTP OFF")
        self.assertEqual(self.supply.send("OUTP?"), "0")
        self.assertEqual(self.supply.send("SYST:ERR?"), NO_ERROR)

    def test_maridun_responses_carry_no_unit_suffix(self) -> None:
        self.supply.send("VOLT 24")
        self.assertEqual(self.supply.send("VOLT?"), "24.000")
        self.assertEqual(float(self.supply.send("VOLT?")), 24.0)

    def test_undocumented_command(self) -> None:
        self.assertEqual(self.supply.send("VOLT:PROT 5"), "")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_UNDEFINED_HEADER)

    def test_out_of_range_keeps_the_previous_setting(self) -> None:
        self.supply.send("VOLT 24")
        self.assertEqual(self.supply.send("VOLT 40.001"), "")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_OUT_OF_RANGE)
        self.assertEqual(self.supply.send("VOLT?"), "24.000")

    def test_illegal_parameter_value(self) -> None:
        self.supply.send("VOLT twelve")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_ILLEGAL_VALUE)
        self.supply.send("VOLT nan")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_ILLEGAL_VALUE)

    def test_missing_parameter(self) -> None:
        self.supply.send("VOLT")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_MISSING_PARAM)

    def test_a_query_with_an_argument_is_refused(self) -> None:
        self.supply.send("VOLT? 5")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_PARAM_NOT_ALLOWED)

    def test_two_commands_in_one_message(self) -> None:
        self.assertEqual(self.supply.send("VOLT 24;CURR 1"), "")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_PARAM_NOT_ALLOWED)
        self.assertEqual(self.supply.send("VOLT?"), "0.000")

    def test_two_parameters_in_one_command(self) -> None:
        self.supply.send("VOLT 24 1")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_PARAM_NOT_ALLOWED)
        self.supply.send("VOLT 24,1")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_PARAM_NOT_ALLOWED)

    def test_error_queue_is_first_in_first_out(self) -> None:
        self.supply.send("BOGUS")
        self.supply.send("VOLT 99")
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_UNDEFINED_HEADER)
        self.assertEqual(self.supply.send("SYST:ERR?"), ERR_OUT_OF_RANGE)
        self.assertEqual(self.supply.send("SYST:ERR?"), NO_ERROR)

    def test_error_queue_overflows_after_ten(self) -> None:
        for _ in range(12):
            self.supply.send("BOGUS")
        seen = [self.supply.send("SYST:ERR?") for _ in range(11)]
        self.assertEqual(seen[:10], [ERR_UNDEFINED_HEADER] * 10)
        self.assertEqual(seen[10], ERR_QUEUE_OVERFLOW)
        self.assertEqual(self.supply.send("SYST:ERR?"), NO_ERROR)

    def test_cls_clears_the_queue(self) -> None:
        self.supply.send("BOGUS")
        self.supply.send("*CLS")
        self.assertEqual(self.supply.send("SYST:ERR?"), NO_ERROR)

    def test_an_empty_message_is_a_command_error(self) -> None:
        self.assertEqual(self.supply.send("   "), "")
        self.assertEqual(self.supply.send("SYST:ERR?"), '-100,"Command error"')


class TestMultimeter(unittest.TestCase):
    def setUp(self) -> None:
        self.bench = Bench()
        self.dmm = self.bench.dmm

    def test_identify_and_reset(self) -> None:
        self.assertEqual(self.dmm.send("*IDN?"), "MARIDUN,MDN-6100,MY26030912,1.08")
        self.assertEqual(self.dmm.send("FUNC?"), '"VOLT:DC"')
        self.assertEqual(self.dmm.send("VOLT:DC:RANG?"), "10.0000")

    def test_range_selection_picks_the_smallest_range_that_fits(self) -> None:
        self.dmm.send("VOLT:DC:RANG 5")
        self.assertEqual(self.dmm.send("VOLT:DC:RANG?"), "10.0000")
        self.dmm.send("VOLT:DC:RANG 0.05")
        self.assertEqual(self.dmm.send("VOLT:DC:RANG?"), "0.1000")

    def test_reads_the_regulator_output(self) -> None:
        power_up(self.bench, volts=24.0, amps=1.0)
        reading = float(self.dmm.send("MEAS:VOLT:DC? 10"))
        self.assertAlmostEqual(reading, 4.993, places=3)

    def test_overload_is_not_an_error(self) -> None:
        """The manual's warning, made real: too small a range returns a number, not an error."""
        power_up(self.bench, volts=24.0, amps=1.0)
        self.dmm.send("CONF:VOLT:DC 0.1")
        self.assertEqual(self.dmm.send("READ?"), Multimeter.OVERLOAD)
        self.assertEqual(self.dmm.send("SYST:ERR?"), NO_ERROR)

    def test_resistance_reads_the_probed_node(self) -> None:
        self.dmm.send("CONF:RES 100000")
        self.assertAlmostEqual(float(self.dmm.send("READ?")), 3300.0, places=1)

    def test_a_shorted_board_reads_near_zero(self) -> None:
        bench = Bench(Dut(output_res_ohm=0.4))
        bench.dmm.send("CONF:RES 100000")
        self.assertAlmostEqual(float(bench.dmm.send("READ?")), 0.4, places=2)

    def test_ac_volts_excludes_what_the_scope_measures(self) -> None:
        """The meter reads the triangular ripple's RMS, not the peak-to-peak with the edges."""
        power_up(self.bench, volts=24.0, amps=3.0)
        rms = float(self.dmm.send("MEAS:VOLT:AC?"))
        expected = self.bench.dut.lc_ripple_v(24.0, 3.0) / (2.0 * math.sqrt(3.0))
        self.assertAlmostEqual(rms, expected, places=9)
        self.assertLess(rms, self.bench.dut.measured_ripple_v(24.0, 3.0))

    def test_a_fixture_offset_shifts_an_absolute_reading(self) -> None:
        bench = Bench(dmm_offset_v=-0.030)
        power_up(bench, volts=24.0, amps=1.0)
        self.assertAlmostEqual(float(bench.dmm.send("MEAS:VOLT:DC? 10")), 4.963, places=3)

    def test_a_fixture_offset_cancels_in_a_regulation_difference(self) -> None:
        """Why exactly one production step moves when a fixture channel is miscalibrated."""
        clean, offset = Bench(), Bench(dmm_offset_v=-0.030)
        deltas = []
        for bench in (clean, offset):
            power_up(bench, volts=24.0, amps=0.1)
            light = float(bench.dmm.send("MEAS:VOLT:DC? 10"))
            bench.load.send("CURR 3.0000")
            bench.refresh()
            heavy = float(bench.dmm.send("MEAS:VOLT:DC? 10"))
            deltas.append(light - heavy)
        self.assertAlmostEqual(deltas[0], deltas[1], places=9)


class TestElectronicLoad(unittest.TestCase):
    def setUp(self) -> None:
        self.bench = Bench()
        self.load = self.bench.load

    def test_identify(self) -> None:
        self.assertEqual(self.load.send("*IDN?"), "TARNLEY,TRN-2400,TL26008145,3.02")

    def test_tarnley_rejects_the_long_keyword_form(self) -> None:
        self.assertEqual(self.load.send("CURRENT 1.0"), "")
        self.assertEqual(self.load.send("SYST:ERR?"), ERR_UNDEFINED_HEADER)
        self.load.send("CURR 1.0")
        self.assertEqual(self.load.send("SYST:ERR?"), NO_ERROR)

    def test_tarnley_rejects_on_and_off_as_words(self) -> None:
        self.assertEqual(self.load.send("INP ON"), "")
        self.assertEqual(self.load.send("SYST:ERR?"), ERR_ILLEGAL_VALUE)
        self.load.send("INP 1")
        self.assertEqual(self.load.send("INP?"), "1")
        self.assertEqual(self.load.send("SYST:ERR?"), NO_ERROR)

    def test_tarnley_responses_carry_a_unit_suffix(self) -> None:
        self.load.send("CURR 1.0")
        self.assertEqual(self.load.send("CURR?"), "1.0000A")
        self.assertTrue(self.load.send("RES?").endswith("OHM"))
        with self.assertRaises(ValueError):
            float(self.load.send("CURR?"))

    def test_mode_query_has_no_suffix(self) -> None:
        self.assertEqual(self.load.send("MODE?"), "CC")

    def test_an_unknown_mode_is_refused(self) -> None:
        self.load.send("MODE XX")
        self.assertEqual(self.load.send("SYST:ERR?"), ERR_ILLEGAL_VALUE)

    def test_setting_the_current_does_not_apply_a_load(self) -> None:
        self.bench.supply.send("VOLT 24")
        self.bench.supply.send("CURR 5")
        self.bench.supply.send("OUTP ON")
        self.load.send("MODE CC")
        self.load.send("CURR 3.0000")
        self.bench.refresh()
        self.assertEqual(self.load.send("MEAS:CURR?"), "0.0000A")
        self.load.send("INP 1")
        self.bench.refresh()
        self.assertEqual(self.load.send("MEAS:CURR?"), "3.0000A")

    def test_terminal_voltage_droops_with_load(self) -> None:
        power_up(self.bench, volts=24.0, amps=3.0)
        heavy = float(self.load.send("MEAS:VOLT?").removesuffix("V"))
        self.assertAlmostEqual(heavy, 4.979, places=3)


class TestOscilloscope(unittest.TestCase):
    def setUp(self) -> None:
        self.bench = Bench()
        self.scope = self.bench.scope
        power_up(self.bench, volts=24.0, amps=3.0)

    def configure(self) -> None:
        for command in ("CHAN1:COUP AC", "CHAN1:BWL 1", "CHAN1:SCAL 0.01", "TIM:SCAL 2e-6"):
            self.scope.send(command)

    def test_identify(self) -> None:
        self.assertEqual(self.scope.send("*IDN?"), "TARNLEY,TRN-1102,TL26100233,5.41")

    def test_measuring_before_an_acquisition_is_a_settings_conflict(self) -> None:
        self.configure()
        self.assertEqual(self.scope.send("MEAS:VPP? CHAN1"), "")
        self.assertEqual(self.scope.send("SYST:ERR?"), ERR_SETTINGS_CONFLICT)

    def test_missing_source_parameter(self) -> None:
        self.scope.send("MEAS:VPP?")
        self.assertEqual(self.scope.send("SYST:ERR?"), ERR_MISSING_PARAM)

    def test_ripple_to_the_test_specification(self) -> None:
        self.configure()
        self.scope.send("SING")
        reading = self.scope.send("MEAS:VPP? CHAN1")
        self.assertTrue(reading.endswith("V"), reading)
        self.assertAlmostEqual(float(reading.removesuffix("V")) * 1000.0, 22.0, delta=0.5)

    def test_dc_coupling_measures_the_rail_and_not_the_ripple(self) -> None:
        self.configure()
        self.scope.send("CHAN1:COUP DC")
        self.scope.send("SING")
        reading = float(self.scope.send("MEAS:VPP? CHAN1").removesuffix("V"))
        # Clipped to the 10 mV/div screen: eight divisions, which is the point.
        self.assertAlmostEqual(reading, 0.08, places=4)

    def test_bandwidth_limit_off_roughly_doubles_the_reading(self) -> None:
        self.configure()
        self.scope.send("SING")
        limited = float(self.scope.send("MEAS:VPP? CHAN1").removesuffix("V"))
        self.scope.send("CHAN1:BWL 0")
        self.scope.send("CHAN1:SCAL 0.02")
        self.scope.send("SING")
        unlimited = float(self.scope.send("MEAS:VPP? CHAN1").removesuffix("V"))
        self.assertGreater(unlimited / limited, 1.8)
        self.assertLess(unlimited / limited, 2.2)

    def test_scale_snaps_to_a_listed_value(self) -> None:
        self.scope.send("CHAN1:SCAL 0.013")
        self.assertEqual(self.scope.send("CHAN1:SCAL?"), "0.0100V")


class TestReadOnlyClassification(unittest.TestCase):
    def test_queries_are_read_only(self) -> None:
        for command in ("*IDN?", "SYST:ERR?", "MEAS:VOLT?", "READ?", "OUTP?", "MEAS:VPP? CHAN1"):
            self.assertTrue(is_read_only(command), command)

    def test_anything_that_sets_state_is_not(self) -> None:
        for command in ("VOLT 24", "OUTP ON", "INP 1", "*RST", "*CLS", "SING", "CHAN1:BWL 1"):
            self.assertFalse(is_read_only(command), command)

    def test_a_compound_message_is_never_read_only(self) -> None:
        self.assertFalse(is_read_only("MEAS:VOLT?;OUTP ON"))

    def test_long_form_queries_are_recognized(self) -> None:
        self.assertTrue(is_read_only("MEASure:VOLTage:DC?"))

    def test_a_query_whose_argument_sets_a_range_is_not_read_only(self) -> None:
        # Found by the writer of the bring-up recipe: the header only reads, the argument does not.
        bench = Bench()
        before = bench.dmm.dc_range_v
        self.assertFalse(is_read_only("MEAS:VOLT:DC? 0.1"))
        self.assertFalse(is_read_only("MEAS:VOLT:AC? 0.1"))
        self.assertFalse(is_read_only("MEAS:RES? 100"))
        self.assertFalse(is_read_only("MEAS:VPP? 0.1"))
        self.assertTrue(is_read_only("MEAS:VPP? CHAN1"))
        self.assertTrue(is_read_only("meas:vpp? chan2"))
        # and the reason it matters: sent anyway, the argument changes the meter and stays changed
        bench.dmm.send("MEAS:VOLT:DC? 0.1")
        self.assertNotEqual(bench.dmm.dc_range_v, before)

    def test_every_listed_header_is_a_query(self) -> None:
        for header in READ_ONLY_HEADERS:
            self.assertTrue(header.endswith("?"), header)


class TestSafetyEnvelope(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope = SafetyEnvelope()

    def test_accepts_a_set_point_inside_the_envelope(self) -> None:
        self.assertEqual(self.envelope.check_voltage(24.0), 24.0)
        self.assertEqual(self.envelope.check_voltage("24.000"), 24.0)
        self.assertEqual(self.envelope.check_current_limit(1.0), 1.0)

    def test_accepts_the_ceiling_exactly(self) -> None:
        self.assertEqual(self.envelope.check_voltage(32.0), 32.0)

    def test_refuses_a_set_point_just_over_the_ceiling(self) -> None:
        with self.assertRaises(SafetyRefusal):
            self.envelope.check_voltage(32.001)
        with self.assertRaises(SafetyRefusal):
            self.envelope.check_current_limit(4.0001)

    def test_refuses_a_negative_value(self) -> None:
        with self.assertRaises(SafetyRefusal):
            self.envelope.check_voltage(-5.0)
        with self.assertRaises(SafetyRefusal):
            self.envelope.check_current_limit("-0.001")

    def test_refuses_nan_and_infinity(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf"), "nan", "inf", "1e400"):
            with self.assertRaises(SafetyRefusal, msg=repr(value)):
                self.envelope.check_voltage(value)

    def test_refuses_things_that_are_not_numbers(self) -> None:
        for value in (None, [24.0], {"v": 24.0}, object(), True):
            with self.assertRaises(SafetyRefusal, msg=repr(value)):
                self.envelope.check_voltage(value)

    def test_the_envelope_is_tighter_than_the_instrument(self) -> None:
        """32 V is the ECN ceiling for boards in the field; the supply can do 40 V."""
        self.assertLess(self.envelope.max_voltage_v, PowerSupply.MAX_VOLTAGE_V)
        self.assertLess(self.envelope.max_current_limit_a, PowerSupply.MAX_CURRENT_A)


class TestGuardedSupply(unittest.TestCase):
    def setUp(self) -> None:
        self.bench = Bench()
        self.supply = GuardedSupply(self.bench)

    def approval(self, volts: float = 24.0, amps: float = 1.0) -> Approval:
        return Approval("R. Osaki", volts, amps, reason="production test step 3")

    def test_the_normal_path(self) -> None:
        self.supply.set_voltage(24.0)
        self.supply.set_current_limit(1.0)
        self.supply.output_on(self.approval())
        self.assertEqual(self.bench.supply.send("OUTP?"), "1")
        self.assertAlmostEqual(self.bench.wiring.input_voltage_v, 24.0)

    def test_output_enable_with_no_approval(self) -> None:
        self.supply.set_voltage(24.0)
        self.supply.set_current_limit(1.0)
        for bad in (None, "approved", True, object()):
            with self.assertRaises(SafetyRefusal, msg=repr(bad)):
                self.supply.output_on(bad)
        self.assertEqual(self.bench.supply.send("OUTP?"), "0")

    def test_an_approval_is_good_once(self) -> None:
        self.supply.set_voltage(24.0)
        self.supply.set_current_limit(1.0)
        approval = self.approval()
        self.supply.output_on(approval)
        self.supply.output_off()
        with self.assertRaises(SafetyRefusal):
            self.supply.output_on(approval)

    def test_an_approval_must_name_the_set_point_it_is_used_for(self) -> None:
        self.supply.set_voltage(32.0)
        self.supply.set_current_limit(1.0)
        with self.assertRaises(SafetyRefusal):
            self.supply.output_on(self.approval(volts=12.0))
        self.assertEqual(self.bench.supply.send("OUTP?"), "0")

    def test_a_set_point_over_the_envelope_never_reaches_the_instrument(self) -> None:
        with self.assertRaises(SafetyRefusal):
            self.supply.set_voltage(36.0)
        self.assertEqual(self.bench.supply.send("VOLT?"), "0.000")
        self.assertEqual(self.bench.supply.send("SYST:ERR?"), NO_ERROR)

    def test_send_refuses_a_compound_message(self) -> None:
        with self.assertRaises(SafetyRefusal):
            self.supply.send("VOLT 24;OUTP ON")

    def test_send_refuses_an_output_enable(self) -> None:
        self.supply.set_voltage(24.0)
        self.supply.set_current_limit(1.0)
        with self.assertRaises(SafetyRefusal):
            self.supply.send("OUTP ON")
        self.assertEqual(self.bench.supply.send("OUTP?"), "0")

    def test_send_allows_output_off(self) -> None:
        self.supply.set_voltage(24.0)
        self.supply.set_current_limit(1.0)
        self.supply.output_on(self.approval())
        self.supply.send("OUTP OFF")
        self.assertEqual(self.bench.supply.send("OUTP?"), "0")

    def test_send_routes_a_set_point_through_the_envelope(self) -> None:
        self.supply.send("VOLT 24.000")
        self.assertEqual(self.bench.supply.send("VOLT?"), "24.000")
        with self.assertRaises(SafetyRefusal):
            self.supply.send("VOLT 33")

    def test_send_refuses_an_unchecked_write(self) -> None:
        """A write the envelope has no rule for is refused, not passed through."""
        with self.assertRaises(SafetyRefusal):
            self.supply.send("*RST")
        with self.assertRaises(SafetyRefusal):
            self.supply.send("VOLT:PROT 5")

    def test_send_passes_a_query_through(self) -> None:
        self.assertEqual(self.supply.send("*IDN?"), "MARIDUN,MDN-4010,MY26014477,2.14")

    def test_send_refuses_a_set_command_with_no_value(self) -> None:
        with self.assertRaises(SafetyRefusal):
            self.supply.send("VOLT")


class TestFullSequence(unittest.TestCase):
    """The production test's step 3, end to end through the guarded interface."""

    def test_step_three(self) -> None:
        bench = Bench()
        supply = GuardedSupply(bench)
        load = GuardedLoad(bench)
        supply.set_voltage(24.0)
        supply.set_current_limit(4.0)
        supply.output_on(Approval("R. Osaki", 24.0, 4.0, reason="TS-5030 step 3"))
        load.set_current(1.0)
        # A second approval, for the second command that energizes the board: 1.000 A out of a
        # board that is already at 24.0 V in.
        load.input_on(Approval("R. Osaki", 24.0, 1.0, reason="TS-5030 step 3"))
        reading = float(bench.dmm.send("MEAS:VOLT:DC? 10"))
        self.assertGreaterEqual(reading, 4.9500)
        self.assertLessEqual(reading, 5.0500)
        load.input_off()
        supply.output_off()
        for instrument in (bench.supply, bench.dmm, bench.load, bench.scope):
            self.assertEqual(instrument.send("SYST:ERR?"), NO_ERROR)

    def test_the_load_refuses_a_current_over_the_envelope(self) -> None:
        bench = Bench()
        load = GuardedLoad(bench)
        with self.assertRaises(SafetyRefusal):
            load.set_current(5.0)
        self.assertEqual(bench.load.send("CURR?"), "0.0000A")


class TestGuardedLoadEnable(unittest.TestCase):
    """`INP 1` is the second command `docs/THE-BENCH.md` classes as energizing a board, and it is
    gated the same way `OUTP ON` is: an `Approval` naming the rail the board is at and the current
    the load is about to pull, good for one use."""

    def setUp(self) -> None:
        self.bench = Bench()
        self.supply = GuardedSupply(self.bench)
        self.load = GuardedLoad(self.bench)
        self.supply.set_voltage(24.0)
        self.supply.set_current_limit(4.0)
        self.supply.output_on(Approval("R. Osaki", 24.0, 4.0, reason="bring-up"))
        self.load.set_current(1.0)

    def approval(self, volts: float = 24.0, amps: float = 1.0) -> Approval:
        return Approval("R. Osaki", volts, amps, reason="production test step 3")

    def test_the_normal_path(self) -> None:
        self.load.input_on(self.approval())
        self.assertEqual(self.bench.load.send("INP?"), "1")
        self.assertAlmostEqual(self.bench.wiring.load_current_a, 1.0)

    def test_a_load_enable_with_no_approval(self) -> None:
        for bad in (None, "approved", True, object()):
            with self.assertRaises(SafetyRefusal, msg=repr(bad)):
                self.load.input_on(bad)
        self.assertEqual(self.bench.load.send("INP?"), "0")
        self.assertEqual(self.bench.wiring.load_current_a, 0.0)

    def test_an_approval_must_name_the_current_the_load_is_actually_set_to(self) -> None:
        with self.assertRaises(SafetyRefusal):
            self.load.input_on(self.approval(amps=3.0))
        self.assertEqual(self.bench.load.send("INP?"), "0")

    def test_an_approval_must_name_the_rail_the_board_is_actually_at(self) -> None:
        with self.assertRaises(SafetyRefusal):
            self.load.input_on(self.approval(volts=12.0))
        self.assertEqual(self.bench.load.send("INP?"), "0")

    def test_an_approval_is_good_once(self) -> None:
        approval = self.approval()
        self.load.input_on(approval)
        self.load.input_off()
        with self.assertRaises(SafetyRefusal):
            self.load.input_on(approval)
        self.assertEqual(self.bench.load.send("INP?"), "0")

    def test_the_supplys_own_approval_cannot_enable_the_load(self) -> None:
        """The supply came up at 24.0 V with a 4.0 A limit; the load is set to 1.0 A. An approval
        written for one enable does not fit the other, which is the point of naming the numbers."""
        with self.assertRaises(SafetyRefusal):
            self.load.input_on(Approval("R. Osaki", 24.0, 4.0, reason="bring-up"))

    def test_a_set_point_over_the_envelope_is_refused_even_with_a_matching_approval(self) -> None:
        """An approval is permission to energize at a set point, not permission to exceed one."""
        self.bench.load.send("CURR 5.0000")  # around GuardedLoad, the way a stray script would
        with self.assertRaises(SafetyRefusal):
            self.load.input_on(self.approval(amps=5.0))
        self.assertEqual(self.bench.load.send("INP?"), "0")

    def test_a_non_cc_mode_is_refused_because_the_envelope_cannot_check_it(self) -> None:
        self.bench.load.send("MODE CR")
        with self.assertRaises(SafetyRefusal):
            self.load.input_on(self.approval())
        self.assertEqual(self.bench.load.send("INP?"), "0")


def power_up(bench: Bench, *, volts: float, amps: float) -> None:
    """Bring a bench up without the envelope, for tests about the instruments themselves."""
    bench.supply.send(f"VOLT {volts}")
    bench.supply.send("CURR 5")
    bench.supply.send("OUTP ON")
    bench.load.send("MODE CC")
    bench.load.send(f"CURR {amps}")
    bench.load.send("INP 1")
    bench.refresh()


if __name__ == "__main__":
    unittest.main()
