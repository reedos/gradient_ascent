"""Tests for the corpus, the question set, and the six examples.

Three groups:
  - `CorpusConsistencyTests` is the checker the task called for: every question's `must_cite`
    resolves to a real section, every `accept` string (or, for numeric questions, every
    `corpus_inputs` value) is actually present in the section text it is cited against, every
    numeric question's `compute` expression reproduces its `accept` value from `inputs`, and
    every `unanswerable` question's `absent_terms` really do not appear anywhere in the corpus.
  - `ExampleTraceTests` runs each of the six examples end to end on a scripted `StubModel` and
    checks the trace's `decided_by` pattern matches what that level is supposed to record.
  - `AgenticCapTests` checks the level-5 loop honours its step cap and its token budget.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals import corpus  # noqa: E402
from examples.common import model as model_mod  # noqa: E402
from examples.common import tools  # noqa: E402
from examples.agentic_rag.run import run as agentic_rag_run  # noqa: E402
from examples.common.model import StubEmbedder, StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.function_calling.run import run as function_calling_run  # noqa: E402
from examples.one_call.run import run as one_call_run  # noqa: E402
from examples.order_zero.run import run as order_zero_run  # noqa: E402
from examples.prompt_chaining.run import run as prompt_chaining_run  # noqa: E402
from examples.rag.run import run as rag_run  # noqa: E402

QUESTIONS_PATH = ROOT / "evals" / "questions.json"
CORPUS_DIR = ROOT / "evals" / "corpus"
KINDS = ["lookup", "multi_hop", "numeric", "unanswerable", "conflicting"]

# Every quantity that appears in more than one document, with the complete set of values the
# corpus is allowed to state for it. A typo or a drifting edit shows up here as an extra value.
# The DR-520 vent run is the one deliberate conflict and is checked separately, by document.
SHARED_FACTS = {
    "place settings": (r"(\d+) place setting", {"12", "14"}),
    "dishwasher noise": (r"(\d+) dBA", {"52", "44"}),
    "annual energy use": (r"(\d+) kWh", {"260", "240"}),
    "water per Normal cycle": (r"([\d.]+) gallons of water", {"3.2", "3.0"}),
    "dryer drum size": (r"([\d.]+) cubic (?:foot|feet)", {"7.0", "7.8"}),
    "dryer empty weight": (r"(\d+) lb", {"110", "125", "128"}),
    "lengths in feet": (r"(\d+) feet", {"6", "8", "25", "35"}),
    "vent elbows": (r"up to (\d+) elbows", {"3", "4"}),
    "dishwasher circuit": (r"(\d+)V, (\d+)A grounded", {("120", "15")}),
    "part prices": (r"\$(\d+\.\d\d), fits", {"38.50", "41.00", "46.00", "14.25", "15.75", "57.00", "61.50", "9.75", "13.25", "6.50", "19.99"}),
}

# Names that must never appear: real trademarks and real programme names have no place in a
# synthetic corpus that ships under MIT.
FORBIDDEN_NAMES = [
    "aqua-stop", "aquastop", "energyguide", "energy guide", "bosch", "whirlpool", "maytag",
    "ge appliances", "lg electronics", "samsung", "kitchenaid", "frigidaire",
]


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]


class CorpusConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.questions = load_questions()
        cls.sections = corpus.load_sections(CORPUS_DIR)
        cls.documents = corpus.load_documents(CORPUS_DIR)
        cls.full_text_norm = corpus.normalize_whitespace("\n\n".join(cls.documents.values())).lower()

    def test_corpus_has_twelve_files(self) -> None:
        self.assertEqual(len(self.documents), 12)

    def test_corpus_files_are_300_to_900_words(self) -> None:
        for name, text in self.documents.items():
            words = len(text.split())
            self.assertTrue(300 <= words <= 900, f"{name}.md has {words} words, outside 300-900")

    def test_corpus_files_use_lf_line_endings(self) -> None:
        for path in corpus.corpus_files(CORPUS_DIR):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, f"{path.name} has a CR byte; corpus must be LF only")

    def test_question_set_has_sixty_questions_twelve_per_kind(self) -> None:
        self.assertEqual(len(self.questions), 60)
        counts = {kind: 0 for kind in KINDS}
        for q in self.questions:
            counts[q["kind"]] += 1
        for kind in KINDS:
            self.assertEqual(counts[kind], 12, f"kind {kind} has {counts[kind]} questions, expected 12")

    def test_question_ids_are_unique(self) -> None:
        ids = [q["id"] for q in self.questions]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_question_has_the_required_fields(self) -> None:
        for q in self.questions:
            for field in ("id", "kind", "question", "answer", "accept", "must_cite", "grading"):
                self.assertIn(field, q, f"{q.get('id')} missing {field}")
            self.assertIn(q["grading"], ("exact", "rubric"))
            if q["grading"] == "rubric":
                self.assertIn("rubric", q, f"{q['id']} is rubric-graded but has no rubric")
                self.assertGreaterEqual(len(q["rubric"]), 2)
                self.assertLessEqual(len(q["rubric"]), 4)

    def test_every_must_cite_resolves_to_a_real_section(self) -> None:
        for q in self.questions:
            for cite in q["must_cite"]:
                self.assertIn(cite, self.sections, f"{q['id']} cites unknown section {cite}")

    def test_non_numeric_accept_patterns_appear_in_their_cited_sections(self) -> None:
        # `accept` entries are regexes (eval_run.grade_question searches them), so this is a
        # regex search, not a literal containment check.
        for q in self.questions:
            # A question with `corpus_inputs` states its own grounding: its answer is computed
            # from those corpus literals and does not appear in the documents verbatim.
            if q.get("corpus_inputs") or not q["must_cite"]:
                continue
            text = corpus.normalize_whitespace(corpus.section_text(self.sections, q["must_cite"]))
            for accept in q["accept"]:
                self.assertIsNotNone(
                    re.search(accept, text, re.IGNORECASE),
                    f"{q['id']}: accept pattern {accept!r} matches nothing in {q['must_cite']}",
                )

    def test_every_canonical_answer_is_graded_correct_by_its_own_accept_patterns(self) -> None:
        # The reference answer is the cheapest correct answer a model can give. If it does not
        # pass the question's own grading, the grading is wrong, not the answer.
        for q in self.questions:
            if q["grading"] != "exact":
                continue
            self.assertTrue(
                any(re.search(pattern, q["answer"], re.IGNORECASE) for pattern in q["accept"]),
                f"{q['id']}: canonical answer {q['answer']!r} matches none of {q['accept']}",
            )

    def test_every_corpus_inputs_literal_appears_in_the_cited_sections(self) -> None:
        for q in self.questions:
            text = corpus.normalize_whitespace(corpus.section_text(self.sections, q["must_cite"]))
            for literal in q.get("corpus_inputs", []):
                self.assertIn(
                    corpus.normalize_whitespace(literal),
                    text,
                    f"{q['id']}: corpus_inputs value {literal!r} not found in {q['must_cite']}",
                )

    def test_numeric_questions_recompute_to_their_expected_value(self) -> None:
        for q in self.questions:
            if q["kind"] != "numeric":
                continue
            for field in ("inputs", "compute", "expected", "corpus_inputs"):
                self.assertIn(field, q, f"{q['id']} missing {field}")
            result = eval(q["compute"], {"__builtins__": {}}, q["inputs"])  # noqa: S307 - trusted, repo-authored data
            self.assertAlmostEqual(
                result, q["expected"], places=6, msg=f"{q['id']}: compute() gave {result}, expected {q['expected']}"
            )
            # the expected number must be what the reference answer actually says, in a form the
            # accept pattern recognises: number, units and all
            rendered = f"{q['expected']:g}"
            self.assertRegex(
                q["answer"].replace(",", ""),
                re.escape(rendered) + r"|" + re.escape(f"{q['expected']:.2f}"),
                f"{q['id']}: answer {q['answer']!r} does not state expected value {q['expected']}",
            )
            self.assertTrue(
                any(re.search(p, q["answer"], re.IGNORECASE) for p in q["accept"]),
                f"{q['id']}: canonical answer {q['answer']!r} matches none of {q['accept']}",
            )

    def test_unanswerable_questions_have_no_citations_and_absent_terms_are_absent(self) -> None:
        # Every unanswerable question cites nothing, except when a section explicitly confirms
        # the fact is absent (U03: specs-comparison#3 says no dBA figure is published), in which
        # case that confirming section is a legitimate citation and is checked separately below.
        allowed_non_empty = {"U03"}
        for q in self.questions:
            if q["kind"] != "unanswerable":
                continue
            if q["id"] not in allowed_non_empty:
                self.assertEqual(q["must_cite"], [], f"{q['id']} should have no citations")
            for term in q.get("absent_terms", []):
                normalized = corpus.normalize_whitespace(term).lower()
                self.assertNotIn(
                    normalized,
                    self.full_text_norm,
                    f"{q['id']}: absent_terms entry {term!r} actually appears in the corpus",
                )

    def test_conflicting_questions_cite_both_sides_of_the_deliberate_contradiction(self) -> None:
        conflicting = [q for q in self.questions if q["kind"] == "conflicting"]
        self.assertEqual(len(conflicting), 12)
        all_cited_docs: set[str] = set()
        for q in conflicting:
            self.assertTrue(q["must_cite"], f"{q['id']} is conflicting-kind but cites nothing")
            all_cited_docs.update(cite.split("#")[0] for cite in q["must_cite"])
        # across the kind as a whole, both the older and the newer source must be represented
        self.assertIn("dr520-manual", all_cited_docs)
        self.assertIn("service-bulletin", all_cited_docs)

    def test_shared_quantities_agree_across_documents(self) -> None:
        for label, (pattern, allowed) in SHARED_FACTS.items():
            found = set(re.findall(pattern, self.full_text_norm, re.IGNORECASE))
            self.assertEqual(
                found,
                allowed,
                f"{label}: corpus states {sorted(found)}, expected exactly {sorted(allowed)}",
            )

    def test_corpus_names_no_real_brand_or_programme(self) -> None:
        for name in FORBIDDEN_NAMES:
            self.assertNotIn(name, self.full_text_norm, f"corpus names {name!r}")
        for q in self.questions:
            blob = json.dumps(q).lower()
            for name in FORBIDDEN_NAMES:
                self.assertNotIn(name, blob, f"{q['id']} names {name!r}")

    def test_the_vent_run_conflict_is_the_only_one_and_the_newer_source_wins(self) -> None:
        manual = corpus.normalize_whitespace(self.documents["dr520-manual"])
        bulletin = corpus.normalize_whitespace(self.documents["service-bulletin"])
        self.assertIn("maximum total vent run of 35 feet", manual)
        self.assertIn("is now 25 feet", bulletin)
        # the DR-210 keeps the original figure in both documents: it is not part of the conflict
        self.assertIn("remains 35 feet", bulletin)
        self.assertIn("maximum total vent run is 35 feet", corpus.normalize_whitespace(self.documents["dr210-manual"]))
        # and no third document states a DR-520 maximum of its own
        for name, text in self.documents.items():
            if name in ("dr520-manual", "service-bulletin"):
                continue
            self.assertNotIn("25 feet", corpus.normalize_whitespace(text), f"{name} states a DR-520 vent figure")

    def test_every_document_revision_date_precedes_the_bulletin_it_defers_to(self) -> None:
        dates = {}
        for name, text in self.documents.items():
            match = re.search(r"(?:Revision|Issued) (\d{4}-\d{2}-\d{2})", text)
            self.assertIsNotNone(match, f"{name} has no revision or issue date")
            dates[name] = match.group(1)
        # a document may only cite another document that already existed when it was written
        self.assertGreater(dates["dr210-manual"], dates["recall-notice"], "the DR-210 manual cites a later recall")
        self.assertGreater(dates["service-bulletin"], dates["dr520-manual"])
        self.assertGreater(dates["service-bulletin"], dates["installation-guide"])

    def test_service_bulletin_postdates_the_manual_it_contradicts(self) -> None:
        manual_date = re.search(r"Revision (\d{4}-\d{2}-\d{2})", self.documents["dr520-manual"])
        bulletin_date = re.search(r"Issued (\d{4}-\d{2}-\d{2})", self.documents["service-bulletin"])
        self.assertIsNotNone(manual_date)
        self.assertIsNotNone(bulletin_date)
        self.assertGreater(bulletin_date.group(1), manual_date.group(1))


class DecidedByDefinitionTests(unittest.TestCase):
    """The definition in `examples/common/trace.py`, asserted rather than described: a step is
    model-decided when the model's output selected which action happens next. Running a tool,
    returning its result, and forcing a final answer are the program's choices, always."""

    def test_levels_zero_to_three_decide_nothing_with_the_model(self) -> None:
        cases = [
            (0, lambda t: order_zero_run("How often is the DW-300 filter cleaned?", None, None, t, corpus_dir=CORPUS_DIR)),
            (1, lambda t: one_call_run("What voltage does a DR-210 need?", StubModel([StubResponse(text="240V.")]), None, t)),
            (2, lambda t: rag_run(
                "How often is the DW-300 filter cleaned?",
                StubModel([StubResponse(text="Every 30 cycles. Sources: dw300-manual#6")]),
                StubEmbedder(), t, corpus_dir=CORPUS_DIR,
            )),
            (3, lambda t: prompt_chaining_run(
                "How often is the DW-300 filter cleaned?",
                StubModel([StubResponse(text="DW-300 filter"), StubResponse(text="Every 30 cycles.")]),
                None, t, corpus_dir=CORPUS_DIR,
            )),
        ]
        for level, call in cases:
            tracer = Tracer(example=f"level{level}", level=level, model_id="stub-1")
            call(tracer)
            self.assertEqual(tracer.model_decided_count(), 0, f"level {level} recorded a model-decided step")
            self.assertTrue(tracer.steps, f"level {level} recorded no steps at all")

    def test_a_model_call_the_code_chose_is_kind_model_but_decided_by_code(self) -> None:
        # the two fields answer different questions and must not collapse into one
        tracer = Tracer(example="one_call", level=1, model_id="stub-1")
        one_call_run("What voltage?", StubModel([StubResponse(text="240V.")]), None, tracer)
        model_steps = [s for s in tracer.steps if s.kind == "model"]
        self.assertEqual(len(model_steps), 1)
        self.assertEqual(model_steps[0].decided_by, "code")
        self.assertEqual(model_steps[0].edge, "solid")

    def test_level_four_scores_a_tool_call_and_a_declined_tool_call_the_same(self) -> None:
        # the decision is "which action happens next"; both branches are the model's answer to it
        called = Tracer(example="function_calling", level=4, model_id="stub-1")
        function_calling_run(
            "What does HLV-2205 cost?",
            StubModel([
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2205"})]),
                StubResponse(text="$52.00."),
            ]),
            None, called, corpus_dir=CORPUS_DIR,
        )
        declined = Tracer(example="function_calling", level=4, model_id="stub-1")
        function_calling_run(
            "What does Halvorsen make?",
            StubModel([StubResponse(text="Dishwashers and dryers.")]),
            None, declined, corpus_dir=CORPUS_DIR,
        )
        self.assertEqual(called.model_decided_count(), 1)
        self.assertEqual(declined.model_decided_count(), 1)

    def test_running_a_tool_and_returning_its_result_are_always_code(self) -> None:
        for tracer, runner, model in [
            (
                Tracer(example="function_calling", level=4, model_id="stub-1"),
                function_calling_run,
                StubModel([
                    StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "vent"})]),
                    StubResponse(text="25 feet."),
                ]),
            ),
            (
                Tracer(example="agentic_rag", level=5, model_id="stub-1"),
                agentic_rag_run,
                StubModel([
                    StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "vent"})]),
                    StubResponse(text="25 feet."),
                ]),
            ),
        ]:
            runner("What is the DR-520 vent limit?", model, None, tracer, corpus_dir=CORPUS_DIR)
            tool_steps = [s for s in tracer.steps if s.title.startswith("Run tool")]
            self.assertTrue(tool_steps, "no tool step was recorded")
            for step in tool_steps:
                self.assertEqual(step.decided_by, "code")
                self.assertEqual(step.kind, "code")

    def test_a_forced_final_answer_is_the_codes_decision_not_the_models(self) -> None:
        def always_search(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "vent"})])

        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-loop")
        agentic_rag_run(
            "What is the DR-520 vent limit?", StubModel(always_search, model_id="stub-loop"), None, tracer,
            corpus_dir=CORPUS_DIR, max_steps=2,
        )
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertEqual(forced[0].decided_by, "code")
        # the model never chose to stop here, so the stop is not counted as its decision
        self.assertEqual(tracer.model_decided_count(), 2, "only the two tool calls were the model's")

    def test_a_model_decided_step_draws_a_dashed_edge(self) -> None:
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        function_calling_run(
            "What does Halvorsen make?", StubModel([StubResponse(text="Dishwashers.")]), None, tracer,
            corpus_dir=CORPUS_DIR,
        )
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertTrue(all(s.edge == "dashed" for s in model_steps))
        self.assertTrue(all(s.edge == "solid" for s in tracer.steps if s.decided_by == "code"))

    def test_the_definition_is_written_down_where_the_field_lives(self) -> None:
        # the site's central claim must not be documented only in a commit message
        for path in (ROOT / "examples" / "common" / "trace.py", ROOT / "docs" / "EVALS.md"):
            text = corpus.normalize_whitespace(path.read_text(encoding="utf-8"))
            self.assertIn("selected which action happens next", text, f"{path.name} omits the definition")
            self.assertIn("Declining to call a tool is a model decision", text, f"{path.name} omits the level-4 rule")


