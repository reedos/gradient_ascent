"""Level 5: voice agents. This is a text simulation of one spoken turn's control flow, not a
real voice pipeline: no audio is recorded, streamed, transcribed or synthesized anywhere in this
repository. The user's utterance is carried as an `AudioPart` label (see
`examples/common/model.py`), the honest way to reference audio in a trace that never reaches a
real speech model, alongside a `TextPart` transcript, which is what the model actually reads.

Real-time turn-taking has two decisions this example keeps separate, the way the makers'
realtime APIs and voice frameworks document them (see this page's Use it lane): whether to keep
talking or yield the floor is the model's decision every time, `decided_by: "model"`, the same
shape as every other level-5 loop on this site. Whether an incoming interruption cuts the agent
off mid-response is not the model's decision at all -- it is a signal the surrounding system
acts on the instant it arrives, `decided_by: "code"`, the same way a step or token cap is. A
per-turn chunk cap stands in for a latency budget: past a certain number of chunks, a real system
has to cut the agent off to stay responsive, whether or not the model was done.
"""
from __future__ import annotations

from examples.common.agent_loop import record_completion
from examples.common.model import AudioPart, Embedder, Message, Model, TextPart
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_CHUNKS_PER_TURN = 3
MAX_TOKENS = 800
SYSTEM_PROMPT = (
    "You are speaking with a caller in real time. Answer in short spoken chunks. After each "
    "chunk, call continue_speaking if you have more to say, or say nothing further and stop "
    "calling tools once you are done, so the floor returns to the caller."
)
CONTINUE_TOOL = {
    "name": "continue_speaking",
    "description": "Add one more short spoken chunk before yielding the floor back to the caller.",
    "parameters": {"type": "object", "properties": {}},
}


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    interrupt_after_chunk: int | None = None,
    max_chunks: int = MAX_CHUNKS_PER_TURN,
    max_tokens: int = MAX_TOKENS,
) -> Answer:
    del embedder  # no retrieval here; this page is about turn control, not what gets said
    content = [AudioPart(media_type="audio/wav", label=question), TextPart(text=question)]
    tracer.record(kind="code", decided_by="code", title="Caller speaks", detail=f"[audio] {question[:150]}")
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=content)]

    chunks: list[str] = []
    tokens_used = 0
    for chunk_index in range(max_chunks):
        if interrupt_after_chunk is not None and chunk_index == interrupt_after_chunk:
            tracer.record(
                kind="code", decided_by="code", title="Caller interrupts; code cuts the agent off",
                detail=f"stopped after {len(chunks)} chunk(s)",
            )
            break

        completion = model.complete(messages, tools=[CONTINUE_TOOL], max_tokens=100)
        tokens_used += completion.tokens_in + completion.tokens_out
        chunks.append(completion.text)

        if not completion.tool_calls:
            record_completion(tracer, decided_by="model", title="Model finishes and yields the floor", completion=completion)
            break

        record_completion(tracer, decided_by="model", title="Model chooses to keep talking", completion=completion)
        messages.append(Message(role="assistant", content=completion.text))

        if tokens_used >= max_tokens:
            tracer.record(
                kind="code", decided_by="code", title="Latency budget reached; code cuts the agent off",
                detail=f"{tokens_used} >= {max_tokens} tokens",
            )
            break
    else:
        tracer.record(
            kind="code", decided_by="code", title="Chunk cap reached; code cuts the agent off",
            detail=f"{max_chunks} chunks",
        )

    return Answer(text=" ".join(c for c in chunks if c), citations=[])
