"""The two pieces of plumbing every agent loop on this site repeats.

`examples/agentic_rag`, `examples/single_agent`, `examples/coding_agents`, `examples/skills` and
`examples/voice_agents` are five different techniques with the same level-5 shape: offer the
model some tools, let its own output choose the next action, and stop when either the model stops
or a cap in the code says so. Recording a completion as a trace step, and making the one extra
call that forces a final answer when a cap bites, were written out five times. They are here for
the same reason `examples/common/tools.py` exists: so each example file is the technique and not
the boilerplate around it, and so one reader comparing two of them sees only what differs.

Neither function decides anything. `record_completion` writes down what happened, and the caller
passes `decided_by` because only the caller knows whether the model's output selected what
happens next (see `examples/common/trace.py`). `force_final` is always the code's decision, by
definition -- the cap is the code's -- so it records `decided_by="code"` and takes no say in it.
"""
from __future__ import annotations

from examples.common.model import Completion, Message, Model, ToolCall, content_text, with_ids
from examples.common.trace import Tracer

FINAL_TURN = "Give your final answer now. Do not call a tool."


def assistant_turn(completion: Completion, step: int) -> tuple[Message, list[ToolCall]]:
    """The model's tool-calling reply as a real assistant turn, plus its calls with ids.

    The calls go back into the conversation as tool calls, not as text describing them. Text such
    as "[called search(...)]" is something a model can copy: the first live run of agentic RAG
    wrote its next call as that text, and the loop took it for the final answer.
    """
    calls = with_ids(list(completion.tool_calls), prefix=f"step{step}")
    return Message(role="assistant", content=completion.text, tool_calls=tuple(calls)), calls


def as_text_history(messages: list[Message]) -> list[Message]:
    """The same conversation with tool turns written out as plain text, for a call that offers no
    tools. The Messages API refuses tool-call turns in a request that defines no tools, and once
    the loop is over there is no next call for a model to imitate the text in."""
    out: list[Message] = []
    for m in messages:
        if m.tool_calls:
            calls = "; ".join(f"{c.name} with {c.arguments}" for c in m.tool_calls)
            text = content_text(m.content)
            out.append(Message(role="assistant", content=(text + "\n" if text else "") + f"(Tools I called: {calls}.)"))
        elif m.role == "tool":
            out.append(Message(role="user", content=f"{m.tool_name} returned: {content_text(m.content)}"))
        else:
            out.append(m)
    return out


def tool_result(call: ToolCall, text: str) -> Message:
    """One tool's output as a tool-result turn, paired with the call that asked for it."""
    return Message(role="tool", content=text, tool_call_id=call.id, tool_name=call.name)
FORCE_TITLE = "Force a final answer"


def record_completion(
    tracer: Tracer,
    *,
    decided_by: str,
    title: str,
    completion: Completion,
    detail: str = "",
) -> None:
    """Record one model call as a trace step, defaulting the detail to the reply's own opening.

    `kind` is always "model" here: a model ran. `decided_by` is the caller's to state and is not
    defaulted, because conflating the two is the single easiest mistake to make against this
    site's central rule, and a default would make it silently.
    """
    tracer.record(
        kind="model",
        decided_by=decided_by,
        title=title,
        detail=detail or completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )


def force_final(
    messages: list[Message],
    model: Model,
    tracer: Tracer,
    *,
    reason: str,
    max_tokens: int = 400,
) -> Completion:
    """Make one last call for a final answer, because a cap in the code stopped the loop.

    Always `decided_by="code"`: the model did not choose to stop, the step cap or the token
    budget did, and a trace that scored this as a model decision would credit the model with a
    stop it never made. `reason` becomes the step's detail, so the trace says which cap bit.
    """
    completion = model.complete(as_text_history(messages) + [Message(role="user", content=FINAL_TURN)], max_tokens=max_tokens)
    record_completion(tracer, decided_by="code", title=FORCE_TITLE, completion=completion, detail=reason)
    return completion
