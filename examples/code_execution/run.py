"""Level 4: code execution. The model writes one line, a Python arithmetic expression that
answers a numeric question about the documents; the code always runs it, in an AST-whitelisted
evaluator, never with Python's own `eval` or `exec` on text the model wrote.

The model's one real decision is the content of that expression (or declining, if the retrieved
passages do not hold enough numbers). Running it is always the code's job, the same as running a
tool is in `examples/function_calling`: this file offers the same shape, one fixed action, with
the argument being an expression instead of a tool name and its arguments.
"""
from __future__ import annotations

import ast
import math
import operator
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 4
SEARCH_K = 3
DECLINE = "NONE"
SYSTEM_PROMPT = (
    "You answer numeric questions about Halvorsen appliances using only the numbered sources "
    "below. Reply with exactly one line: a Python arithmetic expression using only numbers, "
    "+ - * / and parentheses, that computes the answer -- no words, no units, no code fences. "
    f"If the sources do not contain the numbers you would need, reply with the single word "
    f"{DECLINE} instead."
)


class UnsafeExpression(ValueError):
    """Raised when an expression uses anything outside the arithmetic whitelist."""


_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
MAX_EXPRESSION_CHARS = 200
MAX_DEPTH = 32


def safe_eval(expr: str) -> float:
    """Evaluate a numeric expression against an allow-list of AST node types -- never Python's
    own `eval` or `exec` on the model's text. A blocklist has to know every dangerous spelling in
    advance (`os.system`, `__import__`, a walrus assignment hiding a call); this instead names
    the handful of node types arithmetic actually needs and rejects everything else by
    construction, so a name, a call, an attribute lookup, a comprehension and an import all fail
    the same way: `_eval_node` simply never matches them.

    Three bounds sit around that whitelist, because the node type is not the only way an
    expression can be a problem. Length is capped before parsing. Depth is capped while walking,
    so a long chain like `1+1+1+...` is refused instead of exhausting Python's own recursion and
    raising a `RecursionError` this module never promised and the caller does not catch. And a
    result that is not a finite number is refused, so an overflow to infinity (`1e400`, or
    `1e308 * 1e308`) never reaches the reader as a computed figure.
    """
    if len(expr) > MAX_EXPRESSION_CHARS:
        raise UnsafeExpression(f"expression is {len(expr)} characters; the limit is {MAX_EXPRESSION_CHARS}")
    try:
        tree = ast.parse(expr, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise UnsafeExpression(f"not a valid expression: {exc}") from exc
    value = _eval_node(tree.body)
    if isinstance(value, float) and not math.isfinite(value):
        raise UnsafeExpression(f"result is not a finite number: {value}")
    return value


def _eval_node(node: ast.AST, depth: int = 0) -> float:
    if depth > MAX_DEPTH:
        raise UnsafeExpression(f"expression nests deeper than {MAX_DEPTH} levels")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval_node(node.left, depth + 1), _eval_node(node.right, depth + 1))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return _UNARYOPS[type(node.op)](_eval_node(node.operand, depth + 1))
    raise UnsafeExpression(f"{type(node).__name__} is not on the arithmetic whitelist")


def _build_prompt(question: str, sources: list[Section]) -> str:
    blocks = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)
    return f"Sources:\n\n{blocks}\n\nQuestion: {question}"


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    k: int = SEARCH_K,
) -> Answer:
    del embedder  # this level searches by keyword, like the tools in function_calling and agentic_rag
    sections = load_sections(corpus_dir)
    hits = bm25_search(sections, question, k=k)
    sources = [section for section, _ in hits]
    tracer.record(
        kind="code",
        decided_by="code",
        title="Search for passages with the needed numbers",
        detail=", ".join(s.cite for s in sources),
    )

    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=_build_prompt(question, sources)),
    ]
    first = model.complete(messages, max_tokens=60)
    expr = first.text.strip()

    if not expr or expr.upper() == DECLINE:
        tracer.record(
            kind="model",
            decided_by="model",
            title="Model declines: not enough numbers in the passages",
            detail=expr or "(empty)",
            tokens_in=first.tokens_in,
            tokens_out=first.tokens_out,
            ms=first.ms,
        )
        return Answer(text="The documents don't give enough numbers to compute that.", citations=[])

    tracer.record(
        kind="model",
        decided_by="model",
        title="Model writes an expression",
        detail=expr,
        tokens_in=first.tokens_in,
        tokens_out=first.tokens_out,
        ms=first.ms,
    )

    try:
        value = safe_eval(expr)
    except (UnsafeExpression, ArithmeticError) as exc:
        tracer.record(kind="code", decided_by="code", title="Sandbox refused the expression", detail=str(exc))
        return Answer(text=f"Could not safely evaluate that expression: {exc}", citations=[])

    tracer.record(kind="code", decided_by="code", title="Sandbox evaluates the expression", detail=f"{expr} = {value}")

    follow_up = messages + [
        Message(role="assistant", content=expr),
        Message(
            role="user",
            content=f"That expression evaluates to {value}. Answer the question in one short "
            "sentence using that number, and cite the sources you used.",
        ),
    ]
    final = model.complete(follow_up, max_tokens=200)
    tracer.record(
        kind="model",
        decided_by="code",
        title="Ask for a final answer",
        detail=final.text[:200],
        tokens_in=final.tokens_in,
        tokens_out=final.tokens_out,
        ms=final.ms,
    )
    return Answer(text=final.text, citations=[s.cite for s in sources])
