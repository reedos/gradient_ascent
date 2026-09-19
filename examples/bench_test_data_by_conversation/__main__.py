"""Run the test-data-by-conversation example from the command line.

    python -m examples.bench_test_data_by_conversation --model stub:scripted
    python -m examples.bench_test_data_by_conversation --model stub --question "Do the retested boards actually pass?"
    python -m examples.bench_test_data_by_conversation --model stub --question "Did any soak unit fail to settle?"
    python -m examples.bench_test_data_by_conversation --model stub --question "Is any block of the sweep impossible?"

`--question` is the ad hoc question about the retest export, the soak log or the characterization
sweep; `run.py`'s module docstring says which tables are loaded and what the sandbox will and will
not run.

`--model stub` never calls the tool, so the command shows only the range check and an echoed
answer, never the sandbox. `--model stub:scripted` plays SCRIPTED below: the model writes the
snippet the recipe page walks through for the first question above, the sandbox runs it for real
against the retest export, and a second call turns the sandbox's own figures into the final
answer, the same sequence tests/test_example_bench_test_data_by_conversation.py runs end to end.
"""
from __future__ import annotations

import sys

from examples.bench_test_data_by_conversation.run import LEVEL, run
from examples.common.cli import build_cli_model, parse_args
from examples.common.model import StubResponse, ToolCall
from examples.common.trace import Tracer

DEFAULT_QUESTION = "Do the retested boards actually pass?"

#: The snippet the recipe page walks through for DEFAULT_QUESTION: every retested board against
#: the VOUT limits, run for real against evals/bench/data/retest-2026-08-31.csv.
_RETEST_SNIPPET = """
fails = [r for r in TABLES["retest"] if not (4.9500 <= r["value_v"] <= 5.0500)]
passing = [r["value_v"] for r in TABLES["retest"] if 4.9500 <= r["value_v"] <= 5.0500]
result = {
    "n": len(TABLES["retest"]),
    "n_pass": len(passing),
    "n_fail": len(fails),
    "fail_serials": sorted(r["serial"] for r in fails),
    "pass_mean_v": round(mean(passing), 4),
    "pass_min_v": min(passing),
    "pass_max_v": max(passing),
}
"""

# Two model calls: write the analysis snippet, then turn what the sandbox returned into a short
# answer. The same sequence tests/test_example_bench_test_data_by_conversation.py runs end to end.
SCRIPTED = [
    StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": _RETEST_SNIPPET})]),
    (
        "Fifteen of the eighteen retested boards are within spec; three still fail: "
        "SRB5030-2608-0052, SRB5030-2608-0063 and SRB5030-2608-0178."
    ),
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 4: the model writes one analysis snippet; a sandbox runs it.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="bench_test_data_by_conversation", script=SCRIPTED)
    tracer = Tracer(example="bench_test_data_by_conversation", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer)
    # The range check and the sandbox's own output are the point of this recipe, and they live in
    # the trace rather than in the final answer, so print them before it.
    for step in tracer.steps:
        if step.title != "Ask for a final answer":
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("data:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
