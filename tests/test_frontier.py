"""Rules for content/frontier.json: what is unsolved at each level.

scripts/validate.py belongs to another stream in this wave, so these rules live here as a
standalone check rather than as validator rules. They are the ones that would let a bad entry
onto a level page: an unsourced claim, a quotation with no date, a link to a technique page that
does not exist, or a prediction about who will win, which this block is not for.

No network. Nothing here re-fetches a source; that is scripts/check_sources.py's job, and it
reads frontier.json's URLs once they are registered there.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTIER = ROOT / "content" / "frontier.json"
TAXONOMY = ROOT / "content" / "taxonomy.json"

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load() -> dict:
    return json.loads(FRONTIER.read_text(encoding="utf-8"))


def _slugs() -> set[str]:
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    out = {p["slug"] for tier in taxonomy["tiers"] for p in tier["pages"]}
    for track in taxonomy["tracks"]:
        out.add(track["id"])
        out.update(p["slug"] for p in track.get("pages") or [])
    return out


def _entries(data: dict):
    for level in data["levels"]:
        for entry in level["open"]:
            yield level, entry


class FileShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()

    def test_it_round_trips_through_json_so_an_edit_is_a_clean_diff(self) -> None:
        raw = FRONTIER.read_bytes()
        out = (json.dumps(json.loads(raw.decode("utf-8")), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.assertEqual(out, raw, "frontier.json is written by json.dumps(indent=2); rewrite it that way")

    def test_the_file_and_every_level_carry_an_as_of(self) -> None:
        self.assertRegex(self.data["as_of"], DATE)
        for level in self.data["levels"]:
            self.assertRegex(level["as_of"], DATE, f"level {level['order']}")

    def test_every_level_of_the_ladder_has_a_block(self) -> None:
        """The plan puts a frontier block on every tier. A level with none is a hole a reader
        sees, so it is a failure here rather than a silently missing section."""
        orders = sorted(level["order"] for level in self.data["levels"])
        self.assertEqual(orders, list(range(8)))

    def test_each_level_has_between_two_and_four_open_problems(self) -> None:
        for level in self.data["levels"]:
            self.assertGreaterEqual(len(level["open"]), 2, f"level {level['order']}")
            self.assertLessEqual(len(level["open"]), 4, f"level {level['order']}")

    def test_every_id_is_unique_across_the_file(self) -> None:
        ids = [entry["id"] for _, entry in _entries(self.data)]
        self.assertEqual(len(set(ids)), len(ids))


class EntryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()

    def test_every_entry_says_what_is_unsolved_and_what_is_being_tried(self) -> None:
        for level, entry in _entries(self.data):
            where = f"level {level['order']} / {entry['id']}"
            for field in ("problem", "trying"):
                self.assertGreater(len(entry[field]), 60, f"{where}: {field} is too short to say anything")
                self.assertLess(len(entry[field]), 520, f"{where}: {field} is long enough to need cutting")

    def test_every_entry_rests_on_at_least_one_dated_primary_source(self) -> None:
        for level, entry in _entries(self.data):
            where = f"level {level['order']} / {entry['id']}"
            self.assertTrue(entry["sources"], f"{where} has no source")
            self.assertLessEqual(len(entry["sources"]), 2, f"{where} cites more than two sources")
            for source in entry["sources"]:
                for field in ("title", "url", "publisher", "quote"):
                    self.assertTrue(source.get(field), f"{where}: source is missing {field}")
                self.assertRegex(source["checked"], DATE, where)
                self.assertTrue(source["url"].startswith("https://"), f"{where}: {source['url']}")
                self.assertGreater(len(source["quote"]), 25, f"{where}: the quotation is too short to support anything")

    def test_a_named_technique_resolves_to_a_real_page(self) -> None:
        slugs = _slugs()
        for level, entry in _entries(self.data):
            slug = entry.get("technique")
            if slug is not None:
                self.assertIn(slug, slugs, f"level {level['order']} / {entry['id']}")

    def test_no_source_is_checked_in_the_future(self) -> None:
        today = dt.date.today()
        for level, entry in _entries(self.data):
            for source in entry["sources"]:
                checked = dt.date.fromisoformat(source["checked"])
                self.assertLessEqual(checked, today, f"level {level['order']} / {entry['id']}")


class HouseStyleTests(unittest.TestCase):
    """The prose rules the site keeps everywhere. Quotations are exempt from the wording rules:
    a source's own words are never respelled."""

    def setUp(self) -> None:
        self.data = _load()

    def _prose(self):
        for level, entry in _entries(self.data):
            for field in ("problem", "trying"):
                yield f"level {level['order']} / {entry['id']} / {field}", entry[field]

    def test_no_dash_asides(self) -> None:
        for where, text in self._prose():
            self.assertNotIn(" -- ", text, where)
            self.assertNotIn(" — ", text, where)
            self.assertNotIn("–", text, where)

    def test_no_prediction_about_who_wins(self) -> None:
        """The block says what is unsolved and what is being tried. The moment it says which
        approach will win, it stops being a record and starts being a guess."""
        banned = (
            "will win", "is likely to", "will likely", "we expect", "expect to see",
            "the winner", "poised to", "set to become", "in the next few years",
            "by 2027", "by 2028", "inevitably", "bound to happen", "bound to become",
        )
        # "bound to" on its own was here and matched "a credential be bound to the agent that
        # originated the request", which is what a specification asks for and not a forecast.
        for where, text in self._prose():
            lowered = text.lower()
            for phrase in banned:
                self.assertNotIn(phrase, lowered, f"{where}: {phrase!r} reads as a prediction")

    def test_nothing_claims_this_site_measured_it(self) -> None:
        for where, text in self._prose():
            lowered = text.lower()
            for phrase in ("we measured", "our measurement", "this site measured", "we found that"):
                self.assertNotIn(phrase, lowered, where)


if __name__ == "__main__":
    unittest.main()
