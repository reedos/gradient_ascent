# Voice agents

Level 5, but honest about what this is: a text simulation of one spoken turn's control flow, not
audio. Nothing here records, streams, transcribes or synthesizes sound; the caller's utterance is
carried as an `AudioPart` label alongside the transcript actually sent to the model, the pattern
`examples/common/model.py` documents for a trace that never reaches a real speech model.

The model decides, chunk by chunk, whether to keep talking (`continue_speaking`) or yield the
floor, `decided_by: "model"` either way, capped at 3 chunks (`MAX_CHUNKS_PER_TURN`) standing in
for a latency budget. A simulated interruption (`interrupt_after_chunk`) or a token cap
(`MAX_TOKENS`) can cut the agent off first; both are `decided_by: "code"`, since neither is the
model's choice, the same way a real system's voice activity detector, not the model, notices a
caller has started talking.

Run it:

```
python -m examples.voice_agents --model stub:scripted
```

Two chunks rather than one flat reply, with the model choosing to keep talking after the first
and yielding the floor on its own after the second, before the cap could stop it.
