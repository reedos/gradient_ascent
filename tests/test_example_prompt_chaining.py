"""Tests for examples/prompt_chaining: four fixed steps (rewrite into search queries, retrieve,
draft, check citations against retrieval), always run in this order and never branched on by the
model.

Two of these tests exist because the CLI's interactive stub (`examples/common/cli.py`) always
echoes back a single line, so `MAX_QUERIES` and a hallucinated citation can never be exercised by
typing a question at `python -m examples.prompt_chaining --model stub`: the rewrite step only
ever gets one candidate query no matter what `MAX_QUERIES` is set to, and the checked citation is
always whatever the draft step's own prompt happened to contain. `test_max_queries_...` and
`test_a_single_query_can_miss_the_correcting_document_that_three_find` script a `StubModel` with
more than one line instead, which is what actually varies `MAX_QUERIES`'s effect."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from evals.corpus import Section  # noqa: E402
import examples.prompt_chaining.run as pc_run  # noqa: E402
from examples.prompt_chaining.run import LEVEL, _check_citations, run  # noqa: E402

QUESTION = "Is the DR-520 vent length still 35 feet?"


def _model() -> StubModel:
    return StubModel(
        [
            StubResponse(text="DR-520 vent length"),
            StubResponse(text="The maximum vent run for the DR-520 is now 25 feet. Sources: service-bulletin#2"),
        ]
    )


class PromptChainingTraceTests(unittest.TestCase):
    def test_every_step_is_decided_by_code(self) -> None:
        tracer = Tracer(example="prompt_chaining", level=LEVEL, model_id="stub-1")
        run(QUESTION, _model(), None, tracer)
        self.assertTrue(tracer.steps, "recorded no steps at all")
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        # two model calls (rewrite, draft) and two code-only steps (retrieve, check citations)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))


class CheckCitationsTests(unittest.TestCase):
    """`_check_citations` is the gate: a citation the draft claims but retrieval never found is
    dropped, not trusted. No model call anywhere in this test."""

    def test_a_grounded_citation_is_kept(self) -> None:
        sources = [Section(doc="service-bulletin", number=2, title="Revised Vent Specification", text="...")]
        tracer = Tracer(example="prompt_chaining", level=LEVEL, model_id="stub-1")
        grounded = _check_citations("The limit is now 25 feet. Sources: service-bulletin#2", sources, tracer)
        self.assertEqual(grounded, ["service-bulletin#2"])

    def test_an_invented_citation_is_dropped(self) -> None:
        sources = [Section(doc="service-bulletin", number=2, title="Revised Vent Specification", text="...")]
        tracer = Tracer(example="prompt_chaining", level=LEVEL, model_id="stub-1")
        grounded = _check_citations("The limit is now 25 feet. Sources: dr520-manual#4", sources, tracer)
        self.assertEqual(grounded, [], "a citation to a section retrieval never found must not be trusted")


class MaxQueriesTests(unittest.TestCase):
    """What a reader editing MAX_QUERIES in examples/prompt_chaining/run.py and running the CLI
    cannot see: the interactive stub always returns one line, so the truncation this constant
    controls never actually happens on the command line. These tests script enough lines that it
    does."""

    def setUp(self) -> None:
        self._original_max_queries = pc_run.MAX_QUERIES

    def tearDown(self) -> None:
        pc_run.MAX_QUERIES = self._original_max_queries

    def test_max_queries_caps_how_many_rewritten_queries_are_used(self) -> None:
        lines = "\n".join(f"query {i}" for i in range(5))
        model = StubModel([StubResponse(text=lines)])
        tracer = Tracer(example="prompt_chaining", level=LEVEL, model_id="stub-1")
        pc_run.MAX_QUERIES = 2
        queries = pc_run._rewrite_queries("does it matter", model, tracer)
        self.assertEqual(queries, ["query 0", "query 1"])

    def test_a_single_query_can_miss_the_correcting_document_that_three_find(self) -> None:
        # "DR-520 vent length" alone ranks service-bulletin#2 (the corrected 25-foot limit) below
        # its top 2 results; two more differently worded queries bring it in. Both runs use the
        # same draft, which claims the same citation either way -- only what retrieval found
        # changes, which is exactly what `_check_citations` is supposed to police.
        rewrite = (
            "DR-520 vent length\n"
            "DR-520 service bulletin update\n"
            "DR-520 vent specification revision"
        )
        draft = "The maximum vent run for the DR-520 is now 25 feet. Sources: service-bulletin#2"

        pc_run.MAX_QUERIES = 3
        tracer_three = Tracer(example="prompt_chaining", level=LEVEL, model_id="stub-1")
        model_three = StubModel([StubResponse(text=rewrite), StubResponse(text=draft)])
        answer_three = run(QUESTION, model_three, None, tracer_three)
        self.assertEqual(answer_three.citations, ["service-bulletin#2"])

        pc_run.MAX_QUERIES = 1
        tracer_one = Tracer(example="prompt_chaining", level=LEVEL, model_id="stub-1")
        model_one = StubModel([StubResponse(text=rewrite), StubResponse(text=draft)])
        answer_one = run(QUESTION, model_one, None, tracer_one)
        self.assertEqual(
            answer_one.citations,
            [],
            "the first query alone should not have retrieved the correcting section",
        )


if __name__ == "__main__":
    unittest.main()
