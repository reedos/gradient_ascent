"""Run the synthetic data example from the command line.

    python -m examples.synthetic_data --model stub --out .local/scratch/synthetic-data/questions.jsonl

Writes nothing outside the file you pass with --out. No training API is contacted; this only
generates, checks and writes paraphrased questions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examples.common.cli import interactive_stub
from examples.common.model import build_model
from examples.common.trace import Tracer
from examples.synthetic_data.run import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate, deduplicate and verify paraphrased questions.")
    parser.add_argument("--model", default="stub", help="stub | ollama:<tag> | claude:<id>")
    parser.add_argument("--out", required=True, type=Path, help="path to write the verified JSONL to")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="synthetic_data", level=1, model_id=model.model_id)
    result = run(tracer, model, out_path=args.out)
    print(f"wrote {result.out_path} ({len(result.kept)} kept, {len(result.rejected)} rejected)")
    reasons = {"duplicate": 0, "failed verification": 0}
    for r in result.rejected:
        reasons[r.reason] += 1
    print(f"rejected: {reasons['duplicate']} duplicate, {reasons['failed verification']} failed verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
