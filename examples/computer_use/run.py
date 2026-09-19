"""Level 4: computer use. The model looks at one screen and picks at most one action; your code
runs it, or refuses it, and stops there.

Real computer-use products do not stop after one action -- they take a new screenshot, hand it
back to the model, and keep going until the model itself decides the task is done. That loop is
level 5, `examples/single_agent`'s territory, not this one. This example deliberately never takes
a second screenshot, so what it demonstrates stays level 4: one `decided_by: "model"` step, one
action, always bounded by an allowlist your code owns and the model cannot expand.

The "screen" is plain text -- a list of elements with ids, kinds and labels -- standing in for a
real screenshot, which this stdlib-only example never renders as an image. A real tool sends
pixels; the shape of the decision (pick one element, act on it) is the same either way.
"""
from __future__ import annotations

from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 4

# The only elements this run is permitted to act on, regardless of what the model asks for.
# "cookie-accept" and "delete-account" exist on the screen and can be clicked in the sense that a
# tool call naming them is well-formed -- but they are not on this list, so the code refuses them
# before anything happens. This is the allowlist the real makers describe: a fixed set of safe
# actions, not a judgment call made per request.
ALLOWED_ELEMENT_IDS = frozenset({"search-box", "search-button"})

SCREEN = [
    {"id": "search-box", "kind": "field", "label": "Search", "value": ""},
    {"id": "search-button", "kind": "button", "label": "Search"},
    {"id": "cookie-accept", "kind": "button", "label": "Accept all cookies"},
    {"id": "delete-account", "kind": "link", "label": "Delete my account"},
]

CLICK_TOOL = {
    "name": "click",
    "description": "Click an element on the screen by its id.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
}
TYPE_TOOL = {
    "name": "type",
    "description": "Type text into a field element on the screen by its id.",
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
        "required": ["id", "text"],
    },
}
TOOLS = [CLICK_TOOL, TYPE_TOOL]
SYSTEM_PROMPT = (
    "You operate a screen through two actions: click(id) and type(id, text). The screen is "
    "listed below as one element per line: id, kind, and label. Choose exactly one action that "
    "makes progress on the task, or answer directly if the task needs no action."
)


def render_screen(screen: list[dict]) -> str:
    lines = []
    for e in screen:
        value = f' value="{e["value"]}"' if "value" in e else ""
        lines.append(f'[{e["id"]}] {e["kind"]} "{e["label"]}"{value}')
    return "\n".join(lines)


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    screen: list[dict] = SCREEN,
    allowed_ids: frozenset[str] = ALLOWED_ELEMENT_IDS,
) -> Answer:
    del embedder  # this level acts on a screen, not a document index
    screen_text = render_screen(screen)
    tracer.record(kind="code", decided_by="code", title="Render the screen as text", detail=f"{len(screen)} elements")

    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=f"Screen:\n{screen_text}\n\nTask: {question}"),
    ]
    completion = model.complete(messages, tools=TOOLS, max_tokens=200)

    if not completion.tool_calls:
        tracer.record(
            kind="model",
            decided_by="model",
            title="Model takes no action",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        return Answer(text=completion.text or "No action taken.", citations=[])

    call = completion.tool_calls[0]
    element_id = str(call.arguments.get("id", ""))
    tracer.record(
        kind="model",
        decided_by="model",
        title=f"Model chooses {call.name}({element_id})",
        detail=str(call.arguments),
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )

    if call.name not in {"click", "type"} or element_id not in allowed_ids:
        tracer.record(
            kind="code",
            decided_by="code",
            title="Action refused: not on the allowlist",
            detail=f"{call.name}({element_id!r})",
        )
        return Answer(text=f"Refused: {call.name}({element_id!r}) is not on the allowlist for this run.", citations=[])

    if call.name == "click":
        tracer.record(kind="code", decided_by="code", title=f"Code clicks {element_id}", detail="done")
        return Answer(text=f"Clicked {element_id}.", citations=[])

    text = str(call.arguments.get("text", ""))
    tracer.record(kind="code", decided_by="code", title=f"Code types into {element_id}", detail=text[:100])
    return Answer(text=f"Typed {text!r} into {element_id}.", citations=[])
