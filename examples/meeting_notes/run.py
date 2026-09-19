"""Level 1: turn a meeting transcript into decisions, owners and open questions in one call, the
same ask-validate-retry-once contract `examples/structured_output/run.py` uses. The schema and the
retry count are fixed and the model only ever fills in field values, so every step is
`decided_by: "code"`.

A schema guarantees shape, not truth: a decision can be well-formed JSON and still be something
nobody in the room actually decided. The one check this example adds on top of the schema is
grounding: every decision must carry a `quote`, copied from the transcript, and code drops any
decision whose quote is not actually a substring of the transcript (whitespace normalized first,
since a model's reply often collapses or re-wraps line breaks). A dropped decision is reported as
dropped, with its own text, not silently removed, so a person reading the notes knows a decision
was proposed and could not be confirmed against the source rather than assuming nothing was missed.

That check is deliberately narrow. It proves the words were said; it does not prove the room
actually agreed on them. A model that quotes the discussion of an idea that was explicitly
deferred, accurately, and reports it as decided passes this check and still comes out wrong. See
`tests/test_example_meeting_notes.py` for exactly that case, and the recipe page's "How it fails"
section for what to do about it: a person who was in the room reads every run before it goes
anywhere.

The other two rules live in the prompt, not in code, because nothing here can check them
mechanically: an owner the transcript never names comes back as the literal string "unassigned"
rather than a guess, and a due date nobody stated stays an empty string rather than an invented
one.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 1
MAX_RETRIES = 1

DECISION_FIELDS = ("decision", "owner", "due_date", "quote")
REQUIRED_FIELDS = ("attendees", "decisions", "open_questions")
SCHEMA = {
    "type": "object",
    "properties": {
        "attendees": {"type": "array", "items": {"type": "string"}},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "decision": {"type": "string"},
                    "owner": {"type": "string"},
                    "due_date": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": list(DECISION_FIELDS),
            },
        },
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": list(REQUIRED_FIELDS),
}
SYSTEM_PROMPT = (
    "Read the meeting transcript and reply as JSON matching this schema, with no other text and "
    "no markdown fences: " + json.dumps(SCHEMA) + ". "
    "List every decision that was actually made. Something proposed, discussed or explicitly put "
    "off to a later meeting is not a decision; leave it out. For each decision, quote must be "
    "copied character for character from the transcript, the exact sentence that shows the "
    "decision was made. If the transcript never names who owns a decision, set owner to the "
    "literal word unassigned rather than guessing from context. If no due date was stated, set "
    "due_date to an empty string rather than inventing one."
)

#: A small-team meeting, invented. One decision is stated plainly (the signup flow), one is
#: raised and explicitly deferred (the discount, which a good extractor must not report as
#: decided), one action item's owner is a role rather than a name (the FAQ), and one open
#: question is never resolved (the vendor's pricing tier).
TRANSCRIPT = """\
Weekly sync, Thornwood product team, 09/14/2026.
Attendees: Priya Okafor, Marcus Chen, Deshawn Fitts, Yuki Tanaka.

