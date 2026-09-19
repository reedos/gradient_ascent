# Observability: trace to OpenTelemetry-shaped spans

Turns this site's own `trace.json` shape into a list of span-shaped dictionaries named after
OpenTelemetry's generative AI semantic conventions (`gen_ai.operation.name`,
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`). Those conventions are Status:
Development as of the page that cites them; this module borrows the attribute names, not a
finished specification. Only a `kind: "model"` step gets them; a `kind: "code"` step gets none,
since it is not a generative AI operation.

A step's `detail` -- a prompt, answer, retrieved passage or tool-argument fragment -- is left out
unless the caller passes `capture_content=True`, and then it is written to
`gradient_ascent.detail`, never to `gen_ai.input.messages`: that attribute is defined as the
structured chat history sent to the model, and free text is not that.

Two limits the module states rather than fixes: a step's `title` becomes the span name with no
redaction, so a title must never be built out of content; and redacting at export does nothing
about a `trace.json` already written to disk with content in it.

Run it:

```
python -m examples.observability --demo
```

`--demo` builds one small trace with a real `Tracer` and prints it twice, redacted and with
content capture on, so the difference is visible in the output rather than only in the code.
Every step here is `decided_by: "code"`: this module reads a trace already recorded and renames
its fields; nothing in it calls a model.
