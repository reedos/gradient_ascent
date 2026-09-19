"""Level 4: Model Context Protocol. The model picks a tool the same way it does in
`examples/function_calling`; what differs is where the tool comes from. Here it is listed and
called through a small stand-in of an MCP client and server exchanging JSON-RPC-shaped messages,
instead of a Python function your own code defined inline.

This is a TEACHING STAND-IN, not an implementation of the specification. It borrows the shape of
three things the spec defines -- `tools/list`, `tools/call`, and a JSON-RPC 2.0 envelope with a
`content` array of typed blocks in the result -- over a plain in-process function call standing in
for a transport. It skips almost everything else a real client and server do: no `server/discover`
capability negotiation, no `_meta` fields, no authorization, no real stdio or Streamable HTTP
transport. See the technique page for what each shape borrowed here is checked against in the
specification itself.

The revision mirrored is 2026-07-28, which removed the `initialize` handshake and protocol-level
sessions. So there is no connection to open and nothing to negotiate before the first request
here, and that is the current protocol rather than a shortcut this file took: every request
stands on its own, and a server needing state across calls hands back a handle as ordinary tool
data. See the technique page's stateless MCP section.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 4
SEARCH_K = 3
CITE_RE = re.compile(r"[a-z0-9][a-z0-9_-]*#\d+")
SYSTEM_PROMPT = (
    "You answer questions about Halvorsen appliances. You may call one tool, at most once, to "
    "search the documents. If you already know the answer, or no tool would help, answer "
    "directly without calling one."
)

# The one tool this stand-in server exposes, shaped like the specification's own Tool data type,
# whose fields include `name`, `description` and `inputSchema`. The technique page cites the
# specification page that defines it; this file borrows the shape and nothing else.
SEARCH_TOOL = {
    "name": "search_halvorsen_docs",
    "description": "Keyword search over the Halvorsen document set; returns matching sections.",
    "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}

Transport = Callable[[dict], dict]


class StandInServer:
    """Handles `tools/list` and `tools/call`, JSON-RPC-shaped. Not a real MCP server: no
    capability negotiation, no other methods, one hard-coded tool."""

    def __init__(self, sections: dict[str, Section]) -> None:
        self._sections = sections

    def handle(self, request: dict) -> dict:
        method = request.get("method")
        if method == "tools/list":
            return _rpc_result(request, {"tools": [SEARCH_TOOL]})
        if method == "tools/call":
            return self._call_tool(request)
        return _rpc_error(request, f"unknown method: {method}")

    def _call_tool(self, request: dict) -> dict:
        params = request.get("params", {})
        if params.get("name") != SEARCH_TOOL["name"]:
            return _rpc_error(request, f"unknown tool: {params.get('name')}")
        query = params.get("arguments", {}).get("query", "")
        hits = bm25_search(self._sections, query, k=SEARCH_K)
        text = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s, _ in hits) or "no results"
        return _rpc_result(request, {"content": [{"type": "text", "text": text}], "isError": False})


def _rpc_result(request: dict, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request.get("id"), "result": {"resultType": "complete", **result}}


def _rpc_error(request: dict, message: str) -> dict:
    # -32602 is the spec's own example code for "Unknown tool" in its protocol-errors example.
    return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32602, "message": message}}


def connect(server: StandInServer) -> Transport:
    """The in-memory pipe: calling `transport(request)` is this example's entire substitute for
    serializing a JSON-RPC message onto stdio or a Streamable HTTP request and reading the reply
    back off it. A real client does that serialization; here the message dict just changes hands
    inside one process."""
    return server.handle


def list_tools(transport: Transport) -> list[dict]:
    response = transport({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    return response["result"]["tools"]


def call_tool(transport: Transport, name: str, arguments: dict) -> tuple[str, bool]:
    """Returns (text, is_error). `is_error` covers both the spec's tool-execution errors
    (`isError: true` in a normal result) and this stand-in's one protocol error."""
    response = transport({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}})
    if "error" in response:
        return response["error"]["message"], True
    content = response["result"]["content"]
    text = "\n".join(block["text"] for block in content if block.get("type") == "text")
    return text, response["result"].get("isError", False)


def _to_model_tool(mcp_tool: dict) -> dict:
    """This repo's `Model.complete` takes a tool as `{name, description, parameters}`; the
    specification's own field is `inputSchema`. Translating between the two is exactly the
    plumbing a real MCP host performs for whichever model API it calls."""
    return {"name": mcp_tool["name"], "description": mcp_tool["description"], "parameters": mcp_tool["inputSchema"]}


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
) -> Answer:
    del embedder  # this level retrieves through the MCP server's tool, not a vector index
    sections = load_sections(corpus_dir)
    transport = connect(StandInServer(sections))

    mcp_tools = list_tools(transport)
    tracer.record(kind="code", decided_by="code", title="List tools from the MCP server", detail=mcp_tools[0]["name"])

    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=question)]
    first = model.complete(messages, tools=[_to_model_tool(t) for t in mcp_tools], max_tokens=300)

    if not first.tool_calls:
        tracer.record(
            kind="model",
            decided_by="model",
            title="Model answers directly, no tool call",
            detail=first.text[:200],
            tokens_in=first.tokens_in,
            tokens_out=first.tokens_out,
            ms=first.ms,
        )
        return Answer(text=first.text, citations=[])

    call = first.tool_calls[0]
    tracer.record(
        kind="model",
        decided_by="model",
        title=f"Model calls {call.name}",
        detail=str(call.arguments),
        tokens_in=first.tokens_in,
        tokens_out=first.tokens_out,
        ms=first.ms,
    )

    result_text, is_error = call_tool(transport, call.name, call.arguments)
    tracer.record(kind="code", decided_by="code", title="MCP server returns a tool result", detail=result_text[:200])
    citations = [] if is_error else sorted(set(CITE_RE.findall(result_text.lower())))

    follow_up = messages + [
        Message(role="assistant", content=f"[called {call.name}({call.arguments})]"),
        Message(role="user", content=f"Tool result:\n{result_text}\n\nNow answer the question: {question}"),
    ]
    final = model.complete(follow_up, max_tokens=400)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask for a final answer",
        detail=final.text[:200],
        tokens_in=final.tokens_in,
        tokens_out=final.tokens_out,
        ms=final.ms,
    )
    return Answer(text=final.text, citations=citations)
