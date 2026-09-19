"""Tests for examples/bench_bring_up_debug_assistant: a level-5 loop with three read-only tools
over the electronics bench. Mirrors the shape of tests/test_example_single_agent.py: run end to
end on a scripted StubModel and check the decided_by pattern, the step cap and the token budget.
The safety tests attack the `measure` tool the way `docs/WRITING-AN-ENGINEERING-RECIPE.md` asks a
page that teaches a defense to: try to get a state-setting command through it and confirm every
attempt is refused before it ever reaches an instrument.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import PRODUCTION_CSV  # noqa: E402
from examples.bench_bring_up_debug_assistant.run import (  # noqa: E402
    FIXTURE_DMM_OFFSET_V,
    _bring_up,
    _measure,
    _test_log,
    run,
)
from examples.common.bench import NO_ERROR, GuardedLoad, SafetyRefusal  # noqa: E402
from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

SYMPTOM = "SRB5030-2608-0011 failed VOUT on FIX-03. Why, and what should we check next?"


class BringUpDebugAssistantTraceTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.bench_bring_up_debug_assistant.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 5)

    def test_a_full_walkthrough_records_model_decisions_for_every_call_and_the_stop(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="test_log", arguments={"serial": "SRB5030-2608-0011"})]),
                StubResponse(tool_calls=[ToolCall(name="read_doc", arguments={"cite": "failure-analysis-guide#3"})]),
                StubResponse(tool_calls=[ToolCall(name="read_doc", arguments={"cite": "failure-analysis-guide#7"})]),
                StubResponse(tool_calls=[ToolCall(name="measure", arguments={"instrument": "dmm", "command": "MEAS:VOLT:DC?"})]),
                StubResponse(tool_calls=[ToolCall(name="measure", arguments={"instrument": "load", "command": "MEAS:VOLT?"})]),
                StubResponse(tool_calls=[ToolCall(name="measure", arguments={"instrument": "dmm", "command": "*RST"})]),
                StubResponse(
                    text=(
                        "Cause: FIX-03's channel 2 offset, not the board. Only VOUT moved and the "
                        "DMM disagrees with the load's own terminal reading by about the fixture's "
                        "offset, the signature failure-analysis-guide#7 gives for a stale channel "
                        "offset rather than an open sense lead. Next measurement: verify FIX-03 "
                        "channel 2 per calibration-procedure#5, then retest this serial on another "
                        "fixture per failure-analysis-guide#1."
                    )
                ),
            ]
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-1")
        answer = run(SYMPTOM, model, tracer)

        # six tool calls plus the stop: seven model-decided steps, none of them the setup step
        self.assertEqual(tracer.model_decided_count(), 7)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertTrue(all(s.kind == "model" for s in model_steps))
        self.assertTrue(all(s.edge == "dashed" for s in model_steps))

        setup_steps = [s for s in tracer.steps if "energized" in s.title]
        self.assertEqual(len(setup_steps), 1)
        self.assertEqual(setup_steps[0].decided_by, "code")

        refusals = [s for s in tracer.steps if s.title == "Refuse a command that sets state"]
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0].decided_by, "code")
        self.assertIn("*RST", refusals[0].detail)

        self.assertIn("failure-analysis-guide#3", answer.citations)
        self.assertIn("failure-analysis-guide#7", answer.citations)
        self.assertIn("FIX-03", answer.text)

    def test_running_or_refusing_a_tool_is_always_code(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="test_log", arguments={"serial": "SRB5030-2608-0011"})]),
                StubResponse(text="Cause unclear yet."),
            ]
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-1")
        run(SYMPTOM, model, tracer)
        tool_steps = [s for s in tracer.steps if s.title.startswith("Run tool") or "Refuse" in s.title]
        self.assertTrue(tool_steps, "no tool step was recorded")
        for step in tool_steps:
            self.assertEqual(step.decided_by, "code")
            self.assertEqual(step.kind, "code")
            self.assertEqual(step.edge, "solid")


class TestLogToolTests(unittest.TestCase):
    def test_reads_the_real_logged_result_for_a_known_serial(self) -> None:
        # Called directly, not through the trace: a trace step's detail is truncated to 200
        # characters (examples/common/trace.py), and an eight-step log is longer than that.
        text, citations = _test_log("SRB5030-2608-0011", PRODUCTION_CSV)
        self.assertIn("step 3 VOUT=4.9497V (limits 4.9500..5.0500) FAIL", text)
        self.assertIn("low again on fix3", text)
        self.assertIn("step 6 EFF_FL=91.92%", text)
        self.assertEqual(text.count("PASS"), 7)
        self.assertEqual(text.count("FAIL"), 1)
        self.assertEqual(citations, [])

    def test_the_tool_is_wired_into_the_loop(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="test_log", arguments={"serial": "SRB5030-2608-0011"})]),
                StubResponse(text="stop"),
            ]
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-1")
        run(SYMPTOM, model, tracer, log_path=PRODUCTION_CSV)
        detail = next(s.detail for s in tracer.steps if s.title == "Run tool: test_log")
        self.assertIn("step 3 VOUT=4.9497V", detail)

    def test_an_unknown_serial_says_so_rather_than_raising(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="test_log", arguments={"serial": "SRB5030-9999-0001"})]),
                StubResponse(text="stop"),
            ]
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-1")
        run(SYMPTOM, model, tracer, log_path=PRODUCTION_CSV)
        detail = next(s.detail for s in tracer.steps if s.title == "Run tool: test_log")
        self.assertIn("no rows logged", detail)


class MeasureToolSafetyTests(unittest.TestCase):
    """Attack the `measure` tool: every message that is not a bare read only query must be
    refused, and refusing it must mean the instrument's own `send` is never called at all."""

    def _run_one_measure(self, instrument: str, command: str):
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="measure", arguments={"instrument": instrument, "command": command})]),
                StubResponse(text="stop"),
            ]
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-1")
        bench = _bring_up(FIXTURE_DMM_OFFSET_V)
        run(SYMPTOM, model, tracer, bench=bench)
        step = next(s for s in tracer.steps if s.title in ("Run tool: measure", "Refuse a command that sets state"))
        return step, bench

    def test_a_live_read_only_query_reaches_the_instrument(self) -> None:
        step, bench = self._run_one_measure("dmm", "MEAS:VOLT:DC?")
        self.assertEqual(step.title, "Run tool: measure")
        reading = float(step.detail)
        # 24 V in, 1 A out on a typical board is about 4.993 V; the FIX-03 channel reads about
        # 30 mV low on top of that (docs/THE-BENCH.md story 2). A board whose own tolerance is
        # not itself marginal still clears the 4.9500 V test limit through this channel, which is
        # exactly why some FIX-03 boards fail VOUT and most do not.
        self.assertGreaterEqual(reading, 4.9500)
        self.assertLess(reading, 4.980)

    def test_the_same_node_through_the_load_terminals_disagrees_with_the_dmm(self) -> None:
        dmm_step, bench = self._run_one_measure("dmm", "MEAS:VOLT:DC?")
        load_step, _ = self._run_one_measure("load", "MEAS:VOLT?")
        dmm_reading = float(dmm_step.detail)
        load_reading = float(load_step.detail.rstrip("V"))
        self.assertGreaterEqual(load_reading, 4.9500)
        # The two readings of the same output disagree by roughly the fixture's own offset, which
        # is the signature `failure-analysis-guide#7` describes: only the channel that reads an
        # absolute value through the affected path is shifted.
        self.assertAlmostEqual(load_reading - dmm_reading, 0.030, delta=0.010)

    def test_a_command_that_sets_a_voltage_is_refused(self) -> None:
        step, bench = self._run_one_measure("supply", "VOLT 40.0")
        self.assertEqual(step.title, "Refuse a command that sets state")
        self.assertEqual(bench.supply.voltage_setpoint_v, 24.0, "the refused command must not have changed the supply")

    def test_a_reset_is_refused_even_though_it_measures_nothing(self) -> None:
        step, bench = self._run_one_measure("dmm", "*RST")
        self.assertEqual(step.title, "Refuse a command that sets state")

    def test_an_attempt_to_energize_the_supply_is_refused(self) -> None:
        step, bench = self._run_one_measure("supply", "OUTP ON")
        self.assertEqual(step.title, "Refuse a command that sets state")
        self.assertTrue(bench.supply.output_on, "the board should still be the technician's own approved state")

    def test_a_stacked_command_is_refused_rather_than_partially_run(self) -> None:
        step, bench = self._run_one_measure("dmm", "MEAS:VOLT:DC?;VOLT 40")
        self.assertEqual(step.title, "Refuse a command that sets state")

    def test_a_query_argument_that_would_change_the_range_is_refused(self) -> None:
        # The header is read-only and the argument only looks like a range selector, but
        # examples/common/bench.py's Multimeter uses it to set the DC range as a side effect of
        # the read, and the range stays set. `is_read_only` is the check that catches it: a
        # read-only header carrying an argument is read-only on `MEAS:VPP?` alone.
        step, bench = self._run_one_measure("dmm", "MEAS:VOLT:DC? 0.1")
        self.assertEqual(step.title, "Refuse a command that sets state")
        self.assertEqual(bench.dmm.dc_range_v, 10.0, "the refused query must not have changed the DMM's range")

    def test_the_one_query_that_needs_an_argument_is_still_allowed(self) -> None:
        # Called directly against one bench: `MEAS:VPP? CHAN1` is the one read-only header this
        # bench actually needs an argument for, and it must still work after the stricter check.
        bench = _bring_up(FIXTURE_DMM_OFFSET_V)
        bench.scope.send("SING")
        text, _ = _measure("scope", "MEAS:VPP? CHAN1", bench)
        self.assertFalse(text.startswith("refused:"), text)

    def test_the_board_came_up_under_two_approvals_not_one(self) -> None:
        """Both commands docs/THE-BENCH.md classes as energizing a board are in `_bring_up`, and
        `GuardedLoad.input_on` refuses the load enable without an `Approval` of its own."""
        bench = _bring_up(FIXTURE_DMM_OFFSET_V)
        self.assertTrue(bench.supply.output_on)
        self.assertEqual(bench.load.send("INP?"), "1")
        load = GuardedLoad(bench)
        load.input_off()
        with self.assertRaises(SafetyRefusal):
            load.input_on(None)
        self.assertEqual(bench.load.send("INP?"), "0")

    def test_a_refusal_never_touches_the_instruments_error_queue(self) -> None:
        # Refusing a command in code, before `instrument.send` is called, is different from
        # sending it and having the instrument itself reject it: only the second would leave an
        # error in the queue. Confirms `measure` really never calls `send` for a refused command.
        _, bench = self._run_one_measure("supply", "VOLT 40.0")
        self.assertEqual(bench.supply.send("SYST:ERR?"), NO_ERROR)


