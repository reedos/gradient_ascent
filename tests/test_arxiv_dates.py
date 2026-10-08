"""Dates the site gives for arXiv papers must match the v1 submission dates read
from the arXiv abstract pages on 10/08/2026 (WebFetch). Offline check: if a date on
the site is edited, this fails until the paper's date is read again."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# arXiv id -> v1 submission date, as read from https://arxiv.org/abs/<id> on 10/08/2026.
V1 = {
    "1603.02754": "2016-03-09", "1706.03762": "2017-06-12", "2005.14165": "2020-05-28",
    "2201.11903": "2022-01-28", "2203.02155": "2022-03-04", "2303.08774": "2023-03-15",
    "2501.12948": "2025-01-22", "2005.11401": "2020-05-22", "2110.01691": "2021-10-04",
    "2205.00445": "2022-05-01", "2302.04761": "2023-02-09", "2210.03629": "2022-10-06",
    "2303.17760": "2023-03-31", "2305.14325": "2023-05-23", "2304.03442": "2023-04-07",
    "2106.09685": "2021-06-17", "2203.11171": "2022-03-21", "2308.00352": "2023-08-01",
    "2606.07937": "2026-06-06", "2310.03714": "2023-10-05", "2509.04664": "2025-09-04",
    "2306.05685": "2023-06-09", "2410.24164": "2024-10-31",
}


class ArxivDates(unittest.TestCase):
    def test_id_month_matches_date(self):
        for aid, d in V1.items():
            self.assertEqual(aid[:2] + aid[2:4], d[2:4] + d[5:7], aid)

    def test_timeline_milestones(self):
        t = json.loads((ROOT / "content" / "timeline.json").read_text(encoding="utf-8"))
        seen = 0
        for m in t["milestones"]:
            u = (m.get("source") or {}).get("url", "")
            mt = re.match(r"https://arxiv\.org/abs/(\d{4}\.\d{5})$", u)
            if mt and mt.group(1) in V1:
                seen += 1
                self.assertEqual(m["date"], V1[mt.group(1)], m["id"])
        self.assertGreaterEqual(seen, 14)

    def test_technique_sources(self):
        seen = 0
        for f in (ROOT / "site" / "src" / "content" / "techniques").glob("*.mdx"):
            text = f.read_text(encoding="utf-8")
            for aid, d in re.findall(
                r'url: "https://arxiv\.org/abs/(\d{4}\.\d{5})"\s+publisher: [^\n]*\n\s+date: "([\d-]+)"', text
            ):
                if aid in V1:
                    seen += 1
                    self.assertEqual(d, V1[aid], f"{f.name} {aid}")
        self.assertGreaterEqual(seen, 8)


if __name__ == "__main__":
    unittest.main()
