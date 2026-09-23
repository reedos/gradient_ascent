"""Tests for scripts/eval_run.py: dry mode, caching, the budget stop, stub refusal, and scoring."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import eval_run  # noqa: E402
from examples.common.model import StubEmbedder, StubModel, StubResponse, ToolCall  # noqa: E402

# These tests drive command-line entry points, which print what they did. Capturing stdout for
# the module keeps a real failure readable: without it one run of the suite buries its assertion
# messages under several screens of corpus text and "wrote ..." lines. stderr is left alone, so a
# traceback still reaches the terminal.
_STDOUT: contextlib.AbstractContextManager | None = None


def setUpModule() -> None:
    global _STDOUT
    _STDOUT = contextlib.redirect_stdout(io.StringIO())
    _STDOUT.__enter__()


def tearDownModule() -> None:
    if _STDOUT is not None:
        _STDOUT.__exit__(None, None, None)


CORPUS_DIR = ROOT / "evals" / "corpus"


def _tiny_questions() -> list[dict]:
    """A small, self-contained question set (not evals/questions.json) so grading logic is
    tested against answers this file controls, independent of the real corpus content."""
    return [
        {
            "id": "T1",
            "kind": "lookup",
            "question": "How often should the DW-300's filter be cleaned?",
            "answer": "Every 30 cycles.",
            "accept": ["every 30 cycles", "30 cycles"],
            "must_cite": ["dw300-manual#6"],
            "grading": "exact",
        },
        {
            "id": "T2",
            "kind": "lookup",
            "question": "What voltage does a DR-210 need?",
            "answer": "240V, 30A.",
            "accept": ["this will not match anything the stub says"],
            "must_cite": ["dr210-manual#2"],
            "grading": "exact",
        },
        {
            "id": "T3",
            "kind": "unanswerable",
            "question": "What color is the DW-480?",
            "answer": "Not stated.",
            "accept": ["not stated"],
            "abstain": ["do(es)? not (say|state|give)", "not stated"],
            "reject": ["\\b(stainless|white|black)\\b"],
            "must_cite": [],
            "grading": "rubric",
            "rubric": ["states color is not given", "does not invent a color"],
        },
    ]


def _answer(text: str, citations: list[str] | None = None):
    from examples.common.types import Answer

    return Answer(text=text, citations=citations or [])


class DryRunTests(unittest.TestCase):
    def test_dry_run_never_calls_the_model_and_counts_tokens(self) -> None:
        model = eval_run.DryRunModel("ollama:llama3.1")
        embedder = StubEmbedder()
        summary = eval_run.run_example(
            "rag", model=model, embedder=embedder, grader=None, questions=_tiny_questions()[:1], stub=False, dry=True
        )
        self.assertTrue(summary["dry"])
        self.assertGreater(summary["tokens_in"], 0)
        self.assertGreater(summary["tokens_out"], 0)
        # dry mode never grades; there is no real answer to grade
        self.assertIsNone(summary["score_overall"])

    def test_dry_run_projects_a_tool_call_for_tool_using_levels(self) -> None:
        model = eval_run.DryRunModel("stub")
        summary = eval_run.run_example(
            "function_calling", model=model, embedder=StubEmbedder(), grader=None, questions=_tiny_questions()[:1],
            stub=False, dry=True,
        )
        self.assertGreater(summary["tool_calls"], 0)

    def test_dry_run_drives_the_agent_loop_to_its_cap_rather_than_stopping_early(self) -> None:
        # the projection is an upper bound, so the loop must keep calling tools until the
        # example's own cap stops it, not answer after one round trip
        model = eval_run.DryRunModel("stub")
        summary = eval_run.run_example(
            "agentic_rag", model=model, embedder=StubEmbedder(), grader=None, questions=_tiny_questions()[:1],
            stub=False, dry=True,
        )
        self.assertGreaterEqual(summary["tool_calls"], 2)
        self.assertGreaterEqual(model.calls, 3)

    def test_dry_projection_is_at_least_what_the_same_example_really_spends(self) -> None:
        question = _tiny_questions()[:1]
        projected = eval_run.run_example(
            "agentic_rag", model=eval_run.DryRunModel("stub"), embedder=StubEmbedder(), grader=None,
            questions=question, stub=False, dry=True,
        )
        real = eval_run.run_example(
            "agentic_rag",
            model=StubModel(lambda m, t: StubResponse(text="Every 30 cycles."), model_id="stub-real"),
            embedder=StubEmbedder(), grader=None, questions=question, stub=True, dry=False,
        )
        self.assertGreaterEqual(projected["tokens_in"], real["tokens_in"])
        self.assertGreaterEqual(projected["tokens_out"], real["tokens_out"])

    def test_dry_run_grades_nothing_and_reports_no_ungraded_backlog(self) -> None:
        summary = eval_run.run_example(
            "one_call", model=eval_run.DryRunModel("stub"), embedder=StubEmbedder(), grader=None,
            questions=_tiny_questions(), stub=False, dry=True,
        )
        self.assertIsNone(summary["score_overall"])
        self.assertEqual(summary["ungraded"], 0)


class CachingModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def test_repeated_prompt_hits_the_cache_and_does_not_call_the_inner_model_again(self) -> None:
        calls = []

        def responder(messages, tools):
            del tools
            calls.append(1)
            return StubResponse(text="cached answer")

        inner = StubModel(responder, model_id="stub-cache-test")
        caching = eval_run.CachingModel(inner, self._tmp)
        from examples.common.model import Message

        messages = [Message(role="user", content="same prompt every time")]
        first = caching.complete(messages, max_tokens=50)
        second = caching.complete(messages, max_tokens=50)

        self.assertEqual(len(calls), 1, "the inner model should only be called once")
        self.assertEqual(first.text, second.text)
        self.assertEqual(caching.hits, 1)
        self.assertEqual(caching.misses, 1)

    def test_tool_definitions_are_part_of_the_cache_key(self) -> None:
        calls = []
        inner = StubModel(lambda m, t: (calls.append(1), StubResponse(text="x"))[1], model_id="stub-tools")
        caching = eval_run.CachingModel(inner, self._tmp)
        from examples.common.model import Message

        messages = [Message(role="user", content="same prompt")]
        tools_a = [{"name": "search", "parameters": {"type": "object", "properties": {"query": {}}}}]
        tools_b = [{"name": "read", "parameters": {"type": "object", "properties": {"cite": {}}}}]
        caching.complete(messages, tools=tools_a, max_tokens=50)
        caching.complete(messages, tools=tools_b, max_tokens=50)
        caching.complete(messages, tools=tools_a, max_tokens=50)
        self.assertEqual(len(calls), 2, "a different tool set must be a different cache entry")
        self.assertEqual(caching.hits, 1)

    def test_schema_and_max_tokens_are_part_of_the_cache_key(self) -> None:
        calls = []
        inner = StubModel(lambda m, t: (calls.append(1), StubResponse(text="x"))[1], model_id="stub-schema")
        caching = eval_run.CachingModel(inner, self._tmp)
        from examples.common.model import Message

        messages = [Message(role="user", content="same prompt")]
        caching.complete(messages, schema={"type": "object"}, max_tokens=50)
        caching.complete(messages, schema={"type": "string"}, max_tokens=50)
        caching.complete(messages, schema={"type": "object"}, max_tokens=80)
        self.assertEqual(len(calls), 3)

    def test_two_model_ids_do_not_share_a_cache_entry(self) -> None:
        from examples.common.model import Message

        messages = [Message(role="user", content="same prompt")]
        first = eval_run.CachingModel(StubModel(lambda m, t: StubResponse(text="from A"), model_id="model-a"), self._tmp)
        second = eval_run.CachingModel(StubModel(lambda m, t: StubResponse(text="from B"), model_id="model-b"), self._tmp)
        self.assertEqual(first.complete(messages, max_tokens=50).text, "from A")
        self.assertEqual(second.complete(messages, max_tokens=50).text, "from B")
        self.assertEqual(second.hits, 0, "model-b read model-a's cache entry")

    def test_different_prompts_are_not_confused(self) -> None:
        inner = StubModel(lambda messages, tools: StubResponse(text=messages[-1].content), model_id="stub-echo")
        caching = eval_run.CachingModel(inner, self._tmp)
        from examples.common.model import Message

        a = caching.complete([Message(role="user", content="prompt A")], max_tokens=50)
        b = caching.complete([Message(role="user", content="prompt B")], max_tokens=50)
        self.assertNotEqual(a.text, b.text)
        self.assertEqual(caching.misses, 2)

    def test_backend_settings_are_part_of_the_cache_key(self) -> None:
        """Raising Ollama's reasoning allowance changes what comes back for the same prompt. If
        the key ignored it, a re-run after the fix would replay the old empty replies."""
        from examples.common.model import Message

        messages = [Message(role="user", content="same prompt")]
        calls = []
        tight = StubModel(lambda m, t: (calls.append(1), StubResponse(text=""))[1], model_id="stub-settings")
        tight.settings = {"reasoning_allowance": 0}
        roomy = StubModel(lambda m, t: (calls.append(1), StubResponse(text="44 dBA"))[1], model_id="stub-settings")
        roomy.settings = {"reasoning_allowance": 4096}
        eval_run.CachingModel(tight, self._tmp).complete(messages, max_tokens=50)
        again = eval_run.CachingModel(roomy, self._tmp).complete(messages, max_tokens=50)
        self.assertEqual(again.text, "44 dBA")
        self.assertEqual(len(calls), 2)


class RescoreTests(unittest.TestCase):
    """`--rescore` re-grades cached answers after a grading fix. A plain re-run from cache would
    write the time it took to read the cache over the real run's wall time."""

    def test_a_rescore_never_asks_the_model_for_an_answer(self) -> None:
        from examples.common.model import Message

        stand_in = eval_run.CacheOnly(StubModel(lambda m, t: StubResponse(text="new"), model_id="stub-x"))
        with self.assertRaises(RuntimeError):
            stand_in.complete([Message(role="user", content="a prompt nobody cached")])

    def test_a_rescore_keeps_the_runs_own_timing_date_and_commit(self) -> None:
        previous = {"run_date": "2026-09-23T07:00:00+00:00", "commit": "abc1234", "wall_time_s": 598.4, "tokens_in": 10, "tokens_out": 20}
        rescored = eval_run.carry_run_fields({"wall_time_s": 3.1, "commit": "def5678", "score_overall": 0.9}, previous)
        self.assertEqual(rescored["wall_time_s"], 598.4)
        self.assertEqual(rescored["commit"], "abc1234")
        self.assertEqual(rescored["run_date"], previous["run_date"])
        self.assertEqual(rescored["score_overall"], 0.9)
        self.assertIn("date", rescored["rescored"])


