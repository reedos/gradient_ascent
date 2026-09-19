"""Run the reviewing example from the command line.

    python -m examples.reviewing --scenario clean
    python -m examples.reviewing --scenario mismatch
    python -m examples.reviewing --scenario missing

Each scenario is a drafted answer -- its text and the citations it names -- checked against the
synthetic corpus in evals/corpus/. `clean` cites only a section that carries the figure it
states. `mismatch` adds a second citation whose section carries none of them. `missing` states a
figure no cited section carries and cites one section that does not exist at all.

`--model` is accepted for a uniform interface with the other examples but is not used: this
checker calls no model, so there is nothing for `stub:scripted` to play here either.
"""
from __future__ import annotations

import argparse
import sys

from evals.corpus import load_sections
from examples.common.cli import MODEL_HELP
from examples.common.trace import Tracer
from examples.common.types import Answer
from examples.reviewing.run import LEVEL, run

SCENARIOS = {
    "clean": Answer(
        text="The HLV-2205 drain pump costs $52.00. Sources: parts-list#2",
        citations=["parts-list#2"],
    ),
    "mismatch": Answer(
        text="The HLV-2205 drain pump costs $52.00. Sources: parts-list#2, dw300-manual#3",
        citations=["parts-list#2", "dw300-manual#3"],
    ),
    "missing": Answer(
        text="The HLV-2205 drain pump costs $52.00 and is covered for 36 months. "
        "Sources: parts-list#2, warranty-policy#9",
        citations=["parts-list#2", "warranty-policy#9"],
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 2 shape: check a drafted answer's figures against the sections it cites.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="mismatch")
    parser.add_argument("--model", default="stub", help=f"accepted but unused (this example calls no model); {MODEL_HELP}")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    sections = load_sections()
    tracer = Tracer(example="reviewing", level=LEVEL, model_id="no-model-called")
    report = run(SCENARIOS[args.scenario], sections, tracer)
    print("figures claimed:", ", ".join(report.figures_claimed) or "none")
    print("citations checked:", ", ".join(report.checked) or "none")
    print("clean:", report.clean)
    for flag in report.flags:
        print("look at:", flag.subject, "-", flag.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
