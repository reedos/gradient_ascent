"""Export a demo trace to OpenTelemetry-shaped spans and print both a redacted and an
unredacted rendering side by side.

    python -m examples.observability --demo

Builds one small trace with a real `Tracer` -- a retrieval step and a model step, shaped like
this site's own `rag` example -- then calls `to_otel_spans` twice: once with the default
`capture_content=False`, once with it turned on, so the difference is visible in the printed
output rather than only in the code.
"""
from __future__ import annotations

import argparse
import json
import sys

from examples.common.trace import Tracer
from examples.observability.run import span_summary, to_otel_spans


def _demo_trace() -> dict:
    tracer = Tracer(example="rag", level=2, model_id="stub-rag-1")
    tracer.record(
        kind="code",
        decided_by="code",
        title="Embed and retrieve top-k",
        detail="dw480-manual#9, dw480-manual#9.2",
        ms=31.0,
    )
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask the model for a cited answer",
        detail="Two years from delivery [1].",
        tokens_in=1850,
        tokens_out=64,
        ms=2100.0,
    )
    return tracer.to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="export a synthetic trace (the only mode today)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.demo:
        parser.error("pass --demo")

    trace = _demo_trace()
    redacted = to_otel_spans(trace)
    full = to_otel_spans(trace, capture_content=True)

    print("-- redacted (default) --")
    print(json.dumps(redacted, indent=2))
    print("\n-- capture_content=True --")
    print(json.dumps(full, indent=2))
    print("\n-- summary --")
    print(json.dumps(span_summary(redacted), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