class EmptyCompletionTests(unittest.TestCase):
    def test_an_empty_reply_is_counted_as_a_setup_failure_on_the_result(self) -> None:
        """An empty reply is graded as a wrong answer, which a score cannot tell apart from a real
        one. The result file counts them so a reader knows the score is not yet readable."""
        model = StubModel(lambda m, t: StubResponse(text=""), model_id="stub-empty")
        model.settings = {"reasoning_allowance": 0}
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=None,
            questions=_tiny_questions()[:2], stub=True, dry=False,
        )
        self.assertEqual(summary["empty_completions"], 2)
        self.assertEqual(summary["model_settings"], {"reasoning_allowance": 0})

    def test_a_real_reply_is_not_counted(self) -> None:
        model = StubModel(lambda m, t: StubResponse(text="Every 30 cycles."), model_id="stub-full")
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=None,
            questions=_tiny_questions()[:1], stub=True, dry=False,
        )
        self.assertEqual(summary["empty_completions"], 0)
        self.assertIsNone(summary["model_settings"])


class BudgetStopTests(unittest.TestCase):
    def test_budget_stop_writes_a_partial_result(self) -> None:
        model = StubModel(
            [StubResponse(text=f"answer {i}") for i in range(10)], model_id="stub-budget"
        )
        questions = _tiny_questions() * 4  # 12 questions, ids repeat but that's fine here
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=None, questions=questions, stub=False,
            dry=False, budget_tokens=1,
        )
        self.assertTrue(summary["partial"])
        self.assertLess(summary["questions_run"], summary["questions_total"])


class StubRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        # a separate directory: the response cache must never land in the repo's .local, and
        # must not be mistaken for a result file by the assertions below
        self._cache = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self._cache, ignore_errors=True)

    def test_main_refuses_to_write_a_stub_result_without_allow_stub(self) -> None:
        with tempfile.TemporaryDirectory() as questions_dir:
            questions_path = Path(questions_dir) / "questions.json"
            questions_path.write_text(json.dumps({"questions": _tiny_questions()}), encoding="utf-8")
            code = eval_run.main(
                ["--example", "one_call", "--model", "stub", "--questions", str(questions_path), "--out", str(self._tmp), "--cache-dir", str(self._cache)]
            )
        self.assertEqual(code, 0)
        self.assertEqual(list(self._tmp.glob("**/*.json")), [])

    def test_main_writes_a_stub_marked_result_with_allow_stub(self) -> None:
        with tempfile.TemporaryDirectory() as questions_dir:
            questions_path = Path(questions_dir) / "questions.json"
            questions_path.write_text(json.dumps({"questions": _tiny_questions()}), encoding="utf-8")
            code = eval_run.main(
                [
                    "--example", "one_call", "--model", "stub", "--questions", str(questions_path),
                    "--out", str(self._tmp), "--cache-dir", str(self._cache), "--allow-stub",
                ]
            )
        self.assertEqual(code, 0)
        written = [p for p in self._tmp.glob("one_call/*.json") if not p.name.endswith(".review.json")]
        self.assertEqual(len(written), 1)
        data = json.loads(written[0].read_text(encoding="utf-8"))
        self.assertTrue(data["stub"])

    def test_a_dry_run_writes_no_result_file_at_all(self) -> None:
        with tempfile.TemporaryDirectory() as questions_dir:
            questions_path = Path(questions_dir) / "questions.json"
            questions_path.write_text(json.dumps({"questions": _tiny_questions()}), encoding="utf-8")
            code = eval_run.main(
                [
                    "--example", "one_call", "--model", "stub", "--questions", str(questions_path),
                    "--out", str(self._tmp), "--cache-dir", str(self._cache), "--dry", "--allow-stub",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(list(self._tmp.glob("**/*.json")), [], "--dry must never write a result file")

    def test_a_written_result_carries_provenance_and_sorted_keys(self) -> None:
        with tempfile.TemporaryDirectory() as questions_dir:
            questions_path = Path(questions_dir) / "questions.json"
            questions_path.write_text(json.dumps({"questions": _tiny_questions()}), encoding="utf-8")
            eval_run.main(
                [
                    "--example", "one_call", "--model", "stub", "--questions", str(questions_path),
                    "--out", str(self._tmp), "--cache-dir", str(self._cache), "--allow-stub",
                ]
            )
        written = [p for p in self._tmp.glob("one_call/*.json") if not p.name.endswith(".review.json")]
        raw = written[0].read_text(encoding="utf-8")
        data = json.loads(raw)
        for field in ("model_id", "run_date", "commit", "example", "questions_total", "partial", "stub"):
            self.assertIn(field, data)
        self.assertEqual(list(data), sorted(data), "result keys must be written in a fixed order")
        self.assertTrue(raw.endswith("\n"))
        self.assertNotIn("\r", raw)


class ScoringTests(unittest.TestCase):
    def test_exact_grading_matches_any_accept_string(self) -> None:
        model = StubModel([StubResponse(text="Clean it every 30 cycles, per the manual.")], model_id="stub-score")
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=None, questions=[_tiny_questions()[0]],
            stub=True, dry=False,
        )
        self.assertEqual(summary["score_overall"], 1.0)

    def test_exact_grading_fails_when_no_accept_string_matches(self) -> None:
        model = StubModel([StubResponse(text="I am not sure.")], model_id="stub-score")
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=None, questions=[_tiny_questions()[1]],
            stub=True, dry=False,
        )
        self.assertEqual(summary["score_overall"], 0.0)

    def test_rubric_grading_uses_the_grader_model(self) -> None:
        model = StubModel([StubResponse(text="Not stated in the documents.")], model_id="stub-score")
        pass_grader = StubModel([StubResponse(text="PASS")], model_id="stub-grader-pass")
        fail_grader = StubModel([StubResponse(text="FAIL")], model_id="stub-grader-fail")
        rubric_question = [_tiny_questions()[2]]

        passed = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=pass_grader, questions=rubric_question,
            stub=True, dry=False,
        )
        failed = eval_run.run_example(
            "one_call", model=StubModel([StubResponse(text="Not stated in the documents.")], model_id="stub-score"),
            embedder=StubEmbedder(), grader=fail_grader, questions=rubric_question, stub=True, dry=False,
        )
        self.assertEqual(passed["score_overall"], 1.0)
        self.assertEqual(failed["score_overall"], 0.0)

    def test_rubric_grading_with_no_grader_is_ungraded_not_incorrect(self) -> None:
        model = StubModel([StubResponse(text="The documents do not say.")], model_id="stub-score")
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=None, questions=[_tiny_questions()[2]],
            stub=True, dry=False,
        )
        self.assertIsNone(summary["score_overall"], "an ungraded question must not be scored zero")
        self.assertEqual(summary["ungraded"], 1)
        self.assertIsNone(summary["questions"][0]["correct"])

    def test_citation_hit_rate_rewards_a_matching_citation(self) -> None:
        model = StubModel(
            [StubResponse(text="Every 30 cycles. Sources: dw300-manual#6")], model_id="stub-score"
        )
        summary = eval_run.run_example(
            "rag", model=model, embedder=StubEmbedder(), grader=None, questions=[_tiny_questions()[0]],
            stub=True, dry=False,
        )
        self.assertEqual(summary["citation_hit_rate"], 1.0)

    def test_by_kind_scoring_only_counts_present_kinds(self) -> None:
        model = StubModel(
            [StubResponse(text="Every 30 cycles.")], model_id="stub-score"
        )
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=None, questions=[_tiny_questions()[0]],
            stub=True, dry=False,
        )
        self.assertEqual(summary["score_by_kind"]["lookup"]["n"], 1)
        self.assertIsNone(summary["score_by_kind"]["numeric"]["score"])
        self.assertEqual(summary["score_by_kind"]["numeric"]["n"], 0)


