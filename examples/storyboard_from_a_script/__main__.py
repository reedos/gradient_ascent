"""Run the storyboard-from-a-script example from the command line.

    python -m examples.storyboard_from_a_script --model stub:scripted
    python -m examples.storyboard_from_a_script --model stub --question "1. A hand opens a box."

The question is the numbered script to storyboard, in "N. text" lines; leave it empty to run the
module's own SAMPLE_INPUT script. `--model stub` uses the generic interactive stub, which never
replies with real JSON, so the run below falls back to an empty scene and shot list rather than
crashing. `--model stub:scripted` plays SCRIPTED below: the scene split and shot list a real chain
produces for SAMPLE_INPUT, the same two replies tests/test_example_storyboard_from_a_script.py
scripts as its own full-chain run and the token and duration figures the recipe page quotes.
"""
from __future__ import annotations

import json

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.storyboard_from_a_script.run import LEVEL, SAMPLE_INPUT, run

# The script has 25 lines. Scenes split it with no gap and no overlap: 1-13, 14-15, 16-21, 22-25.
_SCENES = [
    {"scene": 1, "heading": "INT. HOME OFFICE - DUSK", "first_line": 1, "last_line": 13},
    {"scene": 2, "heading": "INT. HOME OFFICE - CONTINUOUS", "first_line": 14, "last_line": 15},
    {"scene": 3, "heading": "INT. BEDROOM - NIGHT", "first_line": 16, "last_line": 21},
    {"scene": 4, "heading": "TAG - PRODUCT CARD", "first_line": 22, "last_line": 25},
]

# 20 shots. Scene 2 needs two shots for line 14 (the lamp folding and Mara zipping the box happen
# in the same beat), and the second of those two also carries line 15, the voiceover line with no
# visual of its own -- covered by pairing it with the shot playing while it is read, not dropped.
_SHOTS = [
    {"scene": 1, "shot": 1, "size": "wide", "on_screen": "the cluttered desk at dusk, overhead bulb flickering", "seconds": 3.0, "first_line": 1, "last_line": 1},
    {"scene": 1, "shot": 2, "size": "medium", "on_screen": "a hand pulling the shipping box from a mailer", "seconds": 2.5, "first_line": 2, "last_line": 2},
    {"scene": 1, "shot": 3, "size": "close-up", "on_screen": "the box lid lifting to reveal the lamp", "seconds": 2.5, "first_line": 3, "last_line": 3},
    {"scene": 1, "shot": 4, "size": "medium", "on_screen": "Mara addressing camera about skipping the manual", "seconds": 3.0, "first_line": 4, "last_line": 4},
    {"scene": 1, "shot": 5, "size": "wide", "on_screen": "Mara setting the insert aside and standing the lamp upright", "seconds": 2.0, "first_line": 5, "last_line": 5},
    {"scene": 1, "shot": 6, "size": "close-up", "on_screen": "the lamp head tilting up, light warming then shifting to daylight white", "seconds": 3.0, "first_line": 6, "last_line": 7},
    {"scene": 1, "shot": 7, "size": "close-up", "on_screen": "the base ring glowing blue under her finger", "seconds": 2.0, "first_line": 8, "last_line": 8},
    {"scene": 1, "shot": 8, "size": "close-up", "on_screen": "the ring tapped twice, light dimming, tapped again to full", "seconds": 3.0, "first_line": 9, "last_line": 10},
    {"scene": 1, "shot": 9, "size": "wide", "on_screen": "the desk organized now, lamp centered over the notebook", "seconds": 2.5, "first_line": 11, "last_line": 11},
    {"scene": 1, "shot": 10, "size": "medium", "on_screen": "Mara opening her laptop and typing under steady light", "seconds": 3.0, "first_line": 12, "last_line": 13},
    {"scene": 2, "shot": 1, "size": "insert", "on_screen": "the lamp's arm folding flat against its base", "seconds": 1.5, "first_line": 14, "last_line": 14},
    {"scene": 2, "shot": 2, "size": "medium", "on_screen": "Mara zipping the shipping box shut and setting it by the door", "seconds": 2.0, "first_line": 14, "last_line": 15},
    {"scene": 3, "shot": 1, "size": "wide", "on_screen": "the nightstand: folded lamp beside water and a paperback", "seconds": 2.5, "first_line": 16, "last_line": 16},
    {"scene": 3, "shot": 2, "size": "medium", "on_screen": "Mara at the nightstand, saying she travels with hers", "seconds": 2.5, "first_line": 17, "last_line": 17},
    {"scene": 3, "shot": 3, "size": "close-up", "on_screen": "the woven fabric cord coiled neatly beside the base", "seconds": 2.5, "first_line": 18, "last_line": 19},
    {"scene": 3, "shot": 4, "size": "medium", "on_screen": "Mara unfolding the lamp and switching it to warm light", "seconds": 2.5, "first_line": 20, "last_line": 20},
    {"scene": 3, "shot": 5, "size": "close-up", "on_screen": "Mara, quieter, saying that's the whole lamp", "seconds": 2.5, "first_line": 21, "last_line": 21},
    {"scene": 4, "shot": 1, "size": "close-up", "on_screen": "slow push-in on the lit lamp as the room dims", "seconds": 3.0, "first_line": 22, "last_line": 22},
    {"scene": 4, "shot": 2, "size": "wide", "on_screen": "final card with the product name, the glow visible behind it", "seconds": 2.5, "first_line": 23, "last_line": 24},
    {"scene": 4, "shot": 3, "size": "wide", "on_screen": "the glow fading to black behind the card, closing voiceover", "seconds": 2.5, "first_line": 24, "last_line": 25},
]

# Two model calls: split into scenes, then propose shots for all scenes.
SCRIPTED = [
    json.dumps({"scenes": _SCENES}),
    json.dumps({"shots": _SHOTS}),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        argv or __import__("sys").argv[1:],
        description="Level 3: turn a script into a shot list.",
        default_question=SAMPLE_INPUT,
    )
    script = args.question.strip() or SAMPLE_INPUT
    model = build_cli_model(args.model, example="storyboard_from_a_script", script=SCRIPTED)
    tracer = Tracer(example="storyboard_from_a_script", level=LEVEL, model_id=model.model_id)
    report = run(script, model, tracer)
    print(report.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
