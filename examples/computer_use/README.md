# Computer use

Level 4: the model looks at one screen, given as plain text, a list of elements by id, kind and
label standing in for a screenshot, and picks at most one action, `click(id)` or `type(id, text)`.
Your code runs it, or refuses it, and stops there.

That stop is deliberate. Real computer-use tools take a new screenshot after every action and
keep going until the model decides the task is done. That is a loop, which is level 5
(`examples/single_agent`), not this level. This example never takes a second screenshot, so it
never becomes that loop.

The allowlist is the other half of the point: `ALLOWED_ELEMENT_IDS` names the only elements this
run may act on. The screen also has a cookie-accept button and a delete-account link, both
well-formed to click and both refused, because the code checks the id before doing anything, not
the model's judgment about whether the click was a good idea.

Run it:

```
python -m examples.computer_use --model stub:scripted
```

The screen rendered as four text elements, the model choosing to type into the search box, and
the code doing it. Then it stops, without a second screenshot.

Compare the trace to `examples/function_calling`: the same one-decision shape, but the code's
allowlist, not the tool definitions alone, is what keeps a plausible-looking action from running.
