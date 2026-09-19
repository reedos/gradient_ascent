"""Tests for the shared code every example is built on, and for the corpus loader.

`examples/common/` and `evals/corpus.py` had no tests of their own: they were exercised only
through whichever example happened to call them, so a contract could break and the failure would
surface somewhere else, in a test about a technique. The contracts checked here are the ones
other files are written against and would be wrong without:

- `Embedder` returns unit vectors, which is why `examples/rag/run.py` scores retrieval with a
  bare dot product and calls the result a cosine.
- `Tracer`'s token totals, which `examples/orchestrator_workers/run.py` enforces a team budget
  with.
- `decided_by` is never defaulted by `agent_loop.record_completion`, and is always "code" for
  `force_final`.
- `parse_sections` folds a document's preamble into section 1, so a citation to section 1 also
  carries the revision line -- documented in `evals/corpus.py` and relied on by the question set.
- `bm25_search` ranks, and scores a section with no query term at zero, which every example that
  writes `if score > 0` depends on to mean "this section is not relevant".
"""
from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.corpus import (  # noqa: E402
    DEFAULT_CORPUS_DIR,
    bm25_search,
    load_sections,
    normalize_whitespace,
    parse_sections,
    tokenize,
)
from examples.common import cli  # noqa: E402
from examples.common.agent_loop import FINAL_TURN, FORCE_TITLE, force_final, record_completion  # noqa: E402
from examples.common.model import (  # noqa: E402
    AudioPart,
    Completion,
    ImagePart,
    Message,
    StubEmbedder,
    StubModel,
    StubResponse,
    TextPart,
    build_embedder,
    build_model,
    content_payload,
    content_text,
    count_tokens,
    to_unit,
)
from examples.common.trace import Tracer, git_commit  # noqa: E402


def _tracer() -> Tracer:
    return Tracer(example="test", level=5, model_id="stub-1")


class UnitVectorContractTests(unittest.TestCase):
    def test_to_unit_returns_a_vector_of_length_one(self) -> None:
        for vector in ([3.0, 4.0], [1.0], [-2.0, 0.0, 2.0], [0.5] * 10):
            with self.subTest(vector=vector):
                length = sum(v * v for v in to_unit(vector)) ** 0.5
                self.assertAlmostEqual(length, 1.0, places=12)

    def test_to_unit_leaves_an_all_zero_vector_alone_rather_than_dividing_by_zero(self) -> None:
        self.assertEqual(to_unit([0.0, 0.0, 0.0]), [0.0, 0.0, 0.0])

    def test_to_unit_keeps_direction_so_ranking_does_not_change(self) -> None:
        scaled = to_unit([2.0, 4.0])
        self.assertAlmostEqual(scaled[1] / scaled[0], 2.0, places=12)

    def test_every_stub_embedding_of_real_text_is_a_unit_vector(self) -> None:
        # The contract examples/rag/run.py's bare dot product depends on.
        for vector in StubEmbedder().embed(["one", "two words here", "REPEATED repeated repeated"]):
            self.assertAlmostEqual(sum(v * v for v in vector) ** 0.5, 1.0, places=12)

    def test_embedding_text_with_no_words_gives_a_zero_vector_not_a_crash(self) -> None:
        # The one case that is not unit length, by construction: there is no direction to keep.
        # It scores zero against everything, which is the right answer for empty text.
        self.assertEqual(set(StubEmbedder().embed(["", "   "])[0]), {0.0})

    def test_the_stub_embedder_is_stable_across_processes(self) -> None:
        # sha256, not Python's randomized hash(): a cached embedding must mean the same thing in
        # the next process, or a re-run silently re-ranks.
        code = (
            "import sys; sys.path.insert(0, r'%s');"
            "from examples.common.model import StubEmbedder;"
            "print(StubEmbedder().embed(['warranty period'])[0][:4])" % ROOT
        )
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), str(StubEmbedder().embed(["warranty period"])[0][:4]))


