# Safety: prompt injection and a permission check

One scenario, two defenses. A note fetched from an untrusted source is delimited as data before
it reaches the model, and a code-side permission check refuses any tool call the note alone
asked for, one that the customer's own message does not independently corroborate.

The check is what actually stops the action. Delimiting and the system prompt's own warning
lower the odds a model follows an embedded instruction; the permission check is what runs
regardless of whether they worked.

Run it:

```
python -m examples.safety --model stub:scripted --scenario injected
python -m examples.safety --model stub:scripted --scenario legitimate
```

In `injected`, the model does follow the instruction planted in the retrieved note and calls
`issue_refund` for $500.00; the permission check refuses it, because the customer's own message
never asked for a refund. In `legitimate`, the customer did ask, and the same call runs.

`decided_by: "model"` only for the model's own choice to call a tool and what it asks for;
delimiting the note, checking whether that call is authorized, and refusing or running it are
all `decided_by: "code"`, since the model is never asked whether the action should happen.