class ExampleTraceTests(unittest.TestCase):
    """Each example must run end to end on a stub model and produce a trace whose `decided_by`
    values match the level it claims: 0-3 all `code`, 4 exactly one `model` step (the tool
    call, or the choice not to call one), 5 a `model` step for every tool call and for the stop."""

    def test_order_zero_is_all_code_and_cites_a_real_section(self) -> None:
        tracer = Tracer(example="order_zero", level=0, model_id="none")
        answer = order_zero_run("How often should the DW-300's filter be cleaned?", None, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertTrue(tracer.steps, "order_zero recorded no steps")
        # keyword search is not exact: it returns whichever real section scores highest, which
        # here is the care-and-cleaning-guide's filter section rather than the manual's
        self.assertEqual(len(answer.citations), 1)
        self.assertIn(answer.citations[0], corpus.load_sections(CORPUS_DIR))
        self.assertIn("30 cycles", answer.text)

    def test_order_zero_reports_no_match_without_crashing(self) -> None:
        tracer = Tracer(example="order_zero", level=0, model_id="none")
        answer = order_zero_run("zzz qqq unmatched gibberish", None, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(answer.citations, [])

    def test_one_call_is_all_code_with_one_model_step(self) -> None:
        model = StubModel([StubResponse(text="I do not have that document, so I cannot say.")])
        tracer = Tracer(example="one_call", level=1, model_id="stub-1")
        answer = one_call_run("What voltage does a DR-210 need?", model, None, tracer)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertIn("cannot say", answer.text)

    def test_rag_is_all_code_and_parses_citations(self) -> None:
        model = StubModel([StubResponse(text="Every 30 cycles. Sources: dw300-manual#6")])
        tracer = Tracer(example="rag", level=2, model_id="stub-1")
        answer = rag_run(
            "How often should the DW-300's filter be cleaned?", model, StubEmbedder(), tracer, corpus_dir=CORPUS_DIR
        )
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(answer.citations, ["dw300-manual#6"])

    def test_prompt_chaining_is_all_code_with_two_model_steps(self) -> None:
        model = StubModel(
            [
                StubResponse(text="DW-300 filter cleaning schedule"),
                StubResponse(text="Every 30 cycles. Sources: dw300-manual#6"),
            ]
        )
        tracer = Tracer(example="prompt_chaining", level=3, model_id="stub-1")
        answer = prompt_chaining_run(
            "How often should the DW-300's filter be cleaned?", model, None, tracer, corpus_dir=CORPUS_DIR
        )
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)
        self.assertEqual(answer.citations, ["dw300-manual#6"])

    def test_prompt_chaining_drops_citations_the_retrieval_never_found(self) -> None:
        model = StubModel(
            [
                StubResponse(text="DW-300 filter cleaning schedule"),
                StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            ]
        )
        tracer = Tracer(example="prompt_chaining", level=3, model_id="stub-1")
        answer = prompt_chaining_run(
            "How often should the DW-300's filter be cleaned?", model, None, tracer, corpus_dir=CORPUS_DIR
        )
        self.assertNotIn("recall-notice#1", answer.citations)

    def test_function_calling_records_exactly_one_model_decided_step_when_a_tool_is_called(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2205"})]),
                StubResponse(text="It costs $52.00."),
            ]
        )
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        answer = function_calling_run("What does the DW-480 drain pump cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        model_decided = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(model_decided), 1)
        self.assertEqual(model_decided[0].kind, "model")
        self.assertIn("lookup_part", model_decided[0].title)
        self.assertIn("parts-list#2", answer.citations)
        self.assertIn("52.00", answer.text)

    def test_function_calling_records_one_model_decided_step_when_it_declines_to_call_a_tool(self) -> None:
        # choosing not to call a tool is still the model's choice, same as the stop in level 5
        model = StubModel([StubResponse(text="Halvorsen makes dishwashers and dryers.")])
        tracer = Tracer(example="function_calling", level=4, model_id="stub-1")
        answer = function_calling_run("What kinds of appliances does Halvorsen make?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.model_decided_count(), 1)
        self.assertEqual(answer.citations, [])
        self.assertEqual(len(tracer.steps), 2)

    def test_agentic_rag_records_a_model_decided_step_for_every_tool_call_and_the_stop(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 filter"})]),
                StubResponse(tool_calls=[ToolCall(name="read", arguments={"cite": "dw300-manual#6"})]),
                StubResponse(text="Every 30 cycles, per dw300-manual#6."),
            ]
        )
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-1")
        answer = agentic_rag_run(
            "How often should the DW-300's filter be cleaned?", model, None, tracer, corpus_dir=CORPUS_DIR
        )
        # one search call, one read call, one stop: three model-decided steps
        self.assertEqual(tracer.model_decided_count(), 3)
        model_steps = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertTrue(all(s.kind == "model" for s in model_steps))
        self.assertEqual(answer.citations, ["dw300-manual#6"])


class AgenticCapTests(unittest.TestCase):
    def test_step_cap_forces_a_stop(self) -> None:
        def always_search(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "vent"})])

        model = StubModel(always_search, model_id="stub-loop")
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-loop")
        answer = agentic_rag_run("What is the DR-520 vent limit?", model, None, tracer, corpus_dir=CORPUS_DIR, max_steps=3)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("step cap", forced[0].detail)
        self.assertIsInstance(answer.text, str)

    def test_token_budget_forces_a_stop_before_the_step_cap(self) -> None:
        def always_search(messages, tools):
            del messages, tools
            return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "vent"})])

        model = StubModel(always_search, model_id="stub-loop")
        tracer = Tracer(example="agentic_rag", level=5, model_id="stub-loop")
        agentic_rag_run(
            "What is the DR-520 vent limit?", model, None, tracer, corpus_dir=CORPUS_DIR, max_steps=50, max_tokens=1
        )
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        # the loop should have stopped almost immediately, not run anywhere near 50 steps
        self.assertLess(len(tracer.steps), 10)


