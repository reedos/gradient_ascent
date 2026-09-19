"""Tests for examples/rag's own command-line entry point: the sequence
`python -m examples.rag --model stub:scripted` plays, and the guard that keeps it in step with
this test. The example's general behavior (chunking, retrieval, citation parsing) is covered by
`tests/test_examples.py::ExampleTraceTests.test_rag_is_all_code_and_parses_citations` and by
`DecidedByDefinitionTests`; this file is only about the CLI's own scripted sequence."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.corpus import DEFAULT_CORPUS_DIR, load_sections  # noqa: E402
from examples.common.model import StubEmbedder, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.rag.__main__ import SCRIPTED  # noqa: E402
from examples.rag.run import LEVEL, run  # noqa: E402

QUESTION = "What is the DW-300's Normal cycle water use?"
SEQUENCE = ["3.2 gallons per Normal cycle. Sources: dw300-manual#3"]


class ScriptedCommandTests(unittest.TestCase):
    """The sequence `python -m examples.rag --model stub:scripted` plays, run the same way the
    CLI runs it, plus the guard that keeps the two in step."""

    def test_the_scripted_sequence_answers_with_a_real_citation(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="rag", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, StubEmbedder(), tracer, corpus_dir=DEFAULT_CORPUS_DIR)
        self.assertIn("3.2 gallons", answer.text)
        self.assertEqual(answer.citations, ["dw300-manual#3"])

    def test_the_section_the_scripted_answer_cites_really_carries_the_number(self) -> None:
        # A scripted citation that the corpus does not support would demonstrate the opposite of
        # the page's claim while looking right on the page.
        self.assertIn("3.2 gallons", load_sections(DEFAULT_CORPUS_DIR)["dw300-manual#3"].text)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)


if __name__ == "__main__":
    unittest.main()
