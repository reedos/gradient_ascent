# Human approval

Level 3: a draft answer is checked against two fixed thresholds. One is no citation at all (low
confidence) and the other is a dollar figure in the text (high cost), and if either trips, `run`
returns a `PendingReview` checkpoint instead of a final `Answer`. A separate `resume` call takes
that checkpoint, a person's decision (`approve`, `edit` or `reject`), and, for an edit, their
corrected text, and produces the final answer.

The pause is a fixed rule the code checks against the draft's own content. The model is never
asked whether it wants a person to look, and never sees the reviewer's decision until `resume`
injects it as plain text; a design where the model itself could choose to request approval would
be a tool call, and belongs at level 4, not here.

Run it:

```
python -m examples.human_in_the_loop --model stub:scripted
```

The draft is a real, cited answer, and it still pauses: it quotes $52.00, which trips the
`high_cost` threshold. Add `--decision approve` (or `edit`/`reject`, with `--note` for an edit's
replacement text) to resume it in the same command instead of only printing the checkpoint;
`--decision reject` ends the run with no answer given.

Every step is `decided_by: "code"`, including the pause and the resume.
