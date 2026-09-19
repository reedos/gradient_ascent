"""Tests for examples/bench_test_data_by_conversation: the model writes one analysis snippet,
a sandbox runs it against the real bench CSVs, and the final answer is built from what came back.

Three things are checked beyond the trace shape every other level-4 example gets (see
tests/test_example_function_calling.py for that pattern):

1. The three illustrated snippets, run for real against `evals/bench/data/retest-2026-08-31.csv`,
   `evals/bench/data/soak-2026-08-27.csv` and `evals/bench/data/characterization-2026-09.csv`,
   produce the exact figures the recipe page states.
   Every number is also recomputed independently here with plain `csv` and `statistics`, the way
   `tests/test_example_bench_limits_without_a_model.py` checks its own module's numbers, so a
   shared bug in the loader cannot hide behind a test that only calls the module under test.
2. The range check in `_as_plausible_volts` catches the retest export's millivolts-under-a-volts-
   header column before any snippet runs, on its own and end to end through `run`, and reports
   the characterization sweep's own volts column as already plausible rather than staying silent.
3. The sandbox's grammar refuses every spelling of "run something other than analysis code" in
   `WhitelistBypassTests`, the same shape `tests/test_example_code_execution.py` uses for its own
   arithmetic-only evaluator.
"""
from __future__ import annotations

import ast
import csv
import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import CHARACTERIZATION_CSV, RETEST_CSV, SOAK_CSV  # noqa: E402
from examples.bench_test_data_by_conversation.__main__ import SCRIPTED  # noqa: E402
from examples.bench_test_data_by_conversation.run import (  # noqa: E402
    LEVEL,
    MAX_LOOP_DEPTH,
    MAX_NODES,
    MAX_SOURCE_CHARS,
    ImplausibleUnits,
    UnsafeCode,
    _as_plausible_volts,
    _load_tables,
    _max_loop_depth,
    _parse_characterization_rows,
    _parse_retest_rows,
    _parse_soak_rows,
    _used_tables,
    run,
    run_snippet,
)
from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

# The two snippets the recipe page illustrates, verified against a real run before being written
# into a test: see the docstrings below for the independent recomputation each is checked against.
RETEST_SNIPPET = """
fails = [r for r in TABLES["retest"] if not (4.9500 <= r["value_v"] <= 5.0500)]
passing = [r["value_v"] for r in TABLES["retest"] if 4.9500 <= r["value_v"] <= 5.0500]
result = {
    "n": len(TABLES["retest"]),
    "n_pass": len(passing),
    "n_fail": len(fails),
    "fail_serials": sorted(r["serial"] for r in fails),
    "pass_mean_v": round(mean(passing), 4),
    "pass_min_v": min(passing),
    "pass_max_v": max(passing),
}
"""

SOAK_SNIPPET = """
serials = sorted(set(r["serial"] for r in TABLES["soak"]))
result = {}
for s in serials:
    triples = [(r["elapsed_min"], r["vout_v"], r["tcase_c"]) for r in TABLES["soak"] if r["serial"] == s]
    first = min(triples)
    last = max(triples)
    result[s] = {
        "vout_drop_mv": round((first[1] - last[1]) * 1000, 1),
        "tcase_rise_c": round(last[2] - first[2], 1),
    }
"""

# The characterization question: a board cannot put out more power than it takes in, so any block
# of the sweep where it appears to is a block recorded at a condition it was not taken at
# (docs/THE-BENCH.md Story D). 179 syntax nodes against the sandbox's 200 and two loops deep
# against its cap of two, so the grammar runs it unchanged rather than the cap being widened for
# it; `test_the_characterization_snippet_stays_inside_the_sandboxs_own_bounds` pins both.
POWER_BALANCE_SNIPPET = """
rows = TABLES["characterization"]
result = []
for p in sorted(set((r["serial"], r["tamb_c"], r["vin_v"], r["iout_a"]) for r in rows)):
    block = [r for r in rows if (r["serial"], r["tamb_c"], r["vin_v"], r["iout_a"]) == p]
    iin = mean([r["iin_a"] for r in block])
    pin = p[2] * iin
    pout = p[3] * mean([r["vout_v"] for r in block])
    if pin < pout:
        result = result + [[p, round(iin, 4), round(pin, 2), round(pout, 2)]]
"""


