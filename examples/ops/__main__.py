"""Estimate cost and latency from recorded trace files and a price table you supply.

    python -m examples.ops --traces "path/to/*.json" --prices path/to/prices.json
    python -m examples.ops --demo

`--demo` needs no files: it writes two synthetic trace files (real `Tracer` output, not a
canned dict) to a temporary directory, using a small made-up price table clearly held apart from
`examples.ops.run` -- nothing in that module hard-codes a price, and this table is not a vendor's
published number, only a stand-in so the report has something to divide by.
"""
from __future__ import annotations

import argparse
import glob
import sys
import tempfile
from pathlib import Path

from examples.common.trace import Tracer
from examples.ops.run import PriceTable, Report, build_report, load_price_table

# Invented numbers for the demo, deliberately round and deliberately not near any maker's
# published rate, so nothing printed here can be mistaken for a real price or quoted as one. See
# the ops page for where a real table comes from and how it would be dated and attributed.
DEMO_PRICES: PriceTable = {"stub-chat-1": (0.001, 0.002), "stub-rag-1": (0.004, 0.008)}


def _write_demo_traces(out_dir: Path) -> list[Path]:
    chat = Tracer(example="chat", level=1, model_id="stub-chat-1")
    chat.record(kind="model", decided_by="code", title="Ask the model", tokens_in=40, tokens_out=90, ms=650.0)

    rag = Tracer(example="rag", level=2, model_id="stub-rag-1")
    rag.record(kind="code", decided_by="code", title="Embed and retrieve top-k", tokens_in=0, tokens_out=0, ms=30.0)
    rag.record(kind="model", decided_by="code", title="Ask the model for a cited answer", tokens_in=1850, tokens_out=64, ms=2100.0)

    chat_path, rag_path = out_dir / "chat.json", out_dir / "rag.json"
    chat.write(chat_path)
    rag.write(rag_path)
    return [chat_path, rag_path]


def _print_report(report: Report) -> None:
    print(f"{'example':<12}{'level':>6}{'tokens_in':>12}{'tokens_out':>12}{'ms':>10}{'usd':>10}")
    for c in report.per_question:
        usd = f"{c.usd:.6f}" if c.usd is not None else "unpriced"
        print(f"{c.example:<12}{c.level:>6}{c.tokens_in:>12}{c.tokens_out:>12}{c.ms:>10.1f}{usd:>10}")
    print()
    print(f"{'level':<6}{'n':>4}{'mean_ms':>12}{'mean_usd':>12}")
    for s in report.per_level:
        mean_usd = f"{s.mean_usd:.6f}" if s.mean_usd is not None else "unpriced"
        print(f"{s.level:<6}{s.n:>4}{s.mean_ms:>12.1f}{mean_usd:>12}")
    if report.unpriced_models:
        print("\nno price entry for: " + ", ".join(report.unpriced_models))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--traces", help="glob of trace JSON files, e.g. 'examples/*/trace.json'")
    parser.add_argument("--prices", type=Path, help="price table JSON file (see load_price_table)")
    parser.add_argument("--demo", action="store_true", help="use synthetic traces and a made-up price table")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.demo:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _write_demo_traces(Path(tmp))
            _print_report(build_report(paths, DEMO_PRICES))
        return 0

    if not args.traces or not args.prices:
        parser.error("pass --traces and --prices, or use --demo")
    paths = [Path(p) for p in glob.glob(args.traces)]
    if not paths:
        parser.error(f"no files matched --traces {args.traces!r}")
    _print_report(build_report(paths, load_price_table(args.prices)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
