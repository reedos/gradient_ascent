"""Tests for examples/orchestrator_workers: the lead-agent-and-workers example for the
orchestrator-workers technique page. Mirrors the shape of tests/test_examples.py's
ExampleTraceTests: run end to end on a scripted StubModel and check the trace's decided_by
pattern -- exactly one model-decided step, the split -- plus the worker cap, the team token
budget, and that a duplicate sub-question does not spawn two workers.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubEmbedder, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.orchestrator_workers.__main__ import SCRIPTED  # noqa: E402
from examples.orchestrator_workers.run import MAX_WORKERS, run  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "What is the DW-300's annual energy use, and how much does the DR-520's drive belt cost?"

# The same sequence examples/orchestrator_workers/__main__.py plays under --model stub:scripted.
SEQUENCE = [
    "What is the DW-300's annual energy use?\nWhat does the DR-520's drive belt cost?",
    "260 kWh per year. Sources: dw300-manual#3",
    "$9.75, part HLV-6601. Sources: parts-list#3",
    "The DW-300 uses about 260 kWh per year [dw300-manual#3]. The DR-520's drive belt costs $9.75 [parts-list#3]. Sources: dw300-manual#3, parts-list#3",
]


class OrchestratorWorkersExampleTests(unittest.TestCase):
    def test_split_is_the_only_model_decided_step(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="orchestrator_workers", level=6, model_id="stub-1")
        answer = run(QUESTION, model, StubEmbedder(), tracer, corpus_dir=CORPUS_DIR)

        model_decided = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(model_decided), 1, "only the split is a model decision")
        self.assertEqual(model_decided[0].title, "Lead splits the task")
        self.assertEqual(tracer.model_decided_count(), 1)
        self.assertEqual(sum(1 for s in tracer.steps if s.title.startswith("Spawn worker")), 2)
        self.assertEqual(answer.citations, ["dw300-manual#3", "parts-list#3"])

    def test_more_subquestions_than_the_cap_are_dropped_not_run(self) -> None:
        lines = "\n".join(f"Sub-question {i} about Halvorsen appliances" for i in range(1, 6))
        model = StubModel(
            [StubResponse(text=lines)]
            + [StubResponse(text=f"Answer {i}. Sources: dw300-manual#1") for i in range(1, MAX_WORKERS + 1)]
            + [StubResponse(text="Combined answer. Sources: dw300-manual#1")]
        )
        tracer = Tracer(example="orchestrator_workers", level=6, model_id="stub-1")
        run(QUESTION, model, StubEmbedder(), tracer, corpus_dir=CORPUS_DIR)

        cap_steps = [s for s in tracer.steps if s.title == "Cap the team"]
        self.assertEqual(len(cap_steps), 1)
        self.assertIn("asked for 5 workers", cap_steps[0].detail)
        self.assertEqual(sum(1 for s in tracer.steps if s.title.startswith("Spawn worker")), MAX_WORKERS)

    def test_a_duplicate_subquestion_spawns_one_worker_not_two(self) -> None:
        model = StubModel(
            [
                StubResponse(text="What is the DW-300's annual energy use?\nWhat is the DW-300's annual energy use?"),
                StubResponse(text="260 kWh per year. Sources: dw300-manual#3"),
                StubResponse(text="Combined answer. Sources: dw300-manual#3"),
            ]
        )
        tracer = Tracer(example="orchestrator_workers", level=6, model_id="stub-1")
        run(QUESTION, model, StubEmbedder(), tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.title.startswith("Spawn worker")), 1)

    def test_team_token_budget_stops_spawning_workers_early(self) -> None:
        model = StubModel(
            [
                StubResponse(text="Sub-question one\nSub-question two\nSub-question three"),
                StubResponse(text="Answer one. Sources: dw300-manual#1"),
                StubResponse(text="Combined answer. Sources: dw300-manual#1"),
            ]
        )
        tracer = Tracer(example="orchestrator_workers", level=6, model_id="stub-1")
        run(QUESTION, model, StubEmbedder(), tracer, corpus_dir=CORPUS_DIR, max_team_tokens=100)

        budget_steps = [s for s in tracer.steps if s.title == "Team token budget reached"]
        self.assertEqual(len(budget_steps), 1)
        self.assertEqual(sum(1 for s in tracer.steps if s.title.startswith("Spawn worker")), 1)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.orchestrator_workers.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 6)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)


if __name__ == "__main__":
    unittest.main()
