"""Tests for examples/voice_agents: the text-simulated turn-control example for the voice-agents
technique page. Mirrors the shape of tests/test_examples.py's ExampleTraceTests: run end to end
on a scripted StubModel and check the trace's decided_by pattern, including the two kinds of
forced stop (a simulated interruption, and the chunk/token caps) that are not the model's choice.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import AudioPart, StubModel, StubResponse, TextPart, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.voice_agents.__main__ import SCRIPTED  # noqa: E402
from examples.voice_agents.run import run  # noqa: E402

QUESTION = "What time do you close tonight?"
CONTINUE = ToolCall(name="continue_speaking", arguments={})

# The same sequence examples/voice_agents/__main__.py plays under --model stub:scripted.
SEQUENCE = [
    StubResponse(text="We close at nine,", tool_calls=[CONTINUE]),
    "but the kitchen closes at eight-thirty.",
]


class VoiceAgentsExampleTests(unittest.TestCase):
    def test_the_caller_turn_carries_an_audio_part_and_a_transcript(self) -> None:
        model = StubModel([StubResponse(text="We close at nine.")])
        tracer = Tracer(example="voice_agents", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer)
        first = tracer.steps[0]
        self.assertEqual(first.title, "Caller speaks")
        self.assertIn(QUESTION, first.detail)
        self.assertEqual(first.decided_by, "code")

    def test_a_one_chunk_answer_is_a_single_model_decision_to_yield(self) -> None:
        model = StubModel([StubResponse(text="We close at nine tonight.")])
        tracer = Tracer(example="voice_agents", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer)
        self.assertEqual(tracer.model_decided_count(), 1)
        yield_steps = [s for s in tracer.steps if s.title == "Model finishes and yields the floor"]
        self.assertEqual(len(yield_steps), 1)
        self.assertEqual(yield_steps[0].edge, "dashed")
        self.assertEqual(answer.text, "We close at nine tonight.")

    def test_a_multi_chunk_answer_records_a_model_decision_per_chunk_plus_the_stop(self) -> None:
        model = StubModel([StubResponse(text=t) if isinstance(t, str) else t for t in SEQUENCE])
        tracer = Tracer(example="voice_agents", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer)
        self.assertEqual(tracer.model_decided_count(), 2)
        self.assertEqual(answer.text, "We close at nine, but the kitchen closes at eight-thirty.")

    def test_a_simulated_interruption_cuts_the_agent_off_and_is_codes_decision(self) -> None:
        model = StubModel(
            [
                StubResponse(text="We close at nine,", tool_calls=[CONTINUE]),
                StubResponse(text="and on weekends we close at ten,", tool_calls=[CONTINUE]),
                StubResponse(text="never reached"),
            ]
        )
        tracer = Tracer(example="voice_agents", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, interrupt_after_chunk=2)
        interrupt_steps = [s for s in tracer.steps if "Caller interrupts" in s.title]
        self.assertEqual(len(interrupt_steps), 1)
        self.assertEqual(interrupt_steps[0].decided_by, "code")
        # the model chose to keep talking twice; the interruption was never its choice
        self.assertEqual(tracer.model_decided_count(), 2)
        self.assertNotIn("never reached", answer.text)

    def test_the_chunk_cap_cuts_the_agent_off_if_it_never_yields(self) -> None:
        model = StubModel(lambda messages, tools: StubResponse(text="still talking,", tool_calls=[CONTINUE]))
        tracer = Tracer(example="voice_agents", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, max_chunks=3)
        cap_steps = [s for s in tracer.steps if s.title == "Chunk cap reached; code cuts the agent off"]
        self.assertEqual(len(cap_steps), 1)
        self.assertEqual(cap_steps[0].decided_by, "code")
        self.assertIn("3 chunks", cap_steps[0].detail)
        self.assertEqual(tracer.model_decided_count(), 3, "all three chunks were the model choosing to keep talking")
        self.assertIsInstance(answer.text, str)
        self.assertTrue(answer.text)

    def test_the_token_budget_cuts_the_agent_off_before_the_chunk_cap(self) -> None:
        model = StubModel(lambda messages, tools: StubResponse(text="still talking,", tool_calls=[CONTINUE]))
        tracer = Tracer(example="voice_agents", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer, max_chunks=50, max_tokens=1)
        budget_steps = [s for s in tracer.steps if "Latency budget reached" in s.title]
        self.assertEqual(len(budget_steps), 1)
        self.assertEqual(budget_steps[0].decided_by, "code")
        self.assertLess(len(tracer.steps), 10)

    def test_the_audio_part_is_a_real_part_type_not_a_string(self) -> None:
        # honesty check: the caller's turn really is carried as an AudioPart + TextPart, not
        # just a plain string dressed up in prose
        captured = {}

        def responder(messages, tools):
            captured["content"] = messages[-1].content
            return StubResponse(text="ok")

        tracer = Tracer(example="voice_agents", level=5, model_id="stub-1")
        run(QUESTION, StubModel(responder), None, tracer)
        parts = captured["content"]
        self.assertTrue(any(isinstance(p, AudioPart) for p in parts))
        self.assertTrue(any(isinstance(p, TextPart) and p.text == QUESTION for p in parts))

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.voice_agents.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 5)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual(SCRIPTED, SEQUENCE)


if __name__ == "__main__":
    unittest.main()