class VerdictParserTests(unittest.TestCase):
    def test_a_clean_verdict_parses(self) -> None:
        self.assertIs(eval_run.parse_verdict("PASS"), True)
        self.assertIs(eval_run.parse_verdict(" fail \n"), False)
        self.assertIs(eval_run.parse_verdict("PASS.\nThe answer covers every item."), True)

    def test_malformed_grader_output_is_ungraded_never_correct(self) -> None:
        for text in [
            "",
            "   ",
            "I think the answer is pretty good overall.",
            "PASSABLE",
            "The verdict is PASS",
            "PASS or FAIL",
            "{\"verdict\": \"PASS\"}",
            "Sure! Here is my assessment:",
        ]:
            self.assertIsNone(eval_run.parse_verdict(text), f"{text!r} should be ungraded")

    def test_a_grader_that_returns_prose_leaves_the_question_ungraded(self) -> None:
        model = StubModel([StubResponse(text="Not stated in the documents.")], model_id="stub-score")
        chatty = StubModel([StubResponse(text="Well, it depends on how you read item two.")], model_id="stub-chatty")
        summary = eval_run.run_example(
            "one_call", model=model, embedder=StubEmbedder(), grader=chatty, questions=[_tiny_questions()[2]],
            stub=True, dry=False,
        )
        self.assertEqual(summary["ungraded"], 1)
        self.assertIsNone(summary["score_overall"])