Priya: Morning, everyone. Let's start with the onboarding redesign.
Priya: Marcus, where's the new signup flow?
Marcus: The three-step version is built and tested. I think we can ship it Friday.
Priya: Agreed. We're shipping the three-step signup flow on Friday. Marcus, that's yours.
Marcus: Works for me, I'll cut the release Friday morning.
Priya: Great, thanks Marcus.
Priya: Next, the pricing page. Deshawn raised moving the annual discount from 10 to 20 percent.
Deshawn: Right, support keeps hearing that 10 percent doesn't move anyone off monthly.
Yuki: I've looked at the churn numbers and I'm not convinced 20 percent pays for itself yet.
Yuki: I'd want another week of modeling before we commit to a number.
Priya: Fair, let's not decide the discount today. We'll pick it back up once Yuki has the model.
Deshawn: Okay, I can wait a week.
Priya: Now the support backlog. Somebody needs to own the FAQ for the new signup flow.
Marcus: That should sit with whoever's on support rotation next week, not with engineering.
Priya: Agreed, the FAQ goes to whoever's on support rotation next week.
Deshawn: I'll check the schedule and let them know.
Priya: Last item, the vendor contract renewal. Anything to flag before we close?
Yuki: Only that I still don't know whether the new usage-based pricing applies to us, or whether we're grandfathered into the old tier. I haven't gotten a straight answer from the vendor yet.
Priya: We need that answered before the renewal date. Anyone have a contact there?
Deshawn: I'll ask around and see who we've talked to before.
Marcus: Sounds good. Talk next week.
Priya: Okay, that covers it. Thanks, all.
"""

SAMPLE_INPUT = TRANSCRIPT
_WS_RE = re.compile(r"\s+")


def _normalize_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _validate(record: dict) -> list[str]:
    problems = [f"missing field: {f}" for f in REQUIRED_FIELDS if f not in record]
    if problems:
        return problems
    if not isinstance(record["attendees"], list) or not all(isinstance(a, str) for a in record["attendees"]):
        problems.append("attendees must be a list of strings")
    if not isinstance(record["open_questions"], list) or not all(isinstance(q, str) for q in record["open_questions"]):
        problems.append("open_questions must be a list of strings")
    decisions = record.get("decisions")
    if not isinstance(decisions, list):
        problems.append("decisions must be a list")
    else:
        for i, d in enumerate(decisions):
            if not isinstance(d, dict):
                problems.append(f"decision {i} is not an object")
                continue
            missing = [f for f in DECISION_FIELDS if f not in d]
            if missing:
                problems.append(f"decision {i} missing field(s): {', '.join(missing)}")
                continue
            bad = [f for f in DECISION_FIELDS if not isinstance(d[f], str)]
            if bad:
                problems.append(f"decision {i} field(s) not a string: {', '.join(bad)}")
    return problems


@dataclass(frozen=True)
class Decision:
    decision: str
    owner: str
    due_date: str
    quote: str


@dataclass(frozen=True)
class DroppedDecision:
    """A decision the model proposed whose quote does not actually appear in the transcript.
    Reported, never silently removed: a person reading the notes should know something was
    proposed and could not be confirmed, not assume the extractor found everything."""

    decision: str
    quote: str
    reason: str


@dataclass(frozen=True)
class MeetingNotes:
    attendees: tuple[str, ...]
    decisions: tuple[Decision, ...]
    dropped: tuple[DroppedDecision, ...]
    open_questions: tuple[str, ...]
    error: str = ""

    @property
    def text(self) -> str:
        if self.error:
            return f"Could not extract notes: {self.error}"
        lines = [f"Attendees: {', '.join(self.attendees) or 'none recorded'}", "Decisions:"]
        lines += [f"  {d.decision} (owner: {d.owner}, due: {d.due_date or 'not stated'})" for d in self.decisions]
        if self.dropped:
            lines.append("Dropped, quote not found in the transcript:")
            lines += [f"  {d.decision}" for d in self.dropped]
        lines.append("Open questions:")
        lines += [f"  {q}" for q in self.open_questions]
        return "\n".join(lines)

    @property
    def citations(self) -> list[str]:
        return [d.quote for d in self.decisions]


def _check_quotes(decisions: list[dict], transcript: str) -> tuple[list[Decision], list[DroppedDecision]]:
    haystack = _normalize_ws(transcript)
    kept: list[Decision] = []
    dropped: list[DroppedDecision] = []
    for d in decisions:
        quote = _normalize_ws(d["quote"])
        if quote and quote in haystack:
            kept.append(Decision(decision=d["decision"], owner=d["owner"], due_date=d["due_date"], quote=d["quote"]))
        else:
            dropped.append(DroppedDecision(decision=d["decision"], quote=d["quote"], reason="quote not found in transcript"))
    return kept, dropped


def run(transcript: str, model: Model, tracer: Tracer, *, max_tokens: int = 700) -> MeetingNotes:
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=transcript)]
    record: dict = {}
    problems: list[str] = []
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=SCHEMA, max_tokens=max_tokens)
        tracer.record(
            kind="model",
            decided_by="code",
            title="Ask the model for JSON" if attempt == 0 else "Ask again with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            record = json.loads(completion.text)
            problems = _validate(record)
        except json.JSONDecodeError as exc:
            record, problems = {}, [f"invalid JSON: {exc}"]
        tracer.record(kind="code", decided_by="code", title="Validate against the schema", detail="; ".join(problems) or "valid")
        if not problems:
            break
        if attempt < MAX_RETRIES:
            messages.append(Message(role="user", content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only."))

    if problems:
        tracer.record(kind="code", decided_by="code", title="Give up after the retry", detail="; ".join(problems))
        return MeetingNotes(attendees=(), decisions=(), dropped=(), open_questions=(), error="; ".join(problems))

    kept, dropped = _check_quotes(record["decisions"], transcript)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check each decision's quote against the transcript",
        detail=f"{len(kept)} kept, {len(dropped)} dropped" + (f": {'; '.join(d.decision for d in dropped)}" if dropped else ""),
    )
    return MeetingNotes(
        attendees=tuple(record["attendees"]),
        decisions=tuple(kept),
        dropped=tuple(dropped),
        open_questions=tuple(record["open_questions"]),
    )
