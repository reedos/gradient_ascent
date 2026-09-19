# Coding agents

Level 5: propose an edit, run the test, read the result, decide whether to try again or stop.
`sum_evens`, a small buggy function, lives in memory as a string (`BUGGY_SOURCE`); it fails
`TEST_CASES` because it sums the odd numbers instead of the even ones. The model calls
`propose_edit` with a complete replacement, your code `exec`s it in an empty namespace and runs
the four test cases against it, and returns the pass/fail result as the tool result. Capped at 3
steps and 2000 tokens (`MAX_STEPS`, `MAX_TOKENS`).

Every `propose_edit` call, and the decision to stop, is `decided_by: "model"` -- reading a test
result and deciding to try again, or to stop, is the model's decision either way, the same rule
`examples/agentic_rag/` and `examples/single_agent/` follow. Running the proposed code and the
tests is always `decided_by: "code"`: the model never executes its own code here.

Run it:

```
python -m examples.coding_agents --model stub --question "Fix sum_evens so it returns the sum of the even numbers in a list."
```

If a cap is reached before the model stops on its own, the code forces one last no-tools call for
a final answer, `decided_by: "code"`, and the trace records which cap it was.