class UnanswerableGateTests(unittest.TestCase):
    """An unanswerable question is the one place where a confident answer is the failure."""

    def setUp(self) -> None:
        self.question = _tiny_questions()[2]
        self.grader = StubModel(lambda m, t: StubResponse(text="PASS"), model_id="stub-grader")

    def test_an_invented_answer_fails_even_when_the_grader_says_pass(self) -> None:
        verdict = eval_run.grade_question(self.question, _answer("The DW-480 comes in white."), self.grader)
        self.assertIs(verdict, False)

    def test_an_answer_that_never_declines_fails_even_when_the_grader_says_pass(self) -> None:
        verdict = eval_run.grade_question(self.question, _answer("The DW-480 is a 14 place setting unit."), self.grader)
        self.assertIs(verdict, False)

    def test_a_declining_answer_passes(self) -> None:
        verdict = eval_run.grade_question(self.question, _answer("The documents do not give a color."), self.grader)
        self.assertIs(verdict, True)

    def test_the_gates_run_before_the_grader_is_called(self) -> None:
        calls = []

        def counting(messages, tools):
            calls.append(1)
            return StubResponse(text="PASS")

        grader = StubModel(counting, model_id="stub-grader")
        eval_run.grade_question(self.question, _answer("It is black."), grader)
        self.assertEqual(calls, [], "a hallucinated answer should not cost a grader call")

    def test_every_real_unanswerable_question_passes_its_own_gates(self) -> None:
        questions = eval_run.load_questions(ROOT / "evals" / "questions.json", kind="unanswerable")
        self.assertEqual(len(questions), 12)
        for q in questions:
            self.assertTrue(q["abstain"], f"{q['id']} has no abstain patterns")
            self.assertFalse(
                eval_run.abstention_failure(q, q["answer"]),
                f"{q['id']}: its own reference answer fails the abstention gate",
            )

    def test_an_abbreviated_unit_is_the_same_answer_and_a_longer_number_is_not(self) -> None:
        """The first live run worked C09 out as "35 ft - 25 ft = 10 ft" and failed, because the
        pattern only took "10 feet". The number must still stand alone: "110 ft" is not 10."""
        c09 = next(q for q in eval_run.load_questions(ROOT / "evals" / "questions.json") if q["id"] == "C09")
        self.assertTrue(eval_run.grade_exact(c09, "35 ft - 25 ft = 10 ft"))
        self.assertFalse(eval_run.grade_exact(c09, "The difference is 110 ft."))

    def test_the_answers_the_first_agentic_run_gave_are_graded_as_what_they_are(self) -> None:
        """Real answers from the first agentic_rag run (09/23/2026) that the grading misread: two
        correct answers worded differently, and four clean refusals. Each is paired with the
        invention a pattern must still catch."""
        qs = {q["id"]: q for q in eval_run.load_questions(ROOT / "evals" / "questions.json")}
        self.assertTrue(eval_run.grade_exact(qs["L04"], "**Dedicated 240 V, 30 A circuit** with a 4-wire power cord"))
        self.assertTrue(eval_run.grade_exact(qs["N10"], "180 min / 30 min = 6 back-to-back Quick Wash cycles"))
        self.assertFalse(eval_run.grade_exact(qs["N10"], "16 back-to-back Quick Wash cycles"))
        refusals = {
            "U02": "there is no retrievable specification for a maximum stacking height",
            "U05": "No stacking kit for mounting a dryer above a washing machine is listed in the documentation.",
            "U06": "a customer support phone number for Halvorsen is not shown in the retrieved material.",
            "U12": "the shipping weight is not shown in the returned excerpts. I cannot provide a reliable figure.",
        }
        for qid, text in refusals.items():
            self.assertFalse(eval_run.abstention_failure(qs[qid], text), f"{qid}: a clean refusal failed the gate")
        self.assertTrue(eval_run.abstention_failure(qs["U06"], "It is not shown here, but call 555-201-3040."))

    def test_a_plain_the_sources_do_not_contain_refusal_passes_every_gate(self) -> None:
        """The first live run (09/22/2026) answered 11 of 12 unanswerable questions with a clean
        refusal worded "The provided sources do not contain ...", and the gate failed all 11
        because "contain" was not in its verb list: the result read as a 92% invention rate."""
        for q in eval_run.load_questions(ROOT / "evals" / "questions.json", kind="unanswerable"):
            for text in (
                "The provided sources do not contain any information about that.",
                "The documents don't cover this.",
            ):
                self.assertFalse(eval_run.abstention_failure(q, text), f"{q['id']}: a clean refusal failed the gate: {text!r}")

    def test_a_plausible_invention_fails_each_real_unanswerable_question(self) -> None:
        inventions = {
            "U01": "The DW-480 is available in stainless.",
            "U02": "The maximum stacking height is 16 inches.",
            "U03": "The DR-210 runs at 62 dBA.",
            "U04": "The DW-300 has a suggested retail price of $649.",
            "U05": "Yes, stacking kit HLV-9010 is available.",
            "U06": "Call Halvorsen support on 555-201-3040.",
            "U07": "Halvorsen dryers are rated to 10,000 feet.",
            "U09": "The dispenser holds 110 ml of rinse aid.",
            "U10": "Press and hold Start for five seconds.",
            "U11": "About 120,000 units were sold before the recall.",
            "U12": "Shipping weight is 132 lb.",
        }
        questions = {q["id"]: q for q in eval_run.load_questions(ROOT / "evals" / "questions.json", kind="unanswerable")}
        for qid, text in inventions.items():
            self.assertTrue(
                eval_run.abstention_failure(questions[qid], text),
                f"{qid}: invented answer {text!r} was not caught",
            )