class TokenCountingTests(unittest.TestCase):
    def test_empty_text_costs_nothing(self) -> None:
        self.assertEqual(count_tokens(""), 0)

    def test_the_estimate_is_the_larger_of_words_and_characters_over_four(self) -> None:
        self.assertEqual(count_tokens("a b c d e f g h"), 8)  # 8 words beats 15/4
        self.assertEqual(count_tokens("x" * 400), 100)  # 100 quarter-characters beats 1 word

    def test_the_estimate_never_returns_zero_for_text_that_exists(self) -> None:
        # A budget built on this must never read a real prompt as free.
        for text in ("a", ".", "  x  "):
            with self.subTest(text=text):
                self.assertGreaterEqual(count_tokens(text), 1)

    def test_content_text_stands_a_placeholder_in_for_an_image_or_a_clip(self) -> None:
        content = [ImagePart(media_type="image/png", label="rating plate"), TextPart(text="what model?")]
        rendered = content_text(content)
        self.assertIn("[image image/png: rating plate]", rendered)
        self.assertIn("what model?", rendered)

    def test_content_text_of_a_plain_string_is_that_string(self) -> None:
        self.assertEqual(content_text("just words"), "just words")

    def test_content_payload_is_json_safe_for_a_cache_key(self) -> None:
        import json

        payload = content_payload([TextPart(text="hi"), AudioPart(media_type="audio/wav", label="clip")])
        json.dumps(payload)  # must not raise: this is what the response cache hashes
        self.assertEqual([p["part"] for p in payload], ["TextPart", "AudioPart"])


class ModelSpecTests(unittest.TestCase):
    def test_a_stub_spec_without_a_stub_instance_is_an_error_not_a_live_backend(self) -> None:
        with self.assertRaises(ValueError):
            build_model("stub")

    def test_an_unknown_spec_names_the_three_that_work(self) -> None:
        for spec in ("gpt-4", "ollama", "", "claude"):
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError) as caught:
                    build_model(spec)
                self.assertIn("stub", str(caught.exception))

    def test_building_a_live_backend_makes_no_network_call(self) -> None:
        # Constructing one must be import-safe; only `complete` may reach the network.
        model = build_model("ollama:some-tag")
        self.assertEqual(model.model_id, "ollama:some-tag")
        embedder = build_embedder("ollama:some-embed-tag")
        self.assertEqual(embedder.model_id, "ollama:some-embed-tag")

    def test_build_embedder_defaults_to_the_stub_and_rejects_a_claude_spec(self) -> None:
        self.assertIsInstance(build_embedder("stub"), StubEmbedder)
        with self.assertRaises(ValueError):
            build_embedder("claude:claude-sonnet-5")

    def test_a_stub_that_runs_out_of_responses_says_so_rather_than_repeating_one(self) -> None:
        model = StubModel([StubResponse(text="only one")])
        model.complete([Message(role="user", content="a")])
        with self.assertRaises(IndexError):
            model.complete([Message(role="user", content="b")])


class TracerTotalsTests(unittest.TestCase):
    def test_token_totals_add_up_across_steps(self) -> None:
        tracer = _tracer()
        tracer.record(kind="model", decided_by="code", title="one", tokens_in=100, tokens_out=10)
        tracer.record(kind="code", decided_by="code", title="two")
        tracer.record(kind="model", decided_by="model", title="three", tokens_in=50, tokens_out=5)
        self.assertEqual(tracer.tokens_in_total(), 150)
        self.assertEqual(tracer.tokens_out_total(), 15)
        self.assertEqual(tracer.model_decided_count(), 1)

    def test_an_empty_tracer_totals_zero_rather_than_raising(self) -> None:
        tracer = _tracer()
        self.assertEqual((tracer.tokens_in_total(), tracer.tokens_out_total(), tracer.model_decided_count()), (0, 0, 0))

    def test_steps_returns_a_copy_so_a_caller_cannot_edit_the_record(self) -> None:
        tracer = _tracer()
        tracer.record(kind="code", decided_by="code", title="one")
        tracer.steps().clear() if callable(tracer.steps) else tracer.steps.clear()
        self.assertEqual(len(tracer.steps), 1)

    def test_the_edge_style_follows_decided_by_unless_it_is_given(self) -> None:
        tracer = _tracer()
        self.assertEqual(tracer.record(kind="model", decided_by="model", title="a").edge, "dashed")
        self.assertEqual(tracer.record(kind="model", decided_by="code", title="b").edge, "solid")
        self.assertEqual(tracer.record(kind="code", decided_by="code", title="c", edge="dashed").edge, "dashed")

    def test_git_commit_returns_a_short_hash_here_and_none_outside_a_repo(self) -> None:
        import tempfile

        here = git_commit()
        self.assertTrue(here is None or (here.isalnum() and 6 <= len(here) <= 40), here)
        with tempfile.TemporaryDirectory() as tmp:
            # No repo, or git unavailable: a trace with no commit is still valid, never a crash.
            self.assertIsNone(git_commit(Path(tmp)))


