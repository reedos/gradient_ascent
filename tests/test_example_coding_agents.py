"""Tests for examples/coding_agents: the propose-edit-run-test example for the coding-agents
technique page. Mirrors the shape of tests/test_examples.py's ExampleTraceTests and
AgenticCapTests: run end to end on a scripted StubModel, check the trace's decided_by pattern,
and check both caps force a stop.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.coding_agents.run import BUGGY_SOURCE, FUNC_NAME, TASK, _run_tests, check_source, run  # noqa: E402

# The escape an audit found in the version of this example that ran model-written source through
# `exec(source, {"__builtins__": {}}, ns)` and called that a sandbox. It uses no builtin name at
# all -- only attribute access, indexing and a bare `except` -- so no name-based check would see
# it. Run against the old code it wrote a file into the repository working directory.
NAMESPACE_ESCAPE = (
    "def sum_evens(numbers):\n"
    "    for c in ().__class__.__mro__[-1].__subclasses__():\n"
    "        try:\n"
    "            g = c.__init__.__globals__\n"
    "        except:\n"
    "            continue\n"
    "        if '__builtins__' in g:\n"
    "            bi = g['__builtins__']\n"
    "            op = bi['open'] if bi.__class__ is {}.__class__ else bi.open\n"
    "            f = op('PROOF_OF_ESCAPE.txt', 'w')\n"
    "            f.write('escaped')\n"
    "            f.close()\n"
    "            return 12\n"
    "    return 0\n"
)

CORRECT_SOURCE = (
    "def sum_evens(numbers):\n"
    "    total = 0\n"
    "    for n in numbers:\n"
    "        if n % 2 == 0:\n"
    "            total += n\n"
    "    return total\n"
)
STILL_BROKEN_SOURCE = (
    "def sum_evens(numbers):\n"
    "    total = 0\n"
    "    for n in numbers:\n"
    "        total += n\n"  # sums everything, not just evens
    "    return total\n"
)


class RunTestsHelperTests(unittest.TestCase):
    def test_the_starting_source_fails(self) -> None:
        passed, detail = _run_tests(BUGGY_SOURCE)
        self.assertFalse(passed)
        self.assertIn("sum_evens", detail)

    def test_a_correct_fix_passes_every_case(self) -> None:
        passed, detail = _run_tests(CORRECT_SOURCE)
        self.assertTrue(passed)
        self.assertIn("4", detail)  # four test cases

    def test_code_that_does_not_define_the_function_fails_without_raising(self) -> None:
        passed, detail = _run_tests("x = 1\n")
        self.assertFalse(passed)
        self.assertIn("no function named", detail)

    def test_code_that_raises_fails_without_propagating(self) -> None:
        passed, detail = _run_tests("def sum_evens(numbers):\n    return 1 / 0\n")
        self.assertFalse(passed)
        self.assertIn("raised", detail)

    def test_an_import_is_refused_before_anything_runs(self) -> None:
        passed, detail = _run_tests("def sum_evens(numbers):\n    return __import__('os').getcwd()\n")
        self.assertFalse(passed)
        self.assertIn("refused before running", detail, "an empty __builtins__ alone is not the boundary")


class CheckSourceTests(unittest.TestCase):
    """`check_source` is the boundary, not the empty `__builtins__` dict. These are the attacks."""

    def test_the_task_itself_and_a_correct_fix_are_allowed(self) -> None:
        self.assertEqual(check_source(BUGGY_SOURCE), "")
        self.assertEqual(check_source(CORRECT_SOURCE), "")
        self.assertEqual(check_source(STILL_BROKEN_SOURCE), "")

    def test_a_comprehension_fix_is_allowed(self) -> None:
        self.assertEqual(check_source("def sum_evens(numbers):\n    return sum(n for n in numbers if n % 2 == 0)\n"), "")

    def test_attribute_access_is_refused_because_it_is_the_whole_escape(self) -> None:
        self.assertIn("Attribute", check_source("def sum_evens(numbers):\n    return ().__class__\n"))

    def test_an_import_statement_is_refused(self) -> None:
        self.assertIn("Import", check_source("import os\ndef sum_evens(numbers):\n    return 0\n"))

    def test_unparseable_source_is_refused_rather_than_raising(self) -> None:
        self.assertIn("not parseable", check_source("def sum_evens(\n"))

    def test_the_namespace_escape_never_reaches_exec(self) -> None:
        # The regression test for the real defect: before check_source existed, this wrote a file.
        proof = ROOT / "PROOF_OF_ESCAPE.txt"
        self.addCleanup(lambda: proof.exists() and proof.unlink())
        self.assertNotEqual(check_source(NAMESPACE_ESCAPE), "", "the escape passed the whitelist")
        # It fails on whichever disallowed node `ast.walk` reaches first; what matters is that the
        # attribute chain it needs is not reachable at all.
        self.assertIn("Attribute", check_source("def sum_evens(n):\n    return ().__class__.__mro__\n"))
        passed, detail = _run_tests(NAMESPACE_ESCAPE)
        self.assertFalse(passed)
        self.assertIn("refused before running", detail)
        self.assertFalse(proof.exists(), "model-proposed source escaped the namespace and wrote a file")


class CodingAgentExampleTests(unittest.TestCase):
    def test_a_correct_fix_on_the_first_try_stops_on_the_next_turn(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": CORRECT_SOURCE})]),
                StubResponse(text="Fixed: the condition should check for even numbers, n % 2 == 0."),
            ]
        )
        tracer = Tracer(example="coding_agents", level=5, model_id="stub-1")
        answer = run(TASK, model, None, tracer)
        # one model decision to propose the edit, one to stop: both decided_by "model"
        self.assertEqual(tracer.model_decided_count(), 2)
        self.assertEqual(answer.citations, [FUNC_NAME])
        self.assertIn("even", answer.text)

    def test_a_wrong_fix_then_a_right_one_takes_three_model_decisions(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": STILL_BROKEN_SOURCE})]),
                StubResponse(tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": CORRECT_SOURCE})]),
                StubResponse(text="That fixed it."),
            ]
        )
        tracer = Tracer(example="coding_agents", level=5, model_id="stub-1")
        answer = run(TASK, model, None, tracer, max_steps=5)
        self.assertEqual(tracer.model_decided_count(), 3)
        self.assertEqual(answer.citations, [FUNC_NAME])
        test_steps = [s for s in tracer.steps if s.title.startswith("Run the test against")]
        self.assertEqual(len(test_steps), 2)
        self.assertIn("returned", test_steps[0].detail, "the first, wrong fix should report why it failed")
        self.assertIn("passed", test_steps[1].detail)

    def test_running_the_proposed_code_is_always_code(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": CORRECT_SOURCE})]),
                StubResponse(text="Done."),
            ]
        )
        tracer = Tracer(example="coding_agents", level=5, model_id="stub-1")
        run(TASK, model, None, tracer)
        run_steps = [s for s in tracer.steps if s.title.startswith("Run the")]
        self.assertTrue(run_steps)
        for step in run_steps:
            self.assertEqual(step.decided_by, "code")
            self.assertEqual(step.kind, "code")

    def test_step_cap_forces_a_stop_when_the_model_never_fixes_it(self) -> None:
        model = StubModel(
            lambda messages, tools: StubResponse(
                tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": STILL_BROKEN_SOURCE})]
            ),
            model_id="stub-loop",
        )
        tracer = Tracer(example="coding_agents", level=5, model_id="stub-loop")
        answer = run(TASK, model, None, tracer, max_steps=3)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertEqual(forced[0].decided_by, "code")
        self.assertIn("step cap", forced[0].detail)
        self.assertEqual(answer.citations, [], "the function was never actually fixed")
        propose_steps = [s for s in tracer.steps if s.title == "Model proposes an edit"]
        self.assertEqual(len(propose_steps), 3)

    def test_token_budget_forces_a_stop_before_the_step_cap(self) -> None:
        model = StubModel(
            lambda messages, tools: StubResponse(
                tool_calls=[ToolCall(name="propose_edit", arguments={"new_source": STILL_BROKEN_SOURCE})]
            ),
            model_id="stub-loop",
        )
        tracer = Tracer(example="coding_agents", level=5, model_id="stub-loop")
        run(TASK, model, None, tracer, max_steps=50, max_tokens=1)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        self.assertLess(len(tracer.steps), 10)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.coding_agents.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 5)


if __name__ == "__main__":
    unittest.main()
