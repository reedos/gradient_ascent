"""Keeping a tracker document current from several sources, which is a different job from
writing a report about them.

A report is written once and read once. A tracker document has to still be true next week, so
the work is not producing text: it is reconciling what changed against what is already written,
deciding what is new, what is stale, what conflicts, and leaving the rest alone. Most of the
document does not change most weeks, and a run that rewrites it anyway has destroyed the one
thing a tracker is for.

Three rules hold this example together.

**Code decides what changed.** Field by field, against the source that owns the field. A
comparison, not a judgment.

**A person approves anything that overwrites a field a person wrote.** `owner`, `note` and
`risk` are written by people. So, sometimes, is a date somebody typed in after a phone call. Code
never overwrites one of those, however confident the source is; it queues the change with both
values side by side.

**Absence is reported, never read as agreement.** This is the failure that matters here, and it
has two shapes. A whole source can stop advancing: the time spreadsheet's `as_of` is the same as
it was last run, so nothing it feeds was confirmed this week, and every field it owns is reported
with its age. A single record can also fall out of a source that is otherwise current: the
tracker export no longer lists one project, which is not the same as that project being finished.
Neither is treated as "nothing changed", because the two are indistinguishable from it in a
document that only shows values.

The model's part is small and sits at the front. The shared inbox is prose, so one call per
unread message turns it into zero or more proposed field changes, each carrying the sentence it
came from. `_check_quotes` drops any proposal whose quote is not in the message it was read out
of. Every surviving proposal goes to the approval queue and none of them writes: a fact read out
of somebody's sentence is a claim, and a claim is not a record.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import date
from typing import Sequence

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 3
MAX_RETRIES = 1

#: Fields the tracker document holds, and which source owns each one. A field with no source here
#: is written by people and by nobody else.
FIELD_SOURCE: dict[str, str] = {
    "status": "project tracker",
    "next_milestone": "project tracker",
    "milestone_date": "project tracker",
    "hours_used": "time spreadsheet",
}
PERSON_FIELDS: tuple[str, ...] = ("owner", "note", "risk")
FIELDS: tuple[str, ...] = tuple(FIELD_SOURCE) + PERSON_FIELDS

#: A field not refreshed in this many days is reported as aging, whatever its value says.
AGING_DAYS = 7

#: The day this run stands on. `run` takes it as its one positional input.
SAMPLE_INPUT = "2026-09-18"


@dataclass(frozen=True)
class Cell:
    """One field of one row, with who last wrote it and when.

    Per-field provenance is what makes the rest of this example possible. Without it there is no
    way to tell a value the last run wrote from a value somebody typed after a phone call, and a
    tracker that cannot tell those apart will eventually overwrite the second with the first.
    """

    value: str
    written_by: str  # "code" | "person"
    updated: str  # ISO 8601


@dataclass(frozen=True)
class Row:
    project: str
    cells: dict[str, Cell]


@dataclass(frozen=True)
class Document:
    """The tracker as it stands. Frozen, and every change below produces a new one, so a run can
    be inspected against the document it started from."""

    as_of: str
    rows: tuple[Row, ...]

    def row(self, project: str) -> Row | None:
        return next((r for r in self.rows if r.project == project), None)


@dataclass(frozen=True)
class TrackerRecord:
    """One project as the tracker export lists it this week."""

    project: str
    status: str
    next_milestone: str
    milestone_date: str


@dataclass(frozen=True)
class HoursRecord:
    project: str
    hours_used: str


@dataclass(frozen=True)
class InboxMessage:
    """One unread message from the shared client inbox. This is the only prose in the run."""

    id: str
    project: str
    body: str


@dataclass(frozen=True)
class Sources:
    """This week's pull. Each source carries the date it says it is current to; `run` compares
    that against what the last run saw, which is how a quiet source is told from a quiet week."""

    tracker_as_of: str
    tracker: tuple[TrackerRecord, ...]
    hours_as_of: str
    hours: tuple[HoursRecord, ...]
    inbox_as_of: str
    inbox: tuple[InboxMessage, ...]


SAMPLE_DOCUMENT = Document(
    as_of="2026-09-11",
    rows=(
        Row(
            project="Brightwater Commons",
            cells={
                "status": Cell("Permitting", "code", "2026-09-04"),
                "next_milestone": Cell("Permit hearing", "code", "2026-09-04"),
                # Typed in by hand after a call, which is why the export must not overwrite it.
                "milestone_date": Cell("09/24/2026", "person", "2026-09-14"),
                "hours_used": Cell("65.0", "code", "2026-09-11"),
                "owner": Cell("the project lead", "person", "2026-08-20"),
                "note": Cell("Client is paying the expedited permit fee.", "person", "2026-09-08"),
                "risk": Cell("", "person", "2026-08-20"),
            },
        ),
        Row(
            project="Ferndale Library",
            cells={
                "status": Cell("Design development", "code", "2026-09-11"),
                "next_milestone": Cell("Cost estimate to client", "code", "2026-09-11"),
                "milestone_date": Cell("09/30/2026", "code", "2026-09-11"),
                "hours_used": Cell("31.0", "code", "2026-09-04"),
                "owner": Cell("the project lead", "person", "2026-08-20"),
                "note": Cell("Budget is tight; the client asked for a breakdown.", "person", "2026-09-12"),
                "risk": Cell("", "person", "2026-08-20"),
            },
        ),
        Row(
            project="Halloway Bridge Survey",
            cells={
                "status": Cell("Field work", "code", "2026-09-08"),
                "next_milestone": Cell("Draft report", "code", "2026-09-08"),
                "milestone_date": Cell("10/09/2026", "code", "2026-09-08"),
                "hours_used": Cell("9.5", "code", "2026-09-11"),
                "owner": Cell("the field tech", "person", "2026-08-20"),
                "note": Cell("", "person", "2026-08-20"),
                "risk": Cell("", "person", "2026-08-20"),
            },
        ),
    ),
)

#: What each source's `as_of` was the last time this ran. A source whose `as_of` has not moved
#: since is stale, whatever its records say.
SAMPLE_LAST_SEEN: dict[str, str] = {
    "project tracker": "2026-09-11",
    "time spreadsheet": "2026-09-15",
    "shared inbox": "2026-09-11",
}

SAMPLE_SOURCES = Sources(
    tracker_as_of="2026-09-18",
    tracker=(
        # The export's own date for the hearing, which is older than the one a person typed in.
        TrackerRecord("Brightwater Commons", "Permitting", "Permit hearing", "09/21/2026"),
        TrackerRecord("Ferndale Library", "Cost estimate out", "Cost estimate to client", "10/07/2026"),
        # Halloway Bridge Survey is missing from this week's export. The project did not end.
        TrackerRecord("Mavis Street", "Enquiry", "Scope call", "09/29/2026"),
    ),
    # The spreadsheet has not been touched since the last run: same as_of, same rows.
    hours_as_of="2026-09-15",
    hours=(
        HoursRecord("Brightwater Commons", "65.0"),
        HoursRecord("Ferndale Library", "31.0"),
        HoursRecord("Halloway Bridge Survey", "9.5"),
    ),
    inbox_as_of="2026-09-18",
    inbox=(
        InboxMessage(
            id="IN-51",
            project="Brightwater Commons",
            body=(
                "Confirming what we said on the call this morning: the permit hearing has been "
                "moved to 10/02/2026. We will need the updated site plan a week before that."
            ),
        ),
        InboxMessage(
            id="IN-52",
            project="Ferndale Library",
            body=(
                "Before we sign off on the estimate, the board wants a line-by-line breakdown of "
                "the shelving costs. Nothing else has changed at our end."
            ),
        ),
        InboxMessage(
            id="IN-53",
            project="Halloway Bridge Survey",
            body="Thanks for the photographs. Nothing needed from us this week.",
        ),
    ),
)

PROPOSAL_FIELDS = ("project", "field", "value", "quote")
SCHEMA = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "field": {"type": "string"},
                    "value": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": list(PROPOSAL_FIELDS),
            },
        }
    },
    "required": ["proposals"],
}
SYSTEM_PROMPT = (
    "You read one message from a firm's shared client inbox and report any change it states to "
    "the firm's project tracker. Reply as JSON matching this schema, with no other text and no "
    "markdown fences: " + json.dumps(SCHEMA) + ". "
    "The fields you may propose a change to are: " + ", ".join(FIELDS) + ". "
    "quote must be copied word for word from the message: it is the sentence that states the "
    "change, and a proposal whose quote is not in the message is thrown away. "
    "Propose nothing unless the message says it. Most messages change nothing, and an empty "
    "proposals list is the right answer for those. Do not decide whether a change should be "
    "made, whether it is already recorded, or whether it matters: a person decides all three."
)


@dataclass(frozen=True)
class Proposal:
    """One change the model read out of one message. It is a claim, not a record, and nothing in
    this file lets one write to the document."""

    message_id: str
    project: str
    field: str
    value: str
    quote: str


@dataclass(frozen=True)
class Change:
    """One field this run applied without asking. Both sides are kept: a tracker that cannot say
    what a value used to be cannot be argued with."""

    project: str
    field: str
    old: str
    new: str
    source: str


@dataclass(frozen=True)
class Pending:
    """One change waiting for a person, with the reason it is waiting."""

    id: str
    project: str
    field: str
    old: str
    new: str
    why: str
    quote: str = ""


@dataclass(frozen=True)
class Aging:
    """A field nobody has confirmed lately, with how long it has been and why."""

    project: str
    field: str
    days: int
    reason: str


@dataclass(frozen=True)
class Reconciliation:
    document: Document
    applied: tuple[Change, ...]
    pending: tuple[Pending, ...]
    unchanged: int
    stale_sources: tuple[str, ...]
    absent_rows: tuple[str, ...]
    aging: tuple[Aging, ...]
    dropped: tuple[str, ...]

    @property
    def summary(self) -> str:
        lines = [
            f"Tracker as of {self.document.as_of}: "
            f"{len(self.applied)} field(s) updated, {self.unchanged} left alone, "
            f"{len(self.pending)} waiting for a person."
        ]
        for change in self.applied:
            lines.append(f"  updated {change.project}.{change.field}: {change.old!r} -> {change.new!r} ({change.source})")
        for item in self.pending:
            lines.append(f"  [{item.id}] {item.project}.{item.field}: {item.old!r} -> {item.new!r} ({item.why})")
            if item.quote:
                lines.append(f"      quoted: {item.quote}")
        for name in self.stale_sources:
            lines.append(f"  source not refreshed since the last run: {name}")
        for project in self.absent_rows:
            lines.append(f"  no longer listed by the project tracker, not closed: {project}")
        for field in self.aging:
            lines.append(f"  aging: {field.project}.{field.field}, {field.days} days ({field.reason})")
        for reason in self.dropped:
            lines.append(f"  dropped: {reason}")
        return "\n".join(lines)


_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _days(later: str, earlier: str) -> int:
    return (date.fromisoformat(later) - date.fromisoformat(earlier)).days


def _check_quotes(proposals: Sequence[Proposal], body: str) -> tuple[list[Proposal], list[str]]:
    """Keep the proposals whose quote is really a piece of the message, and name the rest.

    A whitespace-normalized substring comparison, because a model re-wraps a sentence's line
    breaks even when it copies the words correctly. It catches a quote the model wrote rather
    than copied. It does not catch a real sentence read to mean something it does not say, which
    is a different mistake and is a person's to catch.
    """
    haystack = _normalize(body)
    kept: list[Proposal] = []
    dropped: list[str] = []
    for proposal in proposals:
        if _normalize(proposal.quote) and _normalize(proposal.quote) in haystack:
            kept.append(proposal)
        else:
            dropped.append(
                f"{proposal.message_id} proposed {proposal.project}.{proposal.field} on a quote "
                f"that is not in the message"
            )
    return kept, dropped


def _validate(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["reply is not an object"]
    if not isinstance(payload.get("proposals"), list):
        return ["proposals is missing or not a list"]
    problems: list[str] = []
    for i, item in enumerate(payload["proposals"]):
        if not isinstance(item, dict):
            problems.append(f"proposal {i} is not an object")
            continue
        for field in PROPOSAL_FIELDS:
            if not isinstance(item.get(field), str) or not item[field].strip():
                problems.append(f"proposal {i} has no {field}")
    return problems


def _read_message(message: InboxMessage, model: Model, tracer: Tracer, *, max_tokens: int) -> tuple[list[Proposal], list[str]]:
    """One message, one call, one retry if the reply does not validate.

    Returns the proposals whose quotes survive `_check_quotes`, and what was dropped. A message
    whose reply never validates is reported, not skipped silently: a message nobody read is not
    the same as a message that said nothing.
    """
    user = f"Project the message is filed under: {message.project}\n\nMessage:\n{message.body}"
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=user)]
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=SCHEMA, max_tokens=max_tokens)
        tracer.record(
            kind="model",
            decided_by="code",
            title=f"Read {message.id}" if attempt == 0 else f"Ask again about {message.id}",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            payload = json.loads(completion.text)
            problems = _validate(payload)
        except json.JSONDecodeError as exc:
            payload, problems = None, [f"invalid JSON: {exc}"]
        tracer.record(
            kind="code",
            decided_by="code",
            title=f"Validate the reply about {message.id}",
            detail="; ".join(problems) or "valid",
        )
        if not problems:
            raw = [
                Proposal(
                    message_id=message.id,
                    project=p["project"].strip(),
                    field=p["field"].strip(),
                    value=p["value"].strip(),
                    quote=p["quote"].strip(),
                )
                for p in payload["proposals"]
            ]
            kept, dropped = _check_quotes(raw, message.body)
            tracer.record(
                kind="code",
                decided_by="code",
                title=f"Check every quote against {message.id}",
                detail=f"{len(kept)} kept, {len(dropped)} dropped",
            )
            return kept, dropped
        if attempt < MAX_RETRIES:
            messages.append(
                Message(
                    role="user",
                    content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only.",
                )
            )
    return [], [f"{message.id} was never read: the reply did not validate after a retry"]


def reconcile(
    document: Document,
    sources: Sources,
    proposals: Sequence[Proposal],
    *,
    as_of: str,
    last_seen: dict[str, str],
) -> Reconciliation:
    """Everything after the reading, and none of it is a judgment.

    Four kinds of outcome, and the fourth is the one worth naming: a field is updated, or queued
    for a person, or left alone, or nobody confirmed it this week and the run says so.
    """
    stale = tuple(
        name
        for name, as_of_now in (
            ("project tracker", sources.tracker_as_of),
            ("time spreadsheet", sources.hours_as_of),
            ("shared inbox", sources.inbox_as_of),
        )
        if as_of_now <= last_seen.get(name, "")
    )
    tracker_by_project = {r.project: r for r in sources.tracker} if "project tracker" not in stale else {}
    hours_by_project = {r.project: r for r in sources.hours} if "time spreadsheet" not in stale else {}

    applied: list[Change] = []
    pending: list[Pending] = []
    aging: list[Aging] = []
    dropped: list[str] = []
    rows: list[Row] = []

    for row in document.rows:
        cells = dict(row.cells)
        record = tracker_by_project.get(row.project)
        hours = hours_by_project.get(row.project)
        incoming: dict[str, str] = {}
        if record is not None:
            incoming.update(
                status=record.status,
                next_milestone=record.next_milestone,
                milestone_date=record.milestone_date,
            )
        if hours is not None:
            incoming["hours_used"] = hours.hours_used

        for field, value in incoming.items():
            cell = cells[field]
            if cell.value == value:
                # Confirmed this week: the value did not move and now has a date saying a source
                # still agrees with it. That date is what `aging` below is measured from.
                cells[field] = replace(cell, updated=as_of)
                continue
            if cell.written_by == "person":
                pending.append(
                    Pending(
                        id=f"P-{len(pending) + 1:02d}",
                        project=row.project,
                        field=field,
                        old=cell.value,
                        new=value,
                        why=f"the {FIELD_SOURCE[field]} disagrees with a value a person typed in",
                    )
                )
                continue
            applied.append(Change(row.project, field, cell.value, value, FIELD_SOURCE[field]))
            cells[field] = Cell(value=value, written_by="code", updated=as_of)

        for field, source_name in FIELD_SOURCE.items():
            if field in incoming:
                continue
            reason = (
                f"the {source_name} has not been refreshed since the last run"
                if source_name in stale
                else f"the {source_name} no longer lists this project"
            )
            age = _days(as_of, cells[field].updated)
            if age >= AGING_DAYS:
                aging.append(Aging(row.project, field, age, reason))

        rows.append(Row(project=row.project, cells=cells))

    known = {row.project for row in document.rows}
    for record in sources.tracker:
        if record.project not in known:
            pending.append(
                Pending(
                    id=f"P-{len(pending) + 1:02d}",
                    project=record.project,
                    field="(new row)",
                    old="",
                    new=f"{record.status}, {record.next_milestone} {record.milestone_date}",
                    why="a project no row covers yet, and a new row needs an owner",
                )
            )

    absent = tuple(
        row.project
        for row in document.rows
        if "project tracker" not in stale and row.project not in tracker_by_project
    )

    for proposal in proposals:
        if proposal.project not in known:
            dropped.append(f"{proposal.message_id} named a project no row covers: {proposal.project}")
            continue
        if proposal.field not in FIELDS:
            dropped.append(f"{proposal.message_id} named a field the tracker does not have: {proposal.field}")
            continue
        current = next(r for r in document.rows if r.project == proposal.project).cells[proposal.field]
        if current.value == proposal.value:
            dropped.append(f"{proposal.message_id} proposed {proposal.project}.{proposal.field}, which already says that")
            continue
        pending.append(
            Pending(
                id=f"P-{len(pending) + 1:02d}",
                project=proposal.project,
                field=proposal.field,
                old=current.value,
                new=proposal.value,
                why=f"read out of {proposal.message_id}, which is a claim and not a record",
                quote=proposal.quote,
            )
        )

    return Reconciliation(
        document=Document(as_of=as_of, rows=tuple(rows)),
        applied=tuple(applied),
        pending=tuple(pending),
        # Every cell this run did not write. On a tracker that is almost all of them, and the
        # number is here because leaving a field alone is the outcome this recipe exists to
        # protect, not the absence of an outcome.
        unchanged=sum(len(row.cells) for row in document.rows) - len(applied),
        stale_sources=stale,
        absent_rows=absent,
        aging=tuple(aging),
        dropped=tuple(dropped),
    )


def approve(reconciliation: Reconciliation, accepted: Sequence[str], *, as_of: str) -> Document:
    """The second half, called separately once a person has actually looked.

    `accepted` is the ids of the pending changes they approved. Everything else in the queue stays
    out of the document. A cell written here is marked `written_by="person"`, because it was: the
    person decided it, and next week's run must not overwrite it without asking again.

    Two things this function refuses to do. Approving two changes to the same cell raises rather
    than letting the later one win, because the queue can legitimately hold two different answers
    for one field and picking between them is the decision being approved. And a "(new row)" item
    is not applied here: a new row needs an owner, and nothing in this file can supply one.
    """
    wanted = set(accepted)
    keep = {item.id for item in reconciliation.pending if item.id in wanted}
    cells_touched: dict[tuple[str, str], str] = {}
    for item in reconciliation.pending:
        if item.id not in keep or item.field == "(new row)":
            continue
        key = (item.project, item.field)
        if key in cells_touched:
            raise ValueError(
                f"{cells_touched[key]} and {item.id} both change {item.project}.{item.field}; "
                f"approve one of them"
            )
        cells_touched[key] = item.id
    rows: list[Row] = []
    for row in reconciliation.document.rows:
        cells = dict(row.cells)
        for item in reconciliation.pending:
            if item.id in keep and item.project == row.project and item.field in cells:
                cells[item.field] = Cell(value=item.new, written_by="person", updated=as_of)
        rows.append(Row(project=row.project, cells=cells))
    return Document(as_of=as_of, rows=tuple(rows))


def run(
    as_of: str,
    model: Model,
    tracer: Tracer,
    *,
    document: Document = SAMPLE_DOCUMENT,
    sources: Sources = SAMPLE_SOURCES,
    last_seen: dict[str, str] | None = None,
    max_tokens: int = 400,
) -> Reconciliation:
    """One week's upkeep. `as_of` is the day the run stands on.

    The model runs first and only on the inbox. Everything after it is comparison, and nothing the
    model returned reaches the document without a person.
    """
    seen = dict(SAMPLE_LAST_SEEN if last_seen is None else last_seen)
    proposals: list[Proposal] = []
    dropped: list[str] = []
    inbox_stale = sources.inbox_as_of <= seen.get("shared inbox", "")
    for message in () if inbox_stale else sources.inbox:
        kept, lost = _read_message(message, model, tracer, max_tokens=max_tokens)
        proposals.extend(kept)
        dropped.extend(lost)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Read the unread messages",
        detail=f"{0 if inbox_stale else len(sources.inbox)} message(s), {len(proposals)} proposal(s), {len(dropped)} dropped",
    )

    result = reconcile(document, sources, proposals, as_of=as_of, last_seen=seen)
    result = Reconciliation(
        document=result.document,
        applied=result.applied,
        pending=result.pending,
        unchanged=result.unchanged,
        stale_sources=result.stale_sources,
        absent_rows=result.absent_rows,
        aging=result.aging,
        dropped=tuple(dropped) + result.dropped,
    )
    tracer.record(
        kind="code",
        decided_by="code",
        title="Reconcile every field against the source that owns it",
        detail=(
            f"{len(result.applied)} applied, {len(result.pending)} queued for a person, "
            f"{result.unchanged} left alone"
        ),
    )
    tracer.record(
        kind="code",
        decided_by="code",
        title="Report what nobody confirmed this week",
        detail=(
            f"stale source(s): {', '.join(result.stale_sources) or 'none'}; "
            f"absent from the export: {', '.join(result.absent_rows) or 'none'}; "
            f"{len(result.aging)} aging field(s)"
        ),
    )
    return result
