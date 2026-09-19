"""The bench corpus loads exactly the way the appliance corpus does.

`evals/corpus.py` takes a directory, so the second corpus needed no change to the loader and no
change to the behavior any existing caller sees. These tests pin both halves of that: the bench
documents parse into numbered sections and citations work, and `load_sections()` called with no
argument still returns the Halvorsen corpus and nothing else.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.bench import (  # noqa: E402
    BENCH_CORPUS_DIR,
    BENCH_DATA_DIR,
    load_bench_documents,
    load_bench_sections,
)
from evals.corpus import (  # noqa: E402
    DEFAULT_CORPUS_DIR,
    bm25_search,
    corpus_files,
    load_sections,
    normalize_whitespace,
    parse_sections,
)

#: Every document the bench corpus is meant to have. A file added or renamed without this list
#: being updated is a file no page knows about.
EXPECTED_DOCUMENTS = {
    "bringup-notebook",
    "calibration-procedure",
    "characterization-notebook",
    "design-review-rules",
    "ecn-2608-04",
    "failure-analysis-guide",
    "mdn4010-programming-manual",
    "mdn6100-programming-manual",
    "srb5030-bom",
    "srb5030-datasheet",
    "srb5030-test-spec",
    "trn1102-programming-manual",
    "trn2400-programming-manual",
}


class TestBenchCorpusLoads(unittest.TestCase):
    def setUp(self) -> None:
        self.sections = load_bench_sections()

    def test_the_expected_documents_are_all_there(self) -> None:
        stems = {path.stem for path in corpus_files(BENCH_CORPUS_DIR)}
        self.assertEqual(stems, EXPECTED_DOCUMENTS)

    def test_section_count_is_in_the_range_the_corpus_was_designed_for(self) -> None:
        """The band, not the count: a document may gain a section without a test edit.

        It was 60 to 80 for the twelve documents wave 7 wrote, and the corpus sat at 78. Wave 8
        added the characterization notebook and two sections to the MDN-6100's manual, which
        takes it to 86, so the upper bound moves with it. The band exists to catch a corpus
        growing without anybody deciding to grow it, and a bound the corpus has already reached
        catches nothing.
        """
        self.assertGreaterEqual(len(self.sections), 60)
        self.assertLessEqual(len(self.sections), 95)

    def test_every_document_contributes_sections(self) -> None:
        by_doc: dict[str, list[int]] = {}
        for section in self.sections.values():
            by_doc.setdefault(section.doc, []).append(section.number)
        self.assertEqual(set(by_doc), EXPECTED_DOCUMENTS)
        for doc, numbers in by_doc.items():
            self.assertGreaterEqual(len(numbers), 4, doc)

    def test_section_numbers_run_from_one_with_no_gaps(self) -> None:
        by_doc: dict[str, list[int]] = {}
        for section in self.sections.values():
            by_doc.setdefault(section.doc, []).append(section.number)
        for doc, numbers in by_doc.items():
            self.assertEqual(sorted(numbers), list(range(1, len(numbers) + 1)), doc)

    def test_every_section_has_a_title_and_a_body(self) -> None:
        for cite, section in self.sections.items():
            self.assertTrue(section.title.strip(), cite)
            self.assertTrue(section.text.strip(), cite)

    def test_the_citation_format_is_file_hash_number(self) -> None:
        for cite, section in self.sections.items():
            self.assertEqual(cite, f"{section.doc}#{section.number}")
            doc, _, number = cite.partition("#")
            self.assertIn(doc, EXPECTED_DOCUMENTS)
            self.assertTrue(number.isdigit(), cite)

    def test_a_citation_resolves_to_the_text_it_names(self) -> None:
        text = normalize_whitespace(self.sections["ecn-2608-04#1"].text)
        self.assertIn("32.0 V", text)
        self.assertIn("revision A and revision B", text)

    def test_the_preamble_folds_into_section_one(self) -> None:
        """Same rule as the appliance corpus: a citation to section 1 carries the revision line."""
        for doc in sorted(EXPECTED_DOCUMENTS):
            first = normalize_whitespace(self.sections[f"{doc}#1"].text)
            self.assertTrue(first.startswith("# "), doc)
            self.assertRegex(first, r"[Rr]evision|[Ii]ssued|[Ee]ntries from", doc)
        datasheet = normalize_whitespace(self.sections["srb5030-datasheet#1"].text)
        self.assertIn("Datasheet revision B, 06/18/2026", datasheet)
        manual = normalize_whitespace(self.sections["trn2400-programming-manual#1"].text)
        self.assertIn("Firmware 3.02, manual revision B, 07/08/2026", manual)

    def test_documents_load_whole(self) -> None:
        documents = load_bench_documents()
        self.assertEqual(set(documents), EXPECTED_DOCUMENTS)
        for stem, text in documents.items():
            self.assertTrue(text.startswith("# "), stem)

    def test_parse_sections_agrees_with_load_sections(self) -> None:
        raw = (BENCH_CORPUS_DIR / "srb5030-test-spec.md").read_text(encoding="utf-8")
        parsed = parse_sections("srb5030-test-spec", raw)
        self.assertEqual(len(parsed), 8)
        self.assertEqual(parsed[3].title, "Test Steps and Limits")

    def test_search_finds_the_right_section(self) -> None:
        """Level 0 retrieval has to work on this corpus too, or no example above it can."""
        cases = {
            "what is the maximum input voltage": "ecn-2608-04",
            "ceramic capacitor derating rule": "design-review-rules",
            "the load rejects INP ON": "trn2400-programming-manual",
            "what is the meter's accuracy on the 10 V range": "mdn6100-programming-manual",
            "five boards swept over line load and temperature": "characterization-notebook",
        }
        for query, expected_doc in cases.items():
            hits = bm25_search(self.sections, query, k=3)
            self.assertIn(expected_doc, [section.doc for section, _ in hits], query)

    def test_the_ripple_query_needs_five_hits_and_not_three(self) -> None:
        """One query this corpus does not separate cleanly, recorded rather than tuned away.

        "how do I measure output ripple with the scope" wants
        `trn1102-programming-manual#5`, which is exactly the passage that answers it. On the
        twelve-document corpus it ranked third of 78 sections by 0.03 of a point over
        `mdn6100-programming-manual#4`, a section about configuring the meter that shares
        "measure", "output" and "read" with the query and has nothing to do with ripple. Adding
        the characterization notebook changed the corpus statistics BM25 normalizes against and
        the two swapped places: fourth now, by 0.04.

        The claim this file makes is that level 0 retrieval works on this corpus, and it does:
        the right passage is in the first five of 87. The claim it does not make is that a bag of
        words tells four sections apart when three of them share the query's common words and
        only one has its rare one. Widening k for this query says so out loud. Narrowing the
        query until it passed at k=3 would not.
        """
        hits = bm25_search(self.sections, "how do I measure output ripple with the scope", k=5)
        self.assertIn("trn1102-programming-manual", [section.doc for section, _ in hits])

    def test_a_section_with_no_query_term_scores_zero(self) -> None:
        hits = bm25_search(self.sections, "zzzzqqqq", k=3)
        self.assertTrue(all(score == 0.0 for _, score in hits))


class TestTheAppliancCorpusIsUnchanged(unittest.TestCase):
    """The bench must not have moved anything the existing 800 tests stand on."""

    def test_load_sections_still_defaults_to_the_appliance_corpus(self) -> None:
        sections = load_sections()
        docs = {section.doc for section in sections.values()}
        self.assertIn("dw300-manual", docs)
        self.assertNotIn("srb5030-datasheet", docs)

    def test_the_two_corpora_are_separate_directories(self) -> None:
        self.assertNotEqual(BENCH_CORPUS_DIR, DEFAULT_CORPUS_DIR)
        self.assertFalse(BENCH_CORPUS_DIR.is_relative_to(DEFAULT_CORPUS_DIR))
        self.assertTrue(BENCH_DATA_DIR.is_dir())

    def test_no_bench_document_leaks_into_the_appliance_corpus(self) -> None:
        stems = {path.stem for path in corpus_files(DEFAULT_CORPUS_DIR)}
        self.assertEqual(stems & EXPECTED_DOCUMENTS, set())


class TestCorpusIsInternallyConsistent(unittest.TestCase):
    """The documents cite each other and quote each other's numbers. Those have to match."""

    def setUp(self) -> None:
        self.documents = load_bench_documents()

    def test_every_cross_reference_names_a_real_document(self) -> None:
        import re

        pattern = re.compile(r"`([a-z0-9-]+\.md)`")
        for stem, text in self.documents.items():
            for name in set(pattern.findall(text)):
                self.assertIn(name.removesuffix(".md"), EXPECTED_DOCUMENTS, f"{stem} -> {name}")

    def test_the_ecn_and_the_datasheet_disagree_on_exactly_one_number(self) -> None:
        datasheet = normalize_whitespace(self.documents["srb5030-datasheet"])
        ecn = normalize_whitespace(self.documents["ecn-2608-04"])
        self.assertIn("| Input voltage, VIN | 9.0 | 24.0 | 36.0 | V |", datasheet)
        self.assertIn("maximum continuous input voltage of the SRB-5030 is **32.0 V**", ecn)
        # And the datasheet points at the ECN rather than pretending to agree with it.
        self.assertIn("superseded for revision A and revision B boards", datasheet)

    def test_the_test_spec_limits_match_the_generator(self) -> None:
        from evals.bench.make_data import STEPS

        spec = normalize_whitespace(self.documents["srb5030-test-spec"])
        for step, name, unit, low, high, places in STEPS:
            row = f"| {step} | {name} |"
            self.assertIn(row, spec, name)
            for limit in (low, high):
                if limit is not None:
                    self.assertIn(f"{limit:.{places}f}".rstrip("0").rstrip("."), spec, name)

    def test_the_derating_rule_and_the_ecn_agree(self) -> None:
        rules = normalize_whitespace(self.documents["design-review-rules"])
        ecn = normalize_whitespace(self.documents["ecn-2608-04"])
        self.assertIn("at least 1.5 times the maximum steady-state rail voltage", rules)
        self.assertIn("50 V / 1.5 = 33.3 V", ecn)
        # 50 / 1.5 is 33.33, so a 32 V ceiling clears the rule and 36 V does not.
        self.assertLessEqual(32.0, 50.0 / 1.5)
        self.assertGreater(36.0, 50.0 / 1.5)


if __name__ == "__main__":
    unittest.main()
