"""Tests for scripts/check_sources.py, the source-rot checker.

No network: every test drives the pure parts. The states these pin are the ones the first
version of the script got wrong, each of which made it report a live source as dead or a
current page as drifted.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_sources", ROOT / "scripts" / "check_sources.py")
check_sources = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(check_sources)


class CitedTitleTests(unittest.TestCase):
    def test_a_note_about_how_the_page_was_read_is_not_part_of_its_title(self) -> None:
        cited = "Learning to Reason with LLMs (read through the Internet Archive's capture of September 13, 2024)"
        self.assertEqual(check_sources._cited_title(cited), "Learning to Reason with LLMs")

    def test_an_ordinary_parenthetical_is_left_alone(self) -> None:
        self.assertEqual(check_sources._cited_title("Attention Is All You Need (v1)"), "Attention Is All You Need (v1)")


class ResemblesTests(unittest.TestCase):
    def test_a_site_appending_its_own_name_is_not_drift(self) -> None:
        self.assertTrue(check_sources._resembles("Learning to Reason with LLMs", "Learning to Reason with LLMs | OpenAI"))

    def test_an_archived_capture_matches_the_original_pages_title(self) -> None:
        cited = "Introducing Operator (read through the Internet Archive's capture of January 23, 2025)"
        self.assertTrue(check_sources._resembles(cited, "Introducing Operator research preview | OpenAI"))

    def test_a_page_that_no_longer_names_the_subject_is_drift(self) -> None:
        self.assertFalse(check_sources._resembles("Codex", "ChatGPT | ChatGPT Learn"))

    def test_an_empty_title_on_either_side_is_never_called_drift(self) -> None:
        self.assertTrue(check_sources._resembles("", "Anything"))
        self.assertTrue(check_sources._resembles("Anything", ""))


class TitleOfTests(unittest.TestCase):
    def test_it_reads_the_title_element_and_unescapes_it(self) -> None:
        self.assertEqual(check_sources._title_of("<html><title>Tools &amp; Agents</title>"), "Tools & Agents")

    def test_it_falls_back_to_the_open_graph_title(self) -> None:
        html = '<html><head><meta property="og:title" content="A Page"></head>'
        self.assertEqual(check_sources._title_of(html), "A Page")

    def test_no_title_is_an_empty_string_rather_than_a_crash(self) -> None:
        self.assertEqual(check_sources._title_of("<html><body>hi</body></html>"), "")


class BlockSignTests(unittest.TestCase):
    def test_the_block_phrases_are_matched_lowercase(self) -> None:
        for sign in check_sources._BLOCK_SIGNS:
            self.assertEqual(sign, sign.lower())


class SourceCollectionTests(unittest.TestCase):
    def test_the_real_content_files_yield_sources_with_a_place_to_look(self) -> None:
        sources = check_sources._json_sources() + check_sources._mdx_sources()
        self.assertGreater(len(sources), 200)
        for source in sources:
            self.assertTrue(source.url.startswith("http"), source)
            self.assertTrue(source.where, source)

    def test_a_citation_that_records_an_archive_carries_it(self) -> None:
        """A dead original with an archived copy recorded is handled, not a defect, and the
        checker can only know that if the archive_url travels with the source."""
        with_archive = [s for s in check_sources._json_sources() if s.archive]
        self.assertTrue(with_archive, "the timeline records archive_url on several milestones")


if __name__ == "__main__":
    unittest.main()
