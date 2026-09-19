"""Refresh content/capability.json from Epoch AI's published Epoch Capabilities Index.

    python scripts/import_eci.py            # downloads, writes the snapshot
    python scripts/import_eci.py --zip path/to/benchmark_data.zip

The site draws one chart from this file (the timeline page): every scored model by release date,
and the frontier line. This site computes nothing about the scores themselves. The index, the
scores and the confidence intervals are Epoch AI's, reused under CC BY 4.0 with credit, and the
snapshot records when it was taken. This is the only script in the repository that touches the
network, and it calls no model.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import urllib.request
import zipfile
from pathlib import Path

DATA_URL = "https://epoch.ai/data/benchmark_data.zip"
MEMBER = "epoch_capabilities_index/eci_scores.csv"
OUT = Path(__file__).resolve().parent.parent / "content" / "capability.json"


def read_rows(blob: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        text = z.read(MEMBER).decode("utf-8")
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        if not r.get("date") or not r.get("eci"):
            continue
        rows.append({
            "name": (r.get("Display name") or r["Model"]).strip(),
            "org": (r.get("Organization") or "").strip() or None,
            "date": r["date"].strip(),
            "eci": round(float(r["eci"]), 2),
            "lo": round(float(r["eci_ci_low"]), 2) if r.get("eci_ci_low") else None,
            "hi": round(float(r["eci_ci_high"]), 2) if r.get("eci_ci_high") else None,
            "open": (r.get("Accessibility group") or "").strip() == "Open weights",
        })
    rows.sort(key=lambda p: (p["date"], p["name"]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--zip", help="use a downloaded benchmark_data.zip instead of fetching it")
    parser.add_argument("--retrieved", help="ISO date to record (default: today)")
    args = parser.parse_args()

    if args.zip:
        blob = Path(args.zip).read_bytes()
    else:
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "gradient-ascent-import/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - fixed https URL
            blob = resp.read()

    points = read_rows(blob)
    snapshot = {
        "version": 1,
        "retrieved": args.retrieved or dt.date.today().isoformat(),
        "source": {
            "title": "Epoch Capabilities Index",
            "publisher": "Epoch AI",
            "url": "https://epoch.ai/eci",
            "data_url": DATA_URL,
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "citation": "Epoch AI, 'Epoch Capabilities Index'. Published online at epoch.ai. Retrieved from 'https://epoch.ai/eci' [online resource].",
        },
        "what_it_is": "The Epoch Capabilities Index (ECI) combines scores from many different AI benchmarks into a single “general capability” scale, allowing comparisons between models even over timespans long enough for single benchmarks to reach saturation.",
        "note": "Scores, dates, organizations and confidence intervals are Epoch AI's, copied unchanged apart from rounding to two decimals. This site draws them and marks its own level dates beside them; it computes no score.",
        "points": points,
    }
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT} with {len(points)} models, {points[0]['date']} to {points[-1]['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