#: The command's own scripted sequence: write RETEST_SNIPPET, then turn its result into a short
#: answer. Pinned against SCRIPTED in
#: examples/bench_test_data_by_conversation/__main__.py so the two cannot drift apart.
SEQUENCE = [
    StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": RETEST_SNIPPET})]),
    (
        "Fifteen of the eighteen retested boards are within spec; three still fail: "
        "SRB5030-2608-0052, SRB5030-2608-0063 and SRB5030-2608-0178."
    ),
]


def _tracer() -> Tracer:
    return Tracer(example="bench_test_data_by_conversation", level=LEVEL, model_id="stub-1")


class RangeCheckTests(unittest.TestCase):
    """`_as_plausible_volts`: the guard this recipe exists to teach, checked on its own before
    anything about the model or the sandbox is involved."""

    def test_the_real_retest_export_is_millivolts_under_a_volts_header(self) -> None:
        rows, note = _as_plausible_volts(_parse_retest_rows())
        # Recomputed independently, straight from the CSV, not by calling the module's own loader
        # a second time.
        with RETEST_CSV.open(newline="", encoding="utf-8") as handle:
            raw = [float(r["value_v"]) for r in csv.DictReader(handle)]
        expected_bad = sum(1 for v in raw if abs(v) > 40.0)
        self.assertEqual(expected_bad, 16)
        self.assertIn("16 of 18", note)
        self.assertIn("millivolts", note)
        corrected = [r["value_v"] for r in rows]
        self.assertEqual(corrected, [v / 1000.0 for v in raw])
        passing = [v for v in corrected if 4.9500 <= v <= 5.0500]
        self.assertEqual(len(passing), 15)
        self.assertAlmostEqual(statistics.fmean(passing), 4.984046666666666)
        fail_serials = sorted(r["serial"] for r in rows if not (4.9500 <= r["value_v"] <= 5.0500))
        self.assertEqual(fail_serials, ["SRB5030-2608-0052", "SRB5030-2608-0063", "SRB5030-2608-0178"])

    def test_a_column_already_plausible_as_volts_is_left_alone(self) -> None:
        rows = [{"value_v": 4.99}, {"value_v": 5.01}, {"value_v": 0.0}]
        corrected, note = _as_plausible_volts(rows)
        self.assertEqual(note, "")
        self.assertEqual(corrected, rows)

    def test_a_column_still_implausible_after_dividing_by_1000_is_refused_not_guessed(self) -> None:
        with self.assertRaises(ImplausibleUnits) as caught:
            _as_plausible_volts([{"value_v": 999_999.0}, {"value_v": 5.0}])
        self.assertIn("refusing to guess", str(caught.exception))

    def test_the_check_runs_before_any_snippet_regardless_of_the_question(self) -> None:
        tables, note = _load_tables()
        self.assertIn("millivolts", note)
        self.assertTrue(all(abs(r["value_v"]) <= 40.0 for r in tables["retest"]))

    def test_a_volts_column_that_passes_the_check_is_reported_as_passing_it(self) -> None:
        """The check runs on the characterization sweep's `vout_v` too, finds nothing to correct,
        and says so. A guard that only ever speaks when it fires cannot be told apart from one
        that was never wired up."""
        rows, note = _as_plausible_volts(_parse_characterization_rows(), field="vout_v")
        self.assertEqual(note, "")
        self.assertEqual(len(rows), 900)
        _, loaded_note = _load_tables()
        self.assertIn("characterization sweep's vout_v column was already plausible", loaded_note)


