# Incident runbook

Level 3: prompt chaining into a checkpoint. One incident's write-up goes in; a draft runbook
comes out, held for the incident owner's approval. Step 1 asks the model to pull the timeline out
of the write-up. Step 2 asks the model to turn the events that would be done again next time into
numbered steps, each naming who does it and the check that shows it worked. Step 3 is code, not
the model: a step citing an event that is not in the timeline is dropped and reported, and a step
missing a role or a check is kept but flagged incomplete. Every step is `decided_by="code"`.

Run it:

```
python -m examples.incident_runbook --model stub --question ""
```

An empty `--question` uses the module's own sample incident, `SAMPLE_INPUT`. The run always
pauses; pass `--decision approve|edit|reject` (and `--note` for `edit`) to resume it in the same
command instead of only seeing the paused draft.

What it does not do: decide that the draft is usable. Code can check that a step traces to a real
event and names a role and a check; it cannot tell a genuinely repeatable action from a one-off
the model generalized by mistake, such as waking a particular person or emailing particular
customers. That is what `resume` and the person calling it are for. This example never ships a
runbook on its own; `run` always returns a paused draft.
