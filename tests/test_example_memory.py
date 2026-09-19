"""Tests for examples/memory: write, recall by relevance, and forget over a small synthetic fact
set, then one answer built from whatever recall turned up. Every step is `decided_by: "code"`."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubEmbedder, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.memory.__main__ import SCRIPTED  # noqa: E402
from examples.memory.run import LEVEL, MemoryStore, run  # noqa: E402

FACTS = [
    "Owns a Halvorsen DW-300 dishwasher, purchased 2024-03-15.",
    "The DW-300 is installed in a rental property the user manages.",
    "Prefers email over phone for service updates.",
    "Also owns a Halvorsen DR-520 dryer, electric version, purchased 2025-01-10.",
]
QUESTION = "Is my dishwasher still covered under warranty?"
SEQUENCE = [
    "No. The DW-300 was purchased 2024-03-15 and is installed in a rental property, which limits "
    "coverage to 90 days from the purchase date. That window closed months ago."
]


class MemoryStoreTests(unittest.TestCase):
    """The store itself, independent of run()'s trace and model call."""

    def test_write_then_recall_finds_the_written_entry(self) -> None:
        store = MemoryStore(StubEmbedder())
        entry_id = store.write("The sky over the shop is blue today.")
        results = store.recall("What color is the sky?", k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].id, entry_id)

    def test_forget_removes_the_entry_from_every_later_recall(self) -> None:
        store = MemoryStore(StubEmbedder())
        entry_id = store.write("The warranty on the DW-300 expired last year.")
        self.assertTrue(store.forget(entry_id))
        results = store.recall("Tell me about the DW-300 warranty.", k=5)
        self.assertNotIn(entry_id, [e.id for e, _ in results])

    def test_forgetting_an_unknown_id_reports_it_did_nothing(self) -> None:
        store = MemoryStore(StubEmbedder())
        self.assertFalse(store.forget("m99"))

    def test_recall_on_an_empty_store_returns_nothing_and_does_not_crash(self) -> None:
        store = MemoryStore(StubEmbedder())
        self.assertEqual(store.recall("anything"), [])


class MemoryRunTraceTests(unittest.TestCase):
    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel([StubResponse(text="Coverage ended after 90 days for rental use.")])
        tracer = Tracer(example="memory", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, StubEmbedder(), tracer, facts=FACTS)
        self.assertTrue(tracer.steps, "recorded no steps at all")
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertIn("90 days", answer.text)

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 2)
        self.assertTrue(callable(run))

    def test_forgetting_a_fact_removes_it_from_the_citations(self) -> None:
        model = StubModel([StubResponse(text="answer 1")])
        tracer = Tracer(example="memory", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, StubEmbedder(), tracer, facts=FACTS, k=len(FACTS))
        self.assertIn("m1", answer.citations, "the rental-property fact should be recalled before it is forgotten")

        model2 = StubModel([StubResponse(text="answer 2")])
        tracer2 = Tracer(example="memory", level=LEVEL, model_id="stub-1")
        answer2 = run(QUESTION, model2, StubEmbedder(), tracer2, facts=FACTS, forget_ids=["m1"], k=len(FACTS))
        self.assertNotIn("m1", answer2.citations, "a forgotten entry must never be recalled again")

    def test_no_facts_written_yields_no_recall_and_an_empty_context_answer(self) -> None:
        model = StubModel([StubResponse(text="I have no relevant memories.")])
        tracer = Tracer(example="memory", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, StubEmbedder(), tracer, facts=[])
        self.assertEqual(answer.citations, [])
        recall_step = next(s for s in tracer.steps if "Recall memories" in s.title)
        self.assertEqual(recall_step.detail, "none recalled")

    def test_k_controls_how_many_memories_can_be_recalled(self) -> None:
        model = StubModel([StubResponse(text="ok")])
        tracer = Tracer(example="memory", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, StubEmbedder(), tracer, facts=FACTS, k=2)
        self.assertEqual(len(answer.citations), 2)


class ScriptedCommandTests(unittest.TestCase):
    """The sequence `python -m examples.memory --model stub:scripted` plays, run the same way
    the CLI runs it, plus the guard that keeps the two in step."""

    def test_the_scripted_sequence_answers_from_what_recall_actually_finds(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="memory", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, StubEmbedder(), tracer, facts=FACTS)
        self.assertIn("90 days", answer.text)
        self.assertEqual(answer.citations, ["m0", "m1", "m2"])

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)


if __name__ == "__main__":
    unittest.main()
