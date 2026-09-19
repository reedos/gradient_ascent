"""Tests for examples/ops: a cost and latency estimator over trace files (the shape
examples/common/trace.py writes) and a caller-supplied price table. No prices are real here --
made up on purpose, the way the technique's own note requires."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.ops.run import (  # noqa: E402
    LEVEL,
    build_report,
    cost_for_trace,
    load_price_table,
    load_trace,
    run,
    summarize_by_level,
)

# Made-up prices for testing only: not any maker's published rate.
FAKE_PRICES = {"fake-small": (1.0, 2.0), "fake-big": (10.0, 20.0)}


def _trace_dict(*, example: str, level: int, model_id: str, tokens_in: int, tokens_out: int, ms: float) -> dict:
    tracer = Tracer(example=example, level=level, model_id=model_id)
    tracer.record(kind="model", decided_by="code", title="call", tokens_in=tokens_in, tokens_out=tokens_out, ms=ms)
    return tracer.to_dict()


class OpsExampleTests(unittest.TestCase):
    def test_cost_for_trace_multiplies_tokens_by_the_price_table(self) -> None:
        trace = _trace_dict(example="chat", level=1, model_id="fake-small", tokens_in=1000, tokens_out=1000, ms=650.0)
        cost = cost_for_trace(trace, FAKE_PRICES)
        # 1000 in tokens = 1.0 * $1.00, 1000 out tokens = 1.0 * $2.00 -> $3.00
        self.assertAlmostEqual(cost.usd, 3.0)
        self.assertEqual(cost.level, 1)
        self.assertEqual(cost.tokens_in, 1000)

    def test_a_trace_summed_over_several_steps_is_priced_on_the_total(self) -> None:
        tracer = Tracer(example="rag", level=2, model_id="fake-small")
        tracer.record(kind="code", decided_by="code", title="retrieve", tokens_in=0, tokens_out=0, ms=10.0)
        tracer.record(kind="model", decided_by="code", title="answer", tokens_in=500, tokens_out=500, ms=200.0)
        cost = cost_for_trace(tracer.to_dict(), FAKE_PRICES)
        self.assertEqual(cost.tokens_in, 500)
        self.assertEqual(cost.tokens_out, 500)
        self.assertAlmostEqual(cost.ms, 210.0)
        self.assertAlmostEqual(cost.usd, 0.5 * 1.0 + 0.5 * 2.0)

    def test_an_unpriced_model_id_reports_usd_none_not_zero(self) -> None:
        trace = _trace_dict(example="chat", level=1, model_id="unknown-model", tokens_in=100, tokens_out=100, ms=50.0)
        cost = cost_for_trace(trace, FAKE_PRICES)
        self.assertIsNone(cost.usd)

    def test_summarize_by_level_groups_and_averages_correctly(self) -> None:
        costs = [
            cost_for_trace(_trace_dict(example="chat", level=1, model_id="fake-small", tokens_in=1000, tokens_out=0, ms=100.0), FAKE_PRICES),
            cost_for_trace(_trace_dict(example="chat", level=1, model_id="fake-small", tokens_in=3000, tokens_out=0, ms=300.0), FAKE_PRICES),
            cost_for_trace(_trace_dict(example="rag", level=2, model_id="fake-big", tokens_in=1000, tokens_out=0, ms=500.0), FAKE_PRICES),
        ]
        summaries = {s.level: s for s in summarize_by_level(costs)}
        self.assertEqual(summaries[1].n, 2)
        self.assertAlmostEqual(summaries[1].mean_usd, (1.0 + 3.0) / 2)  # $1 and $3 -> mean $2
        self.assertAlmostEqual(summaries[1].mean_ms, 200.0)
        self.assertEqual(summaries[2].n, 1)
        self.assertAlmostEqual(summaries[2].mean_usd, 10.0)  # 1000 in tokens @ $10/1k

    def test_level_summary_mean_usd_is_none_when_nothing_in_that_level_is_priced(self) -> None:
        costs = [cost_for_trace(_trace_dict(example="chat", level=1, model_id="unknown", tokens_in=100, tokens_out=100, ms=10.0), FAKE_PRICES)]
        summaries = summarize_by_level(costs)
        self.assertEqual(len(summaries), 1)
        self.assertIsNone(summaries[0].mean_usd)
        self.assertAlmostEqual(summaries[0].mean_ms, 10.0)  # latency is still known even when price is not

    def test_load_price_table_reads_the_documented_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prices.json"
            path.write_text(json.dumps({"m1": {"in_per_1k": 0.5, "out_per_1k": 1.5}}), encoding="utf-8")
            table = load_price_table(path)
            self.assertEqual(table, {"m1": (0.5, 1.5)})

    def test_run_reads_real_trace_files_written_by_tracer_and_reports_unpriced_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            t1 = Tracer(example="chat", level=1, model_id="fake-small")
            t1.record(kind="model", decided_by="code", title="call", tokens_in=1000, tokens_out=1000, ms=100.0)
            path1 = out_dir / "a.json"
            t1.write(path1)

            t2 = Tracer(example="rag", level=2, model_id="totally-unpriced")
            t2.record(kind="model", decided_by="code", title="call", tokens_in=100, tokens_out=100, ms=50.0)
            path2 = out_dir / "b.json"
            t2.write(path2)

            report = build_report([path1, path2], FAKE_PRICES)
            self.assertEqual(len(report.per_question), 2)
            self.assertEqual(report.unpriced_models, ["totally-unpriced"])
            self.assertEqual({s.level for s in report.per_level}, {1, 2})

    def test_load_trace_reads_a_real_tracer_written_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.json"
            tracer = Tracer(example="chat", level=1, model_id="fake-small")
            tracer.record(kind="model", decided_by="code", title="call", tokens_in=10, tokens_out=20, ms=5.0)
            tracer.write(path)
            trace = load_trace(path)
            self.assertEqual(trace["example"], "chat")
            self.assertEqual(trace["steps"][0]["tokens_in"], 10)


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(text, model, tracer)` is the entry point `record_trace.py` calls. It fits the shared
    convention by calling no model and ignoring `text`: a cost report has no question to route
    through, only the demo traces and price table `--demo` already uses."""

    def test_declares_its_level(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))

    def test_run_ignores_its_arguments_and_reports_on_the_demo_traces(self) -> None:
        tracer = Tracer(example="ops", level=LEVEL, model_id="stub-1")
        report = run("anything", StubModel([]), tracer)
        self.assertEqual(len(report.per_question), 2)
        self.assertEqual(report.unpriced_models, [])
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertTrue(tracer.steps)

    def test_record_trace_now_classifies_ops_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("ops")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