class RealDataSnippetTests(unittest.TestCase):
    """The two illustrated snippets, run for real by `run_snippet` and checked against numbers
    recomputed independently in this file, not against the module's own prior output."""

    def test_the_retest_snippet_matches_an_independent_recomputation(self) -> None:
        tables, _ = _load_tables()
        result = run_snippet(RETEST_SNIPPET, tables)
        self.assertEqual(result["n"], 18)
        self.assertEqual(result["n_pass"], 15)
        self.assertEqual(result["n_fail"], 3)
        self.assertEqual(result["fail_serials"], ["SRB5030-2608-0052", "SRB5030-2608-0063", "SRB5030-2608-0178"])
        self.assertEqual(result["pass_mean_v"], 4.984)
        self.assertEqual(result["pass_min_v"], 4.9678)
        self.assertEqual(result["pass_max_v"], 5.0077)

    def test_the_soak_snippet_matches_docs_the_bench_story_3(self) -> None:
        # Independently recomputed straight from the CSV, first and last reading per serial by
        # elapsed_min, the same numbers docs/THE-BENCH.md Story 3 states.
        with SOAK_CSV.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        by_serial: dict[str, list[tuple[int, float, float]]] = {}
        for r in rows:
            by_serial.setdefault(r["serial"], []).append(
                (int(r["elapsed_min"]), float(r["vout_v"]), float(r["tcase_c"]))
            )
        expected = {}
        for serial, triples in by_serial.items():
            first, last = min(triples), max(triples)
            expected[serial] = {
                "vout_drop_mv": round((first[1] - last[1]) * 1000, 1),
                "tcase_rise_c": round(last[2] - first[2], 1),
            }

        tables, _ = _load_tables()
        result = run_snippet(SOAK_SNIPPET, tables)
        self.assertEqual(result, expected)
        self.assertEqual(result["SRB5030-2608-0121"]["vout_drop_mv"], 75.5)
        self.assertEqual(result["SRB5030-2608-0121"]["tcase_rise_c"], 67.1)
        # the two healthy units drift much less
        self.assertLess(result["SRB5030-2608-0044"]["vout_drop_mv"], 5.0)
        self.assertLess(result["SRB5030-2608-0166"]["vout_drop_mv"], 5.0)

    def test_the_power_balance_snippet_finds_the_one_impossible_block(self) -> None:
        """Every figure the recipe page states for the characterization question, recomputed here
        straight from the CSV with `csv` and `statistics` before the sandbox is asked for it.

        Input power should be a little more than output power; a block where it is less is not a
        board that gained energy, it is a block filed under a condition it was not taken at. The
        page states one block, 0.6729 A of input current where the same point on the other four
        boards draws 1.3123 A, 8.08 W in against 14.95 W out.
        """
        with CHARACTERIZATION_CSV.open(newline="", encoding="utf-8") as handle:
            raw = list(csv.DictReader(handle))
        by_point: dict[tuple, list[dict]] = {}
        for row in raw:
            key = (row["serial"], row["tamb_c"], row["vin_v"], row["iout_a"])
            by_point.setdefault(key, []).append(row)
        impossible = []
        for (serial, tamb, vin, iout), block in by_point.items():
            iin = statistics.fmean(float(r["iin_a"]) for r in block)
            pin = float(vin) * iin
            pout = float(iout) * statistics.fmean(float(r["vout_v"]) for r in block)
            if pin < pout:
                impossible.append((serial, float(tamb), float(vin), float(iout), iin, pin, pout))
        self.assertEqual(len(impossible), 1, "exactly one block in 180, and the rest are sound")
        serial, tamb, vin, iout, iin, pin, pout = impossible[0]
        self.assertEqual((serial, tamb, vin, iout), ("SRB5030-2609-0001", 25.0, 12.0, 3.0))
        self.assertEqual(round(iin, 4), 0.6729)
        self.assertEqual(round(pin, 2), 8.08)
        self.assertEqual(round(pout, 2), 14.95)

        peers = statistics.fmean(
            float(r["iin_a"])
            for r in raw
            if r["serial"] != serial and r["tamb_c"] == "25.0" and r["vin_v"] == "12.0" and r["iout_a"] == "3.000"
        )
        self.assertEqual(round(peers, 4), 1.3123, "the same point on the other four boards")

        tables, _ = _load_tables()
        self.assertEqual(len(tables["characterization"]), 900)
        result = run_snippet(POWER_BALANCE_SNIPPET, tables)
        self.assertEqual(result, [[(serial, tamb, vin, iout), 0.6729, 8.08, 14.95]])

    def test_the_characterization_snippet_stays_inside_the_sandboxs_own_bounds(self) -> None:
        """The sandbox's caps were not widened to let this question through: the snippet fits the
        200-node and two-loop bounds the grammar already had."""
        tree = ast.parse(POWER_BALANCE_SNIPPET)
        self.assertEqual(len(list(ast.walk(tree))), 179)
        self.assertLessEqual(len(list(ast.walk(tree))), MAX_NODES)
        self.assertEqual(_max_loop_depth(tree), MAX_LOOP_DEPTH)
        self.assertEqual(_used_tables(POWER_BALANCE_SNIPPET), ["characterization"])

    def test_used_tables_is_read_from_the_snippets_own_syntax(self) -> None:
        self.assertEqual(_used_tables(RETEST_SNIPPET), ["retest"])
        self.assertEqual(_used_tables(SOAK_SNIPPET), ["soak"])
        self.assertEqual(_used_tables("result = 1"), [])
        self.assertEqual(_used_tables("not valid python ("), [])

    def test_a_snippet_that_reads_both_tables_cites_both(self) -> None:
        code = 'result = len(TABLES["retest"]) + len(TABLES["soak"])'
        self.assertEqual(_used_tables(code), ["retest", "soak"])


