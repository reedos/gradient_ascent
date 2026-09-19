"""Record one example run for one question to `examples/<name>/trace.json`.

Usage:
    python scripts/record_trace.py --list
    python scripts/record_trace.py --example rag --question "..." --model ollama:llama3.1 --dry-run
    python scripts/record_trace.py --example rag --question "..." --model ollama:llama3.1
    python scripts/record_trace.py --example rag --question "..." --model stub --allow-stub
    python scripts/record_trace.py --example rag --question "..." --model claude:claude-sonnet-5 --embedder ollama:nomic-embed-text

Same stub refusal rule as `scripts/eval_run.py`: a trace recorded from the stub model is not
written unless `--allow-stub` is passed, since it would not be a real run for the site to show.
One that is written that way carries `"stub": true`, and the site may only play a trace where
that field is false.

`--embedder` is independent of `--model` and defaults to it. An example whose `run()` takes an
embedder (`takes_embedder` below) needs one built from a spec `build_embedder` accepts --
`examples/common/model.py` has no `claude:` branch there, since Anthropic does not publish an
embeddings endpoint, so recording such an example against a metered `claude:<id>` chat model
needs `--embedder stub` or `--embedder ollama:<tag>` passed explicitly; leaving `--embedder`
unset keeps today's behavior of building the embedder from the same spec as `--model`.

Which examples this can record
-------------------------------
Every directory under `examples/` is discovered on every run; nothing is named here one at a
time. A directory is recordable when its `run.py` follows the one entry-point convention every
question-answering example in this repo already follows (see `examples/rag/run.py`): a callable
named `run` whose positional parameters are, in order,

    (<text>, model, tracer)              or   (<text>, model, embedder, tracer)

-- `<text>` can be named anything (`question`, `query`, `task`, ...): only its position matters,
and it is what `--question` fills in -- and whose keyword-only parameters, if any, all carry a
default, so one `--question` is enough to make a complete call. `classify()` below checks this by
reading the signature with `inspect`, not by name-matching the example. An example whose `run.py`
does not follow that convention (a different entry-point name, a different parameter order, a
required keyword-only argument `record_trace.py` cannot fill in) cannot be recorded here without
a change to the example itself; `--list` names the exact reason for every one of them, and
`.local/page-requests/wave6-traces.md` names the precise change each one would need.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import (  # noqa: E402
    Completion,
    Message,
    StubEmbedder,
    StubModel,
    StubResponse,
    ToolCall,
    build_embedder,
    build_model,
    content_text,
    count_tokens,
)
from examples.common.trace import Tracer  # noqa: E402


def discover_examples() -> list[str]:
    """Every example directory under `examples/`: anything with a `run.py` that is not the
    shared `common` package. This is the only place this script enumerates examples by hand;
    everything downstream works from this list, not from a name typed in twice."""
    examples_dir = ROOT / "examples"
    names = []
    for entry in sorted(examples_dir.iterdir()):
        if not entry.is_dir() or entry.name in {"common", "__pycache__"}:
            continue
        if (entry / "run.py").exists():
            names.append(entry.name)
    return names


EXAMPLE_NAMES = discover_examples()


@dataclass(frozen=True)
class Recordability:
    """Whether `record_trace.py` can call one example's `run`, and why not when it can't.

    `level` is filled in whenever the module got far enough to have one, even for a module this
    script ultimately refuses, so `--list` can print it either way.
    """

    ok: bool
    reason: str = ""
    takes_embedder: bool = False
    level: int | None = None


def classify(example: str) -> Recordability:
    """Apply the one convention described in this module's docstring to `examples/<example>/run.py`."""
    try:
        module = importlib.import_module(f"examples.{example}.run")
    except Exception as exc:  # noqa: BLE001 - a broken example must read as "cannot record", not crash --list
        return Recordability(False, f"examples.{example}.run failed to import: {exc!r}")

    run_fn = getattr(module, "run", None)
    if not callable(run_fn):
        return Recordability(False, "has no `run` function, the one entry point this script calls")

    level = getattr(module, "LEVEL", None)
    if not isinstance(level, int):
        return Recordability(False, "has a `run` function but no integer `LEVEL`")

    try:
        sig = inspect.signature(run_fn)
    except (TypeError, ValueError) as exc:
        return Recordability(False, f"run's signature could not be read: {exc}", level=level)

    positional = [
        p.name
        for p in sig.parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if not positional or positional[-1] != "tracer":
        found = ", ".join(positional) or "none"
        return Recordability(
            False,
            f"run's last positional parameter must be named `tracer`; found ({found})",
            level=level,
        )

    if len(positional) == 4 and positional[1] == "model" and positional[2] == "embedder":
        takes_embedder = True
    elif len(positional) == 3 and positional[1] == "model":
        takes_embedder = False
    else:
        return Recordability(
            False,
            "run's positional parameters are (" + ", ".join(positional) + "); the recordable shape "
            "is (text, model, tracer) or (text, model, embedder, tracer)",
            level=level,
        )

    missing_defaults = [
        p.name
        for p in sig.parameters.values()
        if p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
    ]
    if missing_defaults:
        return Recordability(
            False,
            "run() requires " + ", ".join(missing_defaults) + " with no default, so one --question "
            "cannot fill in a complete call",
            level=level,
        )

    return Recordability(True, takes_embedder=takes_embedder, level=level)


def recordable_examples() -> list[str]:
    """Every discovered example this script can actually call, in the same order as `--list`."""
    return [name for name in EXAMPLE_NAMES if classify(name).ok]


def list_status() -> list[dict]:
    """One row per discovered example: name, level (when known), whether it is recordable, and
    why not when it isn't. Deterministic for a given state of `examples/`, since `EXAMPLE_NAMES`
    is sorted and `classify` reads nothing but each module's own code."""
    rows = []
    for name in EXAMPLE_NAMES:
        rec = classify(name)
        rows.append(
            {
                "example": name,
                "level": rec.level,
                "recordable": rec.ok,
                "reason": "" if rec.ok else rec.reason,
            }
        )
    return rows


def sample_input(example: str) -> str | None:
    """The input an example says it should be tried with, when it says so.

    Most examples answer a question, and any question will do. A few take something narrower as
    their first argument: a serial number that has to be in the production log, say. Refusing a
    serial it has never seen is the right behavior there, so such an example names one that
    exists as `SAMPLE_INPUT` in its `run.py`, and `--question` may then be left out.
    """
    module = importlib.import_module(f"examples.{example}.run")
    value = getattr(module, "SAMPLE_INPUT", None)
    return value if isinstance(value, str) and value else None


def load_run_fn(example: str):
    module = importlib.import_module(f"examples.{example}.run")
    return module.run, module.LEVEL


def placeholder_stub(question: str) -> StubModel:
    """A stub that answers every call, however many an example makes, and never calls a tool.

    It has to be a responder rather than a fixed list: prompt chaining calls the model twice and
    the agent loop calls it as often as it likes, and a list that runs out raises mid-run.
    """

    def responder(messages: list[Message], tools: list[dict] | None) -> StubResponse:
        del tools
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), question)
        return StubResponse(text=f"[stub] {last_user[:200]}")

    return StubModel(responder)


