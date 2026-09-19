"""Run the design review checklist example from the command line.

    python -m examples.bench_design_review_checklist --model stub:scripted
    python -m examples.bench_design_review_checklist --model stub --question B

`--question` fills this example's board revision ("A", "B" or "C", or a sentence naming one), not
a question; see `examples/common/cli.py` for why every example takes `--question` regardless of
what its first parameter means. A revision this board does not have is refused; a request naming
none is reviewed as revision B.

The interactive stub returns free text, not the JSON this example's two model passes ask for, so
a plain `--model stub` run here shows only the five numeric findings. `--model stub:scripted`
plays SCRIPTED below: a first pass that drafts DR-24 as met for the wrong reason (citing thermal
shutdown, which DR-24's own text disclaims) and DR-30 as met for a reason the rule text actually
supports, and a second pass that rejects the first and confirms the second, the same sequence
`tests/test_example_bench_design_review_checklist.py` runs end to end.
"""
from __future__ import annotations

import json
import sys

from examples.bench_design_review_checklist.run import LEVEL, SAMPLE_INPUT, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer

#: A drafted finding for DR-24 that reasons the way DR-24's own text explicitly disclaims: it
#: calls the board compliant because thermal shutdown protects it, not because the computed
#: junction temperature is under the limit. DR-30's draft is one the rule text actually supports.
_DRAFT_RESPONSE = json.dumps(
    {
        "findings": [
            {
                "rule": "DR-24",
                "status": "met",
                "evidence": (
                    "Thermal shutdown at 145 degC protects the design, so the junction "
                    "temperature requirement is satisfied."
                ),
            },
            {
                "rule": "DR-30",
                "status": "met",
                "evidence": (
                    "TP1, TP2 and TP3 are sized for a fixture probe; TP4 is marked for scope "
                    "use only and is not a fixture contact; the silkscreen revision character "
                    "matches the last character of the assembly number."
                ),
            },
        ]
    }
)
_CHECK_RESPONSE = json.dumps(
    {
        "verdicts": [
            {
                "rule": "DR-24",
                "verdict": "reject",
                "reason": (
                    "DR-24 says a design whose junction temperature reaches the shutdown "
                    "threshold in any rated operating condition does not meet this rule, "
                    "whatever the protection does; citing the shutdown as the reason it is met "
                    "is the opposite of what the rule says."
                ),
            },
            {
                "rule": "DR-30",
                "verdict": "confirm",
                "reason": "Every clause DR-30 lists is addressed by name in the evidence.",
            },
        ]
    }
)

# Two model calls: draft a finding for each rule that needs reading, then check each draft
# against the rule's own full text. The same sequence
# tests/test_example_bench_design_review_checklist.py scripts for its own end-to-end tests.
SCRIPTED = [_DRAFT_RESPONSE, _CHECK_RESPONSE]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 3: check a bill of materials and a netlist summary against DR-0100.",
        default_question=SAMPLE_INPUT,
    )
    model = build_cli_model(args.model, example="bench_design_review_checklist", script=SCRIPTED)
    tracer = Tracer(example="bench_design_review_checklist", level=LEVEL, model_id=model.model_id)
    report = run(args.question, model, tracer)
    print(report.text)
    print("citations:", ", ".join(report.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
