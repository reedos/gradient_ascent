"""Tests for examples/mcp: the JSON-RPC-shaped stand-in client/server for the MCP technique page
(level 4).

Two layers are checked: the stand-in protocol itself (`StandInServer.handle`, `list_tools`,
`call_tool`) against the message shapes it borrows from the specification, and the `run`
end-to-end trace, mirroring tests/test_example_function_calling.py's decided_by pattern.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.corpus import DEFAULT_CORPUS_DIR, load_sections  # noqa: E402
from examples.common.model import StubModel, StubResponse, ToolCall  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.mcp.__main__ import SCRIPTED  # noqa: E402
from examples.mcp.run import SEARCH_TOOL, StandInServer, call_tool, connect, list_tools, run  # noqa: E402

CORPUS_DIR = ROOT / "evals" / "corpus"

# The canonical end-to-end sequence: the model calls the stand-in server's one tool, then answers
# from what it returned. Mirrored in examples/mcp/__main__.py's SCRIPTED.
SEQUENCE = [
    StubResponse(tool_calls=[ToolCall(name="search_halvorsen_docs", arguments={"query": "HLV-2205"})]),
    StubResponse(text="HLV-2205 is a drain pump that costs $52.00. Sources: parts-list#2"),
]


class StandInProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sections = load_sections(CORPUS_DIR)
        self.transport = connect(StandInServer(self.sections))

    def test_tools_list_returns_the_one_tool_shaped_like_the_spec(self) -> None:
        tools = list_tools(self.transport)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], SEARCH_TOOL["name"])
        self.assertIn("inputSchema", tools[0])

    def test_tools_call_returns_text_content_with_a_real_citation(self) -> None:
        text, is_error = call_tool(self.transport, "search_halvorsen_docs", {"query": "HLV-2205 drain pump"})
        self.assertFalse(is_error)
        self.assertIn("parts-list#2", text.lower())

    def test_calling_an_unknown_tool_returns_a_protocol_error_not_a_crash(self) -> None:
        text, is_error = call_tool(self.transport, "delete_everything", {})
        self.assertTrue(is_error)
        self.assertIn("unknown tool", text)

    def test_an_unknown_method_returns_a_protocol_error(self) -> None:
        response = self.transport({"jsonrpc": "2.0", "id": 9, "method": "prompts/list", "params": {}})
        self.assertEqual(response["error"]["code"], -32602)


class McpExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.mcp.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 4)

    def test_a_tool_call_is_the_only_model_decided_step(self) -> None:
        model = StubModel(list(SEQUENCE))
        tracer = Tracer(example="mcp", level=4, model_id="stub-1")
        answer = run("What does part HLV-2205 cost?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.model_decided_count(), 1)
        decided_by_model = [s for s in tracer.steps if s.decided_by == "model"]
        self.assertEqual(len(decided_by_model), 1)
        self.assertIn("search_halvorsen_docs", decided_by_model[0].title)
        self.assertIn("52.00", answer.text)
        self.assertIn("parts-list#2", answer.citations)

    def test_answering_without_a_tool_call_is_still_the_one_model_decided_step(self) -> None:
        model = StubModel([StubResponse(text="A dishwasher and a dryer are both major appliances.")])
        tracer = Tracer(example="mcp", level=4, model_id="stub-1")
        answer = run("What is a major appliance?", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.model_decided_count(), 1)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1)
        self.assertEqual(answer.citations, [])

    def test_a_hallucinated_tool_name_comes_back_as_a_protocol_error_the_model_can_see(self) -> None:
        model = StubModel(
            [
                StubResponse(tool_calls=[ToolCall(name="delete_everything", arguments={})]),
                StubResponse(text="I don't have a way to do that."),
            ]
        )
        tracer = Tracer(example="mcp", level=4, model_id="stub-1")
        answer = run("Delete my account", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "the error is reported back, not swallowed")
        self.assertEqual(answer.citations, [])
        server_step = next(s for s in tracer.steps if s.title == "MCP server returns a tool result")
        self.assertIn("unknown tool", server_step.detail)

    def test_the_first_step_lists_tools_from_the_server_before_the_model_sees_the_question(self) -> None:
        model = StubModel([StubResponse(text="answer")])
        tracer = Tracer(example="mcp", level=4, model_id="stub-1")
        run("anything", model, None, tracer, corpus_dir=CORPUS_DIR)
        self.assertEqual(tracer.steps[0].title, "List tools from the MCP server")
        self.assertEqual(tracer.steps[0].decided_by, "code")


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual(list(SCRIPTED), SEQUENCE)


if __name__ == "__main__":
    unittest.main()