class SandboxUnitTests(unittest.TestCase):
    def test_a_kerror_inside_the_snippet_is_reported_not_raised(self) -> None:
        tables, _ = _load_tables()
        with self.assertRaises(UnsafeCode) as caught:
            run_snippet('result = TABLES["nope"]', tables)
        self.assertIn("KeyError", str(caught.exception))

    def test_a_zero_division_inside_the_snippet_is_reported_not_raised(self) -> None:
        tables, _ = _load_tables()
        with self.assertRaises(UnsafeCode):
            run_snippet("result = 1 / 0", tables)

    def test_loop_depth_at_the_cap_is_allowed_one_past_it_is_not(self) -> None:
        at_cap = 'result = [[x for x in TABLES["soak"]] for y in TABLES["retest"]]'
        self.assertEqual(_max_loop_depth(ast.parse(at_cap)), MAX_LOOP_DEPTH)
        tables, _ = _load_tables()
        run_snippet(at_cap, tables)  # does not raise
        one_more = 'result = [[[x for x in TABLES["soak"]] for y in TABLES["retest"]] for z in TABLES["retest"]]'
        self.assertGreater(_max_loop_depth(ast.parse(one_more)), MAX_LOOP_DEPTH)
        with self.assertRaises(UnsafeCode):
            run_snippet(one_more, tables)