class ExactGradingTests(unittest.TestCase):
    def test_require_patterns_must_all_match(self) -> None:
        question = {
            "id": "X", "kind": "multi_hop", "grading": "exact",
            "accept": ["HLV-2205"], "require": ["\\$?52\\.00"], "must_cite": [],
        }
        self.assertTrue(eval_run.grade_exact(question, "HLV-2205, which costs $52.00."))
        self.assertFalse(eval_run.grade_exact(question, "The part is HLV-2205."), "require was not enforced")

    def test_a_right_number_in_a_wrong_statement_does_not_pass(self) -> None:
        # the number is present, but attached to the wrong part
        question = {
            "id": "X", "kind": "multi_hop", "grading": "exact",
            "accept": ["HLV-2205"], "require": ["HLV-2205[^.]{0,40}\\$?52\\.00"], "must_cite": [],
        }
        self.assertFalse(eval_run.grade_exact(question, "HLV-2201 costs $52.00, and HLV-2205 is a drain pump."))

    def test_reject_overrides_an_accept_match(self) -> None:
        question = {
            "id": "X", "kind": "lookup", "grading": "exact",
            "accept": ["25 feet"], "reject": ["35 feet"], "must_cite": [],
        }
        self.assertTrue(eval_run.grade_exact(question, "The maximum is 25 feet."))
        self.assertFalse(eval_run.grade_exact(question, "The manual says 35 feet; the bulletin says 25 feet."))

    def test_every_exact_question_grades_its_own_reference_answer_correct(self) -> None:
        for q in eval_run.load_questions(ROOT / "evals" / "questions.json"):
            if q["grading"] != "exact":
                continue
            self.assertIs(
                eval_run.grade_question(q, _answer(q["answer"]), None),
                True,
                f"{q['id']}: reference answer {q['answer']!r} fails its own grading",
            )


