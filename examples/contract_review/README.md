# Check an agreement against your own checklist

Level 3: a six-rule checklist (payment terms, liability cap, notice period, assignment, governing
law, data deletion) is checked against one invented fifteen-clause agreement, one model call per
rule, all sent at once (`concurrent.futures.ThreadPoolExecutor`). Each call sees only its own rule
and the whole agreement, never the other rules. Code checks every finding before it ships: a quote
that is not a substring of the clause it cites, or a clause number the agreement does not have,
downgrades the finding to `unclear` with the reason recorded; a status outside the closed set is
rejected the same way.

`run` returns a `ReviewCheckpoint`, never a verdict: every `breach`, `missing` and `unclear`
finding needs a person; `meets` findings are listed but need no action. `resume` records a
reviewer's decision.

Run it:

```
python -m examples.contract_review --model stub:scripted
```

Six rules, six findings, each with the clause it turns on: two breaches, two met, one missing and
one unclear, with four of them needing a person.

`--model stub` returns free text instead of the JSON each call asks for, so every finding comes
back `unclear` with "not valid JSON" as the reason. That is what a model ignoring your schema
costs you here: not a wrong answer, six findings nobody can act on.

Nothing here decides whether to sign the agreement, and no output here is legal advice.
