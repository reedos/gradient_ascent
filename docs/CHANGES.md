# Adding a change entry, and keeping pages fresh

Two things live here: how to add an entry to `/changes/`, and how to work the review queue that
tells you which pages have gone stale. They belong together because the second one is what
produces most of the first.

## The change log

`content/changes.json` is the record of what changed on the site and why it matters to somebody
reading it. It drives three things:

| | |
|---|---|
| `/changes/` | The page, newest first, grouped by date |
| `/changes.xml` | An Atom feed, so a reader learns a page was corrected without coming back to look |
| `/changes.md` | The clean Markdown twin, for a reader's own agent |

The plan's living layer was meant to be fed by a runner that reads the field and proposes
updates. This is the half that needs no model: entries are written by hand, and the log is only
as good as the judgment about what belongs in it.

### What belongs in it

One entry for one thing a reader would notice. A new section on every level page is an entry.
Eleven new recipes are one entry, not eleven. A typo is not an entry. Neither is anything that
changed only in the repository.

The test to apply: **would somebody who read this site last month want to know?** If the answer
needs a paragraph of setup about how the site is built, the answer is no.

### How to write one

Write for the reader, not for yourself. Two fields carry the entry:

- `what` says what is different now. Present tense, plain. Not "added a frontier component to the
  level page template"; "each of the eight level pages now ends with two to four open problems".
- `why` says what it is good for, or what was wrong before. This is the field that makes the log
  worth reading. If you cannot write it, you are describing a commit.

House style applies: American English, dates month-day-year, no dash asides, no aphorisms, no
padding. `tests/test_changes.py` enforces the parts a test can: it rejects the words of a commit
message, anything that describes how the site is made, and anything that claims a measured
number, which this site does not have.

### The fields

```json
{
  "id": "frontier-blocks",
  "date": "2026-09-19",
  "title": "Every level page says what is still unsolved at that level",
  "what": "What is different now, in one or two sentences.",
  "why": "Why a reader should care, or what was wrong before.",
  "pages": [{ "label": "Level 02 · Context", "path": "/levels/2/" }]
}
```

- `id` is a lowercase hyphenated slug. It is the page anchor **and** the feed entry's id, so it
  never changes once published: a feed reader that has seen an id treats a new one as a new entry.
- `date` is the day the change reached the site, ISO in the file and rendered month-day-year.
  Several entries can share a date. Within a date, **file order is the order shown**, so put a new
  entry at the top of that date's block.
- `pages` links the pages the change touched, two or three at most. Every path must be a real
  route; the test checks them against `src/pages` and the taxonomy.

### Adding one

1. Put the new object at the top of `changes` in `content/changes.json`.
2. Set `as_of` to the same date.
3. `python -m unittest tests.test_changes`
4. In `site/`: `npx tsx --test tests/changes.test.ts`
5. Build, then look at `/changes/` and fetch `/changes.xml` to see it render.

The file is written by `json.dumps(obj, ensure_ascii=False, indent=2) + "\n"`. A test asserts it
still round-trips that way, so an edit stays a clean diff.

### What does not go in it

Nothing about who makes the site, what it is made with, or the machine it is made on. Nothing
that reports a measured number: every page here is a draft with no recorded run behind it, and a
change entry is not where that quietly stops being true.

## The review queue

The site promises on every page that it says how fresh it is, and that pages unreviewed for 90
days are flagged. `Reviewed.astro` does the first half, on the page. `scripts/review_queue.py`
does the second, across the whole site.

```
python scripts/review_queue.py                     # the whole queue, oldest first
python scripts/review_queue.py --stale-only        # only what is flagged
python scripts/review_queue.py --today 2027-01-01  # pin the date, for a reproducible run
python scripts/review_queue.py --json              # for another tool to read
python scripts/review_queue.py --fail-on-stale     # exit 1 if anything is flagged
```

It reads the `reviewed` date out of every `.mdx` under `site/src/content/` and prints them oldest
first. A teardown is judged by its own expiry from `content/taxonomy.json` instead of the 90-day
rule, and is marked `expiring` before it lapses rather than on the day. A page with a missing or
unparseable `reviewed` date is counted as skipped in the summary, so a page that quietly loses its
date is still visible.

It reports; it does not police. The plan's maintenance budget (oldest first, at most four pages a
month, stop writing new pages if the queue passes twelve) is a decision for whoever works the
queue, and deliberately not something the script prints at a reader.

Working the queue is where most change entries come from: re-read a page, fix what has drifted,
move its `reviewed` date, and if a reader would notice the difference, write it up here.

## Sources rot on their own schedule

Freshness is not only about dates. `scripts/check_sources.py` fetches every URL the site cites and
reports the ones that moved, drifted, are blocked or are gone, into
`.local/research/source-check.md`. It makes no judgment about the words quoted from a page; only a
person re-reading the page can do that, and `drifted` is the signal to go and do it. Run it before
a review pass, not after.
