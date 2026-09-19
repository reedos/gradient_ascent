# Test failure triage

Level 3: sorts one failing SRB-5030 unit's operator note into a cause
`evals/bench/corpus/failure-analysis-guide.md` already lists, then routes it. Scoped to VOUT (test
step 3), the one step the guide itself treats as ambiguous.

Two causes never reach the model: grouping today's VOUT failures by fixture or by lot (a count and
a share) finds a stale calibration offset or a bad reel before any note is read. What is left is a
genuine one-off, and the operator's note is the only signal for it -- read only when there is one
to read.

Run it:

```
python -m examples.bench_test_failure_triage --model stub --question SRB5030-2608-0063
```

That serial is a dead board on the fixture with the stale offset: the note ("dead. no vout at all,
u1 not switching") outranks the fixture's own group signature, so the route is failure analysis,
not a fixture check.

Every step is `decided_by: "code"`: the classification call, the validation, and the route are all
decisions code makes, even though the cause's *value* comes from the model. The route is a
proposal; `confirm` is where a person's decision is recorded, and nothing here ever touches the
row's own PASS/FAIL result.
