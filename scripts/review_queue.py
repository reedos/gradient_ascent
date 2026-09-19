"""Print the review queue: every page that says how fresh it is, oldest first.

    python scripts/review_queue.py                     # the whole queue
    python scripts/review_queue.py --stale-only         # only the flagged rows
    python scripts/review_queue.py --days 60            # a different threshold than 90
    python scripts/review_queue.py --today 2027-01-01   # pin "today", for a reproducible run
    python scripts/review_queue.py --json               # machine readable, for another tool
    python scripts/review_queue.py --fail-on-stale      # exit 1 if anything is flagged

Why this exists: the project plan promises that every page says how fresh it is, a `reviewed`
date and an "as of" block, and that the build lists pages unreviewed for 90 days.
site/src/components/page/Reviewed.astro prints the first half, on the page itself: it computes
one page's own age and flags it there. Nothing printed the second half, the list across every
page. A page can carry a stale `reviewed` date for months and nobody notices unless they happen
to open that exact page. This is what notices.

Two rules, not one. Every page except a teardown is flagged the same way Reviewed.astro flags it:
more than `--days` (90 by default) days since its own `reviewed` date. A teardown is about named
products, which change faster than anything else on the site, so the project plan gives it a hard
expiry instead of the 90-day rule: `reviewed` plus content/taxonomy.json's `teardowns.expires_days`
(180 today). A teardown's row is never measured against `--days`; changing that flag never moves
a teardown's state.

What each state means:

  ok        within the 90-day window, or, for a teardown, not yet close to its expiry
  stale     more than `--days` days since `reviewed`; not a teardown
  expiring  a teardown, not yet past its expiry, but inside the warning window before it
  expired   a teardown, past its own expiry date

A row's `flagged` is true for stale, expiring and expired, and false for ok. Pages that carry no
`reviewed` field at all, or one that does not parse as a date, get no row: they are counted as
skipped in the summary line instead, so a page that quietly loses its date is still visible rather
than silently dropped.

This never calls a model and never touches the network. It only reads MDX frontmatter off disk
and, for the teardown expiry window, content/taxonomy.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "site" / "src" / "content"
TAXONOMY_PATH = ROOT / "content" / "taxonomy.json"

DEFAULT_DAYS = 90
# content/taxonomy.json's own teardowns.expires_days, used only as a fallback if that file
# cannot be read at all: the number the site actually enforces always wins when it is available.
DEFAULT_TEARDOWN_EXPIRES_DAYS = 180
# How much lead time a teardown gets before its expiry to be flagged "expiring" rather than
# reading "ok" right up to the day it lapses. The site does not publish this number; it is not a
# promise to the reader the way the 90-day rule is. It exists so whoever re-reviews teardowns gets
# a heads-up from this queue rather than a surprise on the day the page goes stale.
EXPIRY_WARNING_DAYS = 14

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# -------------------------------------------------------------------------------------------
# Pure logic: plain data in, plain data out. No filesystem here, so tests/test_review_queue.py
# can exercise every rule with synthetic records and never touch disk.
# -------------------------------------------------------------------------------------------


def parse_date(value: str | None) -> dt.date | None:
    """A `YYYY-MM-DD` string as a date, or None for anything else: missing, empty, quoted oddly,
    or a shape this script does not recognize. Never raises. A malformed date is data to skip,
    not a reason to crash a report that is meant to run unattended."""
    if not value or not DATE_RE.match(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def build_queue(
    records: list[dict],
    today: dt.date,
    days: int = DEFAULT_DAYS,
    expiry_warning_days: int = EXPIRY_WARNING_DAYS,
    teardown_expires_days: int = DEFAULT_TEARDOWN_EXPIRES_DAYS,
) -> tuple[list[dict], int]:
    """The queue and how many pages were skipped, from a list of plain records.

    Each record is `{path, collection, slug, reviewed}`, where `reviewed` is the raw frontmatter
    string (possibly missing, possibly not a real date): deciding what counts as usable is this
    function's job, not the file-reading layer's. Rows come back sorted oldest reviewed date
    first, ties broken by path so the order is stable across runs of the same input.
    """
    rows: list[dict] = []
    skipped = 0
    for record in records:
        reviewed = parse_date(record.get("reviewed"))
        if reviewed is None:
            skipped += 1
            continue

        age_days = (today - reviewed).days
        is_teardown = record.get("collection") == "teardowns"
        row: dict = {
            "path": record["path"],
            "collection": record["collection"],
            "slug": record.get("slug", ""),
            "reviewed": reviewed.isoformat(),
            "age_days": age_days,
        }

        if is_teardown:
            expiry = reviewed + dt.timedelta(days=teardown_expires_days)
            days_to_expiry = (expiry - today).days
            if days_to_expiry < 0:
                state = "expired"
                note = f"expired on {expiry.isoformat()}, {-days_to_expiry} days ago"
            elif days_to_expiry <= expiry_warning_days:
                state = "expiring"
                note = f"expires on {expiry.isoformat()}, in {days_to_expiry} days"
            else:
                state = "ok"
                note = f"expires on {expiry.isoformat()}"
            row.update(
                {
                    "rule": "expiry",
                    "expiry_date": expiry.isoformat(),
                    "days_to_expiry": days_to_expiry,
                    "state": state,
                    "flagged": state in ("expired", "expiring"),
                    "note": note,
                }
            )
        else:
            if age_days > days:
                state = "stale"
                note = f"{age_days - days} days past the {days}-day limit"
            else:
                state = "ok"
                note = f"{days - age_days} days left before the {days}-day limit"
            row.update(
                {
                    "rule": "review",
                    "expiry_date": None,
                    "days_to_expiry": None,
                    "state": state,
                    "flagged": state == "stale",
                    "note": note,
                }
            )
        rows.append(row)

    rows.sort(key=lambda r: (r["reviewed"], r["path"]))
    return rows, skipped


def format_table(rows: list[dict]) -> str:
    """A readable, plain-ASCII listing. Thin on purpose: every value it prints was already
    decided by build_queue. The PATH column widens to the longest path actually present, so a
    long repository path never runs into the NOTE column with no gap between them."""
    if not rows:
        return "(nothing to show)"
    collection_w = max(len("COLLECTION"), max(len(r["collection"]) for r in rows))
    path_w = max(len("PATH"), max(len(r["path"]) for r in rows))
    header = f"{'STATE':<9}{'REVIEWED':<12}{'AGE':>6}  {'COLLECTION':<{collection_w}}  {'PATH':<{path_w}}  NOTE"
    lines = [header, "-" * len(header)]
    for row in rows:
        age = f"{row['age_days']}d"
        lines.append(
            f"{row['state']:<9}{row['reviewed']:<12}{age:>6}  "
            f"{row['collection']:<{collection_w}}  {row['path']:<{path_w}}  {row['note']}"
        )
    return "\n".join(lines)


def format_summary(rows: list[dict], skipped: int, days: int) -> str:
    """The one line under the table. It counts the whole queue, never the filtered view: under
    --stale-only an empty table has to say how many pages were read to get there, or a run that
    found nothing looks exactly like a run that read nothing."""
    total = len(rows)
    flagged = sum(1 for r in rows if r["flagged"])
    oldest = f", oldest reviewed {rows[0]['reviewed']}" if rows else ""
    return (
        f"{total} page(s) checked{oldest}, {flagged} flagged, {skipped} skipped "
        f"(no reviewed date, or one that would not parse). The review threshold is {days} days; "
        "a teardown is judged by its own expiry instead."
    )


# -------------------------------------------------------------------------------------------
# The thin file-reading layer.
# -------------------------------------------------------------------------------------------


def _frontmatter_field(front: str, field: str) -> str | None:
    """The raw string value of a top-level scalar field in an MDX frontmatter block, or None if
    the field is absent. Enough YAML for this schema: a plain `key: value` line, matched only at
    the start of a line so a nested field of the same name under `sources:` is never mistaken for
    the page's own."""
    match = re.search(rf"^{re.escape(field)}:\s*(.*)$", front, re.M)
    if not match:
        return None
    value = match.group(1).strip().strip("'\"")
    return value or None


