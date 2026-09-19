# Characterize a design

Level 0: no model. Reads `evals/bench/data/characterization-2026-09.csv`, five revision C
prototype boards swept over input voltage, load current and ambient temperature, five readings a
point. Finds the corner where each board holds the least margin to the datasheet's output-voltage
window, prices one of those readings with an uncertainty budget built from the meter's own
accuracy specification, guardbands every board's line regulation at every ambient the sweep
visited, and groups the output voltage's spread by the meter range each point was read on.

Run it:

```
python -m examples.bench_characterize_a_design --serial SRB5030-2609-0003
python -m examples.bench_characterize_a_design --serial SRB5030-2609-0005
```

900 readings across five boards, the worst corner for each of them, the uncertainty budget behind
the thinnest margin, and the line regulation of the serial you named at all three ambients.

A margin is a subtraction (`window_margin`); an uncertainty budget is `dc_voltage_budget`,
`combined_uncertainty` and `expanded_uncertainty` from `examples/common/bench.py`, called and not
reimplemented; a guardbanded verdict is `guarded_verdict`, called for every board at every
ambient rather than only the one case the notebook happens to flag; and the repeatability problem
in the data is one `GROUP BY` on the `meter_range_v` column every row already carries. Every trace
step is `decided_by: "code"`.

What it does not do: report a pass or a fail (there is no verdict column to compare against, only
a datasheet limit and a margin), read a datasheet or a notebook for a person, or draft an
instrument command. Those are `limits-without-a-model` (the production counterpart on the other
data set), `measurement-writeup` and `instrument-script-from-the-manual`.
