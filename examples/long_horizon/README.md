# Long-running tasks

Level 7: a queue of questions worked through across many separate sessions, separate calls to
`run_session`, each a fresh context window built from a short notes file on disk, not from the
previous session's transcript. A scheduler calling `run_session` on a timer is the trigger
(`decided_by: "code"`); the model's one decision each session is whether to answer or hand the
question to a person instead of guessing (`decided_by: "model"`). `QueueState.save` writes the
checkpoint by replacing a temp file named for this process, so a session killed mid-write never
corrupts the last good checkpoint and never shares a temp file with another writer. An
interrupted session writes nothing: every finished answer survives and is recorded once, while
the question it was working on is asked again, so the work is at-least-once and the record is
once. A checkpoint damaged by anything else raises rather than silently starting the queue over,
and a session whose checkpoint moved underneath it refuses to write rather than overwrite work it
never saw.

Run one session:

```
python -m examples.long_horizon --model stub:scripted
```

The scheduler starts a session nobody asked for, rebuilds context from notes rather than the last
session's transcript, and the model's one decision is to answer rather than hand the question to a
person. The answer is recorded and a note compacted for the next session.

Pass `--state <path>` with the same path twice to see a second session load the first one's
checkpoint instead of starting over. `tests/test_example_long_horizon.py` scripts a model that
answers, one that flags a question for a person, and a simulated crash partway through a queue,
and checks the checkpoint file after each.
