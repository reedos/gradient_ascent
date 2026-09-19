# Human approval

Level 3: a draft answer is checked against two fixed thresholds — no citation at all (low
confidence) or a dollar figure in the text (high cost) — and if either trips, `run` returns a
`PendingReview` checkpoint instead of a final `Answer`. A separate `resume` call takes that
checkpoint, a person's decision (`approve`, `edit` or `reject`), and — for an edit — their
corrected text, and produces the final answer.

The pause is a fixed rule the code checks against the draft's own content. The model is never
asked whether it wants a person to look, and never sees the reviewer's decision until `resume`
injects it as plain text; a design where the model itself could choose to request approval would
be a tool call, and belongs at level 4, not here.

Run it:

```
python -m examples.human_in_the_loop --model stub --question "What does HLV-2205 cost?"
```

Add `--decision approve` (or `edit`/`reject`, with `--note` for an edit's replacement text) to
resume a paused run immediately instead of just printing the checkpoint. Every step is
`decided_by: "code"`, including the pause and the resume.
