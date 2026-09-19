"""Level 7: always-on assistants. A scheduler tick wakes the agent — `decided_by: "code"`,
nobody asked for this run. The model looks at what changed since the last tick and proposes zero
or more actions; whether anything needs doing, and what, is the model's call —
`decided_by: "model"`. A code-side policy then sorts every proposed action into one of three
classes, no matter what the model asked for: run unattended, queue for a person's approval, or
refuse outright. Nothing classified `forbidden` ever reaches `_EXECUTORS`, the functions that
change anything real.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 7

Policy = Literal["auto", "approval", "forbidden"]

# Deny by default: an action type nobody classified is not allowed unattended, and is not queued
# for approval either -- it is simply refused, the same as one explicitly marked "forbidden".
DEFAULT_POLICY: Policy = "forbidden"

POLICY: dict[str, Policy] = {
    "archive_email": "auto",
    "label_email": "auto",
    "draft_reply": "auto",
    "send_email": "approval",
    "schedule_meeting": "approval",
    "make_payment": "forbidden",
    "share_credential": "forbidden",
}

ACTION_TOOLS = [
    {
        "name": name,
        "description": f"Propose to {name.replace('_', ' ')}.",
        "parameters": {"type": "object", "properties": {"detail": {"type": "string"}}, "required": ["detail"]},
    }
    for name in POLICY
]
SYSTEM = (
    "You are an always-on assistant. Given what changed since the last check, call the matching "
    "tool once for each action worth taking. Call none of them if nothing needs doing."
)


@dataclass
class Mailbox:
    """Stands in for the outside world an executed action actually changes."""

    archived: list[str] = field(default_factory=list)
    labeled: list[str] = field(default_factory=list)
    drafts: list[str] = field(default_factory=list)
    sent: list[str] = field(default_factory=list)
    meetings: list[str] = field(default_factory=list)
    payments: list[str] = field(default_factory=list)  # nothing unattended ever writes here


_EXECUTORS: dict[str, Callable[[Mailbox, str], None]] = {
    "archive_email": lambda box, detail: box.archived.append(detail),
    "label_email": lambda box, detail: box.labeled.append(detail),
    "draft_reply": lambda box, detail: box.drafts.append(detail),
    "send_email": lambda box, detail: box.sent.append(detail),
    "schedule_meeting": lambda box, detail: box.meetings.append(detail),
    "make_payment": lambda box, detail: box.payments.append(detail),
}


@dataclass
class TickResult:
    executed: list[dict]
    queued: list[dict]
    refused: list[dict]


def run_tick(events: str, model: Model, tracer: Tracer, box: Mailbox, *, approvals: list[dict]) -> TickResult:
    """One scheduled tick. `approvals` is the shared, persisted queue a person works from; this
    call only ever appends to it, never runs anything out of it."""
    tracer.record(kind="code", decided_by="code", title="Scheduler tick wakes the agent", detail="no person asked for this run")

    messages = [Message(role="system", content=SYSTEM), Message(role="user", content=f"Since the last check:\n{events}")]
    completion = model.complete(messages, tools=ACTION_TOOLS, max_tokens=300)
    proposed = list(completion.tool_calls)
    desc = ", ".join(f"{c.name}({c.arguments.get('detail', '')!r})" for c in proposed) or "nothing -- proposed no actions"
    tracer.record(
        kind="model", decided_by="model", title="Model decides whether anything needs doing, and proposes actions",
        detail=desc, tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )

    executed: list[dict] = []
    queued: list[dict] = []
    refused: list[dict] = []
    for call in proposed:
        detail = str(call.arguments.get("detail", ""))
        item = {"action": call.name, "detail": detail}
        policy = POLICY.get(call.name, DEFAULT_POLICY)
        if policy == "auto":
            _EXECUTORS[call.name](box, detail)
            tracer.record(kind="code", decided_by="code", title=f"Run unattended: {call.name}", detail=detail)
            executed.append(item)
        elif policy == "approval":
            approvals.append(item)
            tracer.record(kind="code", decided_by="code", title=f"Queue for a person's approval: {call.name}", detail=detail)
            queued.append(item)
        else:
            tracer.record(kind="code", decided_by="code", title=f"Refuse: {call.name} is forbidden, unattended or not", detail=detail)
            refused.append(item)
    return TickResult(executed=executed, queued=queued, refused=refused)


def approve(box: Mailbox, approvals: list[dict], index: int, decision: str, tracer: Tracer, *, approver: str) -> dict:
    """A person resolves one queued action. Not on a schedule -- this only runs when someone
    looks at the queue and decides, and it is the only path by which an `approval`-class action
    ever reaches `_EXECUTORS`.

    `approver` is who decided, and it is required: an approval with nobody's name on it is not
    an approval, so a blank one runs nothing. The policy is checked again here rather than
    trusted from the tick that queued the item, because the queue is persisted and the table can
    change between the two -- an action reclassified `forbidden` after it was queued must not
    still run, and an action nobody classified must not reach `_EXECUTORS` by way of the queue
    when `run_tick` would have refused it outright.

    Nothing the model can call reaches this function: the model is offered one tool per entry in
    POLICY, and `approve` is not one of them. It cannot approve its own proposal.
    """
    item = approvals.pop(index)
    policy = POLICY.get(item["action"], DEFAULT_POLICY)
    if policy != "approval":
        tracer.record(kind="code", decided_by="code", title=f"Refuse at approval time: {item['action']} is not approvable", detail=f"policy is {policy}, not approval")
        return {**item, "decision": "refused", "approver": approver}
    if not approver.strip() or decision != "approve":
        tracer.record(kind="code", decided_by="code", title="Person decides on a queued action", detail=f"{item['action']}: not run ({decision or 'no decision'}, approver {approver or 'unnamed'})")
        return {**item, "decision": "rejected", "approver": approver}

    tracer.record(kind="code", decided_by="code", title="Person approves a queued action", detail=f"{item['action']}: approved by {approver}")
    _EXECUTORS[item["action"]](box, item["detail"])
    return {**item, "decision": "approve", "approver": approver}


def run(events: str, model: Model, tracer: Tracer) -> TickResult:
    """Recordable entry point for `record_trace.py`: one scheduler tick against a fresh mailbox
    and an empty approval queue, the same defaults `python -m examples.agent_teammates`'s `main`
    builds by hand."""
    return run_tick(events, model, tracer, Mailbox(), approvals=[])