class CitationNormalizationTests(unittest.TestCase):
    def test_equivalent_spellings_normalize_to_the_same_citation(self) -> None:
        for spelling in [
            "dw300-manual#3",
            "DW300-manual#3",
            "dw300-manual.md#3",
            "evals/corpus/dw300-manual.md#3",
            "dw300-manual #3",
            "dw300-manual, section 3",
            "dw300-manual § 3",
        ]:
            self.assertEqual(eval_run.normalize_cite(spelling), "dw300-manual#3", spelling)

    def test_different_sections_do_not_collide(self) -> None:
        self.assertNotEqual(eval_run.normalize_cite("dw300-manual#3"), eval_run.normalize_cite("dw300-manual#4"))

    def test_citation_hit_uses_normalized_comparison(self) -> None:
        question = {"id": "X", "kind": "lookup", "must_cite": ["dw300-manual#3", "parts-list#2"]}
        hit = eval_run.citation_hit(question, _answer("x", ["DW300-manual.md#3", "parts-list#2"]))
        self.assertEqual(hit, 1.0)

    def test_citation_hit_is_none_when_nothing_must_be_cited(self) -> None:
        self.assertIsNone(eval_run.citation_hit({"id": "X", "kind": "unanswerable", "must_cite": []}, _answer("x")))


class ReviewSampleTests(unittest.TestCase):
    def test_sample_for_review_is_about_ten_percent(self) -> None:
        items = [{"id": i} for i in range(40)]
        sampled = eval_run.sample_for_review(items)
        self.assertEqual(len(sampled), 4)

    def test_sample_for_review_handles_empty_input(self) -> None:
        self.assertEqual(eval_run.sample_for_review([]), [])

    def test_sample_for_review_is_deterministic_for_a_seed(self) -> None:
        items = [{"id": i} for i in range(60)]
        first = eval_run.sample_for_review(items, seed=7)
        second = eval_run.sample_for_review(items, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)

    def test_a_different_seed_draws_a_different_sample(self) -> None:
        items = [{"id": i} for i in range(60)]
        self.assertNotEqual(eval_run.sample_for_review(items, seed=1), eval_run.sample_for_review(items, seed=2))

    def test_the_sample_is_never_empty_when_there_is_anything_to_review(self) -> None:
        self.assertEqual(len(eval_run.sample_for_review([{"id": 1}])), 1)