def discover_records(content_dir: Path | None = None, root: Path | None = None) -> list[dict]:
    """Every `.mdx` page under site/src/content/, in whichever collection it lives in, as plain
    data: `{path, collection, slug, reviewed}`. The collection list is never hard-coded here; it
    is read off the directory name under content_dir, so a new collection is picked up the day
    its directory appears. `reviewed` is passed through unparsed: build_queue decides whether it
    is usable.

    content_dir and root default to the module-level CONTENT_DIR and ROOT, read at call time
    rather than bound as literal defaults, so a test can point this at a throwaway directory by
    assigning review_queue.CONTENT_DIR before calling."""
    content_dir = content_dir if content_dir is not None else CONTENT_DIR
    root = root if root is not None else ROOT
    records: list[dict] = []
    if not content_dir.is_dir():
        return records
    for path in sorted(content_dir.rglob("*.mdx")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        front = text.split("\n---", 1)[0]
        collection = path.relative_to(content_dir).parts[0]
        slug = (
            _frontmatter_field(front, "slug")
            or _frontmatter_field(front, "id")
            or path.stem
        )
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "collection": collection,
                "slug": slug,
                "reviewed": _frontmatter_field(front, "reviewed"),
            }
        )
    return records


def teardown_expires_days(taxonomy_path: Path | None = None) -> int:
    """content/taxonomy.json's `teardowns.expires_days`, the number the site actually enforces
    (see site/src/lib/content.ts and site/src/pages/teardowns/[slug].astro). Falls back to
    DEFAULT_TEARDOWN_EXPIRES_DAYS if the file is missing or will not parse, so a broken taxonomy
    file degrades this report rather than crashing it; scripts/validate.py is what actually
    guards that file's shape. Defaults to the module-level TAXONOMY_PATH, read at call time, the
    same way discover_records reads CONTENT_DIR."""
    taxonomy_path = taxonomy_path if taxonomy_path is not None else TAXONOMY_PATH
    try:
        data = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_TEARDOWN_EXPIRES_DAYS
    value = (data.get("teardowns") or {}).get("expires_days")
    return value if isinstance(value, int) else DEFAULT_TEARDOWN_EXPIRES_DAYS


