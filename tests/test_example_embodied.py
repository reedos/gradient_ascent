"""Tests for examples/embodied: the gripper-and-safety-envelope example for the robots-and-
machines technique page. Checks the decided_by pattern, the bounds clamp, the speed cap, and --
the property this page exists to prove -- that a move into a forbidden zone never reaches the
simulated actuator, whether the model asked for it directly or asked for something the clamp
would otherwise have pushed into one.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.embodied.__main__ import SCRIPTED  # noqa: E402
from examples.embodied.run import BOUNDS, HOME, MAX_SPEED_MM_S, Move, envelope, run_step  # noqa: E402

INF = float("inf")
NAN = float("nan")

SCENE = "A part sits 100mm to the right of home; pick it up."

# The same sequence examples/embodied/__main__.py plays under --model stub:scripted, for its
# default scene ("A part sits 320mm to the right of home; pick it up quickly.").
SEQUENCE = [
    StubResponse(tool_calls=[ToolCall(name="move", arguments={"x": 320.0, "y": 0.0, "z": 50.0, "speed": 400.0})]),
]


def _move_response(x: float, y: float, z: float, speed: float) -> StubModel:
    return StubModel([StubResponse(tool_calls=[ToolCall(name="move", arguments={"x": x, "y": y, "z": z, "speed": speed})])])


def _tracer() -> Tracer:
    return Tracer(example="embodied", level=7, model_id="stub-1")


class EmbodiedExampleTests(unittest.TestCase):
    def test_a_step_records_exactly_one_model_decided_step(self) -> None:
        model = _move_response(100.0, 0.0, 50.0, 100.0)
        tracer = _tracer()
        log: list[Move] = []
        result = run_step(model, tracer, scene=SCENE, actuator_log=log)

        self.assertEqual(tracer.model_decided_count(), 1)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(model_steps), 1)
        self.assertEqual(model_steps[0].title, "Model proposes the next move")
        self.assertEqual(model_steps[0].edge, "dashed")
        self.assertEqual(result.outcome, "actuated")
        self.assertEqual(log, [Move(100.0, 0.0, 50.0, 100.0)])
        code_steps = [s for s in tracer.steps if s.decided_by == "code"]
        self.assertTrue(all(s.edge == "solid" for s in code_steps))

    def test_a_dangerous_command_never_reaches_the_actuator(self) -> None:
        # the forbidden zone is x in (150, 300), y in (-300, -150) -- well inside the workspace
        # bounds, so this proposal is not something the bounds clamp alone would ever catch
        zone_target = Move(x=200.0, y=-200.0, z=100.0, speed=100.0)
        model = _move_response(zone_target.x, zone_target.y, zone_target.z, zone_target.speed)
        tracer = _tracer()
        log: list[Move] = []
        result = run_step(model, tracer, scene="Reach into the operator station.", actuator_log=log)

        self.assertEqual(result.outcome, "refused")
        self.assertEqual(log, [])  # the actuator log stays empty -- nothing was ever sent
        self.assertIn("operator station", result.reason)
        envelope_steps = [s for s in tracer.steps if s.title.startswith("Safety envelope")]
        self.assertEqual(len(envelope_steps), 1)
        self.assertEqual(envelope_steps[0].detail, result.reason)

    def test_a_target_outside_workspace_bounds_is_clamped_not_refused(self) -> None:
        far = Move(x=10_000.0, y=0.0, z=50.0, speed=100.0)
        result = envelope(far, actuator_log := [])
        self.assertEqual(result.outcome, "clamped")
        self.assertEqual(result.move.x, BOUNDS["x"][1])  # pinned to the upper bound, not the raw proposal
        self.assertEqual(actuator_log, [result.move])  # the clamped move did reach the actuator, unlike a refusal

    def test_speed_above_the_cap_is_clamped_to_it(self) -> None:
        fast = Move(x=0.0, y=0.0, z=50.0, speed=999.0)
        result = envelope(fast, [])
        self.assertEqual(result.outcome, "clamped")
        self.assertEqual(result.move.speed, MAX_SPEED_MM_S)

    def test_clamping_toward_a_zone_edge_is_still_refused_not_clamped_in(self) -> None:
        # a target just past the workspace bound, on a line that would clamp to a point still
        # inside the forbidden zone -- the envelope must refuse this, not "helpfully" clamp it
        # to the nearest in-bounds point, since that point is itself forbidden
        just_past_bound_into_zone = Move(x=250.0, y=-200.0, z=500.0, speed=100.0)  # z clamps to 400, still in the zone's z range
        result = envelope(just_past_bound_into_zone, actuator_log := [])
        self.assertEqual(result.outcome, "refused")
        self.assertEqual(actuator_log, [])

    def test_a_path_through_a_zone_is_refused_even_when_both_endpoints_are_legal(self) -> None:
        """The attack this envelope has to survive: every target the model names is outside every
        forbidden zone, but the straight line between two of them cuts the corner of one. An
        endpoint-only check actuates both and sweeps the arm through the operator station."""
        first = Move(x=0.0, y=-200.0, z=100.0, speed=100.0)
        second = Move(x=300.0, y=-100.0, z=100.0, speed=100.0)
        # neither target is itself in the zone (zone x 150..300, y -300..-150)
        for target in (first, second):
            self.assertFalse(150.0 <= target.x <= 300.0 and -300.0 <= target.y <= -150.0)

        log: list[Move] = []
        self.assertEqual(envelope(first, log).outcome, "actuated")
        result = envelope(second, log)
        self.assertEqual(result.outcome, "refused")
        self.assertIn("operator station", result.reason)
        self.assertEqual(log, [first])  # the second move never reached the actuator

    def test_the_path_is_measured_from_where_the_arm_actually_is(self) -> None:
        # the same target is safe from home and unsafe from a position on the far side of the
        # zone, so the check cannot be reading the proposal alone
        target = Move(x=300.0, y=-100.0, z=100.0, speed=100.0)
        self.assertEqual(envelope(target, []).outcome, "actuated")  # from HOME: clear

        parked = Move(x=0.0, y=-300.0, z=100.0, speed=100.0)  # the arm's last actuated position
        self.assertNotEqual(parked, HOME)
        from_there: list[Move] = [parked]
        self.assertEqual(envelope(target, from_there).outcome, "refused")
        self.assertEqual(from_there, [parked])  # nothing appended

    def test_a_non_finite_or_negative_number_is_refused_not_clamped(self) -> None:
        """max()/min() propagate a NaN instead of rejecting it, and nothing in a bare speed cap
        stops a negative speed, so both have to be refused before the clamp runs."""
        bad = [
            Move(NAN, 0.0, 50.0, 100.0),
            Move(0.0, NAN, 50.0, 100.0),
            Move(0.0, 0.0, NAN, 100.0),
            Move(0.0, 0.0, 50.0, NAN),
            Move(INF, 0.0, 50.0, 100.0),
            Move(-INF, 0.0, 50.0, 100.0),
            Move(0.0, 0.0, 50.0, INF),
            Move(0.0, 0.0, 50.0, -INF),
            Move(0.0, 0.0, 50.0, -1.0),
            Move(0.0, 0.0, 50.0, -1e308),
        ]
        for proposed in bad:
            with self.subTest(proposed=proposed):
                log: list[Move] = []
                result = envelope(proposed, log)
                self.assertEqual(result.outcome, "refused")
                self.assertEqual(log, [])  # nothing reaches the actuator, clamped or otherwise

    def test_no_actuated_move_ever_carries_a_nonsense_number(self) -> None:
        # the property behind the test above, stated once over every case in this suite: whatever
        # the model proposes, the log only ever holds finite numbers and a speed within the cap
        import math

        for proposed in [Move(NAN, NAN, NAN, NAN), Move(1e308, -1e308, NAN, -INF), Move(10.0, 10.0, 10.0, 1e308)]:
            log: list[Move] = []
            envelope(proposed, log)
            for move in log:
                self.assertTrue(all(math.isfinite(v) for v in (move.x, move.y, move.z, move.speed)))
                self.assertTrue(0.0 <= move.speed <= MAX_SPEED_MM_S)

    def test_no_proposed_move_is_treated_as_a_refusal_not_a_crash(self) -> None:
        model = StubModel([StubResponse(text="I am not sure what to do.")])
        tracer = _tracer()
        log: list[Move] = []
        result = run_step(model, tracer, scene=SCENE, actuator_log=log)
        self.assertEqual(result.outcome, "refused")
        self.assertEqual(log, [])

    def test_a_non_numeric_move_argument_is_refused_not_a_crash(self) -> None:
        # A tool argument is whatever the model wrote. float("far left") used to raise straight
        # out of run_step, which is a crash rather than a refusal the envelope can report.
        for bad in ("far left", None, [1, 2], {"x": 1}):
            with self.subTest(bad=bad):
                model = StubModel(
                    [StubResponse(tool_calls=[ToolCall(name="move", arguments={"x": bad, "y": 0, "z": 0, "speed": 10})])]
                )
                tracer = Tracer(example="embodied", level=7, model_id="stub-1")
                log: list[Move] = []
                result = run_step(model, tracer, scene="a part is somewhere", actuator_log=log)
                self.assertEqual(result.outcome, "refused")
                self.assertIn("not numbers", result.reason)
                self.assertEqual(log, [], "a move built from a non-number reached the actuator")
                self.assertEqual(tracer.model_decided_count(), 1)

    def test_declares_its_level(self) -> None:
        import examples.embodied.run as module

        self.assertEqual(module.LEVEL, 7)

    def test_the_command_s_scripted_move_is_clamped_not_refused_or_actuated_raw(self) -> None:
        """The end-to-end scenario `python -m examples.embodied --model stub:scripted` runs:
        one step against the default scene, with the model's proposal (320mm right, well past
        the workspace's x bound, at a speed above the cap) played by the same sequence SCRIPTED
        plays."""
        model = StubModel(list(SCRIPTED))
        tracer = _tracer()
        log: list[Move] = []
        result = run_step(model, tracer, scene="A part sits 320mm to the right of home; pick it up quickly.", actuator_log=log)

        self.assertEqual(result.outcome, "clamped")
        self.assertEqual(result.move.x, BOUNDS["x"][1])
        self.assertEqual(result.move.speed, MAX_SPEED_MM_S)
        self.assertEqual(log, [result.move])

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does. Every entry here is a StubResponse with tool calls, not plain
        text, so the sequences are compared directly rather than by their `.text`."""
        self.assertEqual(SCRIPTED, SEQUENCE)


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(scene, model, tracer)` is the entry point `record_trace.py` calls: one
    perceive-plan-act step from a fresh actuator log, the same default `__main__.py`'s `main`
    builds."""

    def test_run_is_one_step_from_a_fresh_actuator_log(self) -> None:
        from examples.embodied.run import run

        model = _move_response(100.0, 0.0, 50.0, 100.0)
        tracer = _tracer()
        result = run(SCENE, model, tracer)
        self.assertEqual(result.outcome, "actuated")

    def test_record_trace_classifies_embodied_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("embodied")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
