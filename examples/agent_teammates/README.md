# Always-on assistants

Level 7: one scheduled tick. The model reads a digest of what changed since the last check and
proposes zero or more actions by calling a tool per action (`decided_by: "model"`, since whether
anything needs doing at all is its call). A fixed, code-side `POLICY` table then sorts every
proposed action into one of three classes no matter what the model asked for: `auto` runs it
immediately, `approval` queues it for a person, and `forbidden` (the default for anything not in
the table) refuses it outright. Only `approve()`, called when a person actually looks at the
queue, can run an `approval`-class action: it re-checks the policy rather than trusting the
queued item, requires a named approver, and is not among the tools the model is offered, so the
model cannot approve its own proposal.

Run it:

```
python -m examples.agent_teammates --model stub:scripted
```

One tick, three proposed actions, one of each class: archiving the newsletter runs unattended,
confirming the meeting is queued for approval, and paying the invoice is refused outright.

`tests/test_example_agent_teammates.py` scripts the same tick and checks the `forbidden` action
never reaches `Mailbox` under any circumstance, including an attempt to approve one planted
directly in the queue.
