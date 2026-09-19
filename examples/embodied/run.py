"""Level 7: robots and machines. A text-simulated gripper arm in a 3D workspace. One step is
perceive (a short text description of the scene), plan (the model proposes a move), act (the
envelope decides what actually reaches the simulated actuator). The model's proposal is
`decided_by: "model"`; everything the safety envelope does with that proposal is
`decided_by: "code"`, and does not depend on what the model was asked or why it chose that move
-- only on the numbers it proposed.

The envelope enforces four fixed limits the model cannot override by asking differently:

1. Every number must be finite and the speed must not be negative. A NaN, an infinity or a
   negative speed is refused, never clamped: clamping a number that means nothing produces a
   real move the model never asked for, which is worse than doing nothing.
2. Workspace bounds and a speed cap, which clamp a proposal back to something reachable.
3. Named forbidden zones, which refuse a proposal outright rather than clamp it -- clamping a
   forbidden-zone target to its edge would still be a target inside the zone's boundary, so a
   zone violation is never satisfied by moving the number, only by not actuating it.
4. The zone check runs on the whole straight-line path from where the arm actually is to the
   clamped target, not only on the target. Two targets can each be outside every zone while the
   line between them passes straight through one, so checking endpoints alone lets a sequence of
   individually legal moves sweep through a zone.

The arm's current position is the last move that reached the actuator, or `HOME` before the
first one. A real controller reports its own position; this example infers it from the log
because the log is the only thing here that ever moves.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 7

# Workspace bounds and speed cap, in millimeters and mm/s from the gripper's home position.
# Fixed at import time: nothing in this module lets a proposed move change them.
BOUNDS = {"x": (-300.0, 300.0), "y": (-300.0, 300.0), "z": (0.0, 400.0)}
MAX_SPEED_MM_S = 250.0
FORBIDDEN_ZONES = [
    {"name": "operator station", "x": (150.0, 300.0), "y": (-300.0, -150.0), "z": (0.0, 400.0)},
]

MOVE_TOOL = {
    "name": "move",
    "description": "Propose the gripper's next target position and speed.",
    "parameters": {
        "type": "object",
        "properties": {
            "x": {"type": "number"},
            "y": {"type": "number"},
            "z": {"type": "number"},
            "speed": {"type": "number"},
        },
        "required": ["x", "y", "z", "speed"],
    },
}
SYSTEM = "You control a gripper arm. Call move(x, y, z, speed) with the next target position in millimeters and a speed in mm/s."


@dataclass(frozen=True)
class Move:
    x: float
    y: float
    z: float
    speed: float


# Where the arm sits before it has moved at all. The path check measures from here until the
# actuator log has an entry of its own.
HOME = Move(0.0, 0.0, 0.0, 0.0)


@dataclass(frozen=True)
class EnvelopeResult:
    outcome: Literal["actuated", "clamped", "refused"]
    move: Move  # what the envelope checked; only "actuated" and "clamped" reached the actuator
    reason: str = ""


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _valid(move: Move) -> str:
    """Empty if every number is usable, otherwise why it is not. Checked before clamping,
    because `min` and `max` propagate a NaN silently instead of rejecting it."""
    if not all(math.isfinite(v) for v in (move.x, move.y, move.z, move.speed)):
        return "target or speed is not a finite number"
    if move.speed < 0:
        return "speed is negative"
    return ""


def _path_enters(start: Move, end: Move, zone: dict) -> bool:
    """True if the straight line from `start` to `end` touches `zone` anywhere, endpoints
    included. The slab test: clip the segment against each axis' pair of planes in turn and see
    whether any of it is left. Exact for a box, so it cannot miss a thin crossing the way
    sampling a fixed number of points along the line would."""
    lo_t, hi_t = 0.0, 1.0
    for axis in ("x", "y", "z"):
        lo, hi = zone[axis]
        a, b = getattr(start, axis), getattr(end, axis)
        if a == b:
            if a < lo or a > hi:
                return False  # parallel to this slab and outside it: the whole segment misses
            continue
        t0, t1 = (lo - a) / (b - a), (hi - a) / (b - a)
        lo_t, hi_t = max(lo_t, min(t0, t1)), min(hi_t, max(t0, t1))
        if lo_t > hi_t:
            return False
    return True


def envelope(proposed: Move, actuator_log: list[Move]) -> EnvelopeResult:
    """The safety check, independent of the model. `actuator_log` stands in for a real motor
    controller: this is the only function in the module that ever appends to it, and it only
    does so for a move that already passed every check. Its last entry is also where the arm is
    now, which is what the path check measures from."""
    invalid = _valid(proposed)
    if invalid:
        return EnvelopeResult(outcome="refused", move=proposed, reason=invalid)

    clamped = Move(
        x=_clamp(proposed.x, *BOUNDS["x"]),
        y=_clamp(proposed.y, *BOUNDS["y"]),
        z=_clamp(proposed.z, *BOUNDS["z"]),
        speed=min(proposed.speed, MAX_SPEED_MM_S),
    )
    start = actuator_log[-1] if actuator_log else HOME
    for zone in FORBIDDEN_ZONES:
        if _path_enters(start, clamped, zone):
            return EnvelopeResult(outcome="refused", move=clamped, reason=f"path to the target crosses forbidden zone: {zone['name']}")

    actuator_log.append(clamped)
    if clamped == proposed:
        return EnvelopeResult(outcome="actuated", move=clamped)
    return EnvelopeResult(outcome="clamped", move=clamped, reason="target or speed was outside the workspace envelope")


def run_step(model: Model, tracer: Tracer, *, scene: str, actuator_log: list[Move]) -> EnvelopeResult:
    """One perceive-plan-act step: the model sees a short text description of the scene and
    proposes the next move; the envelope decides what, if anything, actually reaches the
    actuator log."""
    messages = [Message(role="system", content=SYSTEM), Message(role="user", content=scene)]
    completion = model.complete(messages, tools=[MOVE_TOOL], max_tokens=100)
    call = completion.tool_calls[0] if completion.tool_calls else None
    if call is None:
        tracer.record(
            kind="model", decided_by="model", title="Model proposes no move", detail="(no tool call)",
            tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
        )
        return EnvelopeResult(outcome="refused", move=Move(0.0, 0.0, 0.0, 0.0), reason="no move proposed")

    # The model's decision is recorded before anything is made of it. A proposal the envelope
    # cannot even read is still a decision the model made, and a trace that skipped it would
    # undercount exactly the steps this site charts.
    tracer.record(
        kind="model", decided_by="model", title="Model proposes the next move",
        detail=", ".join(f"{axis}={call.arguments.get(axis)!r}" for axis in ("x", "y", "z", "speed")),
        tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )
    try:
        proposed = Move(
            x=float(call.arguments.get("x", 0.0)),
            y=float(call.arguments.get("y", 0.0)),
            z=float(call.arguments.get("z", 0.0)),
            speed=float(call.arguments.get("speed", 0.0)),
        )
    except (TypeError, ValueError) as exc:
        # A tool argument is whatever the model wrote. "far left" is not a number, and letting
        # float() raise here would take the controller down instead of refusing one bad move.
        # Refusing is the same outcome the envelope reaches for a number it cannot use, and it
        # is reached the same way: without actuating anything.
        reason = f"move arguments are not numbers: {exc}"
        tracer.record(kind="code", decided_by="code", title="Safety envelope: refused", detail=reason)
        return EnvelopeResult(outcome="refused", move=HOME, reason=reason)

    result = envelope(proposed, actuator_log)
    tracer.record(
        kind="code", decided_by="code", title=f"Safety envelope: {result.outcome}",
        detail=result.reason or f"actuated as proposed: {result.move}",
    )
    return result


def run(scene: str, model: Model, tracer: Tracer) -> EnvelopeResult:
    """Recordable entry point for `record_trace.py`: one perceive-plan-act step from a fresh
    actuator log, the same default `python -m examples.embodied`'s `main` builds by hand."""
    return run_step(model, tracer, scene=scene, actuator_log=[])
