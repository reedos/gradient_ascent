"""Tests for examples/code_execution: the model-writes-one-expression example for the
code-execution technique page (level 4).

Two things are checked beyond the trace shape every other level-4 example gets (see
tests/test_example_function_calling.py for that pattern): that `safe_eval` accepts ordinary
arithmetic and nothing else, and that a malicious or otherwise unsafe expression is refused by
the run end to end, never handed to Python's own `eval` or `exec`.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.code_execution.run import MAX_DEPTH, UnsafeExpression, run, safe_eval  # noqa: E402
from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"


class SafeEvalTests(unittest.TestCase):
    def test_accepts_ordinary_arithmetic(self) -> None:
        self.assertEqual(safe_eval("38.50 + 41.00"), 79.5)
        self.assertAlmostEqual(safe_eval("(3.2 - 3.0) * 20"), 4.0)
        self.assertEqual(safe_eval("-5 + 10"), 5)

    def test_rejects_a_call_the_same_way_it_rejects_anything_else_off_the_whitelist(self) -> None:
        with self.assertRaises(UnsafeExpression):
            safe_eval("__import__('os').system('echo pwned')")

    def test_rejects_names_and_attribute_access(self) -> None:
        with self.assertRaises(UnsafeExpression):
            safe_eval("os.system('echo pwned')")
        with self.assertRaises(UnsafeExpression):
            safe_eval("some_variable + 1")

    def test_rejects_exponentiation_not_in_the_whitelist(self) -> None:
        with self.assertRaises(UnsafeExpression):
            safe_eval("2 ** 10")

    def test_rejects_booleans_even_though_they_are_technically_ints(self) -> None:
        with self.assertRaises(UnsafeExpression):
            safe_eval("True + 1")

    def test_a_syntax_error_is_reported_as_unsafe_not_a_crash(self) -> None:
        with self.assertRaises(UnsafeExpression):
            safe_eval("this is not an expression")


class WhitelistBypassTests(unittest.TestCase):
    """Attempts to get something past the whitelist. Every one must come back as
    `UnsafeExpression` -- not a value, and not some other exception the caller never agreed to
    handle. The whitelist's claim is that it does not need to recognise an attack to stop one,
    so these are written as a list of spellings rather than as a list of threats."""

    REFUSED = {
        # reaching for a name, a call, an attribute or an import, in several spellings
        "import expression": "__import__('os').system('echo pwned')",
        "attribute on a literal": "(1).__class__",
        "attribute chain": "(1).__class__.__base__.__subclasses__()",
        "bare name": "credentials",
        "leading underscore name": "__builtins__",
        "underscore name inside a string": "'__import__'",
        "bytes literal": "b'__import__'",
        "f-string": "f'{1}'",
        "lambda call": "(lambda: 1)()",
        "comprehension": "[i for i in [1]]",
        "subscript": "[1, 2][0]",
        "walrus hiding an assignment": "(x := 1)",
        "conditional expression": "1 if 2 else 3",
        "comparison": "1 < 2",
        "await": "await 1",
        # a unicode lookalike does not become a different node type: it is still a Name
        "unicode lookalike identifier": "ımport",
        "full-width digits": "１＋１",
        # operators deliberately left off the whitelist
        "exponentiation": "2 ** 10",
        "large exponentiation": "9 ** 9 ** 9",
        "modulo": "5 % 2",
        "floor division": "5 // 2",
        "bit shift": "1 << 100000000",
        "bitwise xor": "1 ^ 2",
        "bitwise not": "~1",
        # two statements, or something that is not an expression at all
        "statement separator": "1; 2",
        "import statement": "import os",
        "null byte": "1+1\x00",
        "empty": "",
    }

    def test_every_bypass_attempt_is_refused_as_an_unsafe_expression(self) -> None:
        for name, expr in self.REFUSED.items():
            with self.subTest(attempt=name):
                with self.assertRaises(UnsafeExpression):
                    safe_eval(expr)

    def test_a_long_chain_is_refused_by_depth_rather_than_exhausting_recursion(self) -> None:
        """Without the depth bound this raised RecursionError, which `run` does not catch and
        which is not what a sandbox is supposed to do with input it will not evaluate."""
        deep = "1" + "+1" * (MAX_DEPTH + 8)
        with self.assertRaises(UnsafeExpression) as caught:
            safe_eval(deep)
        self.assertIn("nests deeper", str(caught.exception))
        # one under the bound still evaluates, so the cap is a bound and not a blanket refusal
        self.assertEqual(safe_eval("1" + "+1" * (MAX_DEPTH - 1)), MAX_DEPTH)

    def test_a_very_long_expression_is_refused_before_it_is_parsed(self) -> None:
        with self.assertRaises(UnsafeExpression) as caught:
            safe_eval("9" * 5000)
        self.assertIn("characters", str(caught.exception))

    def test_an_overflow_to_infinity_is_refused_rather_than_reported_as_a_number(self) -> None:
        for expr in ("1e400", "1e308 * 1e308", "-1e400"):
            with self.subTest(expr=expr):
                with self.assertRaises(UnsafeExpression):
                    safe_eval(expr)

    def test_the_module_never_calls_pythons_own_eval_or_exec(self) -> None:
        """The claim the page makes about this file, checked against the file itself."""
        source = (ROOT / "examples" / "code_execution" / "run.py").read_text(encoding="utf-8")
        called = {
            node.func.id
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("eval", called)
        self.assertNotIn("exec", called)
        self.assertNotIn("compile", called)

    def test_a_refused_expression_is_refused_end_to_end_not_only_in_safe_eval(self) -> None:
        """The run has its own `except` clause; a refusal that `safe_eval` raises but `run` does
        not catch would crash a question instead of answering it."""
        for expr in ("__import__('os').system('x')", "1" + "+1" * (MAX_DEPTH + 8), "1e400", "1 / 0"):
            with self.subTest(expr=expr[:24]):
                tracer = Tracer(example="code_execution", level=4, model_id="stub-1")
                answer = run(
                    "What does it cost?",
                    StubModel([StubResponse(text=expr)]),
                    None,
                    tracer,
                    corpus_dir=CORPUS_DIR,
                )
                self.assertIn("Could not safely evaluate", answer.text)
                self.assertEqual(answer.citations, [])


class CodeExecutionExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.code_execution.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 4)

    def test_writing_a_valid_expression_is_the_only_model_decided_step(self) -> None:
        model = StubModel(
            [
                StubResponse(text="38.50 + 41.00"),
                StubResponse(text="$79.50 (parts-list#2)."),
            ]
        )
        tracer = Tracer(example="code_execution", level=4, model_id="stub-1")
        answer = run(
            "What is the total price to replace the heating elements on both a DW-300 and a DW-480?",
            model,
            None,
            tracer,
            corpus_dir=CORPUS_DIR,
        )
        self.assertEqual(tracer.model_decided_count(), 1)
        decided_by_model = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(decided_by_model), 1)
        self.assertEqual(decided_by_model[0].title, "Model writes an expression")
        self.assertIn("79.5", answer.text)
        self.assertIn("parts-list#2", answer.citations)

    def test_declining_for_lack_of_numbers_is_still_the_one_model_decided_step(self) -> None:
        model = StubModel([StubResponse(text="NONE")])
        tracer = Tracer(example="code_execution", level=4, model_id="stub-1")
        answer = run("What color is the DW-300?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.model_decided_count(), 1, "declining is still a model decision")
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "no second call when nothing was computed")
        self.assertIn("don't give enough numbers", answer.text)
        self.assertEqual(answer.citations, [])

    def test_a_malicious_expression_never_reaches_a_second_call_and_is_refused(self) -> None:
        model = StubModel([StubResponse(text="__import__('os').system('echo pwned')")])
        tracer = Tracer(example="code_execution", level=4, model_id="stub-1")
        answer = run("What does it cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "the sandbox refusal must not ask the model again")
        self.assertIn("Could not safely evaluate", answer.text)
        self.assertEqual(answer.citations, [])
        refusal = next(s for s in tracer.steps if s.title == "Sandbox refused the expression")
        self.assertEqual(refusal.decided_by, "code")
        self.assertIn("whitelist", refusal.detail)

    def test_a_division_by_zero_is_refused_not_raised(self) -> None:
        model = StubModel([StubResponse(text="1 / 0")])
        tracer = Tracer(example="code_execution", level=4, model_id="stub-1")
        answer = run("What does it cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIn("Could not safely evaluate", answer.text)


if __name__ == "__main__":
    unittest.main()
