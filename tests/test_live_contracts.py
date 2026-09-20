"""Live-backend contracts and scoring regressions, without keys or network calls."""
from __future__ import annotations

import contextlib
import copy
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import get_type_hints
from unittest.mock import patch

from examples.common import model as backend
from examples.common.model import Embedder, Message, StubEmbedder, StubModel, StubResponse, ToolCall
from examples.common.trace import Tracer
from examples.common.types import Answer, cited_sources
from examples.function_calling.run import TOOLS
from examples.structured_output.run import SCHEMA, run as structured_run
from scripts import eval_run


class RequestContracts(unittest.TestCase):
    def test_ollama_wraps_the_actual_example_tools(self):
        definitions = copy.deepcopy(TOOLS)
        with patch.object(backend, "_post_json", return_value={"message": {"content": "ok"}}) as post:
            backend.OllamaModel("test").complete([Message("user", "hello")], tools=TOOLS)
        payload = post.call_args.args[1]
        self.assertEqual(payload["tools"], [{"type": "function", "function": t} for t in TOOLS])
        self.assertEqual(TOOLS, definitions)

    def test_claude_sends_the_actual_extraction_schema_over_http(self):
        response = io.BytesIO(json.dumps({"content": [{"type": "text", "text": "{}"}]}).encode())
        with patch.object(backend.urllib.request, "urlopen", return_value=response) as post:
            backend.ClaudeModel("test", api_key="test-only").complete([Message("user", "extract")], schema=SCHEMA)
        payload = json.loads(post.call_args.args[0].data)
        self.assertEqual(payload["output_config"]["format"], {"type": "json_schema", "schema": SCHEMA})

    def test_nested_objects_are_closed_without_mutating_the_schema(self):
        schema = {"type": "object", "properties": {
            "rows": {"type": "array", "items": {"type": "object", "properties": {"type": {"type": "string"}}}},
            "choice": {"anyOf": [{"type": "object", "properties": {}}, {"type": "null"}]},
        }}
        original = copy.deepcopy(schema)
        result = backend._anthropic_schema(schema)
        self.assertIs(result["additionalProperties"], False)
        self.assertIs(result["properties"]["rows"]["items"]["additionalProperties"], False)
        self.assertIs(result["properties"]["choice"]["anyOf"][0]["additionalProperties"], False)
        self.assertEqual(result["properties"]["rows"]["items"]["properties"]["type"], {"type": "string"})
        self.assertEqual(schema, original)

    def test_explicit_open_dictionary_is_rejected_before_http(self):
        for additional in (True, {"type": "string"}):
            with self.subTest(additional=additional), patch.object(backend.urllib.request, "urlopen") as post:
                with self.assertRaisesRegex(ValueError, "additionalProperties"):
                    backend.ClaudeModel("test", api_key="test-only").complete(
                        [Message("user", "extract")], schema={"type": "object", "additionalProperties": additional},
                    )
                post.assert_not_called()

    def test_other_constraints_are_not_silently_removed(self):
        schema = {"type": "integer", "minimum": 10}
        self.assertEqual(backend._anthropic_schema(schema), schema)


