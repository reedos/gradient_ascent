"""Track: observability. Turns this site's own `trace.json` shape (`examples/common/trace.py`)
into a list of span-shaped dictionaries named the way OpenTelemetry's own generative AI semantic
conventions document them, so a run this site already records could be handed to any
OpenTelemetry-compatible backend instead of only this site's trace player.

Those conventions carry a Status of Development as of the date this page cites them: nothing
below claims to implement a finished specification, only to borrow its attribute names
(`gen_ai.operation.name`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) for a `kind:
"model"` step. A `kind: "code"` step gets none of them, since it is not a generative AI operation
and giving it one would misdescribe it to any backend reading these spans.

`detail` is the one field this module treats as sensitive by default: a step's `detail` can hold
a fragment of a prompt, an answer, a retrieved passage or a tool call's arguments, so it is left
out unless the caller opts in, mirroring the opt-in gate the specification itself documents for
message content. It is NOT written to `gen_ai.input.messages`: that attribute is defined as the
chat history sent to the model, a structured list of messages, and a free-text `detail` string is
not that. It goes to this site's own namespace instead, so no backend reads it as something the
specification defines.

Two limits this module does not fix, stated here because the page that shows it teaches
redaction. A step's `title` is exported as the span name with no redaction at all, so a title
must never be written to carry content. And redacting at export time does nothing for a
`trace.json` that was already written to disk with content in it; redaction has to be in place
before the trace is recorded, not after.
"""
from __future__ import annotations

from typing import Any

from examples.common.model import Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1  # observability is a track technique, not a rung on the ladder; see content/taxonomy.json

# Attribute names as OpenTelemetry's gen-ai semantic conventions document them (Status:
# Development). Copied, not invented, so a diff against a future stable release is a diff
# against these three strings.
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

# Not OpenTelemetry attributes: this site's own fields, namespaced so neither is ever mistaken
# for one the specification defines. `decided_by` is what the site's own charts read, and the
# specification has no equivalent. `detail` is free text, not the structured message list
# `gen_ai.input.messages` is defined as, so it does not borrow that name either.
SITE_DECIDED_BY = "gradient_ascent.decided_by"
SITE_DETAIL = "gradient_ascent.detail"  # only written when capture_content=True


def to_otel_spans(trace: dict[str, Any], *, capture_content: bool = False) -> list[dict[str, Any]]:
    """One span-shaped dict per step in `trace`, in the shape `Tracer.write` produces.

    `capture_content=False` (the default) never lets a step's `detail` leave this function.
    The span's `name` is the step's `title`, copied through either way; see the module docstring.
    """
    spans: list[dict[str, Any]] = []
    for step in trace["steps"]:
        attributes: dict[str, Any] = {SITE_DECIDED_BY: step["decided_by"]}
        if step["kind"] == "model":
            attributes[GEN_AI_OPERATION_NAME] = "chat"
            attributes[GEN_AI_INPUT_TOKENS] = step["tokens_in"]
            attributes[GEN_AI_OUTPUT_TOKENS] = step["tokens_out"]
        if capture_content:
            attributes[SITE_DETAIL] = step["detail"]
        spans.append({"name": step["title"], "duration_ms": step["ms"], "attributes": attributes})
    return spans


def span_summary(spans: list[dict[str, Any]]) -> dict[str, Any]:
    """What a dashboard would chart from one run: total spans, how many the model decided, and
    total tokens -- the same three numbers `docs/EVALS.md` reads out of a result file, so a
    recorded trace and a scored result can be compared on the same terms."""
    model_decided = sum(1 for s in spans if s["attributes"][SITE_DECIDED_BY] == "model")
    tokens_in = sum(s["attributes"].get(GEN_AI_INPUT_TOKENS, 0) for s in spans)
    tokens_out = sum(s["attributes"].get(GEN_AI_OUTPUT_TOKENS, 0) for s in spans)
    return {
        "span_count": len(spans),
        "model_decided_steps": model_decided,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def _recording_demo_trace() -> dict[str, Any]:
    """A small trace built with a real `Tracer` -- a retrieval step and a model step, shaped
    like `examples/rag` -- for `run` below to export. Deliberately its own copy rather than
    `examples.observability.__main__`'s `_demo_trace`: that one is what the page's exercise
    tells a reader to edit, and importing it here would make editing it also change what a
    recording exports."""
    tracer = Tracer(example="rag", level=2, model_id="stub-rag-1")
    tracer.record(
        kind="code",
        decided_by="code",
        title="Embed and retrieve top-k",
        detail="dw480-manual#9, dw480-manual#9.2",
        ms=31.0,
    )
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model for a cited answer",
        detail="Two years from delivery [1].",
        tokens_in=1850,
        tokens_out=64,
        ms=2100.0,
    )
    return tracer.to_dict()


def run(text: str, model: Model, tracer: Tracer) -> Answer:
    """Recordable entry point for `record_trace.py`. Calls no model and ignores `text`: there is
    no question to route through a span exporter. Builds a small demo trace shaped like
    `examples/rag` (see `_recording_demo_trace`), exports it to OpenTelemetry-shaped spans, and
    records both steps as `code`."""
    del text, model
    trace = _recording_demo_trace()
    tracer.record(kind="code", decided_by="code", title="Build a demo trace", detail=f"{len(trace['steps'])} step(s)")
    spans = to_otel_spans(trace)
    tracer.record(
        kind="code", decided_by="code", title="Export to OpenTelemetry-shaped spans", detail=f"{len(spans)} span(s)"
    )
    return Answer(text=f"exported {len(spans)} OpenTelemetry-shaped span(s)", citations=[])
