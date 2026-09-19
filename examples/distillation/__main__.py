"""Run the distillation example from the command line.

    python -m examples.distillation --model stub --out .local/scratch/distillation/student.jsonl

Writes nothing outside the file you pass with --out. No training API is contacted; this only
captures and filters the teacher's answers.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examples.common.cli import interactive_stub
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.distillation.run import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture and filter a teacher model's answers into a student training file.")
    parser.add_argument("--model", default="stub", help="stub | ollama:<tag> | claude:<id> (the teacher)")
    parser.add_argument("--out", required=True, type=Path, help="path to write the filtered JSONL to")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    teacher = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="distillation", level=1, model_id=teacher.model_id)
    result = run(tracer, teacher, out_path=args.out)
    print(f"wrote {result.out_path} ({len(result.kept)} kept, {len(result.dropped)} dropped)")
    print("dropped:", ", ".join(result.dropped) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