class StructuredValidation(unittest.TestCase):
    valid = dict(model="DW-480", full_warranty_years=2, limited_years=5,
                 limited_scope="motor", commercial_rental_days=90)

    def answer(self, replies):
        tracer = Tracer(example="structured_output", level=1, model_id="stub")
        model = StubModel([StubResponse(text=json.dumps(reply)) for reply in replies])
        return structured_run("DW-480 warranty?", model, tracer), tracer

    def test_scalar_and_array_json_retry_into_a_valid_object(self):
        for bad in (None, 42, True, "model", [], ["model"]):
            with self.subTest(bad=bad):
                answer, tracer = self.answer([bad, self.valid])
                self.assertEqual(json.loads(answer.text), self.valid)
                self.assertEqual(sum(s.kind == "model" for s in tracer.steps), 2)

    def test_booleans_and_other_wrong_field_types_trigger_retry(self):
        for field in ("full_warranty_years", "limited_years", "commercial_rental_days"):
            for value in (True, False, "2", None, 2.5):
                with self.subTest(field=field, value=value):
                    answer, tracer = self.answer([dict(self.valid, **{field: value}), self.valid])
                    self.assertEqual(json.loads(answer.text), self.valid)
                    self.assertEqual(sum(s.kind == "model" for s in tracer.steps), 2)

    def test_extra_fields_are_rejected_like_the_provider_schema_requires(self):
        answer, tracer = self.answer([dict(self.valid, extra="unexpected"), self.valid])
        self.assertEqual(json.loads(answer.text), self.valid)
        self.assertEqual(sum(s.kind == "model" for s in tracer.steps), 2)

    def test_repeated_scalar_failure_stops_at_the_retry_cap(self):
        answer, tracer = self.answer([None, 42])
        self.assertIn("error", json.loads(answer.text))
        self.assertEqual(answer.citations, [])
        self.assertEqual(sum(s.kind == "model" for s in tracer.steps), 2)


class EvaluationSetup(unittest.TestCase):
    def test_embedding_registry_matches_required_run_parameters(self):
        required = {name for name in eval_run.EXAMPLE_NAMES
                    if get_type_hints(eval_run.load_run_fn(name)[0]).get("embedder") is Embedder}
        self.assertEqual(required, eval_run.EMBEDDING_EXAMPLES)

    def test_unused_embedder_is_never_constructed(self):
        for name in set(eval_run.EXAMPLE_NAMES) - eval_run.EMBEDDING_EXAMPLES:
            with self.subTest(name=name), patch.object(eval_run, "build_embedder") as build:
                self.assertIsNone(eval_run.evaluation_embedder([name], "claude:test", None))
                build.assert_not_called()

    def test_embedding_spec_is_independent_and_defaults_for_ollama_and_stub(self):
        self.assertIsInstance(eval_run.evaluation_embedder(["rag"], "claude:test", "stub"), StubEmbedder)
        self.assertEqual(eval_run.evaluation_embedder(["rag"], "claude:test", "ollama:embed").model_id, "ollama:embed")
        self.assertEqual(eval_run.evaluation_embedder(["rag"], "ollama:test", None).model_id, "ollama:test")
        self.assertIsInstance(eval_run.evaluation_embedder(["rag"], "stub", None), StubEmbedder)

    def test_missing_claude_embedder_fails_before_loading_a_key_or_making_a_cache(self):
        for name in ("rag", "all"):
            with self.subTest(name=name), patch.object(eval_run, "build_model") as build, contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(eval_run.main(["--example", name, "--model", "claude:test"]), 2)
                self.assertIn("--embedder", err.getvalue())
                build.assert_not_called()

    def test_cli_runs_claude_with_and_without_retrieval_using_a_mocked_backend(self):
        for name, extra in (("one_call", []), ("rag", ["--embedder", "stub"])):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
                raw = StubModel([StubResponse(text="No answer.")], model_id="claude:test")
                with patch.object(eval_run, "build_model", return_value=raw):
                    status = eval_run.main(["--example", name, "--model", "claude:test", "--kind", "lookup", "--limit", "1",
                                            "--cache-dir", str(Path(tmp) / "cache"), "--out", tmp, *extra])
                self.assertEqual(status, 0)
                result = json.loads((Path(tmp) / name / "claude_test.json").read_text())
                self.assertEqual(result["scoring_version"], 2)
                self.assertEqual(result["embedder_id"], "stub-embed-1" if name == "rag" else None)

    def test_dry_cli_never_constructs_live_backends(self):
        with patch.object(eval_run, "build_model") as model, patch.object(eval_run, "build_embedder") as embedder, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(eval_run.main(["--example", "rag", "--model", "claude:test", "--embedder", "ollama:test", "--dry", "--limit", "1"]), 0)
            model.assert_not_called()
            embedder.assert_not_called()


