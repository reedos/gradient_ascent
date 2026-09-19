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


def _source(url: str = "https://example.com/p", title: str = "A Page", archive: str = "") -> object:
    return check_sources.Source(url=url, title=title, where="test", archive=archive)


class ClassifyTests(unittest.TestCase):
    """The state rules, with the fetch handed in. Each of these was a wrong answer the checker
    gave on a real source before the rule existed."""

    def _state(self, source, final=None, body="", error="") -> str:
        return check_sources._classify(source, final or source.url, body, error)["state"]

    def test_the_page_we_named_is_ok(self) -> None:
        self.assertEqual(self._state(_source(), body="<title>A Page</title>"), "ok")

    def test_a_different_final_url_is_moved(self) -> None:
        result = check_sources._classify(_source(), "https://example.com/moved", "<title>A Page</title>", "")
        self.assertEqual(result["state"], "moved")
        self.assertEqual(result["final"], "https://example.com/moved")

    def test_a_dead_url_with_no_capture_is_gone_and_with_one_is_archived(self) -> None:
        self.assertEqual(self._state(_source(), error="URLError"), "gone")
        self.assertEqual(self._state(_source(archive="https://web.archive.org/x"), error="URLError"), "archived")

    def test_pypis_challenge_page_is_a_refusal_not_drift(self) -> None:
        """PyPI answers a burst of requests with a 228-byte page titled "Client Challenge".
        Read as a title that is drift, and it was reported as drift on two release histories."""
        body = "<html><title>Client Challenge</title><body>...</body></html>"
        self.assertEqual(self._state(_source(title="langchain release history"), body=body), "blocked")

    def test_drift_on_a_citation_that_records_a_capture_is_archived(self) -> None:
        """Neeva's post: neeva.com serves a redirect stub now, and the citation already records
        the capture of the publication day, which is the copy the milestone quotes."""
        body = "<html><title>Redirecting...</title></html>"
        self.assertEqual(self._state(_source(title="Introducing NeevaAI"), body=body), "drifted")
        with_capture = _source(title="Introducing NeevaAI", archive="https://web.archive.org/web/2023id_/x")
        self.assertEqual(self._state(with_capture, body=body), "archived")

    def test_a_refusal_code_is_blocked_and_a_declined_redirect_is_moved(self) -> None:
        self.assertEqual(self._state(_source(), error="refused: HTTP 403"), "blocked")
        self.assertEqual(self._state(_source(), final="https://example.com/q", error="redirect: HTTP 307"), "moved")


class SourceCollectionTests(unittest.TestCase):
    def test_the_real_content_files_yield_sources_with_a_place_to_look(self) -> None:
        sources = check_sources._json_sources() + check_sources._mdx_sources()
        self.assertGreater(len(sources), 200)
        for source in sources:
            self.assertTrue(source.url.startswith("http"), source)
            self.assertTrue(source.where, source)

    def test_the_frontier_blocks_sources_are_checked_too(self) -> None:
        """Every source under content/frontier.json is quoted on a live level page, so it has to
        be in the set this script watches."""
        places = {s.where for s in check_sources._json_sources()}
        self.assertTrue(any(p.startswith("frontier.json ") for p in places), sorted(places)[:5])

    def test_a_citation_that_records_an_archive_carries_it(self) -> None:
        """A dead original with an archived copy recorded is handled, not a defect, and the
        checker can only know that if the archive_url travels with the source."""
        with_archive = [s for s in check_sources._json_sources() if s.archive]
        self.assertTrue(with_archive, "the timeline records archive_url on several milestones")


if __name__ == "__main__":
    unittest.main()