class CapTests(unittest.TestCase):
    def test_step_cap_forces_a_stop_and_the_forced_answer_is_codes_decision(self) -> None:
        model = StubModel(
            lambda messages, tools: StubResponse(
                tool_calls=[ToolCall(name="test_log", arguments={"serial": "SRB5030-2608-0011"})]
            ),
            model_id="stub-loop",
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-loop")
        answer = run(SYMPTOM, model, tracer, max_steps=3)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertEqual(forced[0].decided_by, "code")
        self.assertIn("step cap", forced[0].detail)
        self.assertIsInstance(answer.text, str)
        stop_steps = [s for s in tracer.steps if s.title == "Model states a cause and the next measurement"]
        self.assertEqual(len(stop_steps), 0)

    def test_token_budget_forces_a_stop_before_the_step_cap(self) -> None:
        model = StubModel(
            lambda messages, tools: StubResponse(
                tool_calls=[ToolCall(name="test_log", arguments={"serial": "SRB5030-2608-0011"})]
            ),
            model_id="stub-loop",
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-loop")
        run(SYMPTOM, model, tracer, max_steps=50, max_tokens=1)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        self.assertLess(len(tracer.steps), 10, "the loop should stop almost immediately, not run near 50 steps")


class UnknownToolTests(unittest.TestCase):
    def test_an_unknown_tool_is_reported_to_the_model_rather_than_raised(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="reflow_the_board", arguments={})]),
                StubResponse(text="I could not find that."),
            ]
        )
        tracer = Tracer(example="bench_bring_up_debug_assistant", level=5, model_id="stub-1")
        answer = run(SYMPTOM, model, tracer)
        self.assertIn("unknown tool", " ".join(s.detail for s in tracer.steps))
        self.assertIsInstance(answer.text, str)


if __name__ == "__main__":
    unittest.main()
