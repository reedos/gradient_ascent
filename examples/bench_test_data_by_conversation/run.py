"""Level 4: the dashboard (`examples/bench_limits_without_a_model`) already charts limits,
first-pass yield and Cpk from the production log. This example is for the question that dashboard
does not answer: the model writes one short Python snippet, and a sandbox -- never the model --
runs it against the August 31 retest export or the August 27 soak log, and the final answer is
built from what the snippet returned.

Before either table is handed to anything, `_as_plausible_volts` range-checks the retest export's
`value_v` column against the widest node this board has anywhere (0 to 40 V, `VIN_ABS_MAX_V`).
Sixteen of its eighteen readings are millivolts under a header that says volts, and code catches
that and corrects it every time `_load_tables` runs, whether or not the model ever calls the tool.
`docs/THE-BENCH.md` Story 4 is the answer key this module's numbers are checked against.

The sandbox (`run_snippet`) is an allow-listed grammar, the same shape as
`examples/code_execution`'s `safe_eval` for one arithmetic expression, extended to short
table-analysis scripts: no import, no attribute access (so no `x.y`, and nothing dunder-chained
off a literal), no `lambda`, no `while`, no function or class definitions, calls only to a fixed
list of functions, and loops (a `for` statement or a comprehension's own `for` clauses) nested no
more than two deep. Unlike `safe_eval`, this does call Python's own `exec` -- but only on a syntax
tree that has already been walked node by node and refused if anything on it is not on the
grammar. See the recipe page for what that does and does not protect against.
"""
from __future__ import annotations

import ast
import csv
import json
import statistics

from evals.bench import RETEST_CSV, SOAK_CSV
from examples.common.bench import VIN_ABS_MAX_V
from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 4

#: Which CSV backs each table the sandbox can see, for the citation on the final answer.
TABLE_SOURCES = {"retest": RETEST_CSV.name, "soak": SOAK_CSV.name}

MAX_SOURCE_CHARS = 1500
MAX_NODES = 200
MAX_LOOP_DEPTH = 2


class ImplausibleUnits(ValueError):
    """Raised when a column declared to be volts holds values no reading on this board could be."""


class UnsafeCode(ValueError):
    """Raised when a snippet uses anything outside the analysis grammar, or oversteps a bound."""


# ---------------------------------------------------------------------------
# Loading the two tables, with the range check that runs before any analysis
# ---------------------------------------------------------------------------


def _parse_retest_rows() -> list[dict]:
    with RETEST_CSV.open(newline="", encoding="utf-8") as handle:
        return [
            {
                "serial": row["serial"],
                "lot": row["lot"],
                "fixture": row["fixture"],
                "measurement": row["measurement"],
                "value_v": float(row["value_v"]),
                "result": row["result"],
            }
            for row in csv.DictReader(handle)
        ]


def _as_plausible_volts(
    rows: list[dict], *, field: str = "value_v", ceiling_v: float = VIN_ABS_MAX_V
) -> tuple[list[dict], str]:
    """Range-check `field` against the widest node this board has anywhere, before any analysis
    sees it. Every reading in `field` is a volts measurement on an SRB-5030, and this board never
    carries more than `ceiling_v` volts on any pin (`docs/THE-BENCH.md`); a value past that by
    three orders of magnitude is not a surprising board, it is the wrong unit. If dividing by 1000
    brings every value back inside the ceiling, the column was millivolts and code corrects it and
    says so; if it still does not fit, this refuses rather than guess further.
    """

    def implausible(values: list[float]) -> list[float]:
        return [v for v in values if abs(v) > ceiling_v]

    raw = [row[field] for row in rows]
    bad = implausible(raw)
    if not bad:
        return rows, ""
    scaled = [{**row, field: row[field] / 1000.0} for row in rows]
    still_bad = implausible([row[field] for row in scaled])
    if still_bad:
        raise ImplausibleUnits(
            f"{len(bad)} of {len(rows)} {field!r} readings exceed {ceiling_v} V even after "
            f"dividing by 1000; refusing to guess the unit."
        )
    return scaled, (
        f"{len(bad)} of {len(rows)} {field!r} readings (as high as {max(bad):.1f}) exceeded "
        f"{ceiling_v} V, the widest node this board has anywhere. Code divided {field} by 1000 "
        f"before any analysis ran: the export is millivolts under a header that says volts."
    )


def _parse_soak_rows() -> list[dict]:
    with SOAK_CSV.open(newline="", encoding="utf-8") as handle:
        return [
            {
                "serial": row["serial"],
                "elapsed_min": float(row["elapsed_min"]),
                "vin_v": float(row["vin_v"]),
                "iout_a": float(row["iout_a"]),
                "vout_v": float(row["vout_v"]),
                "tcase_c": float(row["tcase_c"]),
            }
            for row in csv.DictReader(handle)
        ]


