# Structured output

Level 1: extract one warranty record from `evals/corpus/warranty-policy.md` into a fixed JSON
schema (model, full warranty years, limited years, limited scope, commercial/rental days), and
validate the reply against that schema before accepting it. If it fails validation, the code
sends the validation error back and asks once more; if the second reply still fails, the run
reports that rather than returning something unvalidated.

The schema is fixed and the retry count is fixed (one), so every step is `decided_by: "code"`:
the model chooses the field values, never what happens next.

Run it:

```
python -m examples.structured_output --model stub:scripted
```

A first record rejected because the warranty term came back as the word "two" where the schema
asks for an integer, the validation error going back to the model, and a second reply that
validates.
