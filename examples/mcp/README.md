# Model Context Protocol

Level 4: the model picks a tool and its arguments, the same shape as `examples/function_calling`.
What differs here is where the tool comes from: instead of a Python function this code defined
inline, it is listed and called through a small stand-in of an MCP client and server, exchanging
JSON-RPC-shaped messages (`tools/list`, `tools/call`) over an in-memory pipe.

This is a teaching stand-in, not an implementation of the Model Context Protocol specification.
It borrows the shape of a few things the spec defines and skips almost everything else: no
capability negotiation, no authorization, no real transport. The technique page checks every
protocol statement this example leans on against the specification itself.

It mirrors revision 2026-07-28, which removed the `initialize` handshake and protocol-level
sessions. Nothing is opened or negotiated before the first request here because the current
protocol has nothing to open: each request stands alone.

Run it:

```
python -m examples.mcp --model stub --question "What does part HLV-2205 cost?"
```

Compare the trace to `examples/function_calling`: the model's one decision looks identical: which
tool, with what arguments. What moved is who defines the tool and who runs it -- a server behind
a protocol boundary, not a function this file wrote.
