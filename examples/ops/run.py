"""Track: ops. Reads trace files in the shape `examples/common/trace.py` writes, and a price
table supplied by the caller, and reports estimated cost and latency per question and per level.

No price is built into this module. A maker's per-token price is specific to one model, changes
without notice, and differs enough between makers that hard-coding one here would go stale
silently and read as this site's own claim about a real price. The caller passes a `PriceTable`
built from whatever list it wants measured against, dated and attributed by the caller, and the
report names any model id it found in a trace but not in that table rather than pricing it as
free.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from examples.common.model import Model
from examples.common.trace import Tracer

LEVEL = 1  # ops is a track technique, not a rung on the ladder; see content/taxonomy.json

PriceTable = dict[str, tuple[float, float]]  # model_id -> (usd per 1k tokens in, usd per 1k tokens out)


@dataclass(frozen=True)
class QuestionCost:
    """One trace file's totals: tokens, wall time, and estimated cost. `usd` is `None` when the
    trace's model id has no entry in the price table, not zero -- an unpriced call costs
    something; this just cannot say how much."""

    example: str
    level: int
    model_id: str
    tokens_in: int
    tokens_out: int
    ms: float
    usd: float | None


@dataclass(frozen=True)
class LevelSummary:
    level: int
    n: int
    mean_usd: float | None
    mean_ms: float


@dataclass(frozen=True)
class Report:
    per_question: list[QuestionCost]
    per_level: list[LevelSummary]
    unpriced_models: list[str]


def load_trace(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_price_table(path: Path) -> PriceTable:
    """A price table file: `{"<model_id>": {"in_per_1k": ..., "out_per_1k": ...}, ...}`, USD per
    1,000 tokens. The caller states where these numbers came from; nothing here checks that."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {model_id: (float(entry["in_per_1k"]), float(entry["out_per_1k"])) for model_id, entry in raw.items()}


def _cost(model_id: str, tokens_in: int, tokens_out: int, prices: PriceTable) -> float | None:
    price = prices.get(model_id)
    if price is None:
        return None
    per_in, per_out = price
    return round(tokens_in / 1000 * per_in + tokens_out / 1000 * per_out, 6)


def cost_for_trace(trace: dict, prices: PriceTable) -> QuestionCost:
    tokens_in = sum(step["tokens_in"] for step in trace["steps"])
    tokens_out = sum(step["tokens_out"] for step in trace["steps"])
    ms = sum(step["ms"] for step in trace["steps"])
    usd = _cost(trace["model_id"], tokens_in, tokens_out, prices)
    return QuestionCost(
        example=trace["example"],
        level=trace["level"],
        model_id=trace["model_id"],
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        ms=ms,
        usd=usd,
    )


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def summarize_by_level(costs: list[QuestionCost]) -> list[LevelSummary]:
    summaries = []
    for level in sorted({c.level for c in costs}):
        subset = [c for c in costs if c.level == level]
        priced = [c.usd for c in subset if c.usd is not None]
        summaries.append(
            LevelSummary(
                level=level,
                n=len(subset),
                mean_usd=_mean(priced) if priced else None,
                mean_ms=_mean([c.ms for c in subset]),
            )
        )
    return summaries


def build_report(trace_paths: list[Path], prices: PriceTable) -> Report:
    costs = [cost_for_trace(load_trace(p), prices) for p in trace_paths]
    unpriced = sorted({c.model_id for c in costs if c.usd is None})
    return Report(per_question=costs, per_level=summarize_by_level(costs), unpriced_models=unpriced)


# Invented numbers, deliberately round and deliberately not near any maker's published rate, so
# nothing built from this table can be mistaken for a real price or quoted as one. See the ops
# page for where a real table comes from and how it would be dated and attributed. Kept separate
# from `examples.ops.__main__`'s own `DEMO_PRICES` -- same idea, not the same object, so editing
# one to try something does not silently change what `run` below records.
_RECORDING_PRICES: PriceTable = {"stub-chat-1": (0.001, 0.002), "stub-rag-1": (0.004, 0.008)}


def run(text: str, model: Model, tracer: Tracer) -> Report:
    """Recordable entry point for `record_trace.py`. Calls no model -- `model` is accepted only
    to fit the shared (text, model, tracer) convention every recordable example follows -- and
    ignores `text`: there is no question for a cost report to route through. Builds two small
    traces in memory with a real `Tracer` (the same shape `python -m examples.ops --demo` writes
    to disk), prices them against a demo table, and records the load and the per-level
    computation as `code` steps."""
    del text, model
    chat = Tracer(example="chat", level=1, model_id="stub-chat-1")
    chat.record(kind="model", decided_by="code", title="Ask the model", tokens_in=40, tokens_out=90, ms=650.0)
    tracer.record(kind="code", decided_by="code", title="Load trace: chat", detail="1 model step")

    rag = Tracer(example="rag", level=2, model_id="stub-rag-1")
    rag.record(kind="code", decided_by="code", title="Embed and retrieve top-k", tokens_in=0, tokens_out=0, ms=30.0)
    rag.record(
        kind="model", decided_by="code", title="Ask the model for a cited answer", tokens_in=1850, tokens_out=64, ms=2100.0
    )
    tracer.record(kind="code", decided_by="code", title="Load trace: rag", detail="2 steps")

    costs = [cost_for_trace(chat.to_dict(), _RECORDING_PRICES), cost_for_trace(rag.to_dict(), _RECORDING_PRICES)]
    unpriced = sorted({c.model_id for c in costs if c.usd is None})
    report = Report(per_question=costs, per_level=summarize_by_level(costs), unpriced_models=unpriced)
    tracer.record(
        kind="code",
        decided_by="code",
        title="Summarize per level",
        detail=f"{len(report.per_level)} level(s), {len(report.unpriced_models)} unpriced model(s)",
    )
    return report
