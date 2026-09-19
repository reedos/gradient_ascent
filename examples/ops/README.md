# Ops: cost and latency estimator

Reads trace files in the shape `examples/common/trace.py` writes, plus a price table you supply,
and reports estimated cost and latency per question and per level. No price is built into
`examples.ops.run`: the caller passes the table, dated and attributed to wherever its numbers
came from.

Run it:

```
python -m examples.ops --demo
python -m examples.ops --traces "path/to/*.json" --prices path/to/prices.json
```

`--demo` needs no files: it writes two synthetic trace files with a real `Tracer`, and prices
them against a small table that is explicitly made up, not a maker's published price.

Every step is `decided_by: "code"`: the estimator only reads numbers already recorded in a trace
and multiplies them by a table it was handed; nothing here calls a model or makes a choice a
model could have made instead.
