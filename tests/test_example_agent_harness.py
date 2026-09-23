"""Tests for examples/agent_harness: the pluggable-parts example for the agent-harness page.

The central claim under test is not any one part -- it is that swapping ONE part (the context
policy) while the model's own scripted logic stays fixed changes the final answer. That is the
page's whole point: the harness, not the model, decided what the run could see. The other tests
check the caps, the hook veto, and the allowlist the same way tests/test_example_single_agent.py
checks single_agent's caps: script a model, run it, read the trace.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.agent_harness.__main__ import SCRIPTED  # noqa: E402
from examples.agent_harness.run import (  # noqa: E402
    DEFAULT_REGISTRY,
    ToolRegistry,
    deny_after,
    keep_everything,
    run,
    trim_to_budget,
)
from examples.common.model import Message, StubModel, StubResponse, ToolCall, content_text  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"
QUESTION = "What does the DW-300's drain pump cost, and how long is it under warranty?"

# The canonical end-to-end sequence this command runs with the default harness (every tool result
# kept, no hook): search, lookup, then answer from both results. Mirrored in
# examples/agent_harness/__main__.py's SCRIPTED.
SEQUENCE = [
    StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 warranty term"})]),
    StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
    StubResponse(text="$46.00, and the DW-300 has a 2-year full warranty."),
]


def _scripted_responder(messages, tools):
    """Calls search, then lookup_part, then answers from whatever tool results the harness
    actually left in the messages it was handed -- the same messages `run` builds, after
    `context_policy` has had its say. Nothing here knows which policy is in effect."""
    del tools
    called = [m for m in messages if m.tool_calls]
    if len(called) == 0:
        return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "DW-300 warranty term"})])
    if len(called) == 1:
        return StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})])
    seen = " ".join(content_text(m.content) for m in messages)
    if "warranty-policy" in seen:
        return StubResponse(text="$46.00, and the DW-300 has a 2-year full warranty.")
    return StubResponse(text="$46.00. I could not confirm the warranty term from what's in front of me.")


class DefaultHarnessEndToEndTests(unittest.TestCase):
    """The command this page prints runs with no flags: the default harness, `keep_everything`
    and `allow_everything`. This is the one fixed sequence that shape actually produces."""

    def test_the_default_harness_runs_search_then_lookup_then_answers(self) -> None:
        model = StubModel(list(SEQUENCE))
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.model_decided_count(), 3)
        self.assertIn("parts-list#2", answer.retrieved_sources)
        self.assertEqual(answer.citations, [], "retrieval must not supply missing answer citations")
        self.assertIn("46.00", answer.text)


class HarnessChangesTheOutcomeTests(unittest.TestCase):
    def test_the_same_scripted_model_answers_differently_under_a_tighter_context_policy(self) -> None:
        generous = run(
            QUESTION,
            StubModel(_scripted_responder, model_id="stub-1"),
            None,
            Tracer(example="agent_harness", level=5, model_id="stub-1"),
            corpus_dir=CORPUS_DIR,
            context_policy=keep_everything,
        )
        # the search result costs ~260 tokens (see this file's own reading of the corpus); a
        # budget of 15 keeps the ~10-token lookup result and drops the search result entirely
        tight = run(
            QUESTION,
            StubModel(_scripted_responder, model_id="stub-1"),
            None,
            Tracer(example="agent_harness", level=5, model_id="stub-1"),
            corpus_dir=CORPUS_DIR,
            context_policy=trim_to_budget(15),
        )
        self.assertIn("2-year", generous.text)
        self.assertNotIn("2-year", tight.text)
        self.assertIn("could not confirm", tight.text)
        # the tool actually ran either way, so the mechanical citations do not change -- only
        # what the model, reading a trimmed context, chose to say about them
        self.assertIn("parts-list#2", generous.retrieved_sources)
        self.assertEqual(generous.citations, [])
        self.assertIn("parts-list#2", tight.retrieved_sources)
        self.assertEqual(tight.citations, [])

    def test_the_tight_policy_leaves_a_visible_placeholder_not_a_silent_gap(self) -> None:
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-1")
        run(
            QUESTION,
            StubModel(_scripted_responder, model_id="stub-1"),
            None,
            tracer,
            corpus_dir=CORPUS_DIR,
            context_policy=trim_to_budget(15),
        )
        # the trim itself is not in the trace (it runs on every model call, not just once), but
        # the tool call it trims away is always recorded in full, so a reader can see what the
        # policy chose to hide
        tool_steps = [s for s in tracer.steps if s.title == "Run tool: search"]
        self.assertTrue(tool_steps)
        self.assertIn("warranty", tool_steps[0].detail.lower())


class ContextPolicyNeverTrimsTheQuestionTests(unittest.TestCase):
    """What a context policy must never drop. `trim_to_budget` once decided what was a tool result
    by reading how a user message opened, and the question is a user message, so a question that
    happened to start with the same words was replaced by the placeholder: the model was then
    asked to answer something it could no longer see, and answered anyway. It now goes by the
    `tool` role; these tests keep the question that caused it."""

    QUESTION_THAT_LOOKS_LIKE_A_TOOL_RESULT = (
        "Result of last week's service call: what does the DW-300's drain pump cost?"
    )

    def test_a_question_that_opens_like_a_tool_result_is_still_in_the_trimmed_context(self) -> None:
        messages = [
            Message(role="system", content="You answer questions about appliances."),
            Message(role="user", content=self.QUESTION_THAT_LOOKS_LIKE_A_TOOL_RESULT),
            Message(
                role="assistant",
                content="",
                tool_calls=(ToolCall(name="search", arguments={"query": "drain pump"}, id="call_0"),),
            ),
            Message(role="tool", content="filler text " * 200, tool_call_id="call_0", tool_name="search"),
        ]
        trimmed = trim_to_budget(15)(messages)
        self.assertEqual(content_text(trimmed[1].content), self.QUESTION_THAT_LOOKS_LIKE_A_TOOL_RESULT)
        self.assertIn("trimmed by the context policy", content_text(trimmed[3].content))
        # the placeholder still answers the call it replaced, so the history stays well formed
        self.assertEqual((trimmed[3].role, trimmed[3].tool_call_id), ("tool", "call_0"))

    def test_the_model_is_still_shown_that_question_on_every_call_of_a_real_run(self) -> None:
        seen: list[list[str]] = []

        def responder(messages, tools):
            del tools
            seen.append([content_text(m.content) for m in messages])
            called = [m for m in messages if m.tool_calls]
            if not called:
                return StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "drain pump"})])
            return StubResponse(text="$46.00.")

        run(
            self.QUESTION_THAT_LOOKS_LIKE_A_TOOL_RESULT,
            StubModel(responder, model_id="stub-1"),
            None,
            Tracer(example="agent_harness", level=5, model_id="stub-1"),
            corpus_dir=CORPUS_DIR,
            context_policy=trim_to_budget(15),
        )
        self.assertTrue(seen)
        for call_messages in seen:
            self.assertIn(self.QUESTION_THAT_LOOKS_LIKE_A_TOOL_RESULT, call_messages)

    def test_an_ordinary_tool_result_is_still_trimmed(self) -> None:
        """The guard must not turn the tight policy into the generous one."""
        messages = [
            Message(role="system", content="You answer questions about appliances."),
            Message(role="user", content="What does the DW-300's drain pump cost?"),
            Message(
                role="assistant",
                content="",
                tool_calls=(ToolCall(name="search", arguments={"query": "drain pump"}, id="call_0"),),
            ),
            Message(role="tool", content="filler text " * 200, tool_call_id="call_0", tool_name="search"),
        ]
        trimmed = trim_to_budget(15)(messages)
        self.assertIn("trimmed by the context policy", content_text(trimmed[3].content))


class HookVetoTests(unittest.TestCase):
    def test_a_hook_can_veto_a_call_the_model_already_chose(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "warranty"})]),
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
                StubResponse(text="I found the warranty term but could not price the part."),
            ]
        )
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, hook=deny_after(1))

        vetoed = [s for s in tracer.steps if s.title == "Hook vetoes the call"]
        self.assertEqual(len(vetoed), 1)
        self.assertEqual(vetoed[0].kind, "code")
        self.assertEqual(vetoed[0].decided_by, "code")
        self.assertEqual(vetoed[0].edge, "solid")
        self.assertIn("tool budget", vetoed[0].detail)
        # the vetoed call never ran, so its citation never arrives
        self.assertNotIn("parts-list#2", answer.citations)
        # the model itself still gets credit for choosing to call it -- the veto is the
        # harness's decision, not evidence the model decided not to act
        model_steps = [s for s in tracer.steps if s.title == "Model picks an action"]
        self.assertEqual(len(model_steps), 2)
        self.assertTrue(all(s.decided_by == "model" for s in model_steps))

    def test_default_hook_allows_every_call(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
                StubResponse(text="$46.00."),
            ]
        )
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertIn("parts-list#2", answer.retrieved_sources)
        self.assertEqual(answer.citations, [], "retrieval must not supply missing answer citations")
        self.assertFalse([s for s in tracer.steps if s.title == "Hook vetoes the call"])


class ToolRegistryTests(unittest.TestCase):
    def test_a_tool_advertised_but_missing_from_the_allowlist_is_refused_like_an_unknown_tool(self) -> None:
        from examples.common import tools as toolkit

        half_open = ToolRegistry(
            definitions=[toolkit.SEARCH_TOOL, toolkit.LOOKUP_PART_TOOL],
            allowed=frozenset({"search"}),  # lookup_part is shown to the model but not runnable
            call=DEFAULT_REGISTRY.call,
        )
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
                StubResponse(text="I could not look up that part."),
            ]
        )
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-1")
        answer = run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, registry=half_open)
        self.assertEqual(answer.citations, [])
        tool_steps = [s for s in tracer.steps if s.title.startswith("Run tool")]
        self.assertIn("unknown tool", tool_steps[0].detail)


class CapTests(unittest.TestCase):
    def test_step_cap_forces_a_stop_and_the_forced_answer_is_codes_decision(self) -> None:
        model = StubModel(
            lambda messages, tools: StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "warranty"})])
        )
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-loop")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_steps=3)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertEqual(forced[0].decided_by, "code")
        self.assertIn("step cap", forced[0].detail)
        self.assertFalse([s for s in tracer.steps if s.title == "Model stops and answers"])

    def test_token_budget_forces_a_stop_before_the_step_cap(self) -> None:
        model = StubModel(
            lambda messages, tools: StubResponse(tool_calls=[ToolCall(name="search", arguments={"query": "warranty"})])
        )
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-loop")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR, max_steps=50, max_tokens=1)
        forced = [s for s in tracer.steps if s.title == "Force a final answer"]
        self.assertEqual(len(forced), 1)
        self.assertIn("token budget", forced[0].detail)
        self.assertLess(len(tracer.steps), 10, "the loop should stop almost immediately, not run near 50 steps")


class DecidedByPatternTests(unittest.TestCase):
    def test_model_steps_are_dashed_and_code_steps_are_solid(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="lookup_part", arguments={"part_number": "HLV-2201"})]),
                StubResponse(text="$46.00."),
            ]
        )
        tracer = Tracer(example="agent_harness", level=5, model_id="stub-1")
        run(QUESTION, model, None, tracer, corpus_dir=CORPUS_DIR)
        for step in tracer.steps:
            if step.decided_by == "model":
                self.assertEqual(step.kind, "model")
                self.assertEqual(step.edge, "dashed")
            else:
                self.assertEqual(step.edge, "solid")

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.agent_harness.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 5)


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual(list(SCRIPTED), SEQUENCE)


if __name__ == "__main__":
    unittest.main()
