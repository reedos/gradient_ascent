"""Tests for examples/agent_graphs: the supervisor-graph example for the agent-graphs technique
page. Mirrors the shape of tests/test_examples.py's ExampleTraceTests: run end to end on a
scripted StubModel and check the trace's decided_by pattern -- every "Supervisor picks the next
agent" step is decided_by="model", everything else is "code" -- plus the hop cap and the
allowlist guard against a hallucinated handoff target.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.agent_graphs.run import ALLOWED_HANDOFFS, MAX_RESEARCH_HOPS, run  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "What is the maximum vent run for the DR-520, and does anything supersede the manual's figure?"


def _supervisor_prompt(m: Message) -> bool:
    return "Reply with exactly one word" in m.content


class AgentGraphsExampleTests(unittest.TestCase):
    def test_three_research_hops_then_a_natural_write_decision(self) -> None:
        model = StubModel(
            [
                StubResponse(text="research"),
                StubResponse(text="research"),
                StubResponse(text="research"),
                StubResponse(text="write"),
                StubResponse(text="The DR-520's vent run is limited to 25 feet with up to 3 elbows, which supersedes the manual's 35-foot, 4-elbow figure. Sources: dr520-manual#4, service-bulletin#2"),
            ]
        )
        tracer = Tracer(example="agent_graphs", level=6, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)

        supervisor_steps = [s for s in tracer.steps if s.title == "Supervisor picks the next agent"]
        research_checkpoints = [s for s in tracer.steps if s.title == "Checkpoint after 'research'"]
        write_checkpoints = [s for s in tracer.steps if s.title == "Checkpoint after 'write'"]
        self.assertEqual(len(supervisor_steps), 4)
        self.assertTrue(all(s.decided_by == "model" for s in supervisor_steps))
        self.assertEqual(len(research_checkpoints), 3)
        self.assertEqual(len(write_checkpoints), 1)
        self.assertTrue(all(s.decided_by == "code" for s in research_checkpoints + write_checkpoints))
        self.assertEqual(tracer.model_decided_count(), 4, "only the four handoff choices are model decisions")
        self.assertFalse(any(s.title in ("Hop cap reached", "Handoff blocked") for s in tracer.steps))
        # bm25 over the real corpus, excluding what was already found each hop, turns up these
        # three sections for this question, in this order (checked directly against evals/corpus).
        self.assertEqual(answer.citations, ["dr520-manual#4", "service-bulletin#1", "service-bulletin#2"])

    def test_the_hop_cap_stops_the_team_without_asking_the_model_again(self) -> None:
        def always_research(messages, tools):
            if _supervisor_prompt(messages[-1]):
                return StubResponse(text="research")
            return StubResponse(text="Not enough was found to answer confidently.")

        model = StubModel(always_research)
        tracer = Tracer(example="agent_graphs", level=6, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_research_hops=2)

        supervisor_steps = [s for s in tracer.steps if s.title == "Supervisor picks the next agent"]
        cap_steps = [s for s in tracer.steps if s.title == "Hop cap reached"]
        self.assertEqual(len(supervisor_steps), 2, "the cap fires before a third supervisor call")
        self.assertEqual(len(cap_steps), 1)
        self.assertTrue(all(s.decided_by == "code" for s in cap_steps))
        self.assertIsInstance(answer.text, str)
        self.assertTrue(answer.text)

    def test_a_handoff_outside_the_allowlist_is_blocked_not_followed(self) -> None:
        model = StubModel(
            [
                StubResponse(text="delete_database"),
                StubResponse(text="I cannot answer without any findings."),
            ]
        )
        tracer = Tracer(example="agent_graphs", level=6, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)

        self.assertNotIn("delete_database", ALLOWED_HANDOFFS)
        blocked = [s for s in tracer.steps if s.title == "Handoff blocked"]
        self.assertEqual(len(blocked), 1)
        self.assertIn("delete_database", blocked[0].detail)
        research_checkpoints = [s for s in tracer.steps if s.title == "Checkpoint after 'research'"]
        self.assertEqual(research_checkpoints, [], "the invented target must not be treated as research")
        self.assertEqual(sum(1 for s in tracer.steps if s.title == "Supervisor picks the next agent"), 1)
        self.assertEqual(answer.citations, [])
        self.assertTrue(answer.text)

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.agent_graphs.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 6)
        self.assertEqual(module.MAX_RESEARCH_HOPS, MAX_RESEARCH_HOPS)


if __name__ == "__main__":
    unittest.main()