class DryRunModel:
    """Stands in for a real model during `--dry-run`. Makes no network call, and projects an
    upper bound rather than a likely run: input tokens are counted for real with `count_tokens`
    over the prompt the example actually builds; output tokens are reported as the `max_tokens`
    the example asked for, which is the most a provider could bill for that call. Whenever tools
    are offered it calls the first one, every time, so a tool-using example runs to its own step
    cap instead of stopping after one round trip. Kept local to this script (rather than shared
    with `scripts/eval_run.py`'s own `DryRunModel`) so the two scripts stay independent.
    """

    def __init__(self, requested_id: str) -> None:
        self.model_id = requested_id

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[dict] | None = None,
        schema: dict | None = None,
        max_tokens: int = 1024,
    ) -> Completion:
        del schema
        tokens_in = sum(count_tokens(content_text(m.content)) for m in messages)
        tool_calls: list[ToolCall] = []
        if tools:
            first = tools[0]
            arg_name = next(iter(first["parameters"]["properties"]), "query")
            tool_calls = [ToolCall(name=first["name"], arguments={arg_name: "projected"})]
        text = "" if tool_calls else "[dry run projection, no model called]"
        return Completion(
            text=text, tool_calls=tool_calls, tokens_in=tokens_in, tokens_out=max_tokens, ms=0.0, model_id=self.model_id
        )


def project(example: str, question: str, model_spec: str, *, out_path: Path) -> dict:
    """What `--dry-run` reports. Never calls `build_model`, so no real backend (`OllamaModel`,
    `ClaudeModel`) is even constructed, and no network call is possible -- see `DryRunModel`.
    """
    rec = classify(example)
    if not rec.ok:
        raise ValueError(f"{example} is not recordable: {rec.reason}")
    run_fn, level = load_run_fn(example)
    model = DryRunModel(model_spec)
    tracer = Tracer(example=example, level=level, model_id=model.model_id, stub=(model_spec == "stub"))
    if rec.takes_embedder:
        run_fn(question, model, StubEmbedder(), tracer)
    else:
        run_fn(question, model, tracer)
    return {
        "example": example,
        "model_id": model.model_id,
        "steps": len(tracer.steps),
        "tokens_in": tracer.tokens_in_total(),
        "tokens_out": tracer.tokens_out_total(),
        "would_write": str(out_path),
    }


