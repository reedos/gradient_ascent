# How the timeline is dated

`content/timeline.json` holds the timeline: dated milestones tied to the eight levels, plus
published measures of pace.

## Three dates per level

- **described** — the earliest publication this site could verify describing the level's defining
  idea in a form recognizable today: a paper, or a maker's own technical post. A paper's date is
  its arXiv v1 submission, not a later revision or the conference publication.
- **buildable** — the earliest release this site could verify of an open framework, library or
  API a developer could build the level with rather than from scratch. Someone still builds it.
- **available** (shown as "Reached the public") — the launch of the widely known product that
  first put the level in front of ordinary people, dated from its maker's own page. See "The
  mark is the product people know" below.

They do not always run in that order: at level 4 the product shipped a month before the API, and
the level's note says so. Every milestone sits at the level whose defining question it answers,
under `level_rule`: a level starts where the answer to "who decides the next step" changes.

**The date a level arrived is its `available` date.** The home page's strip, its headline figure
and the gaps between levels are all product to product. The paper and the framework are kept to
show what led up to the product, and the strip draws the paper as a small hollow dot behind it.
A paper describing an idea does not mean anyone could use it.

**The mark is the product people know, at its launch.** The editor's call after a review of every
marked date (2026-09-18): nobody has heard of AI Dungeon 2, everybody met language models through
ChatGPT. So the mark is an editorial choice, and says so. Lesser-known products got to most levels
first (AI Dungeon 2 in 2019, NeevaAI in January 2023, Zapier's OpenAI step in December 2022,
AgentGPT in April 2023, Genspark in June 2024). They are ordinary milestones on the timeline and
sit in each level's `candidates` with the reason the mark went elsewhere. The marked date is the
launch. Where the launch was a waitlist or an unveiling, `availability` says so and `opened`
records the day an ordinary customer could get in: Microsoft 365 Copilot was unveiled on March 16
2023 and went on sale on November 1, 2023. With launch dates the seven marks run in level order,
and so do the seven papers. Levels 2, 3 and 4 launched within seven weeks of each other: the
ideas depend on one another, but the papers were all written by 2022 and ChatGPT's launch let
them out together.

**`described` must describe the level, not what made it possible.** "Attention Is All You Need"
never mentions prompting, so level 1's paper is OpenAI's GPT-2 post. Toolformer was nine months
behind the MRKL paper. CAMEL is eight weeks ahead of the debate paper.

**A product sits at the level it was at on that date, not the level it reached later.** Claude
Cowork is the worked case. Its January 2026 release ran on the person's own computer and the
person started every task, so that milestone is at level 5, for the same reason ChatGPT agent is.
Scheduled tasks (February 2026) do not change that: the person sets the time. The release note of
July 7, 2026, where sessions run remotely and "scheduled tasks run with no device online", is its
level 7 date, and it is a separate milestone. Level 7's test is the taxonomy's own: the models
decide, "including when to start work".

## Reading a maker's page that will not open

Several makers' hosts refuse this site's fetcher: `openai.com`, `help.openai.com` and
`platform.openai.com` return 403. A date that depends on which server blocks a robot is not a
finding, so where a maker's page will not open, this site reads **the Internet Archive's capture
of that same page** (`https://web.archive.org/web/<timestamp>id_/<url>`, found through
`https://archive.org/wayback/available?url=…`). The capture is the maker's own words on the day
it was taken, so a milestone verified that way rests on a primary source.

It records the original page in `source.url`, the capture read in `source.archive_url`, and is
`verified: true` only if that capture shows **both the date and the fact**. Where it shows the
product but no date — ChatGPT Work, Manus — the milestone stays unverified. A host that does open
(`developers.openai.com`, GitHub, arXiv) is preferred to any capture.

## Previews, waitlists and paid plans

A first announcement is often not the day anyone could use the thing. Product milestones carry an
optional `availability` — `general`, `preview`, `waitlist` or `paid plans`. `available` marks the
earliest date a customer could get in **without an invitation**: a subscription counts, a
waitlist does not. ChatGPT plugins were alpha access from a waitlist on March 23, 2023, so level 4
marks May 12, 2023, when every Plus subscriber got them. Where no invitation-free date verifies,
the preview date is marked and called one.

## What "first" means, and does not

Nothing here is the true first use of an idea. **"First" means the earliest publication or
release this site could open today**, cited to a primary source: the paper, the maker's own page
(or a capture of it), or a standard's own site. News and aggregators help find one but are never
cited as one. Earlier work may exist, unfound.

## The marks are choices, and they are listed

A marked date is a decision between dated candidates. Every level carries a `candidates` list:
each milestone considered, whether it was chosen, and a one-line reason. These print on
`/timeline/` under **What each marked date beat**. Two are openly debatable: level 6's
`available` reads two Anthropic pages together (sold April 2025, documented as multi-agent June
2025), and level 3's is the earliest capture of a page that states no launch date — that feature
was live *by* then rather than *on* then.

## Measures, and arithmetic

`measures` quotes published measures of pace exactly, scoped to whose models, which tasks and
what period; nothing here extends one forward. Intervals on the site are the site's own
arithmetic.

## Correcting a date

Open a pull request against `content/timeline.json` changing the milestone, with its own primary
source (a capture counts), and amend that level's `candidates` so the next reader sees what the
new date beat. Nothing here is final.
