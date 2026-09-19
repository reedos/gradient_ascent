# Function calling

Level 4: the model may call one tool, at most once: `search(query)` for a keyword search, or
`lookup_part(part_number)` for a specific HLV part number. Code runs whichever tool was called
and asks the model for a final answer; if the model does not call a tool, its first response is
the answer.

This is the first level where the model makes a real decision: whether to call a tool, which
one, and with what argument. Everything else is fixed, including the follow-up call that asks
for a final answer once a tool result is in hand. The step where the model decides is the only
`decided_by: "model"` step in this level's trace.

Run it:

```
python -m examples.function_calling --model stub:scripted
```

The model picks `lookup_part` over `search` and fills in the part number, the tool returns the
price, and the final answer cites the parts list.

Compare the trace to `examples/prompt_chaining`: same corpus, same kind of question, but here
the model picks the tool and query instead of the code picking a fixed retrieval step.
