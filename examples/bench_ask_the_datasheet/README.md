# Ask the datasheet

Level 2: chunk the bench corpus by numbered section, embed the question and every chunk, take
the top 8 by cosine similarity, and ask the model to answer as JSON: a value, the board revision
the value holds for, and the citations it came from. Code checks the reply before returning it:
every citation has to be one of the sections actually retrieved, `applies_to_revision` has to be
filled in, not blank, and a reply that cites the datasheet section a change notice supersedes has
to cite the notice too, whenever the notice was itself retrieved.

The bench's datasheet states a maximum input voltage of 36.0 V; an engineering change notice,
ECN-2608-04, supersedes that to 32.0 V for board revisions A and B. The two documents share
enough words that one search returns both without a second, dependent search; what the schema is
for is making sure the reply says which revision its number is actually for, rather than reading
as correct while being wrong for the board on the bench.

Run it:

```
python -m examples.bench_ask_the_datasheet --model stub --question "What is the maximum input voltage of the SRB-5030, revision B, per its recommended operating conditions?"
```

Every step is `decided_by: "code"`: retrieval, prompting, validating and the one retry are fixed,
and the one model call answers but does not choose what happens next. This example only reads
the corpus; it never touches `examples/common/bench.py`'s simulated instruments.