def _load_tables() -> tuple[dict[str, list[dict]], str]:
    """Both tables the sandbox may see. The retest table has already been through
    `_as_plausible_volts` by the time anything else touches it."""
    retest_rows, retest_note = _as_plausible_volts(_parse_retest_rows())
    note = retest_note or "the retest export's value_v column was already plausible as volts"
    return {"retest": retest_rows, "soak": _parse_soak_rows()}, note


# ---------------------------------------------------------------------------
# The sandbox: an allow-listed grammar, then (only then) exec
# ---------------------------------------------------------------------------

#: The only names a snippet may call. No attribute access exists in the grammar below, so there
#: is no `x.y` at all -- not `TABLES.get(...)`, not `"".join(...)`, not `(1).__class__` -- which
#: is most of what a sandbox escape needs. What is left is arithmetic, comparisons, boolean logic,
#: list/dict/set construction and comprehensions, subscripting, and calls to exactly these names.
_ALLOWED_FUNCTIONS = frozenset(
    {"len", "sum", "min", "max", "sorted", "round", "abs", "set", "list", "dict", "float", "int", "str", "mean", "stdev"}
)
_SANDBOX_FUNCTIONS: dict[str, object] = {
    "len": len, "sum": sum, "min": min, "max": max, "sorted": sorted, "round": round, "abs": abs,
    "set": set, "list": list, "dict": dict, "float": float, "int": int, "str": str,
    "mean": statistics.fmean, "stdev": statistics.stdev,
}
#: Names a snippet is given but may not rebind or mutate: the table and every allowed function.
_PROVIDED_NAMES = frozenset({"TABLES"}) | _ALLOWED_FUNCTIONS

_ALLOWED_NODE_TYPES = (
    ast.Module, ast.Assign, ast.For, ast.If, ast.Expr,
    ast.Name, ast.Load, ast.Store,
    ast.Constant,
    ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.BoolOp, ast.And, ast.Or,
    ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Call,
    ast.Subscript, ast.Slice,
    ast.IfExp,
)


