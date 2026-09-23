"""Every built page's feedback button opens the no-account form with that page already filled in.

Run against site/dist; skips cleanly until the site is built.
"""
from __future__ import annotations

import html
import re
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "site" / "dist"
SITE_TS = ROOT / "site" / "src" / "lib" / "site.ts"

FEEDBACK_LINK = re.compile(r'<a class="page-feedback-link" href="([^"]+)"')
CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)"')


def _const(name: str) -> str:
    m = re.search(rf"const {name} = '([^']+)'", SITE_TS.read_text(encoding="utf-8"))
    assert m, f"{name} not found in site.ts"
    return m.group(1)


class FeedbackLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        if not DIST.is_dir():
            self.skipTest(f"{DIST} does not exist; run `npm run build` in site/ first")
        self.form = _const("FEEDBACK_FORM_URL")
        self.entry = _const("FEEDBACK_FORM_PAGE_ENTRY")
        self.pages = [p for p in DIST.rglob("index.html") if "_navtest" not in p.parts]

    def test_every_page_prefills_its_own_address_in_the_form(self) -> None:
        checked = 0
        for page in self.pages:
            raw = page.read_text(encoding="utf-8")
            link, canonical = FEEDBACK_LINK.search(raw), CANONICAL.search(raw)
            if not link or not canonical:
                continue
            href = urlparse(html.unescape(link.group(1)))
            where = page.relative_to(DIST).as_posix()
            self.assertEqual(f"{href.scheme}://{href.netloc}{href.path}", self.form, f"{where}: feedback does not open the form")
            query = parse_qs(href.query)
            self.assertEqual(query.get(self.entry), [html.unescape(canonical.group(1))], f"{where}: the form's Page field is not this page")
            checked += 1
        self.assertGreater(checked, 50, "sanity: most built pages should carry the feedback strip")

    def test_the_public_issue_route_is_still_offered(self) -> None:
        raw = (DIST / "index.html").read_text(encoding="utf-8")
        self.assertIn("github.com/reedos/gradient_ascent/issues/new?template=feedback.yml", html.unescape(raw))


if __name__ == "__main__":
    unittest.main()
