"""Shared `__main__` plumbing for the examples: argument parsing and a default stub model for
interactive use (`python -m examples.<name> --model stub --question "..."`).

No example's *behavior* is tested through this module. Each example's tests build their own
`StubModel` responses and call `run` directly, so a trace's shape is asserted against a scripted
answer rather than against the generic one below. `tests/test_common.py` tests this module
itself, which is a different thing: that the interactive stub never calls a tool, and that it
reads multimodal content as text rather than slicing the parts list.
"""
from __future__ import annotations

import argparse

from examples.common.model import Message, StubModel, StubResponse, content_text


def parse_args(argv: list[str], *, description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--model", default="stub", help="stub | ollama:<tag> | claude:<id>")
    parser.add_argument(
        "--embedder",
        default=None,
        help=(
            "stub | ollama:<tag>, for an example whose run() takes an embedder. Defaults to "
            "--model, today's pairing; pass this separately when --model is claude:<id>, since "
            "build_embedder has no claude: branch (see examples/common/model.py)."
        ),
    )
    parser.add_argument("--question", required=True, help="the question to answer")
    return parser.parse_args(argv)


def interactive_stub() -> StubModel:
    """A `StubModel` for manual `--model stub` runs: never fails, never calls a tool, and
    answers with a short placeholder that names what it was asked. Good enough to exercise an
    example's control flow by hand; a real dry run against the corpus belongs in the tests."""

    def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
        # content_text, not m.content: a multimodal request's content is a list of parts, and
        # slicing that would take the first 100 parts rather than the first 100 characters
        question = next((content_text(m.content) for m in reversed(messages) if m.role == "user"), "")
        return StubResponse(text=f"[interactive stub] no live model; asked: {question[:100]!r}")

    return StubModel(responder, model_id="stub-interactive")
