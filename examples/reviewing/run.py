"""Track: operator craft / reviewing. One review surface: given a drafted answer -- its text and
the citations it names -- and the documents those citations point into, report which figures the
answer states are not present in any section it cites, and which citations carry none of them.

This is a presence check, not a truth check. It says whether a number the answer states appears
in the text it points at; it does not say the section supports the claim, that the right sources
were chosen, or that the answer is complete. A person still does all of that. What it removes is
the one part of review that is pure clerical work -- reading a figure, opening a citation, and
looking for that figure -- which is exactly the part a reviewer stops doing first once a long run
of answers has all been fine.

Two rules keep it from crying wolf, since a checker that flags everything gets ignored the same
way an approval step does:

- Figures are compared as values, not as strings. `$1,200`, `1200` and `1,200.00` are one figure;
  `52` is not a match for `1152`, which a substring search would have accepted.
- An identifier is not a figure. `HLV-2205`, `DW300`, `v2.1` and `dw300-manual#3` state no
  quantity, so nothing is claimed about them and no section is asked to contain them.

Known limits, each pinned by a test in `tests/test_example_reviewing.py`: units are dropped, so
`3.2 gallons` matches a section that says `3.2 kg`; a date written in prose is read as its
separate numbers, so it will not match the same date written `2026-09-18`.

LEVEL is 2, the level citations first appear at (see `examples/rag`). Nothing here calls a model,
so every step is `decided_by: "code"`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from evals.corpus import Section
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 2

# "80%", "80 %" and "80 percent" are one figure written three ways; fold them together first.
_PERCENT_RE = re.compile(r"(\d)\s*(?:%|per\s?cent\b)", re.IGNORECASE)
# A full ISO date is one figure, not three: 2026-09-18 is not 2026, 9 and 18.
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
# A dash between two digits separates a range (18-24); a leading one is a minus sign (-20).
_RANGE_RE = re.compile(r"(?<=\d)[-–—](?=\d)")
# One figure: optional minus, optional currency mark, digits with optional group separators, an
# optional decimal part, an optional percent, and an optional unit written against the digits
# (120V, 52dBA, 120°F). A letter BEFORE the digits makes it an identifier instead, not a figure.
_FIGURE_RE = re.compile(r"([-−]?)[$£€¥]?(\d[\d,]*(?:\.\d+)?)(%?)[A-Za-z°/]*\Z")
_TRIM = "\"'`([{)]}.,;:!?“”‘’"


def _figure(token: str) -> str | None:
    """One token as a comparable figure, or None if it states no quantity."""
    if "#" in token:
        return None
    if _ISO_DATE_RE.match(token):
        return token
    match = _FIGURE_RE.match(token)
    if match is None:
        return None
    sign, digits, percent = match.groups()
    whole, _, fraction = digits.replace(",", "").partition(".")
    whole = whole.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    value = f"{whole}.{fraction}" if fraction else whole
    return f"{'-' if sign else ''}{value}{percent}"


def figures_in(text: str) -> list[str]:
    """Every figure the text states, in one canonical spelling each, sorted and deduplicated."""
    figures = []
    for word in _PERCENT_RE.sub(r"\1%", text).split():
        word = word.strip(_TRIM)
        parts = [word] if _ISO_DATE_RE.match(word) else _RANGE_RE.split(word)
        for part in parts:
            figure = _figure(part)
            if figure is not None:
                figures.append(figure)
    return sorted(set(figures))


@dataclass(frozen=True)
class Flag:
    """One thing for a person to look at: a citation, or a figure the citations do not carry."""

    subject: str
    reason: str


@dataclass(frozen=True)
class ReviewReport:
    figures_claimed: list[str]
    checked: list[str]
    flags: list[Flag]

    @property
    def clean(self) -> bool:
        return not self.flags


def run(answer: Answer, sections: dict[str, Section], tracer: Tracer) -> ReviewReport:
    figures = figures_in(answer.text)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Read the figures the answer states",
        detail=", ".join(figures) or "none",
    )

    flags: list[Flag] = []
    found_somewhere: set[str] = set()
    for citation in answer.citations:
        section = sections.get(citation)
        if section is None:
            tracer.record(
                kind="code", decided_by="code", title=f"Open {citation}", detail="not in the corpus"
            )
            flags.append(Flag(citation, "cited section does not exist"))
            continue
        here = sorted(set(figures) & set(figures_in(section.text)))
        found_somewhere.update(here)
        tracer.record(
            kind="code",
            decided_by="code",
            title=f"Open {citation}",
            detail=f"{section.title}: {', '.join(here) or 'no claimed figure'}",
        )
        if figures and not here:
            flags.append(Flag(citation, "section carries none of the answer's figures"))

    for figure in figures:
        if figure not in found_somewhere:
            flags.append(Flag(figure, "figure appears in no cited section"))

    tracer.record(
        kind="code",
        decided_by="code",
        title="Report",
        detail=f"{len(flags)} thing(s) to look at across {len(answer.citations)} citation(s)",
    )
    return ReviewReport(figures_claimed=figures, checked=list(answer.citations), flags=flags)
