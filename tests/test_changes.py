"""Rules for content/changes.json: what changed on the site and why it matters to a reader.

scripts/validate.py belongs to another stream in this wave, so these live here as a standalone
check. They are the rules that keep the log a reader's log rather than a commit history: entries
written for whoever is reading, every one linking real pages, and nothing about how the site is
made or who makes it.

No network, no model.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGES = ROOT / "content" / "changes.json"
PAGES = ROOT / "site" / "src" / "pages"
TAXONOMY = ROOT / "content" / "taxonomy.json"

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _load() -> dict:
    return json.loads(CHANGES.read_text(encoding="utf-8"))


def _routes() -> set[str]:
    """Every site-relative path a changes entry may link: the fixed pages under src/pages, plus
    the generated level, technique, recipe and teardown paths."""
    routes = {"/"}
    for path in PAGES.rglob("*.astro"):
        rel = path.relative_to(PAGES).as_posix()
        if "[" in rel:
            continue
        rel = rel[: -len("/index.astro")] if rel.endswith("/index.astro") else rel[: -len(".astro")]
        routes.add("/" if rel == "index" else f"/{rel}/")
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    for tier in taxonomy["tiers"]:
        routes.add(f"/levels/{tier['order']}/")
        for page in tier["pages"]:
            routes.add(f"/techniques/{page['slug']}/")
    routes.add("/levels/tracks/")
    for track in taxonomy["tracks"]:
        routes.add(f"/techniques/{track['id']}/")
        for page in track.get("pages") or []:
            routes.add(f"/techniques/{page['slug']}/")
    for recipe in taxonomy["recipes"]:
        routes.add(f"/recipes/{recipe['slug']}/")
    for teardown in taxonomy["teardowns"]["first"]:
        routes.add(f"/teardowns/{teardown['slug']}/")
    for thread in taxonomy["threads"]:
        routes.add(f"/threads/{thread['id']}/")
    return routes


class FileShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()

    def test_it_round_trips_through_json_so_an_edit_is_a_clean_diff(self) -> None:
        raw = CHANGES.read_bytes()
        out = (json.dumps(json.loads(raw.decode("utf-8")), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.assertEqual(out, raw, "changes.json is written by json.dumps(indent=2); rewrite it that way")

    def test_the_file_carries_an_as_of_and_at_least_one_entry(self) -> None:
        self.assertRegex(self.data["as_of"], DATE)
        self.assertTrue(self.data["changes"])

    def test_every_id_is_a_unique_url_safe_anchor(self) -> None:
        """The id is the page anchor and the feed entry's id, so it has to be stable, unique and
        safe in a URL."""
        ids = [c["id"] for c in self.data["changes"]]
        self.assertEqual(len(set(ids)), len(ids))
        for cid in ids:
            self.assertRegex(cid, ID)

    def test_entries_are_newest_first(self) -> None:
        dates = [c["date"] for c in self.data["changes"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_no_entry_is_dated_in_the_future_or_before_the_site_was_public(self) -> None:
        today = dt.date.today()
        launch = dt.date(2026, 9, 18)
        for change in self.data["changes"]:
            self.assertRegex(change["date"], DATE, change["id"])
            when = dt.date.fromisoformat(change["date"])
            self.assertLessEqual(when, today, change["id"])
            self.assertGreaterEqual(when, launch, f"{change['id']} predates the first public release")


class EntryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()

    def test_every_entry_says_what_is_different_and_why_it_matters(self) -> None:
        for change in self.data["changes"]:
            self.assertTrue(change["title"], change["id"])
            self.assertLess(len(change["title"]), 95, f"{change['id']}: the title is a heading, not a sentence")
            for field in ("what", "why"):
                self.assertGreater(len(change[field]), 60, f"{change['id']}: {field} is too short to say anything")
                self.assertLess(len(change[field]), 760, f"{change['id']}: {field} is long enough to need cutting")

    def test_every_linked_page_is_a_real_route(self) -> None:
        routes = _routes()
        for change in self.data["changes"]:
            for page in change["pages"]:
                self.assertTrue(page["label"], change["id"])
                self.assertIn(page["path"], routes, f"{change['id']} links {page['path']}, which is not a page")

    def test_no_entry_links_the_same_page_twice(self) -> None:
        for change in self.data["changes"]:
            paths = [p["path"] for p in change["pages"]]
            self.assertEqual(len(set(paths)), len(paths), change["id"])


class HouseStyleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()

    def _prose(self):
        for change in self.data["changes"]:
            for field in ("title", "what", "why"):
                yield f"{change['id']}/{field}", change[field]

    def test_no_dash_asides(self) -> None:
        for where, text in self._prose():
            self.assertNotIn(" -- ", text, where)
            self.assertNotIn(" — ", text, where)
            self.assertNotIn("–", text, where)

    def test_an_entry_is_not_a_commit_message(self) -> None:
        """A reader does not care that a file was renamed or a test was added. If an entry cannot
        be written without those words, it is not a change a reader needed told about."""
        banned = ("commit", "merge", "refactor", "pull request", "branch", "pushed", "rebase", "lint")
        for where, text in self._prose():
            lowered = text.lower()
            for word in banned:
                self.assertNotIn(word, lowered, f"{where}: {word!r} is about the repository, not the site")

    def test_nothing_describes_how_the_site_is_made(self) -> None:
        """The site does not describe its own production, its owner, or the tooling behind it."""
        banned = (
            "agent wrote", "written by an agent", "subagent", "overseer", "wave 9", "wave 8",
            "claude", "opus", "sonnet", "my machine", "his machine", "the owner's",
        )
        for where, text in self._prose():
            lowered = text.lower()
            for phrase in banned:
                self.assertNotIn(phrase, lowered, f"{where}: {phrase!r} is about how the site is made")

    def test_no_entry_claims_a_measured_number(self) -> None:
        """Every page on this site is a draft with no recorded run behind it. A change entry is
        not the place that quietly stops being true."""
        banned = ("we measured", "measured result", "benchmark score", "scored result file")
        for where, text in self._prose():
            lowered = text.lower()
            for phrase in banned:
                self.assertNotIn(phrase, lowered, where)


if __name__ == "__main__":
    unittest.main()
