# Measurement writeup

Level 1: one model call. `compute_results` reads
`evals/bench/data/characterization-2026-09.csv` and computes every figure a report on this
session might quote: the margin to the datasheet's output voltage minimum at the corner where
line, load and temperature all push it down together, for all five boards; the expanded
uncertainty behind the worst one's corner reading; and the three-ambient line regulation figures
and guardbanded verdict for the board whose margin is smaller than the measurement is worth. The
model is handed those figures, formatted exactly as it may quote them, and the session notebook,
and asked to write the prose around them. It is never asked for a number.

`unsupported_numbers` is the check: every numeric token in the draft has to appear, character for
character, among the figures code computed. Dates are matched first and checked whole against the
sweep's own days, and identifier-shaped tokens are blanked so a serial number is not read as
three quoted measurements. Nothing is retried; a draft the check rejects is handed back with the
exact tokens that failed, not silently patched.

Run it:

```
python -m examples.bench_measurement_writeup --model stub --question ""
```

Every step is `decided_by: "code"`: the one model call always happens, and the check that follows
it is arithmetic and a set lookup, not a judgment. This example touches no instrument; it reads a
CSV and a notebook that a characterization session already produced.
