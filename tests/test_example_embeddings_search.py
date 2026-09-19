"""Tests for examples/embeddings_search: index once, rank a query by embedding similarity and by
keyword, and report the overlap. No model is involved, so every step is `decided_by: "code"`."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.corpus import DEFAULT_CORPUS_DIR  # noqa: E402
from examples.common.model import StubEmbedder  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.embeddings_search.run import LEVEL, run  # noqa: E402


class EmbeddingsSearchTraceTests(unittest.TestCase):
    def test_every_step_is_decided_by_code_and_no_model_is_called(self) -> None:
        tracer = Tracer(example="embeddings_search", level=LEVEL, model_id="none")
        answer = run("DW-300 Normal cycle water use", None, StubEmbedder(), tracer, corpus_dir=DEFAULT_CORPUS_DIR)
        self.assertTrue(tracer.steps, "recorded no steps at all")
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 0, "this level searches; it does not call a model")
        self.assertTrue(answer.citations, "semantic search returned no citations")

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 2)
        self.assertTrue(callable(run))

    def test_a_query_with_strong_literal_overlap_agrees_with_keyword_on_the_top_hit(self) -> None:
        # both methods key off shared words here ("DW-300", "Normal", "cycle", "water"), so the
        # stub's bag-of-words vector and BM25 should at least agree on the strongest match
        tracer = Tracer(example="embeddings_search", level=LEVEL, model_id="none")
        answer = run(
            "DW-300 Normal cycle water use", None, StubEmbedder(), tracer, corpus_dir=DEFAULT_CORPUS_DIR, k=3
        )
        semantic_step = next(s for s in tracer.steps if "rank it by similarity" in s.title)
        keyword_step = next(s for s in tracer.steps if "keyword (BM25)" in s.title)
        self.assertIn("dw300-manual#3", semantic_step.detail)
        self.assertIn("dw300-manual#3", keyword_step.detail)
        self.assertIn("dw300-manual#3", answer.citations)

    def test_a_query_worded_differently_than_the_corpus_shows_the_stub_finding_nothing_useful(self) -> None:
        # the corpus never uses the word "quieter" -- it says "dBA" and "Sound level" -- so a
        # bag-of-words stand-in with no notion of synonymy should not recover the section that
        # actually answers this, which is exactly the honesty check this example exists to make
        tracer = Tracer(example="embeddings_search", level=LEVEL, model_id="none")
        answer = run(
            "Which dishwasher is quieter, the DW-300 or the DW-480?",
            None, StubEmbedder(), tracer, corpus_dir=DEFAULT_CORPUS_DIR, k=3,
        )
        self.assertNotIn("specs-comparison#2", answer.citations)

    def test_the_comparison_reports_agreement_count_and_both_result_sets(self) -> None:
        tracer = Tracer(example="embeddings_search", level=LEVEL, model_id="none")
        answer = run("DW-300 Normal cycle water use", None, StubEmbedder(), tracer, corpus_dir=DEFAULT_CORPUS_DIR, k=3)
        self.assertIn("Semantic top-3:", answer.text)
        self.assertIn("Keyword top-3:", answer.text)
        self.assertRegex(answer.text, r"\d of 3 sections agree")

    def test_k_controls_how_many_results_come_back_from_each_method(self) -> None:
        tracer = Tracer(example="embeddings_search", level=LEVEL, model_id="none")
        answer = run("drain pump price", None, StubEmbedder(), tracer, corpus_dir=DEFAULT_CORPUS_DIR, k=2)
        self.assertEqual(len(answer.citations), 2)


if __name__ == "__main__":
    unittest.main()
