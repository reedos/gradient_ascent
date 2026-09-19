# Rubric grading

Level 6: a grader scores a short essay against a four-criterion rubric, one pass, with a verbatim
quote as evidence for every score. A second, independent reviewer, who has not seen the grader's
own reasoning, sees only the submission, the rubric and the proposed scores, and decides on each
turn whether to check one more criterion's full rubric text or stop with a verdict.

Code drops any score whose quote is not actually in the submission and marks that criterion
unevidenced. A rejected criterion, an unevidenced criterion, or the reviewer's round cap forcing a
verdict all send the whole submission to the teacher as a checkpoint. Everything else returns a
proposed grade; nothing here posts a grade to a gradebook on its own.

Run it:

```
python -m examples.rubric_grading --model stub:scripted
```

The reviewer asks for one criterion's full rubric text, reads it, and rejects a score of 3 the
rubric itself puts at 0. That sends the whole submission to the teacher as a checkpoint.

Every reviewer turn (`CHECK: <criterion>`, `ACCEPT`, or `REJECT: <reason>`) is
`decided_by: "model"`. The grader's own call, the quote check, the round cap, and sending a result
to the teacher are all `decided_by: "code"`.

This example scores one submission per run and does not average, aggregate or rank submissions
against each other, and it never writes a final grade anywhere; the checkpoint or proposed grade
is the whole of its output.
