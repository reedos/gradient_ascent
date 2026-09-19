# Write and check (evaluator-optimizer)

Level 3: one call drafts an answer, a second, separate call checks it against one explicit
criterion — does every citation the draft claims actually appear among the sources it was given
— and if not, a third call revises using that feedback. The loop repeats until the check passes
or a fixed cap (`MAX_REVISIONS`, default 2) is reached, whichever comes first.

The checker is asked for one written-down thing, not "is this good": a vague prompt lets the
checker's own judgment drift between calls the same way the drafter's would, which checks
nothing. The cap is in code, not in the model, so the loop can run its full length but never one
iteration longer.

Run it:

```
python -m examples.evaluator_optimizer --model stub --question "How often should the DW-300's filter be cleaned?"
```

Every step is `decided_by: "code"`: the code decides to check, decides whether to loop again
based on a fixed test of the checker's own output (does it contain one exact pass token), and
decides when the cap has been reached. The model never chooses to keep going or to stop.
