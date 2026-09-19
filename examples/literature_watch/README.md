# Literature watch

Two job shapes joined. The watch half queries a fixed list of sources, drops every record dated
before the last run, and drops every record whose title matches one a previous run already
reported. That is a date comparison and a set difference: no model, level 0. The read half is one
model call per surviving record, with the record's title and abstract in front of it and nothing
to look up: level 1. Nothing chooses what to read next or follows a reference, which is what would
make it level 5 research.

The citation is written by code. `_cite` builds it from the source record, the schema the model
answers in has no field for a link, an author or a year, and a summary that contains something
shaped like a link anyway is flagged for a person rather than published quietly.

The watch half reports three things a digest of items alone would hide: a source that returned
nothing at all (silence is not a quiet week), how many records were dropped as already reported,
and how many were dropped as too old.

Run it:

```
python -m examples.literature_watch --model stub --question ""
```

`--question` is the date the watch last ran, as YYYY-MM-DD. Leave it empty for the sample date
(09/15/2026). The sources in `run.py` are fixture records; nothing here reaches the network.

What it does not do: judge whether a summary is right. The model reads one abstract and writes
three sentences about it, and no check here compares those sentences against the full text. A
person reads the digest, and opens anything they intend to act on.