# -------------------------------------------------------------------------------------------
# The command line.
# -------------------------------------------------------------------------------------------


def build_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="the review threshold in days (default 90)")
    parser.add_argument("--stale-only", action="store_true", help="print only the flagged rows")
    parser.add_argument(
        "--today",
        help="pin today's date as YYYY-MM-DD, for a reproducible run (default: the real date)",
    )
    parser.add_argument("--json", action="store_true", help="print the queue as JSON instead of a table")
    parser.add_argument("--fail-on-stale", action="store_true", help="exit 1 if anything is flagged")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = build_args(argv)

    if args.today:
        today = parse_date(args.today)
        if today is None:
            print(f"--today {args.today!r} is not a YYYY-MM-DD date", file=sys.stderr)
            return 2
    else:
        today = dt.date.today()

    records = discover_records()
    expires_days = teardown_expires_days()
    rows, skipped = build_queue(records, today, args.days, EXPIRY_WARNING_DAYS, expires_days)

    shown = [row for row in rows if row["flagged"]] if args.stale_only else rows

    if args.json:
        print(
            json.dumps(
                {
                    "today": today.isoformat(),
                    "days": args.days,
                    "expiry_warning_days": EXPIRY_WARNING_DAYS,
                    "teardown_expires_days": expires_days,
                    "skipped": skipped,
                    "checked": len(rows),
                    "flagged": sum(1 for row in rows if row["flagged"]),
                    "stale_only": bool(args.stale_only),
                    "rows": shown,
                },
                indent=2,
            )
        )
    else:
        print(format_table(shown))
        print()
        print(format_summary(rows, skipped, args.days))

    if args.fail_on_stale and any(row["flagged"] for row in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
