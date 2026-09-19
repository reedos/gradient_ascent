# Project tracker upkeep

Keeping a tracker document current from three sources: a project tracker export, a hand-typed
time spreadsheet, and a shared client inbox. This is not a report. A report is written once and
read once; a tracker has to still be true next week, so the work is reconciling what changed
against what is already written and leaving the rest alone.

Three rules:

- **Code decides what changed.** Field by field, against the source that owns the field.
- **A person approves anything that overwrites a field a person wrote.** `owner`, `note` and
  `risk` are written by people, and so, sometimes, is a date somebody typed in after a call. Code
  queues those with both values side by side rather than overwriting one.
- **Absence is reported, never read as agreement.** A source whose `as_of` has not moved since
  the last run is stale, and every field it owns is reported with its age. A project that falls
  out of a source that is otherwise current is reported as no longer listed, which is not the
  same as finished.

The model reads the inbox and nothing else: one call per unread message, a fixed schema, one
retry, and `_check_quotes` drops any proposal whose quote is not in the message it came from.
Every surviving proposal goes to the approval queue and none of them writes, because a fact read
out of somebody's sentence is a claim and a claim is not a record.

Run it:

```
python -m examples.project_tracker_upkeep --model stub --question ""
```

`--question` is the date the run stands on, as YYYY-MM-DD. Leave it empty for the sample date
(09/18/2026). The document and the three sources are fixtures inside `run.py`; nothing here
reaches the network.

What it does not do: create the new row it proposes (that needs an owner, and only a person can
supply one), decide which of two disagreeing dates is right, or judge whether a project is in
trouble. `approve` applies what a person accepted, and refuses to apply two changes to the same
cell.
