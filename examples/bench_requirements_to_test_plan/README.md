# Requirements into a test plan

Level 3: a fixed chain over the SRB-5030's datasheet requirements. Read them, ask the model to
propose one test per requirement (one call each, in the same order every run), build the
traceability table from what came back, then have code check it: every requirement covered,
every proposed test naming a requirement, an instrument this bench actually has, a limit and a
unit, and no limit copied from a datasheet figure a later engineering change notice superseded.

`check_coverage` is a pass or fail with no model in it. If it fails, `run` returns a `Blocked`
result naming exactly what is wrong, requirement by requirement, and there is nothing pending
approval. If it passes, `run` returns a `PendingApproval` checkpoint; a separate `resume` call
takes a person's decision (`approve` or `reject`) and produces the final plan or a note that it
was not adopted. Nothing is adopted without that call.

Run it:

```
python -m examples.bench_requirements_to_test_plan --model stub --question "B"
```

`--question` takes a board revision, `A`, `B` or `C`: the datasheet's 36.0 V input ceiling is
superseded to 32.0 V for revisions A and B, and the requirement used to build the plan reflects
that. Add `--decision approve` (or `reject`) to resume a run that cleared the coverage check
immediately instead of just printing the checkpoint. Every step is `decided_by: "code"`: the
model drafts, and code decides everything else, including whether the plan ever reaches a person.
