"""Level 5: coding agents. A tiny buggy function lives in memory as a string; the model proposes
a complete replacement, your code applies it with `exec` and runs four fixed test cases against
it, and the model reads the result and decides whether to try again or stop. Nothing here touches
a real file, a real sandbox, or a real test runner -- see this page's Use it lane for how the
makers themselves document sandboxing, permissions and instruction files for a real coding agent.

Every call to `propose_edit`, and the decision to stop, is `decided_by: "model"`: the model's own
output picks the new source and picks when it is done. Deciding whether the proposal may run at
all, and running it, are always `decided_by: "code"` -- the same separation a real coding agent's
sandbox enforces between what the model proposes and what actually executes.

That separation is only worth something if the code side actually holds. `check_source` is where
it holds, and it is worth reading before the loop: an empty `__builtins__` dict is not a sandbox,
and this example ran model-written source through one until an audit escaped it. What stops the
escape is a whitelist of AST node types, the same shape `examples/code_execution` uses for
arithmetic. Even so, a real coding agent editing real files needs a real sandbox -- a separate
process with its own filesystem and no network -- not a check in the same interpreter.
"""
from __future__ import annotations

import ast

from examples.common.agent_loop import force_final, record_completion
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_STEPS = 3
MAX_TOKENS = 2000
FUNC_NAME = "sum_evens"
TASK = (
    "Fix sum_evens so it returns the sum of the even numbers in a list. It currently fails: "
    "sum_evens([1, 2, 3, 4, 5, 6]) should be 12 but returns 9."
)
BUGGY_SOURCE = (
    "def sum_evens(numbers):\n"
    '    """Return the sum of the even numbers in numbers."""\n'
    "    total = 0\n"
    "    for n in numbers:\n"
    "        if n % 2 == 1:\n"
    "            total += n\n"
    "    return total\n"
)
TEST_CASES = [([1, 2, 3, 4, 5, 6], 12), ([], 0), ([1, 3, 5], 0), ([2, 4], 6)]
SYSTEM_PROMPT = (
    "You are fixing a small Python function so its tests pass. Call propose_edit with the "
    "complete corrected function source each time you want to try a fix. Read the test result "
    "you get back; if it still fails, try again. Once it says every case passed, stop calling "
    "tools and report the fix in your final answer."
)
PROPOSE_EDIT_TOOL = {
    "name": "propose_edit",
    "description": "Replace sum_evens with a corrected implementation. Provide the complete function definition.",
    "parameters": {"type": "object", "properties": {"new_source": {"type": "string"}}, "required": ["new_source"]},
}

# The AST node types a fix for `sum_evens` can be written with. Deliberately short: `Attribute`,
# `Import`, `ImportFrom`, `Global` and `Nonlocal` are absent, which is what closes the escape
# described in `check_source`. Extend it if a legitimate fix is ever refused -- and read that
# function first, because `Attribute` is not an omission.
ALLOWED_NODES = frozenset(
    {
        ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Pass,
        ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.For, ast.While, ast.If,
        ast.Break, ast.Continue, ast.Name, ast.Load, ast.Store, ast.Del, ast.Constant,
        ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Call, ast.keyword,
        ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Starred, ast.Subscript, ast.Slice,
        ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Invert,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
    }
)


def check_source(source: str) -> str:
    """Why this proposed source may not be run, or "" if it may. Checked before `exec`.

    An empty `__builtins__` is NOT a sandbox, and treating it as one is the mistake this check
    exists to stop. Nothing in `{"__builtins__": {}}` removes attribute access, and attribute
    access is all an escape needs: `().__class__.__mro__[-1].__subclasses__()` reaches every
    loaded class, any one of their methods carries a `__globals__` holding a real `__builtins__`,
    and from there `open` and `__import__` are back. No builtin name is used anywhere in that
    chain, so no name-based check would see it coming.

    So this uses the same discipline as `examples/code_execution`'s arithmetic evaluator: name
    the node types the task actually needs and refuse everything else by construction, rather
    than trying to list the dangerous spellings. Fixing `sum_evens` needs arithmetic, comparison,
    a loop, a branch and a return; it needs no attribute access, no import and no global
    statement, so none of those are on the list and the escape above has nowhere to start.

    This is still not a substitute for running a real coding agent's edits in a real sandbox --
    a separate process with its own filesystem and no network. It is the weakest check that makes
    this example honest about the separation the module docstring claims.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        return f"not parseable Python: {exc}"
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return f"{type(node).__name__} is not on the whitelist for a proposed edit"
    return ""


def _run_tests(source: str) -> tuple[bool, str]:
    """Check `source` against `check_source`, define it in a namespace with no builtins, and run
    the fixed test cases against whatever function it defines. Never raises: a bad edit, or one
    the check refuses, is a failing result rather than a crash."""
    refused = check_source(source)
    if refused:
        return False, f"refused before running: {refused}"
    namespace: dict = {}
    try:
        exec(source, {"__builtins__": {}}, namespace)  # noqa: S102 - see check_source: the whitelist, not this dict, is the boundary
    except Exception as exc:  # noqa: BLE001 - any error in the model's code is a failing result, not a crash
        return False, f"could not define {FUNC_NAME}: {exc!r}"
    func = namespace.get(FUNC_NAME)
    if not callable(func):
        return False, f"no function named {FUNC_NAME} was defined"
    for numbers, expected in TEST_CASES:
        try:
            actual = func(numbers)
        except Exception as exc:  # noqa: BLE001 - a raised exception is a failing result, not a crash
            return False, f"{FUNC_NAME}({numbers}) raised {exc!r}"
        if actual != expected:
            return False, f"{FUNC_NAME}({numbers}) returned {actual!r}, expected {expected!r}"
    return True, f"all {len(TEST_CASES)} test cases passed"


def run(
    task: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    max_steps: int = MAX_STEPS,
    max_tokens: int = MAX_TOKENS,
) -> Answer:
    del embedder  # this example has no documents to retrieve; the "test" is the only checker
    passed, detail = _run_tests(BUGGY_SOURCE)
    tracer.record(kind="code", decided_by="code", title="Run the failing test against the starting code", detail=detail)
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=f"{task}\n\nCurrent source:\n{BUGGY_SOURCE}\nTest result: {detail}"),
    ]

    tokens_used = 0
    for _ in range(max_steps):
        completion = model.complete(messages, tools=[PROPOSE_EDIT_TOOL], max_tokens=300)
        tokens_used += completion.tokens_in + completion.tokens_out

        if not completion.tool_calls:
            record_completion(tracer, decided_by="model", title="Model stops and reports the fix", completion=completion)
            return Answer(text=completion.text, citations=[FUNC_NAME] if passed else [])

        new_source = str(completion.tool_calls[0].arguments.get("new_source", ""))
        record_completion(tracer, decided_by="model", title="Model proposes an edit", completion=completion, detail=new_source[:200])
        passed, detail = _run_tests(new_source)
        tracer.record(kind="code", decided_by="code", title="Run the test against the proposed edit", detail=detail)
        messages.append(Message(role="assistant", content=f"[proposed edit]\n{new_source}"))
        messages.append(Message(role="user", content=f"Test result: {detail}"))

        if tokens_used >= max_tokens:
            reason = f"token budget reached: {tokens_used} >= {max_tokens}"
            final = force_final(messages, model, tracer, reason=reason, max_tokens=300)
            return Answer(text=final.text, citations=[FUNC_NAME] if passed else [])

    final = force_final(messages, model, tracer, reason=f"step cap reached: {max_steps} steps", max_tokens=300)
    return Answer(text=final.text, citations=[FUNC_NAME] if passed else [])
