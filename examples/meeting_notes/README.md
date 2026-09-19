# Meeting notes

Level 1: one call turns a meeting transcript into decisions, owners, due dates and open questions
in a fixed JSON shape. If the reply is not valid JSON against the schema, the code sends the
validation error back and asks once more; a reply still invalid after that is reported as such.

Every decision must carry a quote copied from the transcript. Code checks that quote against the
transcript (whitespace normalized first) and drops any decision whose quote is not actually there,
reporting it as dropped rather than removing it silently. An owner the transcript never names comes
back as `unassigned`, and a due date nobody stated stays an empty string; neither is guessed.

Run it:

```
python -m examples.meeting_notes --model stub --question ""
```

Leave `--question` empty to run against the module's own sample transcript
(`examples/meeting_notes/run.py`'s `SAMPLE_INPUT`); pass your own transcript text instead to
extract from it.

What it does not do: tell you whether a quoted decision was actually agreed on. The quote check
proves the words appear in the transcript, not that they describe a real decision rather than a
proposal that was discussed and dropped. A person who was in the meeting reads the notes before
they go anywhere.
