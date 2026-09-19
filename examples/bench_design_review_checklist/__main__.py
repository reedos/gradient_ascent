"""Run the design review checklist example from the command line.

    python -m examples.bench_design_review_checklist --model stub --question B

`--question` fills this example's board revision ("A", "B" or "C", or a sentence naming one), not
a question; see `examples/common/cli.py` for why every example takes `--question` regardless of
what its first parameter means. A revision this board does not have is refused; a request naming
none is reviewed as revision B. The interactive stub returns free text, not the JSON this example's two model
passes ask for, so a plain `--model stub` run here shows only the five numeric findings; the two
findings that need reading are demonstrated with a scripted stub in
`tests/test_example_bench_design_review_checklist.py`.
"""
from __future__ import annotations

import sys

from examples.bench_design_review_checklist.run import LEVEL, run
from examples.common.cli import interactive_stub, parse_args
from examples.common.model import build_model
from examples.common.trace import Tracer


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: check a bill of materials and a netlist summary against DR-0100.",
    )
    model = build_model(args.model, stub=interactive_stub())
    tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id=model.model_id)
    report = run(args.question, model, tracer)
    print(report.text)
    print("citations:", ", ".join(report.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