class AgentLoopTests(unittest.TestCase):
    def test_record_completion_writes_the_caller_s_decided_by_not_a_default(self) -> None:
        for decided_by in ("code", "model"):
            with self.subTest(decided_by=decided_by):
                tracer = _tracer()
                completion = Completion(text="hello there", tool_calls=[], tokens_in=7, tokens_out=3, ms=1.5, model_id="m")
                record_completion(tracer, decided_by=decided_by, title="t", completion=completion)
                step = tracer.steps[0]
                self.assertEqual(step.kind, "model", "a model ran, whoever decided to run it")
                self.assertEqual(step.decided_by, decided_by)
                self.assertEqual((step.tokens_in, step.tokens_out, step.ms), (7, 3, 1.5))

    def test_record_completion_defaults_the_detail_to_the_reply_and_truncates_it(self) -> None:
        tracer = _tracer()
        long_reply = "x" * 500
        record_completion(tracer, decided_by="code", title="t", completion=Completion(long_reply, [], 0, 0, 0.0, "m"))
        record_completion(tracer, decided_by="code", title="t", completion=Completion(long_reply, [], 0, 0, 0.0, "m"), detail="given")
        self.assertEqual(len(tracer.steps[0].detail), 200)
        self.assertEqual(tracer.steps[1].detail, "given")

    def test_force_final_is_always_a_code_decision(self) -> None:
        # The cap is the code's. A trace that scored this as a model stop would credit the model
        # with a decision it never made.
        tracer = _tracer()
        model = StubModel([StubResponse(text="the final answer")])
        completion = force_final([Message(role="user", content="q")], model, tracer, reason="step cap reached: 5 steps")
        self.assertEqual(completion.text, "the final answer")
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertEqual(tracer.steps[0].title, FORCE_TITLE)
        self.assertEqual(tracer.steps[0].decided_by, "code")
        self.assertIn("step cap", tracer.steps[0].detail)

    def test_force_final_asks_for_an_answer_without_a_tool_and_keeps_the_history(self) -> None:
        seen: list[list[Message]] = []

        def responder(messages, tools):
            seen.append(list(messages))
            self.assertIsNone(tools, "the forced turn must not offer a tool to call")
            return StubResponse(text="done")

        force_final([Message(role="user", content="earlier")], StubModel(responder), _tracer(), reason="why")
        self.assertEqual(content_text(seen[0][-1].content), FINAL_TURN)
        self.assertEqual(content_text(seen[0][0].content), "earlier")


