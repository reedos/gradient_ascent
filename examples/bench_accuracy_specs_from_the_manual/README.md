# Accuracy specs from the manual

Level 3: reads section 2 of the MDN-6100's programming manual and fills 15 `AccuracySpec` rows,
one per DC volts range per calibration interval. Code checks the shape, that all 15 combinations
are present once each, and that a fixed range's accuracy only gets looser from the 24 hour row
through the 1 year row. None of that catches a row that borrows another range's numbers, because a
range's own numbers usually get looser with the range too, the same direction the check already
expects. `run` never returns a usable table for that reason: it returns a proposal, and
`confirm_table` is where a person's row-by-row check against the manual is actually recorded.

Run it:

```
python -m examples.bench_accuracy_specs_from_the_manual --model stub --question "mdn6100-programming-manual#2"
```

Once a table is confirmed, `price_reading` is arithmetic: it calls no model, and it is
`dc_voltage_budget` from `examples/common/bench.py`, reading this extraction's own table instead
of the one already coded there. The interval and the range it looks up are facts about how the
reading was taken, not choices the function makes; get either one wrong on a perfectly good table
and it returns a real number from a real row, priced for a measurement that was not actually taken
that way. `tests/test_example_bench_accuracy_specs_from_the_manual.py` reproduces the manual's own
two worked mistakes this way: 79.9 uV from the 24 hour row for a meter calibrated eleven months
ago, and 824.7 uV from the 100 V row for a 10 V reading, both against a true 224.8 uV.
