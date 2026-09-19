# Test failure triage

Level 3: sorts one failing SRB-5030 unit's operator note into a cause
`evals/bench/corpus/failure-analysis-guide.md` already lists, then routes it. Scoped to VOUT (test
step 3), the one step the guide itself treats as ambiguous.

Two causes never reach the model: grouping the run's VOUT failures by fixture or by lot (a count and
a share) finds a stale calibration offset or a bad reel before any note is read. What is left is a
genuine one-off, and the operator's note is the only signal for it, read only when there is one
to read.

Run it:

```
python -m examples.bench_test_failure_triage --model stub:scripted
```

That serial is a dead board on the fixture with the stale offset. The run prints the group
signature the numbers alone give (fixture), the cause read from the note ("dead. no vout at all,
u1 not switching"), and the route that cause wins: failure analysis, not a fixture check.

`--question` takes a serial, not a question, and `run` refuses one that did not fail this
measurement rather than inventing a row for it. The same serial is `SAMPLE_INPUT` in `run.py`, so
`scripts/record_trace.py` can record this example without being handed one.

Every step is `decided_by: "code"`: the classification call, the validation, and the route are all
decisions code makes, even though the cause's *value* comes from the model. The route is a
proposal; `confirm` is where a person's decision is recorded, and nothing here ever touches the
row's own PASS/FAIL result.
