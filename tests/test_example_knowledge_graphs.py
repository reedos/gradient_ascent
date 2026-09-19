"""Tests for examples/knowledge_graphs: extract triples from two documents, build a small graph,
and answer a two-hop question by walking it, citing both edges as provenance."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.corpus import load_sections  # noqa: E402
from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.knowledge_graphs.__main__ import REPLAYED_TRIPLES, replay_stub  # noqa: E402
from examples.knowledge_graphs.run import LEVEL, run  # noqa: E402

PARTS_RESPONSE = StubResponse(
    text=(
        "HLV-5510 | fits | DR-210\n"
        "HLV-5520 | fits | DR-520\n"
        "HLV-6601 | fits | DR-210\n"
        "HLV-6601 | fits | DR-520\n"
        "HLV-7735 | fits | DR-520"
    )
)
WARRANTY_RESPONSE = StubResponse(
    text=(
        "DW-300 | warranty_class | 5-year limited (motor and tub), parts only\n"
        "DW-480 | warranty_class | 5-year limited (motor and tub), parts only\n"
        "DR-210 | warranty_class | 7-year limited (drum and motor), parts only\n"
        "DR-520 | warranty_class | 7-year limited (drum and motor), parts only"
    )
)

QUESTION = "What warranty class covers the model that HLV-5520 fits?"


def _model() -> StubModel:
    return StubModel([PARTS_RESPONSE, WARRANTY_RESPONSE])


class KnowledgeGraphsTraceTests(unittest.TestCase):
    def test_every_step_is_decided_by_code(self) -> None:
        tracer = Tracer(example="knowledge_graphs", level=LEVEL, model_id="stub-1")
        run(QUESTION, _model(), None, tracer)
        self.assertTrue(tracer.steps, "recorded no steps at all")
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        # one extraction call per source document
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 2)
        self.assertTrue(callable(run))

    def test_the_two_hop_answer_walks_part_to_model_to_warranty_class(self) -> None:
        tracer = Tracer(example="knowledge_graphs", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, _model(), None, tracer)
        self.assertIn("DR-520", answer.text)
        self.assertIn("7-year limited (drum and motor)", answer.text)
        # provenance: both edges of the two-hop path must be cited, not just the second one
        self.assertEqual(answer.citations, ["parts-list#3", "warranty-policy#2"])

    def test_a_different_part_number_walks_a_different_path(self) -> None:
        tracer = Tracer(example="knowledge_graphs", level=LEVEL, model_id="stub-1")
        answer = run("What warranty class covers the model that HLV-5510 fits?", _model(), None, tracer)
        self.assertIn("DR-210", answer.text)
        self.assertIn("7-year limited (drum and motor)", answer.text)

    def test_a_part_the_extraction_never_stated_a_fitment_for_finds_no_path(self) -> None:
        # HLV-7734 has no fitment in the source text (parts-list.md itself says so), so a graph
        # built only from what was actually extracted must not invent one
        tracer = Tracer(example="knowledge_graphs", level=LEVEL, model_id="stub-1")
        answer = run("What warranty class covers the model that HLV-7734 fits?", _model(), None, tracer)
        self.assertEqual(answer.citations, [])
        self.assertIn("No warranty class found", answer.text)

    def test_the_cli_replay_stub_drives_the_same_two_hop_answer(self) -> None:
        # `--model stub` replays a transcribed extraction so the walk runs with no model at all;
        # if the replay drifts from what the walk needs, the CLI stops demonstrating the page
        tracer = Tracer(example="knowledge_graphs", level=LEVEL, model_id="stub-replay")
        answer = run(QUESTION, replay_stub(), None, tracer)
        self.assertEqual(answer.citations, ["parts-list#3", "warranty-policy#2"])
        self.assertIn("DR-520", answer.text)
        self.assertIn("7-year limited (drum and motor)", answer.text)

    def test_every_replayed_triple_is_stated_by_the_section_it_is_transcribed_from(self) -> None:
        # a replay that invented an edge would make the CLI demonstrate a graph the corpus does
        # not support, which is exactly what this example is supposed to be honest about
        sections = load_sections()
        fitments, warranties = REPLAYED_TRIPLES
        parts = sections["parts-list#3"].text
        for line in fitments.splitlines():
            subject, relation, obj = (p.strip() for p in line.split("|"))
            self.assertEqual(relation, "fits")
            self.assertIn(subject, parts, f"{subject} is not named in parts-list#3")
            self.assertIn(obj, parts, f"{obj} is not named in parts-list#3")
            self.assertRegex(parts, rf"{subject}.*fits.*{obj}", f"parts-list#3 does not fit {subject} to {obj}")
        policy = sections["warranty-policy#2"].text
        for line in warranties.splitlines():
            subject, relation, obj = (p.strip() for p in line.split("|"))
            self.assertEqual(relation, "warranty_class")
            self.assertIn(subject, policy, f"{subject} is not named in warranty-policy#2")
            years = obj.split("-", 1)[0]
            self.assertIn(f"{years} years", policy, f"warranty-policy#2 states no {years}-year term")
        # HLV-7734 is the part parts-list.md explicitly gives no fitment for: it must not appear
        self.assertNotIn("HLV-7734", fitments)

    def test_an_extraction_response_with_no_parseable_triples_yields_no_path_not_a_crash(self) -> None:
        # this is what happens when a model answers with prose instead of triples
        blank_model = StubModel([StubResponse(text="[interactive stub] no live model"), StubResponse(text="[interactive stub] no live model")])
        tracer = Tracer(example="knowledge_graphs", level=LEVEL, model_id="stub-interactive")
        answer = run(QUESTION, blank_model, None, tracer)
        self.assertEqual(answer.citations, [])
        extract_steps = [s for s in tracer.steps if s.title.startswith("Extract triples")]
        self.assertEqual(len(extract_steps), 2)
        self.assertEqual(extract_steps[0].detail, "none")


if __name__ == "__main__":
    unittest.main()
