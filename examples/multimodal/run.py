"""Level 1: images, audio and video. One request that carries a picture and words together.

A photo of an appliance's rating plate plus a question about it, sent as one request, and the
reply checked against the two fields the caller actually wanted. The picture goes first: the
Messages API's vision guide says a model works best when images come before text, and both
documented backends take the parts in the order you give them.

Nothing in this repo ships real image bytes, so `ImagePart` here carries a reference and a
label rather than base64. The label is what a text-only path prints in the trace; a real caller
reads the file and passes base64 in `data`, which is the form both documented backends take.

Audio does not go in as audio. Neither backend in `examples/common/model.py` documents an audio
input block, so both raise a `NotImplementedError` rather than guess a wire format. The working
shape is the one below: transcribe first, and send the transcript as text alongside the picture.
Every step is `decided_by: "code"`: the code always builds this request and always asks once.
"""
from __future__ import annotations

import re

from examples.common.model import ImagePart, Message, Model, TextPart, content_text
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1
PLATE_RE = re.compile(r"MODEL:\s*(DW-\d{3}|DR-\d{3})\s+SERIAL:\s*([A-Z0-9-]{4,})", re.IGNORECASE)
# A label-only stand-in for a photo, the same way this repo stands in for a picture everywhere
# else it needs one: no real bytes, just enough for a text-only path to say what it would have
# shown. This is what `run` records against when nothing more specific is given -- see
# `record_trace.py`, which cannot supply an image of its own through `--question`.
SYNTHETIC_PLATE = ImagePart(media_type="image/png", label="synthetic DW-480 rating plate")
SYSTEM_PROMPT = (
    "You read appliance rating plates from photographs. Reply in exactly this format and nothing "
    "else:\nMODEL: <model number>\nSERIAL: <serial number>\n"
    "If either is not legible in the picture, write UNREADABLE in its place instead of guessing."
)


def build_request(image: ImagePart, transcript: str, question: str) -> list[Message]:
    """One user message whose content is a list of parts: the picture, then the words.

    A transcript is just text by the time it gets here. That is the whole point of doing the
    transcription as its own step: the request that reaches the model is an ordinary one.
    """
    parts: list[TextPart | ImagePart] = [image]
    if transcript:
        parts.append(TextPart(text=f"What the owner said about this photo: {transcript}"))
    parts.append(TextPart(text=question))
    return [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=parts)]


def run(question: str, model: Model, tracer: Tracer, *, image: ImagePart = SYNTHETIC_PLATE, transcript: str = "") -> Answer:
    messages = build_request(image, transcript, question)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Assemble one request from a picture and words",
        detail=content_text(messages[-1].content),
    )
    completion = model.complete(messages, max_tokens=200)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model to read the plate",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )
    match = PLATE_RE.search(completion.text)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check the reply against the two fields asked for",
        detail="matched MODEL/SERIAL" if match else f"did not match: {completion.text[:80]!r}",
    )
    if not match:
        return Answer(text="The reply did not give a model and a serial in the requested form.")
    return Answer(
        text=f"Model {match.group(1).upper()}, serial {match.group(2).upper()}.",
        citations=[image.label] if image.label else [],
    )
