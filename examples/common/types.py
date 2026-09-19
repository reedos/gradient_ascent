"""The return type every example's `run` function shares."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Answer:
    """What an example hands back for one question."""

    text: str
    citations: list[str] = field(default_factory=list)
