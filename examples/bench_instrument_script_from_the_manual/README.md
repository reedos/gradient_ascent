# Draft an instrument script from its manual

Level 3: a model drafts a SCPI script for the Tarnley TRN-2400 electronic load from an excerpt of
its own programming manual. Code checks every command by running it on a scratch, unwired TRN-2400
and reading `SYST:ERR?`; an undocumented command, a long-form keyword Tarnley does not accept, or
an `ON`/`OFF` word instead of `1`/`0` all come back as the manual's own documented errors. Those
errors, and nothing else, go back to the model for another draft, capped at `MAX_REVISIONS`.

Only a script that runs clean is ever executed for real, and then through
`examples/common/bench.py`'s `GuardedLoad` rather than the load itself. The set point (`CURR`)
goes through `SafetyEnvelope`, and enabling the load (`INP 1`) needs a person's `Approval` naming
the rail the board is at and the current the load is about to pull, the same gate
`GuardedSupply.output_on` puts in front of `OUTP ON`.

Run it:

```
python -m examples.bench_instrument_script_from_the_manual --model stub --question "Set the TRN-2400 to 1.000 A, enable it, read it back, disable it."
```

Every step is `decided_by: "code"`. The model is called twice at most, but code decides whether a
draft passed, what feedback to send back, when to stop, and whether an energize command may run
at all; the model never chooses any of that.
