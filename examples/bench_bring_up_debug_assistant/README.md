# Bring-up debug assistant

Level 5: three read-only tools over the SRB-5030 bench. `test_log(serial)` reads a board's logged
production result. `read_doc(cite)` reads one section of the bench documents (the datasheet, the
test spec, the calibration procedure, the bring-up notebook, an ECN, the failure-analysis guide).
`measure(instrument, command)` sends one SCPI command to the supply, the DMM, the load, or the
scope and returns its response, capped at 8 steps and 5000 tokens (`MAX_STEPS`, `MAX_TOKENS`).

`measure` cannot send a command that sets state. `examples.common.bench.is_read_only` is checked
before `instrument.send` is ever called, so a command outside the read-only set is refused in
code and never reaches the instrument, whatever the model asked for. The board is already
energized when the run starts: `_bring_up` is a technician's own checked sequence through
`GuardedSupply`, `GuardedLoad`, `SafetyEnvelope`, and `Approval`, the one place in this file that
sets anything. The agent's loop cannot reach it.

Run it:

```
python -m examples.bench_bring_up_debug_assistant --model stub --question "SRB5030-2608-0011 failed VOUT on FIX-03. Why, and what should we check next?"
```

`decided_by: "model"` for every tool call and the stop, since the model's own output chooses
which tool and what argument. Running the tool, refusing it, and handing the result back are all
`decided_by: "code"`.

What this does not do: it never proposes a fix, never sets a value, and never energizes anything
itself. Its final answer names a cause and a next measurement for a person to take, the same way
the person who read the board onto the bench in the first place has to be the one who takes it
off.
