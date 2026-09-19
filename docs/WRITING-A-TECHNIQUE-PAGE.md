# Writing a technique page

Copy `site/src/content/techniques/rag.mdx`. This file says what is fixed about it.

## Frontmatter

```yaml
slug: rag              # matches the taxonomy.json slug and the filename
level: 2               # tier order, cross-checked against taxonomy.json
run: rag               # src/data/runs/<id>.json, stepped through by <Run>
lanes: [use, build]
reviewed: 2026-09-18   # ISO; the build flags it after 90 days
sources:               # each needs title, url, accessed
  - title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
    url: "https://arxiv.org/abs/2005.11401"
    publisher: "arXiv (Meta AI Research, UCL, NYU)"
    date: "2020-05-22"
    accessed: "2026-09-18"
```

`status` is not frontmatter: it comes from `content/taxonomy.json`, so the two cannot disagree.
Do **not** put `<Sources>` or `<Reviewed>` in the body — the page renders both from frontmatter,
after the generated blocks, so the reviewed date closes the page.

## Order of the body

What it is (about 200 words, both lanes) → `<Run>` → `<Lanes>` → `<WhenNot>` → Failure modes →
Cost and latency → How to eval it → Run it → Try it. Keep that order.

## Components

```mdx
<Run data={ragRun} label="Level 2 · RAG" runKey="rag" />
<Lanes><Lane name="use" title="Use it">…</Lane><Lane name="build" title="Build it">…</Lane></Lanes>

<WhenNot>Try <Link href="/techniques/order-zero/">order zero</Link> first if …</WhenNot>
<Link href="/techniques/agentic-rag/">agentic RAG</Link>   {/* the ONLY way to link internally */}

<CodeFile file="examples/rag/run.py" func="run" />                    {/* prefer this: pinned by name */}
<CodeFile file="examples/rag/run.py" start={20} end={81} expect="LEVEL = 2" />   {/* lang="text" too */}

<FailureModes modes={[{ name: 'Stale index', notice: 'The answer is …', test: 'Change a fact …' }]} />
<CostStrip stats={[{ label: 'Tokens in', value: '~1,850' }]} level={2} />

<HowToEval questionCount={60} kinds={['lookup', 'multi-hop']}>…prose…</HowToEval>
<RunIt monitor="…" costAtVolume="…" failsInProduction="…" whatToLog="…" />

<TryIt items={[{ lane: 'use', body: 'Open a chat app…' }]} />
Researchers introduced the approach in 2020<Cite n={1}/>.   {/* n = position in sources */}
```

Component props are plain strings: Markdown in them renders literally, so no backticks or
`[text](url)` in `TryIt`, `FailureModes` or `RunIt`.

**Pin code by name wherever you can.** `func=` and `cls=` survive the file being edited above
them; a `start`/`end` range does not, and a slid range is the one CodeFile failure that builds
green and shows the wrong code. When only part of a function is worth showing, a range is the
only option, and then `expect=` is required: it names a literal the block must still contain, so
`scripts/validate.py` fails loudly when the window moves. All 50 range pins on the site carry
one. Never add a range without it.

The other side of that bargain: **a range pin makes the file's line numbers part of the site.**
Before editing a file any page pins by range, check what it pins, and keep the edit
line-count-neutral or tell whoever owns the page. `grep -rhoE '<CodeFile[^>]*/>' site/src/content`
lists every pin in one go.

## Budgets

Use it 400 words. Build it 600 plus code. Run it 200. "What it is" about 200. Over budget goes
to a field note or is cut.

## Sourcing

Every factual claim about the world cites a primary source — the maker's own page — with a
`<Cite>` in the prose. Open the page and check it says the sentence. No measured result may be
claimed: no result file exists, so the illustrative notice on `<CostStrip>` and `<Run>` stays.
Where several companies make a thing, name at least two.

A name in prose must exist in `content/landscape.json` and be registered against a sensible
technique; the validator lists techniques with no named example but cannot tell you that a name
you typed is missing, because pages reference an id rather than typing the name.

## The run file

`site/src/data/runs/<id>.json` is the diagram and the trace in one. Two rules the validator
checks (rule 13), because neither fails the build on its own:

- `h` must clear the lowest node. A node is drawn 19 units below its `y`, so `h` short by less
  than that slices the last box in half — green build, wrong picture.
- Keep every `x` inside the 340-unit canvas. A stray one widens the viewBox instead of clipping,
  which shrinks the whole diagram until the labels fall under 9 px on a phone.

Every run file today carries `"illustrative": true`, which is what stops the site presenting a
hand-drawn diagram as a measurement. **Do not remove that flag from a file you drew.** It comes
off when a real recorded trace replaces the file — see `docs/FIRST-LIVE-RUN.md`.

An edge's `by` field is the same rule as a trace step's `decided_by`: see
`examples/common/trace.py`, which is the single definition. If the diagram plays more
model-decided steps than the example records, one of the two is wrong and it is worth finding out
which before the page is published.

## Style

Direct and literal; about one memorable line per page. No aphorisms, no wordplay, no fragments
for effect. Explain a term the first time you use it. Three edits made to this page:

| Before | After |
|---|---|
| …expands how much a project can hold by up to ten times without a drop in response quality. | Anthropic says that expands capacity by up to ten times while maintaining response quality; that is the maker's claim, not a number this site has measured. |
| Cohere Rerank is one product built for exactly this step. | Cohere and Jina AI both sell one. |
| …compares it against an embedding already computed for every document chunk. | The documents are cut up in advance into chunks — passages of a few hundred words each — and every chunk is turned into an embedding. That set of embeddings is the index. |

## Draft versus published

**Draft** is a working state: the page is written but has no recorded trace and no scored result
file, and says so in its opening. **Published** meets the full anatomy with a real trace and a
real eval. Nothing ships between the two. Set the status in `taxonomy.json`, not here.

All 37 pages are `draft` today, and no example has ever called a model. The seven conditions a
page must meet to become `published`, and the order the first live runs happen in, are in
`docs/FIRST-LIVE-RUN.md`.

## Before you commit

1. Every `<Cite>` resolves to a source you opened today, and `accessed` says today.
2. No sentence claims a measured number; the illustrative notices are intact.
3. Every `<CodeFile>` range is code the prose actually walks through.
4. No raw `](/…)` link anywhere — use `<Link>`, which applies the Pages base path. The validator
   catches this one for you, and a raw link is why: it builds green and 404s in production.
5. Every `<CodeFile>` range carries an `expect=`, and every pin still points at what the prose
   walks through.
6. Word budgets met; no unexplained term in the Use it lane.
7. Exit 0 from: `scripts/validate.py`; `-m unittest discover -s tests`; in `site/`,
   `npx astro check`, `npm run build` and `npm test`.
8. Read the built page at 500 px wide: nothing scrolls sideways but the code block.