class WhitelistBypassTests(unittest.TestCase):
    """Attempts to get something past the grammar. Every one must come back as `UnsafeCode`, not
    a value and not some other exception -- the same discipline
    tests/test_example_code_execution.py holds `safe_eval` to, extended here because the grammar
    covers statements and comprehensions, not one arithmetic expression."""

    REFUSED = {
        "import": "import os\nresult = 1",
        "dunder attribute on a literal": "result = (1).__class__",
        "attribute chain": "result = ().__class__.__bases__[0].__subclasses__()",
        "attribute method call": 'result = "x".upper()',
        "lambda": "f = lambda: 1\nresult = f()",
        "while loop": "result = 0\nwhile True:\n    result += 1",
        "function def": "def f():\n    return 1\nresult = f()",
        "class def": "class C: pass\nresult = C",
        "eval call": 'result = eval("1")',
        "exec call": 'exec("1")\nresult = 1',
        "open call": 'result = open("x")',
        "dunder import call": 'result = __import__("os")',
        "assign to TABLES": 'TABLES["retest"] = []\nresult = 1',
        "shadow a provided function": "len = 1\nresult = len",
        "f-string": 'result = f"{1}"',
        "walrus": "result = (x := 1)",
        "starred unpack": "a, *b = [1, 2, 3]\nresult = b",
        "global statement": "global x\nresult = 1",
        "dict unpacking": "result = {**TABLES}",
        "keyword argument": "result = round(1.2345, ndigits=2)",
        "unknown function": "result = unknown_func(1)",
        "no result assigned": "x = 1",
        "empty snippet": "",
        "not valid python": "this is not : code(",
        "exponentiation is off the whitelist too": "result = 2 ** 64",
        "nested loops past the depth cap": (
            'result = [[[x for x in TABLES["retest"]] for y in TABLES["retest"]] for z in TABLES["retest"]]'
        ),
    }

    def test_every_bypass_attempt_is_refused_as_unsafe_code(self) -> None:
        tables, _ = _load_tables()
        for name, code in self.REFUSED.items():
            with self.subTest(attempt=name):
                with self.assertRaises(UnsafeCode):
                    run_snippet(code, tables)

    def test_a_very_long_snippet_is_refused_before_it_is_parsed(self) -> None:
        tables, _ = _load_tables()
        with self.assertRaises(UnsafeCode) as caught:
            run_snippet("result = 1" + "+1" * MAX_SOURCE_CHARS, tables)
        self.assertIn("characters", str(caught.exception))

    def test_a_snippet_with_too_many_nodes_is_refused(self) -> None:
        tables, _ = _load_tables()
        many_terms = "result = 1" + "".join(f"+{i}" for i in range(MAX_NODES))
        with self.assertRaises(UnsafeCode) as caught:
            run_snippet(many_terms, tables)
        self.assertIn("syntax nodes", str(caught.exception))

    def test_the_module_never_calls_pythons_own_eval(self) -> None:
        """`run_snippet` does call `exec`, unlike `code_execution.safe_eval`; the claim this
        module makes is narrower and this test checks exactly that claim: `eval` is never called,
        and `exec` is only ever called on the output of `compile`, never on raw text."""
        source = (ROOT / "examples" / "bench_test_data_by_conversation" / "run.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertNotIn("eval", called)
        exec_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "exec"]
        self.assertEqual(len(exec_calls), 1)
        first_arg = exec_calls[0].args[0]
        self.assertIsInstance(first_arg, ast.Call)
        self.assertEqual(first_arg.func.id, "compile")


class RunEndToEndTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.bench_test_data_by_conversation.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 4)

    def test_writing_a_snippet_is_the_only_model_decided_step(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": RETEST_SNIPPET})]),
                StubResponse(
                    text="Fifteen of the eighteen retested boards are within spec; three still fail: "
                    "SRB5030-2608-0052, SRB5030-2608-0063 and SRB5030-2608-0178."
                ),
            ]
        )
        tracer = _tracer()
        answer = run("Do the retested boards actually pass?", model, tracer)
        self.assertEqual(tracer.model_decided_count(), 1)
        decided_by_model = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(decided_by_model), 1)
        self.assertEqual(decided_by_model[0].title, "Model writes analysis code")
        # the range check ran before the model was ever asked anything
        self.assertEqual(tracer.steps[0].title, "Load bench tables, range-check value columns before any analysis")
        self.assertIn("millivolts", tracer.steps[0].detail)
        # the sandbox's own output, not the model's prose, carries the figures
        sandbox_step = next(s for s in tracer.steps if s.title == "Sandbox runs the snippet")
        self.assertIn('"n_fail": 3', sandbox_step.detail)
        self.assertIn("SRB5030-2608-0052", sandbox_step.detail)
        self.assertIn("SRB5030-2608-0052", answer.text)
        self.assertEqual(answer.citations, ["retest-2026-08-31.csv"])

    def test_the_recipe_pages_token_figures_are_what_a_run_actually_counts(self) -> None:
        """The cost section states 617 input tokens and 155 output tokens across the retest
        question's two calls, counted by `examples/common/model.py`'s deterministic estimator and
        not by a provider's tokenizer. The system prompt now describes three tables, so this moves
        when a table is added: that is the point of pinning it here rather than on the page alone.
        """
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": RETEST_SNIPPET})]),
                StubResponse(
                    text="Fifteen of the eighteen retested boards are within spec; three still fail: "
                    "SRB5030-2608-0052, SRB5030-2608-0063 and SRB5030-2608-0178."
                ),
            ]
        )
        tracer = _tracer()
        run("Do the retested boards actually pass?", model, tracer)
        self.assertEqual(sum(s.tokens_in or 0 for s in tracer.steps), 617)
        self.assertEqual(sum(s.tokens_out or 0 for s in tracer.steps), 155)

    def test_the_soak_question_cites_the_soak_csv(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": SOAK_SNIPPET})]),
                StubResponse(
                    text="Unit SRB5030-2608-0121 drops 75.5 mV while its case climbs to 91.7 C; the "
                    "other two settle under 3 mV."
                ),
            ]
        )
        tracer = _tracer()
        answer = run("Did any soak unit fail to settle?", model, tracer)
        self.assertEqual(answer.citations, ["soak-2026-08-27.csv"])
        self.assertIn("75.5", answer.text)

    def test_the_characterization_question_cites_the_sweep(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": POWER_BALANCE_SNIPPET})]),
                StubResponse(
                    text="One block is impossible: SRB5030-2609-0001 at a labeled 12.0 V and "
                    "3.000 A computes 8.08 W in against 14.95 W out."
                ),
            ]
        )
        tracer = _tracer()
        answer = run("Is any block in the sweep impossible?", model, tracer)
        self.assertEqual(answer.citations, ["characterization-2026-09.csv"])
        sandbox_step = next(s for s in tracer.steps if s.title == "Sandbox runs the snippet")
        self.assertIn("SRB5030-2609-0001", sandbox_step.detail)
        self.assertIn("8.08", sandbox_step.detail)

    def test_answering_without_code_is_still_the_one_model_decided_step(self) -> None:
        model = StubModel([StubResponse(text="That is not something these two tables can answer.")])
        tracer = _tracer()
        answer = run("What color is the board?", model, tracer)
        self.assertEqual(tracer.model_decided_count(), 1, "declining to write code is still a model decision")
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "no second call when nothing ran")
        self.assertEqual(answer.citations, [])

    def test_a_second_requested_call_is_dropped_not_run(self) -> None:
        model = StubModel(
            [
                StubResponse(
                    tool_calls=[
                        ToolCall(name="run_python", arguments={"code": 'result = len(TABLES["retest"])'}),
                        ToolCall(name="run_python", arguments={"code": 'result = len(TABLES["soak"])'}),
                    ]
                ),
                StubResponse(text="Eighteen boards were retested."),
            ]
        )
        tracer = _tracer()
        run("How many boards were retested?", model, tracer)
        call_step = next(s for s in tracer.steps if s.title == "Model writes analysis code")
        self.assertIn("dropped 1 further call", call_step.detail)
        self.assertEqual(sum(1 for s in tracer.steps if s.title == "Sandbox runs the snippet"), 1)

    def test_an_unsafe_snippet_is_refused_end_to_end_and_never_reaches_a_second_call(self) -> None:
        model = StubModel(
            [StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": "import os\nresult = 1"})])]
        )
        tracer = _tracer()
        answer = run("Do something unsafe", model, tracer)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "a refusal must not ask the model again")
        self.assertIn("Could not safely run", answer.text)
        self.assertEqual(answer.citations, [])
        refusal = next(s for s in tracer.steps if s.title == "Sandbox refused the snippet")
        self.assertEqual(refusal.decided_by, "code")
        self.assertIn("grammar", refusal.detail)

    def test_tables_can_be_supplied_for_a_deterministic_test_fixture(self) -> None:
        tiny = {"retest": [{"serial": "X", "value_v": 5.0}], "soak": []}
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="run_python", arguments={"code": 'result = len(TABLES["retest"])'})]),
                StubResponse(text="One board."),
            ]
        )
        tracer = _tracer()
        answer = run("How many rows?", model, tracer, tables=tiny)
        self.assertEqual(answer.text, "One board.")


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual(SCRIPTED, SEQUENCE)

    def test_the_scripted_sequence_runs_the_real_retest_snippet(self) -> None:
        model = StubModel([StubResponse(text=e) if isinstance(e, str) else e for e in SEQUENCE])
        tracer = _tracer()
        answer = run("Do the retested boards actually pass?", model, tracer)
        self.assertIn("SRB5030-2608-0052", answer.text)
        self.assertEqual(answer.citations, ["retest-2026-08-31.csv"])
        sandbox_step = next(s for s in tracer.steps if s.title == "Sandbox runs the snippet")
        self.assertIn('"n_fail": 3', sandbox_step.detail)


if __name__ == "__main__":
    unittest.main()
