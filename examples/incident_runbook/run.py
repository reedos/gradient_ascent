"""Level 3: prompt chaining into a checkpoint. Two fixed steps pull a runbook out of one
incident's write-up, a third step checks what the model drafted, and nothing is a runbook until
the person who ran the incident approves it.

Step 1 asks the model to pull the timeline out of the write-up: time, actor, what happened, one
event per line of the narrative. Step 2 shows the model that timeline, numbered, and asks it to
turn the events that would be done again next time into runbook steps, an action with a role and
a check, each naming the event it came from. Both steps call the model, and both steps are
`decided_by="code"`: the code always runs step 2 after step 1, in that order, and always runs
step 3 after that, whatever either call returns. The model never chooses what happens next.

Step 3 is the whole argument of this recipe and it never touches the model. A step whose
`from_event` names an id that is not in the timeline is dropped and reported: a citation to
nothing is worse than no citation. A step with no role or no check is kept, because dropping it
would hide that the model tried and failed to say who does it or how to tell it worked, and
flagged incomplete instead, because a runbook step nobody can check is the failure this recipe
exists to prevent.

One thing step 3 cannot do: tell a genuinely repeatable action from a one-off the model wrongly
generalized. Waking a specific person and emailing specific customers are both actions with a
plausible role and a plausible check; nothing in their shape marks them as belonging to this one
incident and not the next. That is what the approval gate is for. The write-up below is one
incident, and a runbook drafted from a sample of one incident is a draft, not a procedure, until
the person who was there reads it and says so.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 3
MAX_RETRIES = 1

#: One incident, written the way a tired on-call engineer writes one at 3 a.m.: short lines, a
#: timestamp on each, some of it typed while still reading a dashboard. Thistledown Labs,
#: order-sync-worker, jrivera and dcho are all invented; no real company, person or product
#: appears below.
INCIDENT_WRITEUP = """\
Incident notes: order-sync backlog, Thistledown Labs, 2026-08-14