def _result_text_and_citations(result: object) -> tuple[str, list[str]]:
    """Most `run` functions return `Answer` (`.text`, `.citations`). `human_in_the_loop` can also
    return `PendingReview`, which has `.draft_text` instead of `.text`. Reading both generically
    here means this script does not need to special-case one example among the ones it discovers."""
    text = getattr(result, "text", None)
    if text is None:
        text = getattr(result, "draft_text", repr(result))
    citations = list(getattr(result, "citations", None) or [])
    return text, citations


def _print_list() -> None:
    rows = list_status()
    name_width = max(len(r["example"]) for r in rows)
    for r in rows:
        level = "?" if r["level"] is None else str(r["level"])
        status = "recordable" if r["recordable"] else "NOT recordable"
        line = f"{r['example']:<{name_width}}  level {level:>1}  {status}"
        if not r["recordable"]:
            line += f" -- {r['reason']}"
        print(line)
    ok = sum(1 for r in rows if r["recordable"])
    print(f"\n{ok} of {len(rows)} examples are recordable by this script's convention.")
    print("See .local/page-requests/wave6-traces.md for what the rest would need.")


def _print_dry_run(summary: dict) -> None:
    print(f"example      {summary['example']}")
    print(f"model_id     {summary['model_id']}")
    print(f"steps        {summary['steps']}")
    print(f"tokens_in    {summary['tokens_in']}")
    print(f"tokens_out   {summary['tokens_out']}")
    print(f"would write  {summary['would_write']}")
    print("\nno model was called.")


def build_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--example", default=None, help="see --list for every discovered example and its status")
    parser.add_argument("--question", default=None)
    parser.add_argument("--model", default="stub", help="stub | ollama:<tag> | claude:<id>")
    parser.add_argument(
        "--embedder",
        default=None,
        help=(
            "stub | ollama:<tag>, for an example whose run() takes an embedder. Defaults to "
            "--model (today's behavior), so pass this separately when --model is claude:<id>: "
            "build_embedder has no claude: branch (see examples/common/model.py), so pairing a "
            "metered chat model with the local embedder needs the two specs to differ."
        ),
    )
    parser.add_argument("--allow-stub", action="store_true")
    parser.add_argument("--out", default=None, type=Path, help="defaults to examples/<name>/trace.json")
    parser.add_argument(
        "--list", action="store_true", help="print every discovered example and whether it can be recorded, then exit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be called and projected tokens, with no model call, then exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = build_args(argv)

    if args.list:
        _print_list()
        return 0

    if not args.example:
        print("Missing --example. Pass --list to see every discovered example and whether it can be recorded.")
        return 2
    if args.example not in EXAMPLE_NAMES:
        print(f"Unknown example: {args.example!r}. Pass --list to see every discovered example.")
        return 2

    rec = classify(args.example)
    if not rec.ok:
        print(
            f"{args.example} cannot be recorded by this script: {rec.reason}\n"
            f"See .local/page-requests/wave6-traces.md for the change that would fix it."
        )
        return 2

    if not args.question:
        args.question = sample_input(args.example)
    if not args.question:
        print("Missing --question.")
        return 2

    out_path = args.out or (ROOT / "examples" / args.example / "trace.json")

    if args.dry_run:
        summary = project(args.example, args.question, args.model, out_path=out_path)
        _print_dry_run(summary)
        return 0

    is_stub = args.model == "stub"
    if is_stub and not args.allow_stub:
        print("Refusing to record a trace from the stub model without --allow-stub.")
        return 1

    run_fn, level = load_run_fn(args.example)
    model = build_model(args.model, stub=placeholder_stub(args.question))
    tracer = Tracer(example=args.example, level=level, model_id=model.model_id, stub=is_stub)
    if rec.takes_embedder:
        # Independent of --model, defaulting to it: today's pairing keeps working when the two
        # specs happen to agree, and a metered claude:<id> chat model can be paired with a local
        # embedder by passing --embedder explicitly (build_embedder has no claude: branch).
        embedder_spec = args.embedder or args.model
        embedder = build_embedder(embedder_spec, stub=StubEmbedder())
        result = run_fn(args.question, model, embedder, tracer)
    else:
        result = run_fn(args.question, model, tracer)

    payload = tracer.write(out_path, repo_root=ROOT)
    text, citations = _result_text_and_citations(result)
    print(f"wrote {out_path} ({len(payload['steps'])} steps, model {model.model_id})")
    print(text[:300])
    print("citations:", ", ".join(citations) or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