class ExampleRegistrationTests(unittest.TestCase):
    """Which examples the question set scores, and which it refuses to score.

    The rule: an example is scored when it does the question set's own task -- one question about
    the synthetic corpus in, one answer with citations out. Everything else is refused with a
    reason. The test that matters most is the last one: a new example under `examples/` has to be
    put in one list or the other, so nobody can add one and leave it silently unscored.
    """

    def test_the_two_lists_do_not_overlap(self) -> None:
        self.assertEqual(set(eval_run.EXAMPLE_NAMES) & set(eval_run.NOT_SCORED), set())

    def test_every_example_directory_is_classified(self) -> None:
        on_disk = {
            p.name
            for p in (ROOT / "examples").iterdir()
            if p.is_dir() and (p / "run.py").exists()
        }
        classified = set(eval_run.EXAMPLE_NAMES) | set(eval_run.NOT_SCORED)
        self.assertEqual(
            on_disk - classified,
            set(),
            "a new example must be added to EXAMPLE_NAMES or to NOT_SCORED with a reason",
        )
        self.assertEqual(classified - on_disk, set(), "a listed example has no examples/<name>/run.py")

    def test_every_scored_example_answers_the_question_it_was_asked(self) -> None:
        """Not 'it runs': the runner's contract is an `Answer` whose text is about this
        question. A scripted stub answers one corpus fact; whatever the example does around the
        model, the fact has to survive into the answer text for the graders to see it."""
        question = _tiny_questions()[0]
        for name in eval_run.EXAMPLE_NAMES:
            with self.subTest(example=name):
                run_fn, level = eval_run.load_run_fn(name)
                self.assertIsInstance(level, int)
                model = StubModel(
                    lambda m, t: StubResponse(text="Every 30 cycles. Sources: dw300-manual#6"),
                    model_id="stub-registration",
                )
                from examples.common.trace import Tracer

                tracer = Tracer(example=name, level=level, model_id=model.model_id, stub=True)
                answer = run_fn(question["question"], model, StubEmbedder(), tracer)
                self.assertIsInstance(answer.text, str)
                self.assertIsInstance(answer.citations, list)
                # levels 0 to 3 decide nothing with the model; 4 and 5 may
                if level <= 3:
                    self.assertEqual(tracer.model_decided_count(), 0, f"{name} recorded a model decision below level 4")

    def test_every_scored_example_survives_a_dry_projection(self) -> None:
        for name in eval_run.EXAMPLE_NAMES:
            with self.subTest(example=name):
                _, level = eval_run.load_run_fn(name)
                summary = eval_run.run_example(
                    name, model=eval_run.DryRunModel("ollama:llama3.1"), embedder=StubEmbedder(),
                    grader=None, questions=_tiny_questions()[:1], stub=False, dry=True,
                )
                self.assertTrue(summary["dry"])
                self.assertEqual(summary["questions_run"], 1)
                if level == 0:
                    # level 0 calls no model, so a projection of zero is the right answer
                    self.assertEqual(summary["tokens_in"], 0)
                    self.assertEqual(summary["tokens_out"], 0)
                else:
                    self.assertGreater(summary["tokens_in"], 0, f"{name} projected no input tokens")
                    self.assertGreater(summary["tokens_out"], 0, f"{name} projected no output tokens")

    def test_every_refusal_reason_says_what_would_be_measured_instead(self) -> None:
        for name, reason in eval_run.NOT_SCORED.items():
            with self.subTest(example=name):
                self.assertIn("easure", reason, f"{name}'s reason does not say what to measure instead")
                self.assertGreater(len(reason), 80)

    def test_asking_to_score_an_unmeasured_example_is_refused_with_the_reason(self) -> None:
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as tmp:
            questions_path = Path(tmp) / "questions.json"
            questions_path.write_text(json.dumps({"questions": _tiny_questions()}), encoding="utf-8")
            out_dir = Path(tmp) / "results"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = eval_run.main(
                    ["--example", "memory", "--model", "stub", "--questions", str(questions_path),
                     "--out", str(out_dir), "--allow-stub"]
                )
            printed = buffer.getvalue()
            self.assertEqual(code, 2)
            self.assertIn("not part of the question-set eval", printed)
            self.assertIn("empty store", printed)
            self.assertFalse(out_dir.exists(), "a refused example must not write a result file")

    def test_all_runs_only_the_scored_examples(self) -> None:
        args = eval_run.build_args(["--example", "all", "--model", "stub"])
        self.assertEqual(args.example, "all")
        self.assertNotIn("memory", eval_run.EXAMPLE_NAMES)


class LoadQuestionsTests(unittest.TestCase):
    def test_kind_filter_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q.json"
            path.write_text(json.dumps({"questions": _tiny_questions()}), encoding="utf-8")
            lookups = eval_run.load_questions(path, kind="lookup")
            self.assertEqual(len(lookups), 2)
            limited = eval_run.load_questions(path, limit=1)
            self.assertEqual(len(limited), 1)


if __name__ == "__main__":
    unittest.main()
