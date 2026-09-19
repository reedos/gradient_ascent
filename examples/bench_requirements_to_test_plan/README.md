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
python -m examples.bench_requirements_to_test_plan --model stub:scripted
```

Eight requirements, each with a proposed test naming the instrument it runs on, its limit and its
unit, held pending approval because the coverage check cleared.

The same run against the echo stub exits 1 and prints "no test was proposed for this requirement"
eight times:

```
python -m examples.bench_requirements_to_test_plan --model stub --question "B"
```

That is honest, not broken. The echo is never the JSON the proposal step asks for, so no
requirement ends up covered, `check_coverage` fails, and `run` returns `Blocked` with nothing
pending approval. A coverage check that let a plan through on eight empty proposals would be the
defect.

`--question` takes a board revision. A bare `A`, `B` or `C` works, and so does a sentence naming
one ("a test plan for revision C boards"), since `scripts/record_trace.py` fills this example's
first argument from `--question` like any other. A revision this board does not have is refused
rather than guessed at, and a request that names none gets revision A, whose 32.0 V ceiling is the
stricter of the two. The revision decides two requirements: the datasheet's 36.0 V input ceiling
is superseded to 32.0 V for revisions A and B, and the line regulation sweep those revisions are
tested over stops at 32.0 V with it.

Add `--decision approve` (or `reject`) to resume a run that cleared the coverage check
immediately instead of just printing the checkpoint. Every step is `decided_by: "code"`: the
model drafts, and code decides everything else, including whether the plan ever reaches a person.
