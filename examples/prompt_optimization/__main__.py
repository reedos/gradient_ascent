"""Run the prompt optimization example from the command line.

    python -m examples.prompt_optimization --model stub
    python -m examples.prompt_optimization --model stub:scripted --max-questions 6

Nothing is written to disk and no training API is contacted; this only searches, selects and
reports scores.

`--model stub` ties every candidate at 0/24 on the full 32-question set (the numbers this page's
own Try It quotes), because the echoed text never matches a real question's accept pattern; the
"winner" is then just the first candidate in list order, which is the whole point that command
demonstrates.

`--max-questions n` bounds the search to the first `n` of the site's own exact-graded questions,
which is what makes a scripted demo possible: the full set is 80 model calls (3 candidates x 24
development questions, plus 8 held-out for the winner), too many to read. At 6 it is 14 calls,
and SCRIPTED below can show a real winner instead of a three-way tie. The questions are the real
ones, scored the real way, and there are fewer of them.

The full 32-question search stays reachable and unscripted: `--model ollama:<tag>` or
`--model claude:<id>` with no `--max-questions` runs the real thing this page describes.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import build_cli_model, MODEL_HELP
from examples.common.trace import Tracer
from examples.prompt_optimization.run import run

DEMO_MAX_QUESTIONS = 6

# 14 model calls under the default seed=0, held_out_fraction=0.25: the first 6 exact-graded
# questions (L01-L06) shuffle and split into 4 development questions (L02, L01, L06, L04, in that
# order) and 2 held-out (L05, L03). Every candidate is scored on the same 4 development questions
# in CANDIDATE_INSTRUCTIONS order; only the middle one ("You are a Halvorsen appliance support
# assistant...") answers them correctly, so it is selected and then scored on the 2 held-out
# questions, which it also answers correctly. Confirmed by running
# examples.prompt_optimization.run.run against the real question set with max_questions=6; see
# tests/test_example_prompt_optimization.py's ScriptedCommandTests for the same check pinned.
_WRONG = "I have no idea."
SCRIPTED = [
    _WRONG, _WRONG, _WRONG, _WRONG,  # candidate 0 ("Answer... one short sentence"), dev: L02 L01 L06 L04
    "44 dBA.", "12 place settings.", "F2.", "A dedicated 240V, 30A circuit.",  # candidate 1 (the winner), dev
    _WRONG, _WRONG, _WRONG, _WRONG,  # candidate 2 ("Think step by step..."), dev
    "Every 30 cycles.", "7.8 cubic feet.",  # held-out, winner only: L05, L03
]

# The demo command needs the bound, or SCRIPTED's 14 replies run out against the full 32-question
# set on the fifth call.
DEMO_ARGV = ["--max-questions", str(DEMO_MAX_QUESTIONS)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search candidate instructions on a development split; report the winner on a held-out split.")
    parser.add_argument("--model", default="stub", help=MODEL_HELP)
    parser.add_argument(
        "--max-questions",
        type=int,
        default=None,
        help=(
            "search over only the first n of the site's exact-graded questions instead of all 32; "
            "bounds the run to a demo-sized number of model calls (6 gives 14 calls)"
        ),
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    model = build_cli_model(args.model, example="prompt_optimization", script=SCRIPTED)
    tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)

    result = run(tracer, model, max_questions=args.max_questions)

    for c in result.candidates:
        marker = " <- selected" if c.instruction == result.selected else ""
        print(f"{c.dev_correct}/{c.dev_total} dev  {c.instruction!r}{marker}")
    print(f"held-out score for the selected candidate: {result.held_out_correct}/{result.held_out_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