class ExampleShapeTests(unittest.TestCase):
    """The plan promises a runnable example of about 50 lines per technique. A reader follows
    `run()` on a web page, so that is what is measured; helpers belong in `examples/common/`."""

    EXAMPLES = ["order_zero", "one_call", "rag", "prompt_chaining", "function_calling", "agentic_rag"]

    def _run_function_lines(self, example: str) -> int:
        import ast

        source = (ROOT / "examples" / example / "run.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        run_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        return run_fn.end_lineno - run_fn.lineno + 1

    def test_every_example_run_function_stays_readable_on_one_page(self) -> None:
        for example in self.EXAMPLES:
            lines = self._run_function_lines(example)
            self.assertLessEqual(lines, 60, f"{example}.run() is {lines} lines; move helpers to examples/common")

    def test_every_example_declares_its_level_and_a_run_function(self) -> None:
        import importlib

        for example in self.EXAMPLES:
            module = importlib.import_module(f"examples.{example}.run")
            self.assertTrue(callable(module.run), example)
            self.assertIsInstance(module.LEVEL, int, example)

    def test_the_two_tool_examples_are_given_genuinely_different_search_tools(self) -> None:
        # level 5 is only a loop if search withholds the text, forcing a second decision to read
        sections = corpus.load_sections(CORPUS_DIR)
        full_text, full_cites = tools.search_full_text(sections, "DW-300 filter cleaning")
        titles, title_cites = tools.search_titles(sections, "DW-300 filter cleaning")
        self.assertIn("30 cycles", full_text, "level 4's search must return usable text")
        self.assertNotIn("30 cycles", titles, "level 5's search must return titles only")
        self.assertTrue(full_cites, "level 4 can cite what it searched")
        self.assertEqual(title_cites, [], "level 5 may only cite what it has read")

    def test_reading_a_section_is_what_earns_a_citation_at_level_five(self) -> None:
        sections = corpus.load_sections(CORPUS_DIR)
        text, cites = tools.read_section(sections, "dw300-manual#6")
        self.assertIn("30 cycles", text)
        self.assertEqual(cites, ["dw300-manual#6"])
        missing_text, missing_cites = tools.read_section(sections, "no-such-doc#9")
        self.assertIn("not found", missing_text)
        self.assertEqual(missing_cites, [])

    def test_an_unknown_tool_is_reported_to_the_model_rather_than_raised(self) -> None:
        text, cites = tools.unknown_tool("delete_everything")
        self.assertIn("unknown tool", text)
        self.assertEqual(cites, [])

    def test_a_part_lookup_cites_the_parts_list_section_it_came_from(self) -> None:
        sections = corpus.load_sections(CORPUS_DIR)
        text, cites = tools.part_line(sections, "HLV-2205")
        self.assertIn("52.00", text)
        self.assertEqual(cites, ["parts-list#2"])
        self.assertIn("not found", tools.part_line(sections, "HLV-0000")[0])


class BackendRequestShapeTests(unittest.TestCase):
    """The real backends are never called by the suite. What can be checked without a network
    call is the request they would build, and that constructing one does no I/O."""

    def test_ollama_always_sends_an_explicit_context_size(self) -> None:
        sent = {}

        def fake_post(url, payload, *, timeout=60):
            sent["url"], sent["payload"], sent["timeout"] = url, payload, timeout
            return {"message": {"content": "ok"}}

        model = model_mod.OllamaModel("llama3.1")
        with unittest.mock.patch.object(model_mod, "_post_json", fake_post):
            model.complete([model_mod.Message(role="user", content="hi")], max_tokens=64)
        self.assertEqual(sent["payload"]["options"]["num_ctx"], model_mod.DEFAULT_NUM_CTX)
        self.assertEqual(sent["payload"]["options"]["num_predict"], 64)
        self.assertFalse(sent["payload"]["stream"])
        self.assertEqual(sent["url"], "http://127.0.0.1:11434/api/chat")
        self.assertGreater(sent["timeout"], 0)

    def test_the_ollama_embedder_returns_unit_vectors_like_the_stub_does(self) -> None:
        """`Embedder` promises unit vectors and the RAG page's Build it lane says so in prose,
        which is what lets `_cosine` be a plain dot product. Ollama's `/api/embeddings` returns
        whatever the embedding model produced, so the scaling has to happen in the embedder. No
        network call: `_post_json` is replaced with a fixed reply."""
        raw = {"a": [3.0, 4.0], "b": [0.0, 0.0, 2.0]}
        asked = []

        def fake_post(url, payload, *, timeout=60):
            asked.append((url, payload["prompt"]))
            return {"embedding": list(raw[payload["prompt"]])}

        embedder = model_mod.OllamaEmbedder("nomic-embed-text")
        with unittest.mock.patch.object(model_mod, "_post_json", fake_post):
            vectors = embedder.embed(["a", "b"])

        self.assertEqual([u for _, u in asked], ["a", "b"])
        self.assertEqual(asked[0][0], "http://127.0.0.1:11434/api/embeddings")
        for vector in vectors:
            self.assertAlmostEqual(sum(v * v for v in vector) ** 0.5, 1.0, places=9)
        self.assertEqual(vectors[0], [0.6, 0.8])
        # direction is preserved: scaling must not reorder or re-sign the components
        self.assertEqual(vectors[1], [0.0, 0.0, 1.0])

    def test_a_dot_product_of_ollama_vectors_is_a_cosine_not_a_length_contest(self) -> None:
        """The defect this guards: with raw vectors a dot product rewards a long passage for
        being long. Here the short vector is the one pointing the same way as the query, so it
        must win; against the unnormalized reply it would lose to the longer one."""

        def fake_post(url, payload, *, timeout=60):
            return {"embedding": {"q": [1.0, 0.0], "short": [2.0, 0.0], "long": [6.0, 8.0]}[payload["prompt"]]}

        embedder = model_mod.OllamaEmbedder("nomic-embed-text")
        with unittest.mock.patch.object(model_mod, "_post_json", fake_post):
            query, short, long = embedder.embed(["q", "short", "long"])

        dot = lambda a, b: sum(x * y for x, y in zip(a, b))  # noqa: E731 - one line, read once
        self.assertGreater(dot(query, short), dot(query, long))
        self.assertAlmostEqual(dot(query, short), 1.0, places=9)

    def test_ollama_never_asks_the_server_to_pull_a_model(self) -> None:
        source = (ROOT / "examples" / "common" / "model.py").read_text(encoding="utf-8")
        self.assertNotIn("/api/pull", source)
        self.assertNotIn("\"pull\"", source)

    def test_claude_tools_are_converted_to_input_schema(self) -> None:
        model = model_mod.ClaudeModel("claude-sonnet-5", api_key="test-key-not-real")
        payload = model.build_payload(
            [model_mod.Message(role="user", content="hi")],
            tools=[{"name": "search", "description": "d", "parameters": {"type": "object", "properties": {}}}],
        )
        self.assertIn("input_schema", payload["tools"][0])
        self.assertNotIn("parameters", payload["tools"][0], "the API rejects 'parameters'")

    def test_claude_lifts_system_out_and_keeps_only_user_and_assistant_turns(self) -> None:
        model = model_mod.ClaudeModel("claude-sonnet-5", api_key="test-key-not-real")
        payload = model.build_payload(
            [
                model_mod.Message(role="system", content="be brief"),
                model_mod.Message(role="user", content="question"),
                model_mod.Message(role="assistant", content="[called search]"),
                model_mod.Message(role="user", content="Result of search: a"),
                model_mod.Message(role="user", content="Result of read: b"),
            ]
        )
        self.assertEqual(payload["system"], "be brief")
        self.assertEqual([m["role"] for m in payload["messages"]], ["user", "assistant", "user"])
        self.assertIn("Result of search: a", payload["messages"][2]["content"])
        self.assertIn("Result of read: b", payload["messages"][2]["content"])

    def test_claude_does_not_drop_a_requested_output_schema(self) -> None:
        model = model_mod.ClaudeModel("claude-sonnet-5", api_key="test-key-not-real")
        payload = model.build_payload(
            [model_mod.Message(role="user", content="hi")], schema={"type": "json_schema"}
        )
        self.assertEqual(payload["output_config"], {"format": {"type": "json_schema"}})

    def test_building_a_backend_reads_no_key_and_opens_no_socket(self) -> None:
        # importing and constructing must stay free of I/O, or the test suite would need a key
        model = model_mod.build_model("ollama:llama3.1")
        self.assertEqual(model.model_id, "ollama:llama3.1")
        with self.assertRaises(ValueError):
            model_mod.build_model("openai:gpt-9")

    def test_a_failed_request_is_not_retried(self) -> None:
        # a retry would silently multiply the cost of a metered run
        attempts = []

        def failing_urlopen(request, timeout=None):
            attempts.append(request)
            raise model_mod.urllib.error.HTTPError("https://api.anthropic.com/v1/messages", 500, "boom", {}, None)

        model = model_mod.ClaudeModel("claude-sonnet-5", api_key="test-key-not-real")
        with unittest.mock.patch.object(model_mod.urllib.request, "urlopen", failing_urlopen):
            with self.assertRaises(RuntimeError) as caught:
                model.complete([model_mod.Message(role="user", content="hi")])
        self.assertEqual(len(attempts), 1, "the request was retried")
        self.assertIn("500", str(caught.exception), "the status code must reach the operator")

    def test_the_api_key_is_read_only_from_the_local_file(self) -> None:
        source = (ROOT / "examples" / "common" / "model.py").read_text(encoding="utf-8")
        self.assertIn('.local" / "api-keys.json', source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("sk-ant", source)


if __name__ == "__main__":
    unittest.main()
