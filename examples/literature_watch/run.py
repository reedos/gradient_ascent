"""Two job shapes joined: a watch that finds what is new, and a read that summarizes each new
item. The seam between them is the point of this example.

The watch half calls no model at all. A fixed list of sources is queried, every record dated
before the last run is dropped, and every record whose title matches one already reported is
dropped as well. That is a comparison and a set difference, so it is level 0, and it is where
"what is new" is decided. The read half is one model call per surviving record, with the record's
title and abstract in front of it and nothing else to look up, so it is level 1. Nothing here
chooses what to read next, follows a reference, or searches a term it thought of itself; that
would be level 5 research, and this is not it.

One rule holds the join together: **the citation is written by code, from the source record, and
never by the model.** The schema the model answers in has no field for a link, an author or a
year, so there is nowhere for it to put one, and `_cite` builds the line from the record the
summary came from. A model that writes a link into its prose anyway is flagged by `_flag_links`
rather than quietly published, because a link inside a digest entry reads as a citation and the
only citation here is the record's own.

Three things the watch half reports that a reader would otherwise have to notice for themselves:
a source that returned nothing at all (silence is not the same as nothing new), how many records
were dropped as already reported, and how many were dropped as too old. See
`tests/test_example_literature_watch.py` and the recipe page's "How it fails" section, which say
which half each failure belongs to.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 1
MAX_RETRIES = 1

SUMMARY_FIELDS = ("what_is_new", "why_it_matters", "read_if")
SCHEMA = {
    "type": "object",
    "properties": {
        "what_is_new": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "read_if": {"type": "string"},
    },
    "required": list(SUMMARY_FIELDS),
}
SYSTEM_PROMPT = (
    "You summarize one item for a weekly reading digest. Reply as JSON matching this schema, "
    "with no other text and no markdown fences: " + json.dumps(SCHEMA) + ". "
    "what_is_new: one sentence on what this work reports that earlier work did not. "
    "why_it_matters: one sentence on what it would change for someone working on this topic. "
    "read_if: one sentence naming who should open the full text. "
    "Use only the title and abstract given to you. Do not write a citation, a link, an author "
    "name or a year: the digest attaches the citation itself from its own records. If the "
    "abstract does not say something, do not supply it."
)


@dataclass(frozen=True)
class Record:
    """One item as a source listed it. Every field on the citation line comes from here."""

    id: str
    title: str
    authors: str
    venue: str
    date: str  # ISO 8601, the date the source listed it
    url: str
    abstract: str


#: The three sources this watch is pointed at, invented. Nothing here reaches the network: a real
#: watch would swap these lists for whatever each source's own feed or query returns and change
#: nothing below. The set is arranged to exercise all four outcomes the watch half reports: two
#: records that are genuinely new, one that is last week's preprint in its journal version and so
#: is not new, two dated before the last run, and one source that answers with nothing at all.
SOURCES: dict[str, tuple[Record, ...]] = {
    "preprint-feed": (
        Record(
            id="pp-2291",
            title="Street tree canopy and nighttime cooling in three mid-sized cities",
            authors="Halloran, D. and Vetsch, R.",
            venue="Preprint server, urban climate section",
            date="2026-09-10",
            url="https://example.org/preprints/pp-2291",
            abstract=(
                "We paired 41 fixed temperature loggers with per-street canopy cover measured from "
                "aerial imagery across three mid-sized cities over two summers."
            ),
        ),
        Record(
            id="pp-2304",
            title="A low-cost logger network for street-level heat, two years on",
            authors="Ferrante, N., Okoye, B. and Lindqvist, S.",
            venue="Preprint server, instrumentation section",
            date="2026-09-17",
            url="https://example.org/preprints/pp-2304",
            abstract=(
                "Two years of operation of 120 self-built street-level temperature loggers, "
                "including the failure record: 14 units lost to water ingress, 9 to battery "
                "swelling in direct sun, and a calibration drift of 0.2 C per year in the "
                "uncorrected units. We publish the enclosure revision that ended the water "
                "failures and the field calibration procedure we now run twice a year."
            ),
        ),
        Record(
            id="pp-2260",
            title="Pavement albedo trials on residential streets",
            authors="Sarraf, L.",
            venue="Preprint server, urban climate section",
            date="2026-09-02",
            url="https://example.org/preprints/pp-2260",
            abstract=(
                "A trial of three reflective pavement coatings on eleven residential blocks, "
                "reporting surface temperature, air temperature at 1.5 m, and resident survey "
                "responses after one summer."
            ),
        ),
    ),
    "journal-contents": (
        Record(
            id="j-8814",
            title="Street Tree Canopy and Nighttime Cooling in Three Mid-Sized Cities",
            authors="Halloran, D. and Vetsch, R.",
            venue="Journal of Urban Microclimate 14(3)",
            date="2026-09-18",
            url="https://example.org/journals/jum/14/3/8814",
            abstract=(
                "The peer-reviewed version of the three-city canopy and nighttime cooling study, "
                "with one additional city-year and an appendix on logger siting."
            ),
        ),
        Record(
            id="j-8822",
            title="Shade and pedestrian route choice on a hot afternoon",
            authors="Berthold, K. and Nwachukwu, A.",
            venue="Journal of Urban Microclimate 14(3)",
            date="2026-09-18",
            url="https://example.org/journals/jum/14/3/8822",
            abstract=(
                "Anonymized route traces from 2,800 walking trips in one city, matched against a "
                "modeled shade map at the hour each trip was taken. On afternoons above 31 C, "
                "trips took routes that were on average 6 percent longer and 19 percent more "
                "shaded than the shortest path; below 26 C the difference disappeared."
            ),
        ),
    ),
    "city-open-data-notices": (),
}

#: What last week's digest reported, as the same normalized titles the watch compares against.
#: A real watch keeps this in a file or a table between runs; it is passed in here so the test
#: suite can run the same code twice with different history and no state on disk.
SAMPLE_SEEN: tuple[str, ...] = (
    "street tree canopy and nighttime cooling in three mid sized cities",
)

#: The date the watch last ran. `run` takes it as its one positional input.
SAMPLE_INPUT = "2026-09-15"

_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")
_LINK_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def title_key(title: str) -> str:
    """The key the watch compares titles on: lowercased, punctuation dropped, spaces collapsed.

    A preprint and its journal version carry different ids, different dates and different
    capitalization, and are the same work. Comparing ids would report it twice; comparing this
    key reports it once. It is also the weakness of the watch half: a work that is retitled
    between versions is a new key and comes through again. See the recipe page.
    """
    return _WS_RE.sub(" ", _PUNCT_RE.sub(" ", title.lower())).strip()


@dataclass(frozen=True)
class SourceReport:
    """What one source did this run. `silent` is the one a reader must not miss: a source that
    returned nothing at all looks exactly like a quiet week in a digest that only lists items."""

    source: str
    returned: int
    fresh: int
    new: int

    @property
    def silent(self) -> bool:
        return self.returned == 0


@dataclass(frozen=True)
class DigestItem:
    record: Record
    what_is_new: str
    why_it_matters: str
    read_if: str
    citation: str
    #: Summary fields that carried something shaped like a link. Reported, never hidden.
    flagged: tuple[str, ...] = ()


@dataclass(frozen=True)
class Digest:
    since: str
    items: tuple[DigestItem, ...]
    sources: tuple[SourceReport, ...]
    already_reported: tuple[str, ...]
    failed: tuple[str, ...] = ()
    seen_after: tuple[str, ...] = field(default_factory=tuple)

    @property
    def text(self) -> str:
        lines = [f"New since {self.since}: {len(self.items)} item(s)."]
        for it in self.items:
            lines.append("")
            lines.append(f"  {it.record.title}")
            lines.append(f"    {it.citation}")
            lines.append(f"    New: {it.what_is_new}")
            lines.append(f"    Matters: {it.why_it_matters}")
            lines.append(f"    Read if: {it.read_if}")
            if it.flagged:
                lines.append(f"    Check by hand: the model wrote a link in {', '.join(it.flagged)}")
        lines.append("")
        lines.append("Sources:")
        for s in self.sources:
            note = " (returned nothing at all)" if s.silent else ""
            lines.append(f"  {s.source}: {s.returned} listed, {s.fresh} since the last run, {s.new} new{note}")
        if self.already_reported:
            lines.append(f"Already reported, not repeated: {len(self.already_reported)}")
        if self.failed:
            lines.append(f"Could not summarize: {', '.join(self.failed)}")
        return "\n".join(lines)

    @property
    def citations(self) -> list[str]:
        return [it.citation for it in self.items]


def _cite(record: Record) -> str:
    """The citation line, built from the record. The model never writes one and has no field to
    write it in; this is the only function on this path that produces one."""
    return f"{record.authors} ({record.date[:4]}). {record.title}. {record.venue}. {record.url}"


def _flag_links(summary: dict) -> tuple[str, ...]:
    """Summary fields carrying something shaped like a link. A link in a digest entry reads as a
    citation, and the citation here is `_cite`'s alone."""
    return tuple(f for f in SUMMARY_FIELDS if _LINK_RE.search(str(summary.get(f, ""))))


