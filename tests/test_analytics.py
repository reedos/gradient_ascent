"""Every built page carries the Cloudflare Web Analytics beacon exactly once in its head, and
GoatCounter's existing origin-gated pageview script is untouched.

Run against site/dist; skips cleanly until the site is built. Cloudflare Web Analytics was
approved 2026-10-01; its token is public by design (it only identifies the site, not a secret).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "site" / "dist"

CF_BEACON = (
    '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
    'data-cf-beacon=\'{"token": "7d357826b1264eb38e3db3ba16dd8319"}\'></script>'
)


class CloudflareAnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        if not DIST.is_dir():
            self.skipTest(f"{DIST} does not exist; run `npm run build` in site/ first")
        self.pages = [p for p in DIST.rglob("index.html") if "_navtest" not in p.parts]

    def test_every_page_loads_the_beacon_exactly_once(self) -> None:
        checked = 0
        for page in self.pages:
            raw = page.read_text(encoding="utf-8")
            where = page.relative_to(DIST).as_posix()
            if "</head>" not in raw:
                # A handful of generated stubs (e.g. /learn/ -> /examples/) are bare
                # meta-refresh redirects with no <head> and never go through Base.astro.
                continue
            self.assertEqual(raw.count(CF_BEACON), 1, f"{where}: Cloudflare beacon missing or duplicated")
            checked += 1
        self.assertGreater(checked, 50, "sanity: most built pages should carry the beacon")

    def test_the_beacon_is_in_the_head_not_the_body(self) -> None:
        raw = (DIST / "index.html").read_text(encoding="utf-8")
        head, _, body = raw.partition("</head>")
        self.assertIn(CF_BEACON, head)
        self.assertNotIn(CF_BEACON, body)

    def test_goatcounter_gate_is_unchanged(self) -> None:
        raw = (DIST / "index.html").read_text(encoding="utf-8")
        self.assertIn("location.origin === 'https://reedos.dev'", raw)
        self.assertIn("gc.zgo.at/count.js", raw)


if __name__ == "__main__":
    unittest.main()