class InteractiveCliTests(unittest.TestCase):
    def test_parse_args_defaults_to_the_stub_and_requires_a_question(self) -> None:
        args = cli.parse_args(["--question", "how long is the warranty?"], description="d")
        self.assertEqual((args.model, args.question), ("stub", "how long is the warranty?"))
        with contextlib.redirect_stderr(io.StringIO()):  # argparse prints its own usage
            with self.assertRaises(SystemExit):
                cli.parse_args([], description="d")

    def test_the_interactive_stub_never_calls_a_tool_and_names_what_it_was_asked(self) -> None:
        model = cli.interactive_stub()
        completion = model.complete(
            [Message(role="system", content="s"), Message(role="user", content="what voltage?")],
            tools=[{"name": "search", "parameters": {"type": "object", "properties": {}}}],
        )
        self.assertEqual(completion.tool_calls, [], "the interactive stub must never call a tool")
        self.assertIn("what voltage?", completion.text)

    def test_the_interactive_stub_reads_multimodal_content_as_text_not_as_parts(self) -> None:
        # Slicing the content list directly would take the first 100 parts, not 100 characters.
        model = cli.interactive_stub()
        content = [ImagePart(media_type="image/png", label="plate"), TextPart(text="read this")]
        completion = model.complete([Message(role="user", content=content)])
        self.assertIn("read this", completion.text)


class CorpusTests(unittest.TestCase):
    def test_parse_sections_folds_the_preamble_into_section_one(self) -> None:
        # Documented in evals/corpus.py and relied on by the question set: a citation to section 1
        # also carries the document's title and revision line.
        text = "# A Manual\n\nRevision 2026-01-01. Covers the DW-300.\n\n## 1. First\n\nbody one\n\n## 2. Second\n\nbody two\n"
        sections = parse_sections("a-manual", text)
        self.assertEqual([s.cite for s in sections], ["a-manual#1", "a-manual#2"])
        self.assertIn("Revision 2026-01-01", sections[0].text)
        self.assertIn("body one", sections[0].text)
        self.assertNotIn("Revision 2026-01-01", sections[1].text)

    def test_a_document_with_no_numbered_section_yields_nothing_rather_than_raising(self) -> None:
        self.assertEqual(parse_sections("x", "# Just a title\n\nsome prose\n"), [])

    def test_section_titles_and_numbers_come_off_the_heading(self) -> None:
        sections = parse_sections("d", "## 3. Maintenance and Filter Cleaning\n\nbody\n")
        self.assertEqual((sections[0].number, sections[0].title, sections[0].cite), (3, "Maintenance and Filter Cleaning", "d#3"))

    def test_tokenize_lowercases_and_keeps_only_letters_and_digits(self) -> None:
        self.assertEqual(tokenize("DW-300's 3.2 gallons!"), ["dw", "300", "s", "3", "2", "gallons"])

    def test_normalize_whitespace_joins_a_phrase_wrapped_across_lines(self) -> None:
        self.assertEqual(normalize_whitespace("a phrase\nthat wrapped   here"), "a phrase that wrapped here")

    def test_bm25_scores_a_section_with_no_query_term_at_exactly_zero(self) -> None:
        # Every example that writes `if score > 0` reads this as "not relevant". If an unrelated
        # section could score above zero, those examples would quietly retrieve noise.
        sections = load_sections(DEFAULT_CORPUS_DIR)
        hits = bm25_search(sections, "zzzznotawordanywhere", k=len(sections))
        self.assertEqual({score for _, score in hits}, {0.0})

    def test_bm25_returns_k_results_ranked_high_to_low(self) -> None:
        sections = load_sections(DEFAULT_CORPUS_DIR)
        hits = bm25_search(sections, "warranty coverage", k=4)
        self.assertEqual(len(hits), 4)
        self.assertEqual([s for s in hits], sorted(hits, key=lambda pair: pair[1], reverse=True))
        self.assertGreater(hits[0][1], 0.0)

    def test_bm25_finds_the_section_that_actually_answers_a_question(self) -> None:
        sections = load_sections(DEFAULT_CORPUS_DIR)
        top = bm25_search(sections, "DR-520 maximum vent run", k=3)
        self.assertTrue(
            any("vent" in s.text.lower() for s, _ in top),
            f"nothing about venting in the top 3: {[s.cite for s, _ in top]}",
        )

    def test_an_empty_query_ranks_nothing_above_zero(self) -> None:
        sections = load_sections(DEFAULT_CORPUS_DIR)
        self.assertEqual({score for _, score in bm25_search(sections, "", k=3)}, {0.0})


if __name__ == "__main__":
    unittest.main()
