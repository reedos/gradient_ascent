"""Tests for examples/observability: turning this site's own trace.json shape into
OpenTelemetry-named span dictionaries, with content redacted by default."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.observability.run import (  # noqa: E402
    GEN_AI_INPUT_TOKENS,
    GEN_AI_OPERATION_NAME,
    GEN_AI_OUTPUT_TOKENS,
    LEVEL,
    SITE_DECIDED_BY,
    SITE_DETAIL,
    run,
    span_summary,
    to_otel_spans,
)

SECRET_DETAIL = "the customer's account number is 9910284"


def _trace() -> dict:
    tracer = Tracer(example="rag", level=2, model_id="stub-rag-1")
    tracer.record(kind="code", decided_by="code", title="Embed and retrieve top-k", detail="dw480-manual#9", ms=31.0)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model for a cited answer",
        detail=SECRET_DETAIL,
        tokens_in=1850,
        tokens_out=64,
        ms=2100.0,
    )
    return tracer.to_dict()


class ObservabilityExampleTests(unittest.TestCase):
    def test_only_model_steps_get_gen_ai_attributes(self) -> None:
        spans = to_otel_spans(_trace())
        code_span, model_span = spans
        self.assertNotIn(GEN_AI_OPERATION_NAME, code_span["attributes"])
        self.assertNotIn(GEN_AI_INPUT_TOKENS, code_span["attributes"])
        self.assertEqual(model_span["attributes"][GEN_AI_OPERATION_NAME], "chat")
        self.assertEqual(model_span["attributes"][GEN_AI_INPUT_TOKENS], 1850)
        self.assertEqual(model_span["attributes"][GEN_AI_OUTPUT_TOKENS], 64)

    def test_decided_by_is_carried_on_every_span(self) -> None:
        spans = to_otel_spans(_trace())
        self.assertEqual([s["attributes"][SITE_DECIDED_BY] for s in spans], ["code", "code"])

    def test_redaction_is_the_default_and_the_secret_never_appears(self) -> None:
        spans = to_otel_spans(_trace())
        dump = str(spans)
        self.assertNotIn(SECRET_DETAIL, dump)
        for span in spans:
            self.assertNotIn(SITE_DETAIL, span["attributes"])

    def test_capture_content_true_includes_the_detail(self) -> None:
        spans = to_otel_spans(_trace(), capture_content=True)
        self.assertEqual(spans[1]["attributes"][SITE_DETAIL], SECRET_DETAIL)

    def test_detail_never_borrows_an_attribute_name_the_specification_defines(self) -> None:
        # `detail` is free text; `gen_ai.input.messages` is defined as the structured chat
        # history. Writing one into the other would misdescribe it to any backend reading these
        # spans, so the site's own namespace carries it in both modes.
        for spans in (to_otel_spans(_trace()), to_otel_spans(_trace(), capture_content=True)):
            for span in spans:
                for name in span["attributes"]:
                    if name.startswith("gen_ai."):
                        self.assertIn(name, {GEN_AI_OPERATION_NAME, GEN_AI_INPUT_TOKENS, GEN_AI_OUTPUT_TOKENS})

    def test_a_code_step_gets_no_gen_ai_attribute_even_with_content_captured(self) -> None:
        # The bypass: turning content capture on used to put a gen_ai.* attribute on a code step,
        # which is not a generative AI operation at all.
        code_span = to_otel_spans(_trace(), capture_content=True)[0]
        self.assertFalse([k for k in code_span["attributes"] if k.startswith("gen_ai.")])

    def test_a_title_is_not_redacted_which_is_why_titles_must_not_carry_content(self) -> None:
        # Attacking the redaction: `title` becomes the span name unconditionally. This function
        # cannot tell a descriptive title from one built out of a prompt, so the rule lives on
        # whatever records the trace. Pinned here so the limit is documented, not discovered.
        tracer = Tracer(example="safety", level=4, model_id="stub-1")
        tracer.record(kind="code", decided_by="code", title=f"Run tool: refund {SECRET_DETAIL}", detail="")
        spans = to_otel_spans(tracer.to_dict())
        self.assertIn(SECRET_DETAIL, spans[0]["name"])

    def test_span_summary_counts_tokens_and_model_decided_steps(self) -> None:
        trace = _trace()
        trace["steps"][0]["decided_by"] = "model"  # force one model-decided step to count
        summary = span_summary(to_otel_spans(trace))
        self.assertEqual(summary["span_count"], 2)
        self.assertEqual(summary["model_decided_steps"], 1)
        self.assertEqual(summary["tokens_in"], 1850)
        self.assertEqual(summary["tokens_out"], 64)

    def test_works_on_a_real_tracer_written_and_reloaded_trace(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.json"
            Tracer(example="chat", level=1, model_id="stub-1").write(path)
            reloaded = json.loads(path.read_text(encoding="utf-8"))
        # a level-1 chat trace this repo would actually write has no steps recorded above, so
        # to_otel_spans should simply return an empty list rather than raise
        self.assertEqual(to_otel_spans(reloaded), [])


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(text, model, tracer)` is the entry point `record_trace.py` calls. It fits the shared
    convention by calling no model and ignoring `text`: there is no question to route through a
    span exporter, only a small demo trace to build and export."""

    def test_declares_its_level(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))

    def test_run_ignores_its_arguments_and_exports_a_demo_trace(self) -> None:
        tracer = Tracer(example="observability", level=LEVEL, model_id="stub-1")
        answer = run("anything", StubModel([]), tracer)
        self.assertIn("span", answer.text)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertTrue(tracer.steps)

    def test_record_trace_now_classifies_observability_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("observability")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
