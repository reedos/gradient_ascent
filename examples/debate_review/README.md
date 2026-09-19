# Review and debate

Level 6: an author retrieves its own sources and drafts an answer; a separate reviewer, with its
own independent retrieval over the same corpus, decides on each turn whether to check one more
specific claim (`CHECK: <query>`) or stop and give a verdict (`ACCEPT` or `REJECT: <reason>`).
The reviewer never sees what the author searched, only the draft and its own checks.

Every reviewer turn is a model decision -- keep checking, or stop -- capped at `MAX_ROUNDS`
(default 2) checks before code forces a verdict. The reviewer's own search always runs for real
against the corpus; nothing in this file fabricates a result to make a draft look right.

Run it:

```
python -m examples.debate_review --model stub --question "What is the maximum vent run for the DR-520?"
```

`decided_by: "model"` on every reviewer turn; `decided_by: "code"` on the author's draft, the
reviewer's own search, and the round cap.