02:14 - on-call page fires for jrivera. order-sync-worker queue-depth alert, over
threshold.
02:19 - jrivera acks. checks the queue-depth dashboard for order-sync-queue: 42,100
and climbing, normal is under 500.
02:23 - jrivera checks the worker pool in the fleet console. 3 of 12
order-sync-worker pods are crash-looping.
02:26 - jrivera decides this is bad enough to wake the on-call lead, calls dcho.
02:31 - dcho joins. both read the logs: each crash was the process getting killed
for using too much memory, which had been climbing steadily for about two hours
first.
02:38 - dcho restarts the order-sync-worker pool (fleetctl rollout restart
order-sync-worker).
02:44 - queue depth still climbing, 44,500. the restart alone hasn't turned it yet.
02:47 - dcho also rolls the worker image back to the previous build, 8821, in case
the new build caused the leak. queue depth keeps climbing for a few more minutes;
the rollback by itself doesn't change the direction, it's the fresh pods from the
restart that start draining it.
02:55 - queue depth peaks at 45,100, starts dropping.
03:10 - queue depth back under 1,000.
03:16 - jrivera checks the order-sync-lag metric on the dashboard. back under 30
seconds, inside the normal range again.
03:20 - dcho drafts a short email to the three enterprise accounts with delayed
orders, explaining the delay and that it's resolved now.
03:25 - jrivera closes the page. root cause still open, probably the leak in build
8822; files THIST-4410 to track it.
"""
SAMPLE_INPUT = INCIDENT_WRITEUP

TIMELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "time": {"type": "string"},
                    "actor": {"type": "string"},
                    "action": {"type": "string"},
                },
                "required": ["time", "actor", "action"],
            },
        },
    },
    "required": ["events"],
}
STEP_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "role": {"type": "string"},
                    "check": {"type": "string"},
                    "from_event": {"type": "string"},
                },
                "required": ["action", "role", "check", "from_event"],
            },
        },
    },
    "required": ["steps"],
}
TIMELINE_SYSTEM = (
    "Read the incident write-up and pull out its timeline. For each event give the time as "
    "written, who or what did it, and what happened, close to the write-up's own words. Reply "
    "as JSON matching the schema and nothing else."
)
STEP_SYSTEM = (
    "You are given an incident's timeline, one numbered event per line. Some of what happened "
    "would be done again if the same kind of incident happened next time: checking a metric, "
    "restarting a service, noting something that was tried and did not help. Others are "
    "specific to this one incident and would not be repeated as written: waking a particular "
    "person, writing to particular customers. Draft one runbook step for each event that would "
    "be done again: the action, the role who does it, and the check that shows it worked. Name "
    "the event id it came from in from_event. Leave out the one-off events. Reply as JSON "
    "matching the schema and nothing else."
)

Decision = Literal["approve", "edit", "reject"]


@dataclass(frozen=True)
class TimelineEvent:
    id: str
    time: str
    actor: str
    action: str


@dataclass(frozen=True)
class RunbookStep:
    """One drafted step. `incomplete` and `problems` are code's own verdict, from step 3: a step
    can be kept and still be missing what makes it usable."""

    n: int
    action: str
    role: str
    check: str
    from_event: str
    incomplete: bool = False
    problems: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PendingApproval:
    """Everything the incident owner needs to see, and everything `resume` needs once they
    decide. Nothing here is a runbook yet."""

    writeup: str
    timeline: tuple[TimelineEvent, ...]
    steps: tuple[RunbookStep, ...]
    dropped: tuple[str, ...]

    @property
    def citations(self) -> list[str]:
        return sorted({s.from_event for s in self.steps})

    @property
    def text(self) -> str:
        lines = [f"Draft runbook: {len(self.steps)} step(s) from {len(self.timeline)} timeline event(s)"]
        for s in self.steps:
            flag = f"  [INCOMPLETE: {', '.join(s.problems)}]" if s.incomplete else ""
            lines.append(f"{s.n}. {s.action}{flag}")
            lines.append(f"   role: {s.role or '(none given)'}")
            lines.append(f"   check: {s.check or '(none given)'}")
            lines.append(f"   from: {s.from_event}")
        if self.dropped:
            lines.append("Dropped:")
            lines += [f"  {d}" for d in self.dropped]
        return "\n".join(lines)


@dataclass(frozen=True)
class Runbook:
    text: str
    steps: tuple[RunbookStep, ...]
    approved: bool


def _json_problems(items: object, required: tuple[str, ...]) -> list[str]:
    if not isinstance(items, list):
        return ["expected a list"]
    problems: list[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"item {i} is not an object")
            continue
        missing = [f for f in required if not item.get(f)]
        if missing:
            problems.append(f"item {i} missing: {', '.join(missing)}")
    return problems


def _complete_json(
    model: Model,
    tracer: Tracer,
    *,
    messages: list[Message],
    schema: dict,
    list_key: str,
    required: tuple[str, ...],
    title: str,
) -> list[dict]:
    """Ask for JSON matching `schema`, validate the `list_key` array's required fields, retry
    once with the problem appended, and give up to an empty list rather than raise: a chain step
    that raises on bad input takes the whole run down instead of leaving step 3 to report it."""
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=schema, max_tokens=700)
        tracer.record(
            kind="model",
            decided_by="code",
            title=title if attempt == 0 else "Ask again with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            items = json.loads(completion.text)[list_key]
            problems = _json_problems(items, required)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            items, problems = [], [f"invalid JSON: {exc}"]
        tracer.record(kind="code", decided_by="code", title=f"Validate the {list_key} reply", detail="; ".join(problems) or "valid")
        if not problems:
            return items
        if attempt < MAX_RETRIES:
            messages.append(Message(role="user", content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only."))
    return []


def _extract_timeline(writeup: str, model: Model, tracer: Tracer) -> list[TimelineEvent]:
    messages = [Message(role="system", content=TIMELINE_SYSTEM), Message(role="user", content=writeup)]
    items = _complete_json(
        model, tracer, messages=messages, schema=TIMELINE_SCHEMA, list_key="events",
        required=("time", "actor", "action"), title="Pull the timeline out of the write-up",
    )
    events = [TimelineEvent(id=f"e{i}", time=it["time"], actor=it["actor"], action=it["action"]) for i, it in enumerate(items, start=1)]
    tracer.record(kind="code", decided_by="code", title="Assign each event an id",
                  detail=", ".join(f"{e.id} {e.time}" for e in events) or "none")
    return events


def _draft_steps(timeline: list[TimelineEvent], model: Model, tracer: Tracer) -> list[dict]:
    numbered = "\n".join(f"{e.id} [{e.time}] {e.actor}: {e.action}" for e in timeline)
    messages = [Message(role="system", content=STEP_SYSTEM), Message(role="user", content=numbered)]
    return _complete_json(
        model, tracer, messages=messages, schema=STEP_SCHEMA, list_key="steps",
        required=("action", "from_event"), title="Turn the repeatable events into runbook steps",
    )


def _verify_steps(drafts: list[dict], timeline: list[TimelineEvent], tracer: Tracer) -> tuple[list[RunbookStep], list[str]]:
    known = {e.id for e in timeline}
    kept: list[RunbookStep] = []
    dropped: list[str] = []
    for draft in drafts:
        from_event = draft.get("from_event", "")
        if from_event not in known:
            dropped.append(f"{draft.get('action', '(no action)')!r} cites event {from_event!r}, which is not in the timeline")
            continue
        role = (draft.get("role") or "").strip()
        check = (draft.get("check") or "").strip()
        problems = [p for p, missing in (("no role", not role), ("no check", not check)) if missing]
        kept.append(RunbookStep(
            n=len(kept) + 1, action=draft.get("action", ""), role=role, check=check,
            from_event=from_event, incomplete=bool(problems), problems=tuple(problems),
        ))
    tracer.record(
        kind="code", decided_by="code",
        title="Verify every step traces to a real event and names a role and a check",
        detail=f"{len(kept)} kept, {len(dropped)} dropped, {sum(1 for s in kept if s.incomplete)} incomplete",
    )
    return kept, dropped


def run(writeup: str, model: Model, tracer: Tracer) -> PendingApproval:
    tracer.record(kind="code", decided_by="code", title="Read the write-up", detail=f"{len(writeup.splitlines())} line(s)")
    timeline = _extract_timeline(writeup, model, tracer)
    drafts = _draft_steps(timeline, model, tracer)
    steps, dropped = _verify_steps(drafts, timeline, tracer)
    tracer.record(
        kind="code", decided_by="code", title="Hold the draft for the incident owner's approval",
        detail=f"{len(steps)} step(s) pending, {sum(1 for s in steps if s.incomplete)} incomplete, {len(dropped)} dropped",
    )
    return PendingApproval(writeup=writeup, timeline=tuple(timeline), steps=tuple(steps), dropped=tuple(dropped))


def resume(pending: PendingApproval, decision: Decision, tracer: Tracer, *, note: str = "") -> Runbook:
    tracer.record(
        kind="code", decided_by="code", title="Resume from checkpoint with the incident owner's decision",
        detail=f"decision={decision}" + (f" note={note!r}" if note else ""),
    )
    if decision == "approve":
        return Runbook(text=pending.text, steps=pending.steps, approved=True)
    if decision == "edit":
        return Runbook(text=note, steps=pending.steps, approved=True)
    return Runbook(text="The incident owner rejected this draft; no runbook exists.", steps=(), approved=False)
