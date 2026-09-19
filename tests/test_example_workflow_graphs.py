"""Tests for examples/workflow_graphs: the dict-based graph runner for the workflow-graphs
technique page. Mirrors the shape of tests/test_examples.py's ExampleTraceTests: run end to end
on a scripted StubModel and check the trace's decided_by pattern, the branch to a dead end when
retrieval finds nothing, and the same revision-cap behavior as write-and-check, now reached
through the graph's edge functions instead of a hand-written loop.
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
from examples.workflow_graphs.run import PASS_TOKEN, run  # noqa: E402
from examples.workflow_graphs.__main__ import SCRIPTED  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "How often should the DW-300's filter be cleaned?"

# The same four replies examples/workflow_graphs/__main__.py scripts for `--model stub:scripted`:
# a first draft that fails the check node, then a revision that passes it.
SEQUENCE = [
    "Every 30 cycles. Sources: dw300-manual#6",
    "MISSING: dw300-manual#6",
    "Every 30 cycles, per the care and cleaning guide.\nSources: care-and-cleaning-guide#1",
    "ALL CITATIONS SUPPORTED",
]


class WorkflowGraphsExampleTests(unittest.TestCase):
    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6"),
            StubResponse(text=PASS_TOKEN),
        ])
        tracer = Tracer(example="workflow_graphs", level=3, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_a_checkpoint_is_recorded_after_every_node_visited(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6"),
            StubResponse(text=PASS_TOKEN),
        ])
        tracer = Tracer(example="workflow_graphs", level=3, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        checkpoint_steps = [s for s in tracer.steps if s.title.startswith("Checkpoint after")]
        node_steps = [s for s in tracer.steps if s.title.startswith("Node:")]
        self.assertEqual(len(checkpoint_steps), len(node_steps), "one checkpoint per node visited")
        self.assertEqual(
            [s.title for s in checkpoint_steps],
            ["Checkpoint after 'retrieve'", "Checkpoint after 'draft'", "Checkpoint after 'check'"],
        )

    def test_no_matching_sections_routes_to_the_dead_end_with_no_model_call(self) -> None:
        tracer = Tracer(example="workflow_graphs", level=3, model_id="none")
        answer = run("zzz qqq unmatched gibberish", None, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 0, "no_match must never call the model")
        self.assertIn("None of the retrieved sections", answer.text)
        self.assertEqual(answer.citations, [])
        node_titles = [s.title for s in tracer.steps if s.title.startswith("Node:")]
        self.assertEqual(node_titles, ["Node: retrieve", "Node: no_match"])

    def test_a_bad_citation_is_caught_and_fixed_within_the_cap(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6"),
            StubResponse(text=PASS_TOKEN),
        ])
        tracer = Tracer(example="workflow_graphs", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        revise_steps = [s for s in tracer.steps if s.title == "Node: revise"]
        self.assertEqual(len(revise_steps), 1)
        self.assertEqual(answer.citations, ["dw300-manual#6"])
        last_checkpoint = [s for s in tracer.steps if s.title.startswith("Checkpoint")][-1]
        self.assertIn("stop", last_checkpoint.detail)

    def test_a_draft_that_never_passes_stops_at_the_cap(self) -> None:
        model = StubModel([
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
            StubResponse(text="Every 30 cycles. Sources: dw300-manual#6, recall-notice#1"),
            StubResponse(text="MISSING: recall-notice#1"),
        ])
        tracer = Tracer(example="workflow_graphs", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        revise_steps = [s for s in tracer.steps if s.title == "Node: revise"]
        self.assertEqual(len(revise_steps), 2, "must not exceed the code-owned MAX_REVISIONS")
        self.assertIsInstance(answer.text, str)
        self.assertTrue(answer.text)
        last_checkpoint = [s for s in tracer.steps if s.title.startswith("Checkpoint")][-1]
        self.assertIn("revisions=2", last_checkpoint.detail)
        self.assertIn("-> next: stop", last_checkpoint.detail)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.workflow_graphs.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 3)


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)

    def test_the_scripted_sequence_visits_the_revise_node_once_before_passing(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="workflow_graphs", level=3, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        node_titles = [s.title for s in tracer.steps if s.title.startswith("Node:")]
        self.assertEqual(node_titles, ["Node: retrieve", "Node: draft", "Node: check", "Node: revise", "Node: check"])
        self.assertEqual(answer.citations, ["care-and-cleaning-guide#1"])
        last_checkpoint = [s for s in tracer.steps if s.title.startswith("Checkpoint")][-1]
        self.assertIn("-> next: stop", last_checkpoint.detail)


if __name__ == "__main__":
    unittest.main()
