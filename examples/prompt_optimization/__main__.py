"""Run the prompt optimization example from the command line.

    python -m examples.prompt_optimization --model stub
    python -m examples.prompt_optimization --model stub:scripted --demo-subset

No training API is contacted and nothing is written to disk except the small demo subset file
`--demo-subset` builds; this only searches, selects and reports scores.

`--model stub` ties every candidate at 0/24 on the real 32-question set (the numbers this page's
own Try It quotes), because the echoed text never matches a real question's accept pattern; the
"winner" is then just the first candidate in list order, which is the whole point that command
demonstrates. Scripting a real search over the full 32 questions would need 80 individual replies
(3 candidates x 24 development questions, plus 8 held-out for the winner) -- too many to read as
a demo and not what `--demo-subset` is for.

`--demo-subset` writes a small, real subset of the site's own exact-graded questions (six of the
sixty in `evals/questions.json`, chosen and copied verbatim, not invented) to a path -- the
default scratch path if you pass no value -- and searches over that instead. With the built-in
default split, that is 4 development questions per candidate and 2 held-out questions: 14 model
calls total, not 80, and SCRIPTED below can show a real winner instead of a three-way tie.

The full 32-question search stays reachable and unscripted: `--model ollama:<tag>` or
`--model claude:<id>` with no `--demo-subset` runs the real thing this page describes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from examples.common.cli import build_cli_model, MODEL_HELP
from examples.common.trace import Tracer
from examples.prompt_optimization.run import run

DEFAULT_DEMO_SUBSET_PATH = Path(".local/scratch/prompt_optimization/demo_questions.json")

# Six of evals/questions.json's own exact-graded lookup questions (L01-L06), copied verbatim:
# real ids, real question text, real accept patterns. --demo-subset writes this out and points
# questions_path at it, which is what keeps the scripted demo's search small and still honest --
# scoring the same way the real 32-question run does, just on fewer of them.
DEMO_QUESTIONS = {
    "questions": [
        {
            "id": "L01",
            "question": "How many place settings does the DW-300 dishwasher hold?",
            "accept": ["12 place setting"],
            "grading": "exact",
        },
        {
            "id": "L02",
            "question": "What is the noise rating of the DW-480 dishwasher during its Normal cycle?",
            "accept": ["44 dBA"],
            "grading": "exact",
        },
        {
            "id": "L03",
            "question": "How many cubic feet is the DR-520 dryer's drum?",
            "accept": [r"7\.8 cubic (foot|feet)"],
            "grading": "exact",
        },
        {
            "id": "L04",
            "question": "What electrical circuit does a DR-210 dryer require?",
            "accept": [r"240V,? ?30A"],
            "grading": "exact",
        },
        {
            "id": "L05",
            "question": "How often should the DW-300's fine filter be cleaned?",
            "accept": ["every 30 cycles"],
            "grading": "exact",
        },
        {
            "id": "L06",
            "question": "Which dryer error code indicates the thermal fuse has opened?",
            "accept": ["F2"],
            "grading": "exact",
        },
    ]
}

# 14 model calls under the default seed=0, held_out_fraction=0.25: DEMO_QUESTIONS shuffles and
# splits into 4 development questions (L02, L01, L06, L04, in that order) and 2 held-out (L05,
# L03). Every candidate is scored on the same 4 development questions in CANDIDATE_INSTRUCTIONS
# order; only the middle one ("You are a Halvorsen appliance support assistant...") answers them
# correctly, so it is selected and then scored on the 2 held-out questions, which it also
# answers correctly. Confirmed by actually running examples.prompt_optimization.run.run against
# DEMO_QUESTIONS before writing this file down; see
# tests/test_example_prompt_optimization.py's ScriptedCommandTests for the same check pinned.
_WRONG = "I have no idea."
SCRIPTED = [
    _WRONG, _WRONG, _WRONG, _WRONG,  # candidate 0 ("Answer... one short sentence"), dev: L02 L01 L06 L04
    "44 dBA.", "12 place settings.", "F2.", "A dedicated 240V, 30A circuit.",  # candidate 1 (the winner), dev
    _WRONG, _WRONG, _WRONG, _WRONG,  # candidate 2 ("Think step by step..."), dev
    "Every 30 cycles.", "7.8 cubic feet.",  # held-out, winner only: L05, L03
]

# The demo command needs --demo-subset, or SCRIPTED's 14 replies run out against the full
# 32-question set; {tmpdir} is substituted for a real temporary directory so running the suite
# leaves nothing behind in .local/scratch.
DEMO_ARGV = ["--demo-subset", "{tmpdir}/prompt_optimization_demo_questions.json"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search candidate instructions on a development split; report the winner on a held-out split.")
    parser.add_argument("--model", default="stub", help=MODEL_HELP)
    parser.add_argument(
        "--demo-subset",
        nargs="?",
        type=Path,
        const=DEFAULT_DEMO_SUBSET_PATH,
        default=None,
        help=(
            "write the small built-in subset of real exact-graded questions to this path (or "
            f"{DEFAULT_DEMO_SUBSET_PATH} if no path is given) and search over that instead of "
            "the full 32-question set; bounds the search to a demo-sized number of model calls"
        ),
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    model = build_cli_model(args.model, example="prompt_optimization", script=SCRIPTED)
    tracer = Tracer(example="prompt_optimization", level=1, model_id=model.model_id)

    run_kwargs = {}
    if args.demo_subset is not None:
        args.demo_subset.parent.mkdir(parents=True, exist_ok=True)
        args.demo_subset.write_text(json.dumps(DEMO_QUESTIONS), encoding="utf-8")
        run_kwargs["questions_path"] = args.demo_subset

    result = run(tracer, model, **run_kwargs)

    for c in result.candidates:
        marker = " <- selected" if c.instruction == result.selected else ""
        print(f"{c.dev_correct}/{c.dev_total} dev  {c.instruction!r}{marker}")
    print(f"held-out score for the selected candidate: {result.held_out_correct}/{result.held_out_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
