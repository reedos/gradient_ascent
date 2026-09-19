# Household paperwork

Level 0: no model anywhere. Eleven invented household records and an eleven-file documents folder
go in; what auto-renews in the next 30 days, what is unpaid, what the year costs by category, the
largest commitments and what is not findable in the folder come out.

Run it:

```
python -m examples.household_paperwork --question "2026-09-19"
```

The question is the date the report is run for. Leave it empty and the module's own `AS_OF` is
used; pass text with no date in it and the run is refused rather than quietly answered for today.
`--model` is accepted because every example here takes it, and it is ignored: `run` calls
`del model` on its first line.

What it does not do: read a bill. Nothing here turns a scanned or photographed document into a
record, which is the one part of household paperwork that does need a model. This example starts
from records that already exist, and every number it prints is a sort, a date subtraction or a
sum over them.

Money is integer cents throughout, and the amounts, providers and file names are invented.
