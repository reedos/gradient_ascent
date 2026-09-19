"""Build the adaptation example's fine-tuning JSONL files from the command line.

    python -m examples.adaptation --out .local/scratch/adaptation

Writes nothing outside the directory you pass with --out. No model is called and no training
API is contacted; this only builds and validates the data files, so there is nothing for
`stub:scripted` to play here either.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examples.adaptation.run import run
from examples.common.cli import MODEL_HELP
from examples.common.trace import Tracer

DEFAULT_OUT = Path(".local/scratch/adaptation")

# No model call, so no SCRIPTED sequence; --out needs a real directory to write into, and the
# test harness substitutes a real temporary one for {tmpdir} so running the suite leaves nothing
# behind in .local/scratch.
DEMO_ARGV = ["--out", "{tmpdir}/adaptation"]


def _is_placeholder(out: Path) -> bool:
    """True if --out still carries the {tmpdir} placeholder DEMO_ARGV holds.

    Only tests/test_scripted_stub.py substitutes it. Copied into a shell by hand it is an
    ordinary path, and writing to it creates a directory literally named `{tmpdir}`, so main
    refuses it instead and says what to pass.
    """
    if "{" not in str(out):
        return False
    print(
        f"--out is still the {{tmpdir}} placeholder from DEMO_ARGV, which only "
        f"tests/test_scripted_stub.py substitutes. Pass a real path: --out {DEFAULT_OUT}",
        file=sys.stderr,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate a small supervised fine-tuning file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"directory to write train.jsonl and val.jsonl into (defaults to {DEFAULT_OUT})")
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default="stub", help=f"accepted but unused (this example calls no model); {MODEL_HELP}")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if _is_placeholder(args.out):
        return 2

    tracer = Tracer(example="adaptation", level=1, model_id="none")
    result = run(tracer, out_dir=args.out, val_fraction=args.val_fraction, seed=args.seed)
    print(f"wrote {result.train_path} ({len(result.train)} examples)")
    print(f"wrote {result.val_path} ({len(result.val)} examples)")
    print("leaked questions:", ", ".join(result.leaked) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