class CitationContracts(unittest.TestCase):
    def test_parser_normalizes_supported_spelling_variants_and_deduplicates(self):
        text = "Sources: DW300-manual#3, evals/corpus/dw300-manual.md, section 3; parts-list \u00a7 2"
        self.assertEqual(cited_sources(text), ["dw300-manual#3", "parts-list#2"])

    def test_retrieval_does_not_create_citations(self):
        answer = Answer.from_text("I do not know.", ["parts-list#2"])
        question = {"must_cite": ["parts-list#2"]}
        self.assertEqual(eval_run.citation_hit(question, answer), 0)
        self.assertEqual(eval_run.retrieval_hit(question, answer), 1)

    def test_only_the_subset_cited_in_the_answer_earns_credit(self):
        answer = Answer.from_text("Sources: parts-list#2", ["parts-list#2", "warranty-policy#1"])
        question = {"must_cite": ["parts-list#2", "warranty-policy#1"]}
        self.assertEqual(eval_run.citation_hit(question, answer), 0.5)
        self.assertEqual(eval_run.retrieval_hit(question, answer), 1)

    def test_uncited_tool_answers_keep_retrieval_separate_on_natural_and_forced_stops(self):
        for name in ("function_calling", "mcp", "single_agent", "agent_harness", "agentic_rag"):
            for stop in (("natural", "steps", "tokens") if name in ("single_agent", "agent_harness", "agentic_rag") else ("natural",)):
                with self.subTest(name=name, stop=stop):
                    module = importlib.import_module(f"examples.{name}.run")
                    if name == "mcp":
                        call = ToolCall("search_halvorsen_docs", {"query": "HLV-2205"})
                    elif name == "agentic_rag":
                        call = ToolCall("read", {"cite": "parts-list#2"})
                    else:
                        call = ToolCall("lookup_part", {"part_number": "HLV-2205"})
                    replies = [StubResponse(tool_calls=[call]), StubResponse(text="It costs $52.00.")]
                    if name == "single_agent":
                        replies.insert(0, StubResponse(text="Look up the part."))
                    tracer = Tracer(example=name, level=module.LEVEL, model_id="stub")
                    kwargs = {"max_steps": 1} if stop == "steps" else {"max_tokens": 0} if stop == "tokens" else {}
                    answer = module.run("What does HLV-2205 cost?", StubModel(replies), None, tracer, **kwargs)
                    self.assertIn("parts-list#2", answer.retrieved_sources)
                    self.assertEqual(answer.citations, [])

    def test_lead_cannot_inherit_citations_it_dropped_from_worker_answers(self):
        module = importlib.import_module("examples.orchestrator_workers.run")
        worker = Answer.from_text("Sources: parts-list#2", ["parts-list#2"])
        with patch.object(module, "rag_worker", return_value=worker):
            answer = module.run("Price?", StubModel([StubResponse(text="Price?"), StubResponse(text="$52.")]),
                                StubEmbedder(), Tracer(example="orchestrator_workers", level=6, model_id="stub"))
        self.assertEqual(answer.citations, [])
        self.assertEqual(answer.retrieved_sources, ["parts-list#2"])

    def test_result_file_contains_distinct_metrics_and_source_lists(self):
        model = StubModel([StubResponse(tool_calls=[ToolCall("lookup_part", {"part_number": "HLV-2205"})]), StubResponse(text="$52.")])
        question = dict(id="T", kind="lookup", question="HLV-2205 price?", grading="exact", accept=["52"], must_cite=["parts-list#2"])
        result = eval_run.run_example("function_calling", model=model, embedder=None, grader=None,
                                      questions=[question], stub=True, dry=False)
        self.assertEqual(result["citation_coverage"], 0)
        self.assertEqual(result["retrieval_coverage"], 1)
        self.assertEqual(result["questions"][0]["citations"], [])
        self.assertEqual(result["questions"][0]["retrieved_sources"], ["parts-list#2"])
