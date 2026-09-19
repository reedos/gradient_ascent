# Code execution

Level 4: the model writes one line, a Python arithmetic expression that answers a numeric
question about the documents. Your code always runs it, in an AST-whitelisted evaluator that
accepts numbers, `+ - * /` and parentheses and nothing else. It never calls Python's own `eval`
or `exec` on anything the model wrote.

The whitelist is the point: it is an allow-list of syntax nodes, not a blocklist of dangerous
words, so there is no phrasing that sneaks past it. A name, a function call, an attribute lookup
and an import all fail the same way, because `_eval_node` never matches any of them in the first
place -- the same shape of guarantee a real sandbox gives by disabling network access outright
rather than trying to recognize every possible exfiltration attempt.

Run it:

```
python -m examples.code_execution --model stub --question "What is the total price to replace the heating elements on both a DW-300 and a DW-480?"
```

Compare the trace to `examples/function_calling`: the same one-decision-then-answer shape, but
here the model's one choice is the content of an expression, not which of two named tools to
call.
