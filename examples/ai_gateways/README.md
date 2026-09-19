# AI gateways: a tiny in-process gateway

One entry point in front of several model providers, minimal: per-key routing to a primary and a
fallback provider, a per-key token budget, and one log line per call. Both providers are
`Model`s (`examples.common.model`), here two `StubModel`s; a real gateway would route to an
Ollama tag and a Claude model id behind the same interface, and add key checking, rate limits and
policy on top.

Run it:

```
python -m examples.ai_gateways --demo
```

Two keys: `team-a`'s primary answers directly, and its budget is set small on purpose so a second
call is refused outright rather than made and billed. `team-b`'s primary always fails, so every
call for that key falls back to its secondary provider. The printed log shows every call's model
id, token counts and whether it fell back, with the prompt itself left out, since the gateway's
`redact` flag defaults to on.

Every step here is `decided_by: "code"`: routing, fallback and budget enforcement are all fixed
rules the gateway applies to whatever a provider returns; nothing in it is a choice a model made.
