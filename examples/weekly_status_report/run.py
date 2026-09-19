"""A standing Friday status report, assembled from three systems that do not agree about
anything except what week it is.

Two halves, and the seam between them is what this example is for.

The assembly half calls no model. Three sources are pulled, their project names are reconciled
against one list a person wrote down once, and every count, date and total the report can quote
is computed from the records: tasks closed and opened inside the window, tasks open and overdue
as of the report date, threads waiting on the firm and for how long, hours logged against hours
budgeted. Two people handed the same three exports would produce the same figures. That is
level 0, and it is most of the job.

The writing half is one model call. It is handed the figures, formatted exactly as it is allowed
to quote them, plus whatever free-text note the person running the report added, and its only job
is the sentences between the numbers. It has nothing to look up and nothing to decide.

Two checks run in code after it, and they point in opposite directions:

- `unsupported_figures` is the one `examples/bench_measurement_writeup/run.py` argues for: every
  numeric token in the draft has to be, character for character, one of the figures code
  computed. It catches a number the model made up.
- `missing_required` is the other direction, and it is the one a status report needs that a
  characterization report does not. Code marks some figures as must-say (a non-zero overdue
  count's own date, a project at or over 90 percent of its budgeted hours) and this check reports
  any of those the draft never quoted. It catches a bad week quietly left out.

A figure shorter than `MIN_CHECKABLE` characters is never marked must-say, however important it
is. A check that a draft mentions "2" somewhere is not a check, and pretending otherwise would be
worse than not running one. Those figures come back in `Report.confirm_by_eye` for the person who
reads the report before it goes out, which is the last step of this recipe and not an optional
one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 1

#: A figure has to be at least this long for `missing_required` to say anything useful about
#: whether a draft quoted it. See the module docstring.
MIN_CHECKABLE = 3

#: The report's own week. A standing job takes both ends of its window from the schedule rather
#: than from a person's judgment: `SINCE` is the day the last report closed, `REPORT_DATE` is the
#: day this one closes, and every "this week" figure below is computed against that pair.
SINCE = "2026-09-11"
REPORT_DATE = "2026-09-18"

#: The free-text note the person running the report added this week. It never contributes a
#: figure, so it never reaches the check.
SAMPLE_INPUT = "Lead with the library: the client asked about the budget on Tuesday's call."


@dataclass(frozen=True)
class Task:
    """One row of the project tracker's export. The tracker is the firm's system of record for
    what is being worked on, and it is machine-written: a date here moved because somebody
    dragged a card."""

    id: str
    project: str
    title: str
    owner: str
    due: str  # ISO 8601
    opened: str
    closed: str | None = None


@dataclass(frozen=True)
class Thread:
    """One conversation in the shared client inbox. The inbox is reliable about dates and not
    about anything else: it knows when a message arrived and which side sent it, and nothing in
    this recipe reads a word of the message itself."""

    id: str
    project: str
    subject: str
    last_message: str  # ISO 8601
    waiting_on: str  # "us" | "client"


@dataclass(frozen=True)
class TimesheetRow:
    """One week of hours on one project, typed into a spreadsheet by hand. It is the source that
    goes stale, because keeping it current is somebody's Monday job rather than a side effect of
    doing the work."""

    project: str
    week_ending: str  # ISO 8601
    hours: float


@dataclass(frozen=True)
class Source:
    """One pull from one system. `as_of` is what the source itself says it is current to, which
    is not the same as the day the report runs and is not assumed to be."""

    name: str
    as_of: str
    tasks: tuple[Task, ...] = ()
    threads: tuple[Thread, ...] = ()
    rows: tuple[TimesheetRow, ...] = ()


#: The three projects the firm has open, as the tracker spells them. This list is the one place a
#: project name is authoritative.
PROJECTS: tuple[str, ...] = (
    "Brightwater Commons",
    "Ferndale Library",
    "Halloway Bridge Survey",
)

#: Budgeted hours per project, agreed with the client when the work was taken on.
BUDGET_HOURS: dict[str, float] = {
    "Brightwater Commons": 180.0,
    "Ferndale Library": 60.0,
    "Halloway Bridge Survey": 60.0,
}

#: What each other system calls each project. A person wrote this down once; reconciling names is
#: a level-0 job and this is the whole of it. Anything a source names that is not in here or in
#: PROJECTS is reported rather than dropped, which is the only safe thing to do with a name
#: nobody recognizes.
ALIASES: dict[str, str] = {
    "brightwater": "Brightwater Commons",
    "brightwater commons": "Brightwater Commons",
    "ferndale": "Ferndale Library",
    "ferndale library": "Ferndale Library",
    "halloway": "Halloway Bridge Survey",
    "halloway bridge": "Halloway Bridge Survey",
    "halloway bridge survey": "Halloway Bridge Survey",
}

SOURCES: tuple[Source, ...] = (
    Source(
        name="project tracker",
        as_of="2026-09-18",
        tasks=(
            Task("BW-101", "Brightwater Commons", "Foundation drawings", "the drafter", "2026-09-16", "2026-08-28", "2026-09-15"),
            Task("BW-104", "Brightwater Commons", "Permit application", "the office manager", "2026-09-16", "2026-09-02"),
            Task("BW-107", "Brightwater Commons", "Client review packet", "the project lead", "2026-09-25", "2026-09-09"),
            Task("BW-110", "Brightwater Commons", "Site photographs", "the field tech", "2026-09-18", "2026-09-14", "2026-09-17"),
            Task("FL-201", "Ferndale Library", "Shelving layout", "the drafter", "2026-09-18", "2026-09-08", "2026-09-16"),
            Task("FL-204", "Ferndale Library", "Lighting schedule", "the drafter", "2026-09-22", "2026-09-04"),
            Task("FL-206", "Ferndale Library", "Accessibility review", "the project lead", "2026-09-10", "2026-08-31"),
            Task("FL-208", "Ferndale Library", "Cost estimate revision B", "the project lead", "2026-09-30", "2026-09-16"),
            Task("HB-301", "Halloway Bridge Survey", "Field survey, first day", "the field tech", "2026-09-11", "2026-09-01", "2026-09-09"),
            Task("HB-303", "Halloway Bridge Survey", "Deck condition notes", "the field tech", "2026-10-02", "2026-09-08"),
            Task("HB-305", "Halloway Bridge Survey", "Draft report", "the project lead", "2026-10-09", "2026-09-17"),
        ),
    ),
    Source(
        name="shared inbox",
        as_of="2026-09-18",
        threads=(
            Thread("IN-41", "brightwater commons", "Permit fee schedule", "2026-09-16", "us"),
            Thread("IN-44", "ferndale library", "Shelving sign-off", "2026-09-17", "client"),
            Thread("IN-45", "ferndale", "Budget question from Tuesday", "2026-09-12", "us"),
            Thread("IN-47", "halloway bridge", "Access permission for the north span", "2026-09-18", "client"),
            Thread("IN-48", "Mavis Street", "Can you look at a small job", "2026-09-17", "us"),
            Thread("IN-49", "brightwater", "Revised site plan", "2026-09-10", "us"),
        ),
    ),
    Source(
        # Hand-maintained, and three days behind the report. Nothing about that is unusual, and
        # the point of carrying `as_of` is that code can say so instead of reporting a zero.
        name="time spreadsheet",
        as_of="2026-09-15",
        rows=(
            TimesheetRow("brightwater", "2026-08-28", 18.0),
            TimesheetRow("brightwater", "2026-09-04", 24.5),
            TimesheetRow("brightwater", "2026-09-11", 22.5),
            TimesheetRow("ferndale", "2026-09-04", 31.0),
            TimesheetRow("ferndale", "2026-09-11", 28.0),
            TimesheetRow("halloway", "2026-09-11", 9.5),
        ),
    ),
)

#: A thread the firm has not answered in more than this many days is worth naming in the report.
#: A number a person chose once, not one a model weighs up per thread.
WAITING_DAYS = 3

SYSTEM_PROMPT = (
    "You write a short weekly status report for a small firm, from a list of figures another "
    "program computed from the firm's own systems. Write plain prose the whole team can read in "
    "two minutes: what moved this week, what is behind, and what needs somebody's attention "
    "before Monday. Rules, with no exceptions:\n"
    "- Every number in your report must be copied character for character from the Figures list "
    "below. Never compute, add, average, round or convert a number yourself, even an easy one.\n"
    "- Use a figure only for the quantity its label names. Do not reuse a figure's number for a "
    "different quantity.\n"
    "- For anything not in the Figures list (how many projects there are, which project is "
    "busier than which), use words, not digits.\n"
    "- Every figure marked (must say) has to appear in the report. These are the ones a reader "
    "would act on, and a report that leaves one out is worse than no report.\n"
    "- Do not soften a figure. An overdue task is overdue; a project over its budgeted hours is "
    "over them. Say so and move on.\n"
    "- Where a figure's label says a source is behind, say that in the report rather than "
    "treating the missing week as a quiet one."
)


@dataclass(frozen=True)
class Figure:
    """One number code computed, formatted exactly as the model is allowed to quote it.

    `label` is what the prompt calls it. `text` is the literal character sequence the checks look
    for in the draft; it is compared as a string and not as a number, so "98.3" and "98.30" are
    different figures. Formatting happens once, here, so the prompt and the checks cannot drift
    apart.

    `must_say` is honored only when `text` is at least `MIN_CHECKABLE` characters long. See
    `required_figures` and `short_must_say`.
    """

    label: str
    text: str
    must_say: bool = False


def required_figures(figures: Sequence[Figure]) -> tuple[Figure, ...]:
    """The must-say figures long enough for `missing_required` to actually test."""
    return tuple(f for f in figures if f.must_say and len(f.text) >= MIN_CHECKABLE)


def short_must_say(figures: Sequence[Figure]) -> tuple[Figure, ...]:
    """The must-say figures too short to test. A one- or two-character figure appears in almost
    any draft by coincidence, so code reports these to the person reading the report instead of
    claiming to have checked them."""
    return tuple(f for f in figures if f.must_say and len(f.text) < MIN_CHECKABLE)


#: Identifier-shaped tokens, blanked before the numeric scan: a run beginning with letters that
#: carries a digit somewhere, with optional hyphenated groups. Task ids ("BW-104") and thread ids
#: ("IN-45") are that shape. Without this, every id in a draft would have to be pre-approved as a
#: figure. The cost is that a digit a model buries inside a word is invisible to the check, which
#: this recipe's page says out loud.
IDENTIFIER_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+\b")

#: A date in month-day-year form, matched whole so 09/18/2026 is one token rather than the three
#: numbers 09, 18 and 2026. Every date a report may quote is a figure, computed from the records.
DATE_RE = re.compile(r"(?<![\d/])\d{1,2}/\d{1,2}/\d{4}(?![\d/])")

#: A numeric token: an optional sign, digits with optional thousands separators, an optional
#: decimal part, or a bare decimal. It starts only where no digit or decimal point precedes it and
#: ends only where no digit follows, so "98.3 percent" gives 98.3 rather than 98, and "22.5-28.0"
#: gives up both halves.
NUMBER_RE = re.compile(r"(?<![\d.])[+-]?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)(?!\d)")


@dataclass(frozen=True)
class ProjectFigures:
    """The computed week for one project, kept as numbers as well as formatted text so the tests
    can check the arithmetic without parsing the prompt."""

    project: str
    closed: int
    opened: int
    open_now: int
    overdue: int
    earliest_due: str | None
    hours_to_date: float
    budget_hours: float
    percent_of_budget: float


@dataclass(frozen=True)
class Assembly:
    """Everything the assembly half produced. No model has run at this point, and every field
    here is a count, a date, a total or a name read off a record."""

    figures: tuple[Figure, ...]
    projects: tuple[ProjectFigures, ...]
    waiting: tuple[Thread, ...]
    unmatched: tuple[str, ...]
    behind: tuple[tuple[str, int], ...]  # (source name, days behind the report date)
    hours_through: str | None


def project_key(name: str) -> str | None:
    """The canonical project a source's spelling refers to, or None when nobody recognizes it.

    Returning None rather than guessing is the whole design: a name no list knows is reported to
    a person, because the alternative is a thread or a timesheet row silently attached to the
    wrong project or silently dropped.
    """
    cleaned = " ".join(name.lower().replace("-", " ").split())
    if cleaned in ALIASES:
        return ALIASES[cleaned]
    for project in PROJECTS:
        if cleaned == project.lower():
            return project
    return None


def _mdy(iso: str) -> str:
    """`2026-09-18` as `09/18/2026`, the form this site writes dates in."""
    year, month, day = iso.split("-")
    return f"{month}/{day}/{year}"


def _days(later: str, earlier: str) -> int:
    return (date.fromisoformat(later) - date.fromisoformat(earlier)).days


def compute_figures(
    sources: Sequence[Source] = SOURCES,
    *,
    since: str = SINCE,
    report_date: str = REPORT_DATE,
) -> Assembly:
    """The assembly half, whole. Pull, reconcile the names, count, subtract, compare dates.

    Nothing in this function is a judgment, and nothing in it calls a model. The window is
    `since` exclusive to `report_date` inclusive, which is the schedule's window and not
    anybody's opinion about which week a task belongs to.
    """
    tasks = tuple(t for s in sources for t in s.tasks)
    threads = tuple(t for s in sources for t in s.threads)
    rows = tuple(r for s in sources for r in s.rows)

    unmatched: list[str] = []
    for name in [t.project for t in threads] + [r.project for r in rows]:
        if project_key(name) is None and name not in unmatched:
            unmatched.append(name)

    behind = tuple(
        (s.name, _days(report_date, s.as_of)) for s in sources if _days(report_date, s.as_of) > 0
    )
    dated_rows = [r for r in rows if project_key(r.project) is not None]
    hours_through = max((r.week_ending for r in dated_rows), default=None)

    waiting = tuple(
        t
        for t in threads
        if t.waiting_on == "us"
        and project_key(t.project) is not None
        and _days(report_date, t.last_message) > WAITING_DAYS
    )

    figures: list[Figure] = [
        Figure("week ending", _mdy(report_date)),
        Figure("previous report", _mdy(since)),
    ]

    projects: list[ProjectFigures] = []
    for project in PROJECTS:
        mine = [t for t in tasks if t.project == project]
        closed = [t for t in mine if t.closed and since < t.closed <= report_date]
        opened = [t for t in mine if since < t.opened <= report_date]
        open_now = [t for t in mine if not t.closed]
        overdue = [t for t in open_now if t.due < report_date]
        earliest = min((t.due for t in open_now), default=None)
        hours = sum(r.hours for r in rows if project_key(r.project) == project)
        budget = BUDGET_HOURS[project]
        percent = 100.0 * hours / budget
        projects.append(
            ProjectFigures(
                project=project,
                closed=len(closed),
                opened=len(opened),
                open_now=len(open_now),
                overdue=len(overdue),
                earliest_due=earliest,
                hours_to_date=hours,
                budget_hours=budget,
                percent_of_budget=percent,
            )
        )
        figures.append(Figure(f"{project}: tasks closed this week", str(len(closed))))
        figures.append(Figure(f"{project}: tasks opened this week", str(len(opened))))
        figures.append(Figure(f"{project}: tasks open now", str(len(open_now))))
        figures.append(Figure(f"{project}: tasks overdue now", str(len(overdue)), must_say=bool(overdue)))
        for task in overdue:
            # The date is the checkable half of an overdue claim: a count of 1 is a token any
            # draft may contain by accident, and 09/11/2026 is not.
            figures.append(Figure(f"{project}: {task.title} was due", _mdy(task.due), must_say=True))
        if earliest:
            figures.append(Figure(f"{project}: earliest due date still open", _mdy(earliest)))
        figures.append(Figure(f"{project}: hours logged to date", f"{hours:.1f}"))
        figures.append(Figure(f"{project}: hours budgeted", f"{budget:.0f}"))
        figures.append(
            Figure(
                f"{project}: percent of budgeted hours used",
                f"{percent:.1f}",
                must_say=percent >= 90.0,
            )
        )

    figures.append(Figure("tasks closed this week, all projects", str(sum(p.closed for p in projects))))
    figures.append(Figure("tasks opened this week, all projects", str(sum(p.opened for p in projects))))
    figures.append(
        Figure(
            "tasks overdue now, all projects",
            str(sum(p.overdue for p in projects)),
            must_say=any(p.overdue for p in projects),
        )
    )
    figures.append(
        Figure(
            f"client threads waiting on us for more than {WAITING_DAYS} days",
            str(len(waiting)),
            must_say=bool(waiting),
        )
    )
    for thread in waiting:
        figures.append(
            Figure(
                f"{thread.subject}: days since the client wrote",
                str(_days(report_date, thread.last_message)),
            )
        )
    if hours_through:
        figures.append(Figure("hours entered through", _mdy(hours_through)))
    for name, days in behind:
        # The source's own as_of, not the number of days: a date is distinctive enough for
        # `missing_required` to test, and "3" is not.
        as_of = next(s.as_of for s in sources if s.name == name)
        figures.append(Figure(f"the {name} is current only to", _mdy(as_of), must_say=True))
        figures.append(Figure(f"days the {name} is behind this report", str(days)))
    figures.append(Figure("project names no list recognized", str(len(unmatched))))

    return Assembly(
        figures=tuple(figures),
        projects=tuple(projects),
        waiting=waiting,
        unmatched=tuple(unmatched),
        behind=behind,
        hours_through=hours_through,
    )


def _blank_identifiers(text: str) -> str:
    """Replace every identifier-shaped token carrying a digit with spaces of the same length, so
    offsets into the blanked text still point at the same characters of the original."""

    def blank(match: re.Match[str]) -> str:
        token = match.group()
        return " " * len(token) if any(ch.isdigit() for ch in token) else token

    return IDENTIFIER_RE.sub(blank, text)


def unsupported_figures(draft: str, figures: Sequence[Figure]) -> tuple[str, ...]:
    """Every numeric token in `draft` that is not, character for character, one of `figures`.

    In reading order, repeats included, so a draft that leans on one invented number three times
    shows all three. Dates are matched first and checked whole; identifiers are then blanked; what
    is left is scanned for numbers.

    This is the cheap half of the argument for letting one model call write a report nobody
    re-derives by hand. It is a pass or a fail, never a judgment. What it cannot do is tell
    whether a real figure is sitting next to the claim it belongs to, which is why a person still
    reads the report.
    """
    allowed = {figure.text for figure in figures}
    scanned = _blank_identifiers(DATE_RE.sub(lambda m: " " * len(m.group()), draft))
    hits = [(m.start(), m.group()) for m in DATE_RE.finditer(draft)]
    hits += [(m.start(), m.group()) for m in NUMBER_RE.finditer(scanned)]
    return tuple(token for _, token in sorted(hits) if token not in allowed)


def missing_required(draft: str, figures: Sequence[Figure]) -> tuple[Figure, ...]:
    """The must-say figures whose text never appears in the draft.

    The other direction from `unsupported_figures`, and the one a standing report needs: a draft
    can be entirely truthful and still be useless because it left out the only line anybody had to
    act on. Only figures of at least `MIN_CHECKABLE` characters are tested; the rest are in
    `Report.confirm_by_eye` for the person reading it.
    """
    return tuple(f for f in required_figures(figures) if f.text not in draft)


def _figures_block(figures: Sequence[Figure]) -> str:
    return "\n".join(
        f"- {f.label}: {f.text}" + (" (must say)" if f.must_say else "") for f in figures
    )


@dataclass(frozen=True)
class Report:
    """What `run` hands back. `text` is the model's draft whichever way the checks came out:
    deciding what happens to a draft that failed one is a person's job, so the failures are named
    rather than the draft being discarded or quietly patched."""

    text: str
    figures: tuple[Figure, ...]
    unsupported: tuple[str, ...]
    missing: tuple[Figure, ...]
    confirm_by_eye: tuple[Figure, ...]
    assembly: Assembly

    @property
    def ok(self) -> bool:
        return not self.unsupported and not self.missing


def run(
    notes: str,
    model: Model,
    tracer: Tracer,
    *,
    sources: Sequence[Source] = SOURCES,
    since: str = SINCE,
    report_date: str = REPORT_DATE,
    max_tokens: int = 700,
) -> Report:
    """One week of the standing report. One model call, whatever happened in the week.

    `notes` is the free text the person running the report added. It is appended to the prompt
    and never reaches either check, because it never contributes a figure of its own.
    """
    assembly = compute_figures(sources, since=since, report_date=report_date)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Pull the three sources and reconcile the project names",
        detail=(
            f"{len(assembly.projects)} projects; "
            f"{len(assembly.unmatched)} name(s) no list recognized; "
            f"{len(assembly.behind)} source(s) behind the report date"
        ),
    )
    tracer.record(
        kind="code",
        decided_by="code",
        title="Compute every figure the report may quote",
        detail=(
            f"{len(assembly.figures)} figures, "
            f"{len(required_figures(assembly.figures))} of them must-say and checkable, "
            f"{len(short_must_say(assembly.figures))} must-say but too short to check"
        ),
    )

    user_parts = [f"Figures (use only these numbers, exactly as written):\n{_figures_block(assembly.figures)}"]
    if notes and notes.strip():
        user_parts.append(f"Note from the person running the report: {notes.strip()}")
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content="\n\n".join(user_parts)),
    ]
    tracer.record(
        kind="code",
        decided_by="code",
        title="Build the prompt from the figures and the week's note",
        detail=f"{len(assembly.figures)} figures, note of {len(notes.strip())} characters",
    )

    completion = model.complete(messages, max_tokens=max_tokens)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model to write the report around the figures",
        detail=completion.text[:200],
        tokens_in=completion.tokens_in,
        tokens_out=completion.tokens_out,
        ms=completion.ms,
    )

    unsupported = unsupported_figures(completion.text, assembly.figures)
    missing = missing_required(completion.text, assembly.figures)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Check the draft against the figures, both directions",
        detail=(
            ("every number is supported" if not unsupported else f"unsupported: {', '.join(unsupported)}")
            + "; "
            + ("nothing must-say was left out" if not missing else f"left out: {', '.join(f.label for f in missing)}")
        ),
    )
    return Report(
        text=completion.text,
        figures=assembly.figures,
        unsupported=unsupported,
        missing=missing,
        confirm_by_eye=short_must_say(assembly.figures),
        assembly=assembly,
    )