def _select_new(
    sources: dict[str, tuple[Record, ...]], since: str, seen: set[str]
) -> tuple[list[Record], list[SourceReport], list[str]]:
    """The watch half, whole. No model, no judgment: a date comparison and a set difference.

    Returns the records to summarize, one report per source, and the titles that were dropped
    because a previous run already reported them.
    """
    new: list[Record] = []
    reports: list[SourceReport] = []
    repeats: list[str] = []
    for name in sorted(sources):
        records = sources[name]
        fresh = [r for r in records if r.date >= since]
        picked: list[Record] = []
        for record in fresh:
            key = title_key(record.title)
            if key in seen:
                repeats.append(record.title)
                continue
            seen.add(key)
            picked.append(record)
        new.extend(picked)
        reports.append(SourceReport(source=name, returned=len(records), fresh=len(fresh), new=len(picked)))
    return new, reports, repeats


def _validate(summary: dict) -> list[str]:
    problems = [f"missing field: {f}" for f in SUMMARY_FIELDS if f not in summary]
    problems += [f"{f} is not a string" for f in SUMMARY_FIELDS if f in summary and not isinstance(summary[f], str)]
    problems += [f"{f} is empty" for f in SUMMARY_FIELDS if isinstance(summary.get(f), str) and not summary[f].strip()]
    return problems


