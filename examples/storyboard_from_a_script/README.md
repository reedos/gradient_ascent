# Storyboard from a script

Level 3: two model calls, then a check in code. A numbered script goes in; the model splits it
into scenes, then proposes shots inside each scene; code checks that every script line is inside
at least one shot's range, that every shot's range is inside the script, and that every shot's
range is inside its own scene. Uncovered lines, out-of-script shots and scene-escaping shots are
all reported by number, not fixed automatically.

Run it:

```
python -m examples.storyboard_from_a_script --model stub:scripted
```

The module's own 25-line `SAMPLE_INPUT` script broken into 4 scenes and 20 shots, each shot with
a size, a duration and the script lines it covers, and no line reported uncovered. Pass your own
numbered script as `--question` to run it against a real model instead.

`--model stub` never replies with valid JSON, so the same command falls back to an empty scene
and shot list, reports every line uncovered, and does not crash. That is the coverage check
working on a model that returned nothing usable.

What it does not do: draw anything. `on_screen` is a sentence a camera operator reads, not a
frame, and no image is generated here. It also does not decide style, casting or location; a
director reads the output and makes those calls.
