"""The stub embedder has to be good enough that the examples retrieve the right section.

This is a guard, not a benchmark. `StubEmbedder` is a hashing bag of words and knows nothing
about meaning, so it will never score well on the harder questions. What it must not do is what
it did before September 19, 2026: rank a section about a different appliance above the one the
question names, which made the first command in the README answer the wrong question. The
thresholds below sit under what it scores today, so an accidental regression fails and an
improvement does not.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, load_sections
from examples.common.model import StubEmbedder

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = json.loads((ROOT / "evals" / "questions.json").read_text(encoding="utf-8"))["questions"]


def _recall_at_k(k: int = 4) -> tuple[int, int]:
    sections = list(load_sections(DEFAULT_CORPUS_DIR).values())
    embedder = StubEmbedder()
    chunk_vectors = embedder.embed([f"{s.title}\n{s.text}" for s in sections])
    hit = total = 0
    for question in QUESTIONS:
        wanted = question.get("must_cite") or []
        if not wanted:
            continue
        total += 1
        query = embedder.embed([question["question"]])[0]
        ranked = sorted(
            zip(sections, chunk_vectors),
            key=lambda pair: sum(a * b for a, b in zip(query, pair[1])),
            reverse=True,
        )
        top = {section.cite for section, _ in ranked[:k]}
        if all(cite in top for cite in wanted):
            hit += 1
    return hit, total


class RetrievalQualityTests(unittest.TestCase):
    def test_the_readme_question_retrieves_the_section_that_answers_it(self) -> None:
        """The first command a newcomer runs, from README.md and examples/rag/README.md."""
        sections = list(load_sections(DEFAULT_CORPUS_DIR).values())
        embedder = StubEmbedder()
        chunk_vectors = embedder.embed([f"{s.title}\n{s.text}" for s in sections])
        query = embedder.embed(["What is the DW-300's Normal cycle water use?"])[0]
        ranked = sorted(
            zip(sections, chunk_vectors),
            key=lambda pair: sum(a * b for a, b in zip(query, pair[1])),
            reverse=True,
        )
        self.assertEqual(ranked[0][0].cite, "dw300-manual#3", "the DW-300 cycles section must rank first")

    def test_recall_at_4_stays_well_above_chance(self) -> None:
        hit, total = _recall_at_k(4)
        self.assertGreaterEqual(hit / total, 0.40, f"recall@4 fell to {hit}/{total}")

    def test_a_question_never_ranks_another_appliance_first(self) -> None:
        """Every lookup question names one appliance; the top section must belong to it."""
        sections = list(load_sections(DEFAULT_CORPUS_DIR).values())
        embedder = StubEmbedder()
        chunk_vectors = embedder.embed([f"{s.title}\n{s.text}" for s in sections])
        wrong = []
        for question in QUESTIONS:
            if question["kind"] != "lookup":
                continue
            models = [m for m in ("DW-300", "DW-480", "DR-210", "DR-520") if m in question["question"]]
            if len(models) != 1:
                continue
            prefix = models[0].replace("-", "").lower()
            query = embedder.embed([question["question"]])[0]
            ranked = sorted(
                zip(sections, chunk_vectors),
                key=lambda pair: sum(a * b for a, b in zip(query, pair[1])),
                reverse=True,
            )
            top = ranked[0][0].cite
            # A shared document (specs, warranty, troubleshooting) is a fair first hit; another
            # appliance's own manual is not.
            if "-manual#" in top and not top.startswith(prefix):
                wrong.append((question["id"], models[0], top))
        self.assertEqual(wrong, [], f"a question about one appliance ranked another's manual first: {wrong}")


if __name__ == "__main__":
    unittest.main()