def _summarize(record: Record, model: Model, tracer: Tracer, *, max_tokens: int) -> dict | None:
    """The read half, for one record: one call, a fixed schema, one retry on a reply that does
    not validate. Everything the summary needs is in the two fields sent."""
    user = f"Title: {record.title}\n\nAbstract: {record.abstract}"
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=user)]
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=SCHEMA, max_tokens=max_tokens)
        tracer.record(
            kind="model",
            decided_by="code",
            title=f"Summarize {record.id}" if attempt == 0 else f"Ask again for {record.id}",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            summary = json.loads(completion.text)
            problems = _validate(summary) if isinstance(summary, dict) else ["reply is not an object"]
        except json.JSONDecodeError as exc:
            summary, problems = None, [f"invalid JSON: {exc}"]
        tracer.record(
            kind="code",
            decided_by="code",
            title=f"Validate the summary of {record.id}",
            detail="; ".join(problems) or "valid",
        )
        if not problems:
            return summary
        if attempt < MAX_RETRIES:
            messages.append(
                Message(
                    role="user",
                    content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only.",
                )
            )
    return None


def run(
    since: str,
    model: Model,
    tracer: Tracer,
    *,
    seen: tuple[str, ...] = SAMPLE_SEEN,
    sources: dict[str, tuple[Record, ...]] | None = None,
    max_tokens: int = 320,
) -> Digest:
    """One week of the watch. `since` is the date the watch last ran; `seen` is the normalized
    titles it has already reported."""
    catalog = SOURCES if sources is None else sources
    seen_keys = {title_key(t) for t in seen}
    before = len(seen_keys)

    new, reports, repeats = _select_new(catalog, since, seen_keys)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Work out what is new",
        detail=(
            f"{sum(r.returned for r in reports)} listed across {len(reports)} source(s); "
            f"{len(new)} new since {since}; {len(repeats)} already reported; "
            f"{sum(1 for r in reports if r.silent)} source(s) returned nothing"
        ),
    )

    items: list[DigestItem] = []
    failed: list[str] = []
    for record in new:
        summary = _summarize(record, model, tracer, max_tokens=max_tokens)
        if summary is None:
            failed.append(record.id)
            continue
        flagged = _flag_links(summary)
        items.append(
            DigestItem(
                record=record,
                what_is_new=summary["what_is_new"],
                why_it_matters=summary["why_it_matters"],
                read_if=summary["read_if"],
                citation=_cite(record),
                flagged=flagged,
            )
        )
        tracer.record(
            kind="code",
            decided_by="code",
            title=f"Attach the citation for {record.id}",
            detail=_cite(record) + (f" [flagged: {', '.join(flagged)}]" if flagged else ""),
        )

    tracer.record(
        kind="code",
        decided_by="code",
        title="Assemble the digest for a person to read",
        detail=f"{len(items)} item(s), {len(failed)} could not be summarized, {len(seen_keys) - before} title(s) added to the history",
    )
    return Digest(
        since=since,
        items=tuple(items),
        sources=tuple(reports),
        already_reported=tuple(repeats),
        failed=tuple(failed),
        seen_after=tuple(sorted(seen_keys)),
    )
