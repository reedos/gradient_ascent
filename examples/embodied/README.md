# Robots and machines

Level 7: a text-simulated gripper arm. One step is perceive (a scene description), plan (the
model proposes a move by calling `move(x, y, z, speed)` — `decided_by: "model"`), act (the safety
`envelope` decides what actually reaches the actuator log — `decided_by: "code"`, independent of
what the model was asked or why). The envelope refuses any number that is not finite and any
negative speed; clamps a target or speed outside the fixed workspace bounds back to something
reachable; and refuses outright — never clamps — a move whose straight-line path from the arm's
current position touches a named forbidden zone, since clamping a zone violation to the zone's
edge would still be a point inside its boundary, and checking only the target would let two
individually legal moves sweep through a zone on the way.

Run it:

```
python -m examples.embodied --model stub --question "A part sits 320mm to the right of home; pick it up quickly."
```

`tests/test_example_embodied.py` scripts a model that proposes a move inside the forbidden zone
and checks it never reaches `actuator_log`, plus separate tests for the bounds clamp, the speed
cap, NaN and negative speeds, and two legal targets whose path crosses a zone.
