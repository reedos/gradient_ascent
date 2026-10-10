"""Wherever the site lists the 0.05 cache-read exception, it names both models.

Anthropic's prompt-caching page reads: "Cache hits and refreshes on Claude Opus 5.5 and Claude
Sonnet 5.5 are priced at 0.05x the base input price." A page once listed only Opus 5.5. This
finds every paragraph of site or content text that says "0.05 for" next to cache pricing and
requires both model names in it, and requires that at least one such paragraph exists so the
guard cannot pass by finding nothing.

Usage: python -m unittest tests.test_cache_read_exceptions -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = [ROOT / "site" / "src", ROOT / "content"]
SUFFIXES = {".md", ".mdx", ".json", ".astro", ".ts", ".yaml", ".yml"}
EXCEPTION = re.compile(r"0\.05\s+for\b")
REQUIRED = ("Opus 5.5", "Sonnet 5.5")


def exception_paragraphs():
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in SUFFIXES or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for para in re.split(r"\n\s*\n", text):
                if "cache" in para.lower() and EXCEPTION.search(para):
                    yield path, para


class CacheReadExceptions(unittest.TestCase):
    def test_exception_list_is_found(self):
        self.assertTrue(list(exception_paragraphs()), "no 0.05 cache-read exception found")

    def test_exception_names_both_models(self):
        for path, para in exception_paragraphs():
            for name in REQUIRED:
                with self.subTest(file=str(path.relative_to(ROOT)), model=name):
                    self.assertIn(name, para)


if __name__ == "__main__":
    unittest.main()
