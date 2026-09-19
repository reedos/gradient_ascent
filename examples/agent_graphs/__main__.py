"""Run the agent-graphs example from the command line.

    python -m examples.agent_graphs --model stub:scripted
    python -m examples.agent_graphs --model stub --question "What is the maximum vent run for the DR-520, and does anything supersede the manual's figure?"

`--model stub` never answers exactly `research` or `write`, so every handoff lands outside
`ALLOWED_HANDOFFS` and the graph is forced straight to `write` with no findings behind it.
`--model stub:scripted` plays SCRIPTED below: the supervisor sends the team back to `research`
three times, each hop turning up one more real source from the corpus, then hands off to `write`
once there is enough to answer -- so the reader sees the graph actually loop and stop on its own.
"""
from __future__ import annotations

import sys

from examples.common.cli import build_cli_model, parse_args
from examples.common.trace import Tracer
from examples.agent_graphs.run import LEVEL, run

DEFAULT_QUESTION = (
    "What is the maximum vent run for the DR-520, and does anything supersede the manual's figure?"
)

# Five model calls: three "research" handoffs, then "write", then the write step's own answer.
# The same sequence tests/test_example_agent_graphs.py scripts for its three-hops-then-write test.
SCRIPTED = [
    "research",
    "research",
    "research",
    "write",
    "The DR-520's vent run is limited to 25 feet with up to 3 elbows, which supersedes the "
    "manual's 35-foot, 4-elbow figure. Sources: dr520-manual#4, service-bulletin#2",
]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(
        sys.argv[1:] if argv is None else argv,
        description="Level 6: agent graphs, a supervisor node that hands off from an allowlist.",
        default_question=DEFAULT_QUESTION,
    )
    model = build_cli_model(args.model, example="agent_graphs", script=SCRIPTED)
    tracer = Tracer(example="agent_graphs", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, None, tracer)
    # The supervisor's handoffs and what each research hop turned up are where this level's claim
    # lives, so print them before the final answer.
    for step in tracer.steps:
        if step.title in ("Supervisor picks the next agent", "Checkpoint after 'research'"):
            print(f"{step.title}: {step.detail}")
    print(answer.text)
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
