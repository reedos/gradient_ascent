# Running models locally: a memory estimator

Estimates how much memory a model needs to run: weights (parameters times bits per weight) plus
a KV cache, which grows with context length and how many requests are served at once. This is an
estimate, not a measurement: it counts only those two costs, and real usage (activation memory,
a runtime's own overhead) runs higher, never lower.

Run it:

```
python -m examples.local_inference --demo
```

`--demo` prints four made-up shapes of the same illustrative 8B-parameter model: full precision
against roughly 4-bit quantized, a short context against a long one, and one concurrent user
against eight, so the effect of each variable is visible on its own rather than all mixed
together in one number.

Every step here is `decided_by: "code"`: this is arithmetic over numbers the caller supplies,
not a model call, and nothing in it chooses anything a model could have chosen instead.
