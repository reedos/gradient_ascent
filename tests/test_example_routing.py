"""Tests for examples/routing: the classify-then-dispatch example for the routing technique page.

Mirrors the shape of tests/test_examples.py's ExampleTraceTests: run the example end to end on a
scripted StubModel and check the trace's decided_by pattern, plus the routing-specific behaviour
(which handler a label sends the question to, and the fallback when a route cannot serve it).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.routing.run import _parse_label, run  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"


class ParseLabelTests(unittest.TestCase):
    def test_recognizes_each_known_label(self) -> None:
        self.assertEqual(_parse_label("lookup"), "lookup")
        self.assertEqual(_parse_label("Numeric"), "numeric")
        self.assertEqual(_parse_label("unclear"), "unclear")

    def test_trims_punctuation_and_case(self) -> None:
        self.assertEqual(_parse_label(" Lookup.\n"), "lookup")

    def test_anything_unrecognized_falls_back_to_unclear(self) -> None:
        self.assertEqual(_parse_label("I'm not sure, maybe lookup?"), "unclear")
        self.assertEqual(_parse_label(""), "unclear")


class RoutingExampleTests(unittest.TestCase):
    def test_every_step_is_decided_by_code_on_every_route(self) -> None:
        cases = [
            StubModel([StubResponse(text="lookup"), StubResponse(text="Every 30 cycles. Sources: dw300-manual#6")]),
            StubModel([StubResponse(text="numeric")]),
            StubModel([StubResponse(text="unclear")]),
        ]
        for model in cases:
            tracer = Tracer(example="routing", level=3, model_id="stub-1")
            run("a question", model, None, tracer, corpus_dir=CORPUS_DIR)
            self.assertTrue(all(s.decided_by == "code" for s in tracer.steps), "routing recorded a model-decided step")
            self.assertEqual(tracer.model_decided_count(), 0)
            self.assertTrue(tracer.steps)

    def test_lookup_label_routes_to_the_lookup_handler_and_calls_the_model_twice(self) -> None:
        model = StubModel([StubResponse(text="lookup"), StubResponse(text="Every 30 cycles. Sources: dw300-manual#6")])
        tracer = Tracer(example="routing", level=3, model_id="stub-1")
        answer = run("How often should the DW-300's filter be cleaned?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)
        self.assertIn("dw300-manual#6", answer.citations)

    def test_numeric_label_with_a_part_number_answers_with_no_second_model_call(self) -> None:
        model = StubModel([StubResponse(text="numeric")])
        tracer = Tracer(example="routing", level=3, model_id="stub-1")
        answer = run("What does HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "the numeric route must not call the model")
        self.assertIn("52.00", answer.text)
        self.assertIn("parts-list#2", answer.citations)

    def test_numeric_label_without_a_part_number_falls_back_to_a_person(self) -> None:
        model = StubModel([StubResponse(text="numeric")])
        tracer = Tracer(example="routing", level=3, model_id="stub-1")
        answer = run("What does the drain pump cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIn("needs a person", answer.text)
        self.assertEqual(answer.citations, [])

    def test_unclear_label_answers_nothing_and_calls_the_model_only_once(self) -> None:
        model = StubModel([StubResponse(text="unclear")])
        tracer = Tracer(example="routing", level=3, model_id="stub-1")
        answer = run("What is the meaning of life?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertIn("needs a person", answer.text)

    def test_a_garbled_classification_still_routes_somewhere_rather_than_raising(self) -> None:
        model = StubModel([StubResponse(text="I think this is a lookup question, probably.")])
        tracer = Tracer(example="routing", level=3, model_id="stub-1")
        answer = run("Some question", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIn("needs a person", answer.text)
        dispatch_steps = [s for s in tracer.steps if s.title == "Route on the label"]
        self.assertEqual(len(dispatch_steps), 1)
        self.assertIn("unclear", dispatch_steps[0].detail)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.routing.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 3)


if __name__ == "__main__":
    unittest.main()
