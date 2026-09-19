"""Records one example run as an ordered list of steps and writes `trace.json`.

`decided_by` is the central claim of the site, so it has one definition and no exceptions:

    A step is `decided_by: "model"` when the model's output, not the program, selected which
    action happens next. That is: choosing to call a tool, choosing which tool, choosing its
    arguments, or choosing to stop. Everything else is `decided_by: "code"`.

Three consequences worth stating, because each one is easy to get wrong:

- **Calling the model is not a model decision.** Levels 1, 2 and 3 call a model, sometimes more
  than once, but the code decided every one of those calls would happen, in that order. Their
  steps are `kind: "model"` (a model ran) and `decided_by: "code"` (the program chose to run it).
  The two fields answer different questions and must not be conflated.
- **Returning a tool result to the model is always `code`.** So is forcing a final answer when a
  cap is reached, and so is parsing, filtering or checking whatever the model returned.
- **Declining to call a tool is a model decision.** At level 4 the program offers the model a
  choice between calling a tool and answering directly; whichever the model's output selects, the
  model made the selection. This is the same decision as the stop at level 5, and it is scored
  the same way. Otherwise a model that refuses every tool would look, in the trace, exactly like
  a level-3 workflow, and the site's own measurement would hide the difference.

By level, on the examples here: levels 0 to 3 record only `code` steps; level 4 records
exactly one `model` step per run, either the tool call or the decision to answer without one;
level 5 records a `model` step for every tool call plus one for the stop, unless a cap cut the
run short first, in which case the forced final answer is a `code` step.

The edge into a step is drawn dashed when the model chose the transition and solid when code
did, which `record` sets automatically from `decided_by` unless `edge` is given explicitly.
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

StepKind = Literal["code", "model"]
DecidedBy = Literal["code", "model"]

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Step:
    i: int
    kind: StepKind
    decided_by: DecidedBy
    title: str
    detail: str
    tokens_in: int
    tokens_out: int
    ms: float
    edge: str  # "solid" | "dashed"


def git_commit(repo_root: Path = REPO_ROOT) -> str | None:
    """The short commit hash of the working tree, or None outside a git repo (or if git is
    unavailable). A trace with no commit is still valid; the field is best-effort provenance."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


@dataclass
class Tracer:
    """Collects steps during one example run, then writes them with a header via `write`."""

    example: str
    level: int
    model_id: str
    stub: bool = False  # a stub run: recorded for testing, never something the site may show
    _steps: list[Step] = field(default_factory=list, init=False, repr=False)

    def record(
        self,
        *,
        kind: StepKind,
        decided_by: DecidedBy,
        title: str,
        detail: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        ms: float = 0.0,
        edge: str | None = None,
    ) -> Step:
        step = Step(
            i=len(self._steps),
            kind=kind,
            decided_by=decided_by,
            title=title,
            detail=detail,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            ms=ms,
            edge=edge or ("dashed" if decided_by == "model" else "solid"),
        )
        self._steps.append(step)
        return step

    @property
    def steps(self) -> list[Step]:
        return list(self._steps)

    def model_decided_count(self) -> int:
        """How many steps the model, not the program, chose. See this module's definition: the
        number the site charts against level, and the number that must stay zero below level 4."""
        return sum(1 for s in self._steps if s.decided_by == "model")

    def tokens_in_total(self) -> int:
        return sum(s.tokens_in for s in self._steps)

    def tokens_out_total(self) -> int:
        return sum(s.tokens_out for s in self._steps)

    def to_dict(self, *, repo_root: Path = REPO_ROOT) -> dict:
        return {
            "example": self.example,
            "level": self.level,
            "model_id": self.model_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "illustrative": False,
            "stub": self.stub,
            "commit": git_commit(repo_root),
            "model_decided_steps": self.model_decided_count(),
            "steps": [asdict(s) for s in self._steps],
        }

    def write(self, path: Path, *, repo_root: Path = REPO_ROOT) -> dict:
        """Write `trace.json` to `path` (LF, UTF-8, no BOM) and return what was written."""
        payload = self.to_dict(repo_root=repo_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        return payload
