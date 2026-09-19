# Storyboard from a script

Level 3: two model calls, then a check in code. A numbered script goes in; the model splits it
into scenes, then proposes shots inside each scene; code checks that every script line is inside
at least one shot's range, that every shot's range is inside the script, and that every shot's
range is inside its own scene. Uncovered lines, out-of-script shots and scene-escaping shots are
all reported by number, not fixed automatically.

Run it:

```
python -m examples.storyboard_from_a_script --model stub --question "1. A hand opens a box."
```

Leave `--question` empty to run the module's own 25-line `SAMPLE_INPUT` script instead. `--model
stub` here is the generic interactive stub, which never replies with valid JSON, so that run falls
back to an empty scene and shot list rather than crashing; the scripted responses that exercise
scene splitting, shot proposing and the coverage check live in the tests, not in this command.

What it does not do: draw anything. `on_screen` is a sentence a camera operator reads, not a
frame, and no image is generated here. It also does not decide style, casting or location; a
director reads the output and makes those calls.
