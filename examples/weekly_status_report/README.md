# Weekly status report

A standing Friday report assembled from three systems: a project tracker export, a shared client
inbox, and a hand-typed time spreadsheet.

The assembly half calls no model. It pulls the three sources, reconciles their project names
against one list a person wrote down once, and computes every count, date and total the report
can quote. That is level 0 and it is most of the job.

The writing half is one model call. It is handed the figures, formatted exactly as it is allowed
to quote them, plus the free-text note whoever ran the report added, and it writes the sentences
between the numbers. It has nothing to look up and nothing to decide.

Two checks then run in code, pointing in opposite directions:

- `unsupported_figures` reports every numeric token in the draft that is not, character for
  character, one of the figures code computed. It catches an invented number.
- `missing_required` reports every must-say figure the draft never quoted. It catches a bad week
  quietly left out.

A figure shorter than three characters is never marked must-say, however important it is: a check
that a draft mentions "2" somewhere is not a check. Those come back in `Report.confirm_by_eye`
for the person who reads the report before it goes out.

Run it:

```
python -m examples.weekly_status_report --model stub --question ""
```

`--question` is the free-text note for the week. Leave it empty for the sample note. The three
sources in `run.py` are fixture records; nothing here reaches the network.

What it does not do: decide whether a project is in trouble, write to any of the three systems,
or send anything. It produces a draft with its failures named, and a person reads it.
