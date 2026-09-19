"""Build the adaptation example's fine-tuning JSONL files from the command line.

    python -m examples.adaptation --out .local/scratch/adaptation

Writes nothing outside the directory you pass with --out. No model is called and no training
API is contacted; this only builds and validates the data files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examples.adaptation.run import run
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate a small supervised fine-tuning file.")
    parser.add_argument("--out", required=True, type=Path, help="directory to write train.jsonl and val.jsonl into")
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    tracer = Tracer(example="adaptation", level=1, model_id="none")
    result = run(tracer, out_dir=args.out, val_fraction=args.val_fraction, seed=args.seed)
    print(f"wrote {result.train_path} ({len(result.train)} examples)")
    print(f"wrote {result.val_path} ({len(result.val)} examples)")
    print("leaked questions:", ", ".join(result.leaked) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
