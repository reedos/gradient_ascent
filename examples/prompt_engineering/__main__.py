"""Run the prompt-engineering example from the command line.

    python -m examples.prompt_engineering --model stub:scripted --structured
    python -m examples.prompt_engineering --model stub:scripted --no-structured
    python -m examples.prompt_engineering --model stub --structured
    python -m examples.prompt_engineering --model stub --no-structured

`--model stub` echoes the passage and question back either way, which never matches the PART/
PRICE format the check looks for, so the two runs are indistinguishable in the reply text. Wave 9
worked around that by printing the system prompt itself so a reader could tell the difference by
eye. `--model stub:scripted` now does that job honestly: it plays a different SCRIPTED reply per
flag (`scripted()` below), matching a real reply to each style of prompt, so the two commands are
distinguishable by their actual output, not by a dump of the prompt that produced it.
"""
from __future__ import annotations

import argparse
import sys

from examples.common.cli import MODEL_HELP, build_cli_model
from examples.common.trace import Tracer
from examples.prompt_engineering.run import LEVEL, run

DEFAULT_QUESTION = "What is the DW-480's drain pump part number and price?"


def scripted(*, structured: bool = True) -> list[str]:
    """The one reply each style of prompt tends to get. A structured prompt (role, exact output
    format, one worked example) gets a reply the PART/PRICE check can parse; a bare prompt with
    no format instruction tends to get a hedged, unstructured answer that fails it."""
    if structured:
        return ["PART: HLV-2205\nPRICE: $52.00"]
    return ["I believe it's one of the HLV-22 series pumps, but I'm not certain of the exact price."]


# One model call either way; which reply plays depends on --structured / --no-structured.
SCRIPTED = scripted()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 1: prompt engineering, structured vs. bare.")
    parser.add_argument("--model", default="stub", help=MODEL_HELP)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--structured", dest="structured", action="store_true", default=True)
    parser.add_argument("--no-structured", dest="structured", action="store_false")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    script = SCRIPTED if args.structured else scripted(structured=False)
    model = build_cli_model(args.model, example="prompt_engineering", script=script)
    tracer = Tracer(example="prompt_engineering", level=LEVEL, model_id=model.model_id)
    answer = run(args.question, model, tracer, structured=args.structured)
    print(f"structured: {args.structured}")
    print(f"reply: {answer.text}")
    print("matched PART/PRICE format:", "yes" if answer.citations else "no")
    print("citations:", ", ".join(answer.citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
