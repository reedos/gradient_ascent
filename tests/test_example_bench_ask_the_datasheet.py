"""End-to-end tests for the ask-the-datasheet example.

Three things are being pinned here, and they are different kinds of claim:

- **Retrieval actually finds both conflicting sources.** For the question this recipe is built
  around, `evals.bench`'s datasheet section and its engineering change notice both come back in
  one top-k search, with no second, dependent search. If a future edit to the bench corpus or the
  stub embedder ever made that stop being true, this is the test that would say so.
- **A reply that skips the revision, or cites something it was never shown, is not accepted.**
  Both are validation failures that retry once and are reported, not silently passed through, the
  same contract `examples/structured_output/run.py` tests for its own schema.
- **Every step is `decided_by: "code"`.** Calling the model is not a model decision; nothing here
  chooses what happens next except the fixed retrieve-prompt-validate-retry sequence.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import load_bench_sections  # noqa: E402
from examples.bench_ask_the_datasheet.run import LEVEL, SCHEMA, _retrieve, run  # noqa: E402
from examples.common.model import StubEmbedder, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

QUESTION = (
    "What is the maximum input voltage of the SRB-5030, revision B, per its recommended "
    "operating conditions?"
)
DATASHEET_CITE = "srb5030-datasheet#3"  # "Recommended Operating Conditions": states 36.0 V
ECN_CITE = "ecn-2608-04#1"  # "Change": supersedes it to 32.0 V for revisions A and B
CORRECT_RECORD = {
    "answer": "The maximum input voltage is 32.0 V, not the datasheet's 36.0 V.",
    "applies_to_revision": "A and B",
    "citations": [ECN_CITE, DATASHEET_CITE],
}


def _tracer() -> Tracer:
    return Tracer(example="bench_ask_the_datasheet", level=LEVEL, model_id="stub-1")


class RetrievalTests(unittest.TestCase):
    def test_one_search_finds_both_the_datasheet_and_the_change_notice(self) -> None:
        sections = load_bench_sections()
        hits = {s.cite for s in _retrieve(QUESTION, sections, StubEmbedder(), k=8)}
        self.assertIn(DATASHEET_CITE, hits, "the datasheet's own number must be reachable")
        self.assertIn(ECN_CITE, hits, "the notice that supersedes it must be reachable too")

    def test_a_narrower_top_k_can_miss_the_change_notice(self) -> None:
        # The point of retrieving 8, not 2: a phrasing close to the datasheet's own words ("input
        # voltage", "recommended operating conditions") ranks the datasheet section first and the
        # notice that supersedes it well below a narrow cut. A search that stops too early returns
        # the datasheet's 36.0 V with nothing to say it is wrong for the board on the bench.
        sections = load_bench_sections()
        narrow_question = "SRB-5030 input voltage recommended operating conditions table"
        hits = {s.cite for s in _retrieve(narrow_question, sections, StubEmbedder(), k=2)}
        self.assertIn(DATASHEET_CITE, hits)
        self.assertNotIn(ECN_CITE, hits, "a top-2 cut here finds the datasheet without the notice")


class RunTests(unittest.TestCase):
    def test_a_valid_reply_names_the_revision_and_cites_both_sources(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(CORRECT_RECORD))])
        tracer = _tracer()
        answer = run(QUESTION, model, StubEmbedder(), tracer)
        self.assertIn("32.0", answer.text)
        self.assertIn("A and B", answer.text)
        self.assertEqual(set(answer.citations), {ECN_CITE, DATASHEET_CITE})
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "a valid reply must not retry")

    def test_a_reply_missing_the_revision_retries_once_then_succeeds(self) -> None:
        unscoped = dict(CORRECT_RECORD, applies_to_revision="")
        model = StubModel([StubResponse(text=json.dumps(unscoped)), StubResponse(text=json.dumps(CORRECT_RECORD))])
        tracer = _tracer()
        answer = run(QUESTION, model, StubEmbedder(), tracer)
        self.assertEqual(set(answer.citations), {ECN_CITE, DATASHEET_CITE})
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)
        retries = [s for s in tracer.steps if s.title == "Ask again with the validation error"]
        self.assertEqual(len(retries), 1)

    def test_a_reply_that_names_the_revision_but_never_cites_the_notice_still_fails_validation(self) -> None:
        # Naming a revision is not enough on its own: a reply that answers 36.0 V "for revision B"
        # without citing the notice that changes that number for revision B is exactly the wrong
        # answer this recipe exists to catch, so the datasheet-only citation list must not pass.
        datasheet_only = dict(CORRECT_RECORD, citations=[DATASHEET_CITE])
        model = StubModel([StubResponse(text=json.dumps(datasheet_only)), StubResponse(text=json.dumps(CORRECT_RECORD))])
        tracer = _tracer()
        answer = run(QUESTION, model, StubEmbedder(), tracer)
        self.assertEqual(set(answer.citations), {ECN_CITE, DATASHEET_CITE})
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)

    def test_a_citation_the_search_never_retrieved_is_rejected(self) -> None:
        hallucinated = dict(CORRECT_RECORD, citations=[ECN_CITE, "srb5030-bom#99"])
        model = StubModel([StubResponse(text=json.dumps(hallucinated)), StubResponse(text=json.dumps(CORRECT_RECORD))])
        tracer = _tracer()
        run(QUESTION, model, StubEmbedder(), tracer)
        validations = [s for s in tracer.steps if s.title == "Validate the reply"]
        self.assertIn("not among the retrieved sources", validations[0].detail)

    def test_still_invalid_after_the_retry_is_reported_not_accepted(self) -> None:
        bad = {"answer": "32.0 V"}  # missing applies_to_revision and citations
        model = StubModel([StubResponse(text=json.dumps(bad)), StubResponse(text=json.dumps(bad))])
        tracer = _tracer()
        answer = run(QUESTION, model, StubEmbedder(), tracer)
        self.assertEqual(answer.citations, [], "an unvalidated record must not be cited as an answer")
        self.assertIn("error", json.loads(answer.text))
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "must not retry more than once")

    def test_invalid_json_is_caught_the_same_way_as_a_schema_mismatch(self) -> None:
        model = StubModel([StubResponse(text="not json at all"), StubResponse(text=json.dumps(CORRECT_RECORD))])
        tracer = _tracer()
        answer = run(QUESTION, model, StubEmbedder(), tracer)
        self.assertEqual(set(answer.citations), {ECN_CITE, DATASHEET_CITE})

    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(CORRECT_RECORD))])
        tracer = _tracer()
        run(QUESTION, model, StubEmbedder(), tracer)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_the_token_counts_the_page_quotes(self) -> None:
        """The recipe page's cost section quotes this call's tokens; pin them here so the page
        cannot drift from the prompt the code actually builds. Counted by `count_tokens` over the
        eight retrieved sections, the schema, the question and the scripted reply."""
        model = StubModel([StubResponse(text=json.dumps(CORRECT_RECORD))])
        tracer = _tracer()
        run(QUESTION, model, StubEmbedder(), tracer)
        self.assertEqual(tracer.tokens_in_total(), 1977)
        self.assertEqual(tracer.tokens_out_total(), 42)

    def test_declares_its_level_a_run_function_and_a_schema(self) -> None:
        self.assertEqual(LEVEL, 2)
        self.assertTrue(callable(run))
        self.assertEqual(SCHEMA["required"], ["answer", "applies_to_revision", "citations"])


if __name__ == "__main__":
    unittest.main()
