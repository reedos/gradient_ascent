# Limits without a model

Level 0: no model. Reads `evals/bench/data/production-run-2026-08.csv`, the SRB-5030 production
log, checks one measurement's rows against its own limits, and reports first-pass yield, Cpk, a
Shewhart individuals control chart, and all of it again grouped by lot, by fixture, by day and by
shift.

Run it:

```
python -m examples.bench_limits_without_a_model --measurement RIPPLE
python -m examples.bench_limits_without_a_model --measurement VOUT
```

The first prints 198 RIPPLE readings against a 50 mV limit, broken out by lot, fixture, day and
shift, with Cpk and yield for every group. One lot carries almost all of the loss.

Every trace step is `decided_by: "code"`. The limit check in `within_limits` is two comparisons;
Cpk in `cpk` is a mean, a standard deviation and a subtraction; the control chart in
`control_chart` is a mean, a standard deviation and a plot. Nothing here reads a model's opinion
of any of it, and the pass or fail decision never will.

What it does not do: read a datasheet, triage an operator's free-text note, or draft an
instrument command. Those are `ask-the-datasheet`, `test-failure-triage` and
`instrument-script-from-the-manual`, the recipes this one's own page points to for the parts of a
test engineer's week that a `GROUP BY` cannot do.