def _assignment_base_name(node: ast.AST) -> str | None:
    """The `Name` a target ultimately writes through: `result` for `result`, `result` for
    `result[s]` and `result[s]["x"]` too. `None` for anything else (a tuple target, say), which
    the caller treats as refused."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Subscript):
        return _assignment_base_name(node.value)
    return None


def _max_loop_depth(node: ast.AST, depth: int = 0) -> int:
    """The deepest a `for` statement or a comprehension's own `for` clauses ever nest. A
    comprehension with several `for` clauses (`[x for x in a for y in b]`) is one AST node but
    nested iteration all the same, so each of its `generators` counts toward the depth exactly
    like a separate `for` statement would."""
    worst = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.For):
            worst = max(worst, _max_loop_depth(child, depth + 1))
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            worst = max(worst, _max_loop_depth(child, depth + len(child.generators)))
        else:
            worst = max(worst, _max_loop_depth(child, depth))
    return worst


def _check_grammar(tree: ast.AST) -> None:
    """Refuse anything not on the grammar above, by construction: a node type not in
    `_ALLOWED_NODE_TYPES` is refused the same way whether it is a name, a call, an attribute or an
    import, because nothing here ever asks what it is trying to do."""
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise UnsafeCode(f"snippet has {len(nodes)} syntax nodes; the limit is {MAX_NODES}")
    for node in nodes:
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise UnsafeCode(f"{type(node).__name__} is not on the analysis grammar")
        if isinstance(node, ast.Dict) and any(key is None for key in node.keys):
            raise UnsafeCode("dict-unpacking ({**x}) is not on the analysis grammar")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise UnsafeCode("a call must be to a plain name, never to an attribute")
            if node.func.id not in _ALLOWED_FUNCTIONS:
                raise UnsafeCode(f"{node.func.id!r} is not one of the functions this sandbox provides")
            if node.keywords:
                raise UnsafeCode("keyword arguments are not on the analysis grammar")
        if isinstance(node, (ast.Assign, ast.For)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                name = _assignment_base_name(target)
                if name is None:
                    raise UnsafeCode(f"cannot assign to a {type(target).__name__} target")
                if name in _PROVIDED_NAMES:
                    raise UnsafeCode(f"refusing to assign to {name!r}, a name the sandbox provided")
    depth = _max_loop_depth(tree)
    if depth > MAX_LOOP_DEPTH:
        raise UnsafeCode(f"snippet nests {depth} loops deep; the limit is {MAX_LOOP_DEPTH}")


def run_snippet(code: str, tables: dict[str, list[dict]]) -> object:
    """Run one analysis snippet against `tables` and return whatever it assigned to `result`.

    Never calls Python's own `eval`. It does call `exec`, but only on a tree `_check_grammar` has
    already walked node by node, in a namespace with `__builtins__` emptied out, holding nothing
    but `TABLES` and the functions in `_SANDBOX_FUNCTIONS` -- so there is no name anywhere in
    scope that reaches a file, a socket, or the interpreter itself.
    """
    if len(code) > MAX_SOURCE_CHARS:
        raise UnsafeCode(f"snippet is {len(code)} characters; the limit is {MAX_SOURCE_CHARS}")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise UnsafeCode(f"not valid analysis code: {exc}") from exc
    _check_grammar(tree)
    namespace: dict[str, object] = {"__builtins__": {}, "TABLES": tables, **_SANDBOX_FUNCTIONS}
    try:
        exec(compile(tree, "<analysis-snippet>", "exec"), namespace)  # noqa: S102 -- see docstring
    except UnsafeCode:
        raise
    except Exception as exc:  # the snippet's own runtime error: a KeyError, a ZeroDivisionError...
        raise UnsafeCode(f"the snippet raised {type(exc).__name__}: {exc}") from exc
    if "result" not in namespace:
        raise UnsafeCode("the snippet must assign its answer to a variable named result")
    return namespace["result"]


def _used_tables(code: str) -> list[str]:
    """Which of `TABLES["retest"]` / `TABLES["soak"]` a snippet's text actually names, read
    straight from its syntax tree so the citation on the final answer is something code found,
    not something the model claimed it used. Best effort: invalid code returns none, since
    `run_snippet` will refuse it before this ever matters."""
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError:
        return []
    names = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "TABLES"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    return sorted(names)


def _render_result(result: object) -> str:
    try:
        return json.dumps(result, indent=2, sort_keys=True)
    except TypeError:
        return repr(result)


# ---------------------------------------------------------------------------
# The one tool, and the one-decision run
# ---------------------------------------------------------------------------

RUN_PYTHON_TOOL = {
    "name": "run_python",
    "description": (
        "Run one short Python analysis snippet against the loaded tables and return the value "
        "assigned to result. No imports, no attribute access, no while loops; call only the "
        "provided functions."
    ),
    "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
}
TOOLS = [RUN_PYTHON_TOOL]

SYSTEM_PROMPT = (
    "You answer questions about Orbeck SRB-5030 test data by writing one short Python snippet "
    "for run_python. Two tables are loaded: TABLES['retest'] (serial, lot, fixture, measurement, "
    "value_v, result -- one row per retested board, value_v already checked and corrected to "
    "volts) and TABLES['soak'] (serial, elapsed_min, vin_v, iout_a, vout_v, tcase_c -- one row "
    "per five-minute sample of a 90-minute soak). Call run_python at most once, with a snippet "
    "that assigns its answer to a variable named result. You may call only len, sum, min, max, "
    "sorted, round, abs, set, list, dict, float, int, str, mean and stdev; no import, no "
    "attribute access (a.b), no lambda, no while, no function or class definitions. If you "
    "already know the answer without running anything, answer directly instead."
)


def run(question: str, model: Model, tracer: Tracer, *, tables: dict[str, list[dict]] | None = None) -> Answer:
    if tables is None:
        tables, note = _load_tables()
    else:
        note = "tables supplied by the caller; the range check already ran when they were built"
    tracer.record(
        kind="code",
        decided_by="code",
        title="Load bench tables, range-check value columns before any analysis",
        detail=note,
    )

    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=question)]
    first = model.complete(messages, tools=TOOLS, max_tokens=400)
    if not first.tool_calls:
        tracer.record(
            kind="model",
            decided_by="model",
            title="Model answers directly, no code run",
            detail=first.text[:200],
            tokens_in=first.tokens_in,
            tokens_out=first.tokens_out,
            ms=first.ms,
        )
        return Answer(text=first.text, citations=[])

    call = first.tool_calls[0]
    dropped = "" if len(first.tool_calls) == 1 else f" (dropped {len(first.tool_calls) - 1} further call(s))"
    code = str(call.arguments.get("code", ""))
    tracer.record(
        kind="model",
        decided_by="model",
        title="Model writes analysis code",
        detail=code[:300] + dropped,
        tokens_in=first.tokens_in,
        tokens_out=first.tokens_out,
        ms=first.ms,
    )

    try:
        result = run_snippet(code, tables)
    except UnsafeCode as exc:
        tracer.record(kind="code", decided_by="code", title="Sandbox refused the snippet", detail=str(exc))
        return Answer(text=f"Could not safely run that analysis: {exc}", citations=[])

    result_text = _render_result(result)
    tracer.record(kind="code", decided_by="code", title="Sandbox runs the snippet", detail=result_text[:400])

    follow_up = messages + [
        Message(role="assistant", content="[called run_python(code=...)]"),
        Message(
            role="user",
            content=f"The snippet returned:\n{result_text}\n\nAnswer the question in one or two "
            f"short sentences, using only that result: {question}",
        ),
    ]
    final = model.complete(follow_up, max_tokens=250)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask for a final answer",
        detail=final.text[:200],
        tokens_in=final.tokens_in,
        tokens_out=final.tokens_out,
        ms=final.ms,
    )
    citations = [TABLE_SOURCES[name] for name in _used_tables(code) if name in TABLE_SOURCES]
    return Answer(text=final.text, citations=citations)
