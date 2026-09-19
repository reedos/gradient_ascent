"""Run the gateway demo from the command line.

    python -m examples.ai_gateways --demo

Two keys, two providers each. `team-a`'s primary answers directly. `team-b`'s primary always
fails, so every call for that key falls back to its secondary. `team-a`'s budget is set small on
purpose so the second call for that key is refused outright, printed rather than raised, so the
whole demo runs to completion.
"""
from __future__ import annotations

import argparse
import sys

from examples.ai_gateways.run import BudgetExceeded, Gateway, Route
from examples.common.model import Message, StubModel, StubResponse


class _AlwaysFails(StubModel):
    """A provider that never answers -- stands in for an outage or a rejected request."""

    def __init__(self) -> None:
        super().__init__([], model_id="down-provider")

    def complete(self, messages, **kwargs):  # noqa: ANN001, ANN003 - matches Model.complete
        raise RuntimeError("provider unavailable")


def _demo_gateway() -> Gateway:
    team_a_primary = StubModel([StubResponse(text="answer from team-a's primary")], model_id="primary-a")
    team_a_fallback = StubModel([StubResponse(text="unused")], model_id="fallback-a")
    team_b_primary = _AlwaysFails()
    team_b_fallback = StubModel([StubResponse(text="answer from team-b's fallback")], model_id="fallback-b")
    return Gateway(
        routes={
            "team-a": Route(primary=team_a_primary, fallback=team_a_fallback),
            "team-b": Route(primary=team_b_primary, fallback=team_b_fallback),
        },
        budgets={"team-a": 10, "team-b": 10_000},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="run the two-key, two-provider demo (the only mode today)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.demo:
        parser.error("pass --demo")

    gateway = _demo_gateway()
    question = [Message(role="user", content="What's the DW-300's Normal cycle water use?")]

    completion = gateway.complete("team-a", question)
    print(f"team-a: {completion.text!r} (model={completion.model_id})")

    try:
        gateway.complete("team-a", question)
    except BudgetExceeded as exc:
        print(f"team-a, second call: refused -- {exc}")

    completion = gateway.complete("team-b", question)
    print(f"team-b: {completion.text!r} (model={completion.model_id}, fell back to its secondary)")

    print("\nlog (prompt redacted by default):")
    for entry in gateway.log:
        print(f"  {entry.key:<8} model={entry.model_id:<14} in={entry.tokens_in:>3} out={entry.tokens_out:>3} "
              f"fell_back={entry.fell_back} prompt={entry.prompt!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
