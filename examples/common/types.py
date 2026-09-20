"""The return type every example's `run` function shares."""
from __future__ import annotations

from dataclasses import dataclass, field
import re


CITE_RE = re.compile(r"[a-z0-9][a-z0-9_-]*#\d+")
_CITATION = re.compile(
    r"(?<![a-z0-9_-])([a-z0-9][a-z0-9_-]*)(?:\.md)?"
    r"(?:\s*[#§]\s*|[\s,]+sect?(?:ion)?\.?\s*)(\d+)\b",
    re.IGNORECASE,
)


def cited_sources(text: str) -> list[str]:
    """Unique file#section citations actually present in the final answer."""
    return sorted({f"{name.lower()}#{section}" for name, section in _CITATION.findall(text)})


@dataclass(frozen=True)
class Answer:
    """What an example hands back for one question."""

    text: str
    citations: list[str] = field(default_factory=list)
    # Sources supplied to the answering workflow, independent of what its answer cites.
    retrieved_sources: list[str] = field(default_factory=list)

    @classmethod
    def from_text(cls, text: str, retrieved_sources: list[str] | None = None) -> Answer:
        return cls(text, cited_sources(text), sorted(set(retrieved_sources or [])))
