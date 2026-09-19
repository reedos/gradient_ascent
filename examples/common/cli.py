"""Shared `__main__` plumbing for the examples: argument parsing and the two stub models an
example can be run against by hand.

    python -m examples.<name> --model stub --question "..."
    python -m examples.<name> --model stub:scripted

`--model stub` is the generic stub: it answers every call by echoing back the last user message.
It exercises an example's control flow and nothing else. Anything an example varies in the
*system* prompt is invisible to it, and any example that parses structure out of the reply takes
its fallback path, every time. That is fine for "does this run", and useless for "show me what
this page says happens".

`--model stub:scripted` is the second stub: an ordered sequence of replies, one per model call,
written down in the example's own `__main__.py` as `SCRIPTED` (a list of `str` or `StubResponse`,
in call order). The sequence is the answer a run would get from a model that behaved the way the
page describes, so the command prints the routing decision, the failed check, the revision, the
pause, rather than an echo. Nothing here calls a model or touches a network: it is a fixture that
lives next to the example it belongs to.

Why `SCRIPTED` lives in `__main__.py` and not in a table somewhere: a sequence kept apart from
the example drifts from it silently, and the first sign is a demo that prints nothing. Here,
`tests/test_scripted_stub.py` runs every example's own command against its own `SCRIPTED` and
fails when the two stop matching, and each example's test file asserts that the sequence it
scripts for itself is the same one `SCRIPTED` holds.

No example's *behavior* is tested through this module. Each example's tests build their own
`StubModel` responses and call `run` directly, so a trace's shape is asserted against a scripted
answer rather than against the generic one below. `tests/test_common.py` tests this module
itself, which is a different thing: that the interactive stub never calls a tool, that it reads
multimodal content as text rather than slicing the parts list, and that the scripted stub says
which call ran out instead of raising `IndexError`.
"""
from __future__ import annotations

import argparse
from typing import Sequence

from examples.common.model import (
    Embedder,
    Message,
    Model,
    StubEmbedder,
    StubModel,
    StubResponse,
    build_embedder,
    build_model,
    content_text,
)

SCRIPTED_SPEC = "stub:scripted"

MODEL_HELP = "stub | stub:scripted | ollama:<tag> | claude:<id>"

Script = Sequence["str | StubResponse"]


def parse_args(
    argv: list[str],
    *,
    description: str,
    default_question: str | None = None,
) -> argparse.Namespace:
    """The common `--model` / `--embedder` / `--question` parser.

    `default_question` is for an example whose first argument is narrower than a question: a
    serial number that has to exist in the production log, a document name. Such an example
    already names a usable one as `SAMPLE_INPUT` in its `run.py`, which is the same constant
    `scripts/record_trace.py` falls back to, so pass that here rather than inventing a second
    convention. `--question` stays accepted either way, so every command already printed on a
    page keeps working.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--model", default="stub", help=MODEL_HELP)
    parser.add_argument(
        "--embedder",
        default=None,
        help=(
            "stub | ollama:<tag>, for an example whose run() takes an embedder. Defaults to "
            "--model, today's pairing; pass this separately when --model is claude:<id>, since "
            "build_embedder has no claude: branch (see examples/common/model.py)."
        ),
    )
    parser.add_argument(
        "--question",
        required=default_question is None,
        default=default_question,
        help="the question to answer" if default_question is None else f"defaults to {default_question!r}",
    )
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


class ScriptExhausted(RuntimeError):
    """The run asked the scripted stub for one more reply than `SCRIPTED` holds.

    Raised instead of `IndexError` (what `StubModel`'s list form raises) and instead of an empty
    string, because both of those read as "the example is broken" when what happened is that the
    example now makes one more call than its sequence was written for. The message names the call
    number, the length of the sequence, and what that call was asking for.
    """


def _excerpt(messages: list[Message], role: str, limit: int = 160) -> str:
    text = next((content_text(m.content) for m in reversed(messages) if m.role == role), "")
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def scripted_stub(script: Script, *, example: str, model_id: str = "stub-scripted") -> StubModel:
    """A `StubModel` that returns `script` in order, one entry per `complete` call.

    Entries are plain strings, or `StubResponse` where a call has to return a tool call. Running
    past the end raises `ScriptExhausted` naming the call number and what was being asked, so a
    sequence that has fallen behind the example says so on the first run rather than producing a
    silently truncated demo.
    """
    responses = [StubResponse(text=entry) if isinstance(entry, str) else entry for entry in script]
    calls = {"n": 0}

    def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
        del tools
        index = calls["n"]
        if index >= len(responses):
            raise ScriptExhausted(
                f"{example}: the scripted stub ran out on model call {index + 1}; SCRIPTED in "
                f"examples/{example}/__main__.py has {len(responses)} "
                f"{'reply' if len(responses) == 1 else 'replies'}.\n"
                f"  call {index + 1} system: {_excerpt(messages, 'system') or '(none)'}\n"
                f"  call {index + 1} user:   {_excerpt(messages, 'user') or '(none)'}\n"
                f"Add the reply that call should get to SCRIPTED, in order, and to the sequence "
                f"tests/test_example_{example}.py asserts against."
            )
        calls["n"] = index + 1
        return responses[index]

    return StubModel(responder, model_id=model_id)


def build_cli_model(spec: str, *, example: str, script: Script | None = None) -> Model:
    """Build the model a `__main__` should run against, from a `--model` spec.

    Additive over `examples.common.model.build_model`: `stub` and every live spec behave exactly
    as before, and `stub:scripted` is the new one. It is an error, not a fallback, to ask for
    `stub:scripted` from an example that has no sequence: falling back to the echo stub would put
    us back where we started, with a command that prints something and demonstrates nothing.
    """
    if spec == SCRIPTED_SPEC:
        if not script:
            raise SystemExit(
                f"--model {SCRIPTED_SPEC} needs an ordered sequence of replies, and "
                f"examples/{example}/__main__.py defines no SCRIPTED. Either add one or run this "
                f"example with --model stub."
            )
        return scripted_stub(script, example=example)
    return build_model(spec, stub=interactive_stub())


def build_cli_embedder(spec: str | None, *, model_spec: str, stub: Embedder | None = None) -> Embedder:
    """The embedder for an example whose `run()` takes one: `--embedder` if it was given, else
    whatever `--model` was, which is the pairing `scripts/record_trace.py` also defaults to.

    `stub:scripted` reads as plain `stub` here. There is nothing to script about a vector: the
    sequence is a list of things a model *said*, and `StubEmbedder` is deterministic already, so
    the retrieval a reader sees under `stub:scripted` is the same retrieval `--model stub` does.
    Without this, `build_embedder` would reject the spec and the command would fail on an example
    that retrieves.
    """
    spec = spec or model_spec
    if spec == SCRIPTED_SPEC:
        spec = "stub"
    return build_embedder(spec, stub=stub or StubEmbedder())
