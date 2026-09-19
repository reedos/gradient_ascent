# Always-on assistants

Level 7: one scheduled tick. The model reads a digest of what changed since the last check and
proposes zero or more actions by calling a tool per action (`decided_by: "model"` — whether
anything needs doing at all is its call). A fixed, code-side `POLICY` table then sorts every
proposed action into one of three classes no matter what the model asked for: `auto` runs it
immediately, `approval` queues it for a person, and `forbidden` (the default for anything not in
the table) refuses it outright. Only `approve()`, called when a person actually looks at the
queue, can run an `approval`-class action: it re-checks the policy rather than trusting the
queued item, requires a named approver, and is not among the tools the model is offered, so the
model cannot approve its own proposal.

Run it:

```
python -m examples.agent_teammates --model stub --question "3 new emails: a newsletter, a meeting request from a client, and an invoice asking to be paid."
```

`tests/test_example_agent_teammates.py` scripts a model that proposes one action from each of the
three classes in a single tick, and checks the `forbidden` one never reaches `Mailbox` under any
circumstance, including an attempt to approve one planted directly in the queue.
