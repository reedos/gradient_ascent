"""Run the distillation example from the command line.

    python -m examples.distillation --model stub:scripted --out .local/scratch/distillation/student.jsonl
    python -m examples.distillation --model stub --out .local/scratch/distillation/student.jsonl

Writes nothing outside the file you pass with --out (defaults to the path above). No training API
is contacted; this only captures and filters the teacher's answers.

`--model stub` echoes each question back as the teacher's own answer, which never matches any
question's accept pattern, so every one of the 32 exact-graded questions is dropped and the
student file comes out empty. `--model stub:scripted` plays SCRIPTED below: 30 answers a real
support assistant would give, which the site's own grading contract keeps, and 2 answers with the
right shape but a wrong figure, which the same contract drops -- so the run shows the filter
actually filtering, not just a clean pass-through.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examples.common.cli import MODEL_HELP, build_cli_model
from examples.common.trace import Tracer
from examples.distillation.run import run

DEFAULT_OUT = Path(".local/scratch/distillation/student.jsonl")
DEMO_ARGV = ["--out", "{tmpdir}/student.jsonl"]

# 32 model calls, one per exact-graded question in evals/questions.json, in the order
# load_exact_questions reads them: L01-L12, M01, M02, M08, M09, N01-N12, C01, C02, C09, C12.
# Every reply but two is the question's own reference answer, which the grading contract keeps;
# L06 and N04 are deliberately wrong (a made-up error code, an arithmetic slip), which the same
# contract drops, so the printed summary shows the filter doing something, not a clean 32-for-32.
SCRIPTED = [
    "12 place settings.",  # L01
    "44 dBA.",  # L02
    "7.8 cubic feet.",  # L03
    "A dedicated 240V, 30A circuit.",  # L04
    "Every 30 cycles.",  # L05
    "F4.",  # L06 -- wrong: the thermal fuse code is F2, not F4; dropped
    "30 minutes.",  # L07
    "$19.99.",  # L08
    "2 years from the original date of purchase.",  # L09
    "8 feet.",  # L10
    "It shuts off the water supply and stops the cycle immediately.",  # L11
    "110 lb.",  # L12
    (
        "The drain pump is part HLV-2205, priced at $52.00 in the parts list; the DW-480 owner's "
        "manual confirms HLV-2205 is the drain pump used in that model."
    ),  # M01
    (
        "Part HLV-7734, priced at $12.50 in the parts list; the DR-210 owner's manual confirms "
        "HLV-7734 is the door latch switch used on the DR-210."
    ),  # M02
    (
        "The Heavy cycle, run empty with a dishwasher-safe cleaner. On the DW-300 the Heavy cycle "
        "runs 130 minutes."
    ),  # M08
    "One Air Fluff cycle, which runs 20 minutes on the DR-520.",  # M09
    "32 gallons.",  # N01
    "$33.60 per year (240 kWh x $0.14/kWh).",  # N02
    "20 kWh (260 - 240).",  # N03
    "5 gallons ((3.2 - 3.0) x 20).",  # N04 -- wrong: the correct figure is 4 gallons; dropped
    "$79.50 ($38.50 + $41.00).",  # N05
    "$66.75 ($57.00 + $9.75).",  # N06
    "10 minutes (140 - 130).",  # N07
    "104 minutes (42 x 2 + 20).",  # N08
    "$0.03 (3.0 gallons x $0.010/gallon).",  # N09
    "6 cycles (180 / 30).",  # N10
    "3 lb (128 - 125).",  # N11
    "$25.75 ($12.50 + $13.25).",  # N12
    (
        "25 feet, per Service Bulletin SB-2026-07 (2026-06-01), which supersedes the DR-520 "
        "owner's manual's 35-foot figure (revision 2024-03-01)."
    ),  # C01
    "3 elbows, per the 2026 service bulletin, which supersedes the manual's original figure of 4.",  # C02
    "10 feet (35 - 25).",  # C09
    "35 feet, with up to 4 elbows.",  # C12
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture and filter a teacher model's answers into a student training file.")
    parser.add_argument("--model", default="stub", help=MODEL_HELP)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path, help="path to write the filtered JSONL to")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    teacher = build_cli_model(args.model, example="distillation", script=SCRIPTED)
    tracer = Tracer(example="distillation", level=1, model_id=teacher.model_id)
    result = run(tracer, teacher, out_path=args.out)
    print(f"wrote {result.out_path} ({len(result.kept)} kept, {len(result.dropped)} dropped)")
    print("dropped:", ", ".join(result.dropped) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
