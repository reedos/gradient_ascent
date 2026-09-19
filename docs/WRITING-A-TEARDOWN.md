# Writing a teardown

A teardown takes one kind of product the reader has already used (a deep-research mode, a coding
agent, an always-on teammate) and takes it apart into the techniques this site explains. It is
the concrete end of the content model: the technique pages teach a pattern with a synthetic
example, and a teardown shows the same patterns running inside something with a logo on it.

Three are listed in `content/taxonomy.json` under `teardowns.first`, each with a slug, a title and
the technique slugs it decodes (`patterns`). The taxonomy owns that list; your file owns the
writing. Write `site/src/content/teardowns/<slug>.mdx` and nothing else. If a teardown needs a
technique that is not in its `patterns`, or a product that is not in `content/landscape.json`, ask
the integrator in your page-requests file; do not edit either content file yourself.

## What a teardown is not

- Not a review. No rankings, no "best", no advice about which product to buy.
- Not a guess about how a product works inside. Every sentence about a product is what its own
  maker documents, quoted or paraphrased from a page you opened, or it is cut.
- Not a second technique page. Where a mechanism needs explaining, link the technique page and
  keep moving.

## Frontmatter

```yaml
slug: coding-agent            # matches the taxonomy slug and the filename
products:                     # registry ids from content/landscape.json, at least one
  - claude-code
  - codex
reviewed: 2026-09-18          # ISO; the page prints the expiry date computed from it
sources:                      # at least one; each needs title, url, accessed
  - title: "Claude Code by Anthropic | AI Coding Agent, Terminal, IDE"
    url: "https://claude.com/product/claude-code"
    publisher: "Anthropic"
    date: "2026-09-18"
    accessed: "2026-09-18"
```

That is the whole schema (`site/src/content.config.ts`), and it is final. `products` is what the
page prints as "decoded from", with each maker's name resolved through the registry, so a product
renamed or retired says so without this file being touched. Never type a product name that is not
in the registry.

`title` is not frontmatter: it comes from the taxonomy. Neither is `status`. Do not put
`<Sources>` or `<Reviewed>` in the body: the page renders both from frontmatter, last.

## The expiry

A teardown dates faster than anything else on the site, so the project plan gives the layer two limits, and
both are enforced: at most `teardowns.cap` are live at once, and each one expires
`teardowns.expires_days` days after its `reviewed` date. The page prints its own expiry date. Once
that date passes, the teardown is badged stale on `/teardowns/`, and technique pages stop linking
to it until someone re-reads every claim and moves `reviewed` forward. Re-reviewing means opening
every source again, not editing the date.

## Sections, in this order

1. **What you see.** Open with the surface: what the reader does, and what comes back. Name the
   products in `products` and nothing else. About 150 words.
2. **What is happening underneath.** The main section. Walk the work level by level, lowest first,
   and say which technique each part is. Each technique named in the taxonomy's `patterns` for
   this teardown gets a paragraph and a `<Link>` to its page. About 450 words.
3. **Which page explains each part.** A Markdown table: what you see, what it is, and the page.
   This is the map a reader uses to go deeper; keep it to one line per part.
4. **What the makers say.** Two to four quotations from the makers' own pages about how theirs
   works, each attributed by name and marked with `<Cite n={…}/>`. This is the section the
   sourcing rule below exists for.
5. **Where it fails.** What this kind of product is documented not to do, or what the failure
   modes on the technique pages predict here. Attribute a limit to whoever states it. Never
   invent a benchmark, and never report a number no source published.
6. **If you build one.** What a reader assembling the same thing should take from it, and which
   level they would be working at. Point at the recipes where one exists.

## Length and components

900 to 1400 words. Under 900 and it is a summary of the technique pages; over 1400 and it has
become one.

Use the components in `site/src/components/page/`: `<Link>` for every internal link (raw Markdown
links and raw HTML both fail the build on purpose), `<Cite n={…}/>` for a source marker, and
Markdown tables for tables. `<Run>`, `<CodeFile>`, `<CostStrip>`, `<FailureModes>`, `<TryIt>`,
`<HowToEval>` and `<RunIt>` belong to technique pages: a teardown decodes somebody else's system,
and it has no example of its own, no recorded run and no eval. If a teardown seems to want one,
what it wants is a technique page.

## Sourcing

The rule is the one in the project plan, applied to a page that is entirely about other people's
products:

- Every claim about a product is quoted or paraphrased from that maker's own page, which you
  opened. Fetch the raw page and confirm your sentence is in it before you use it.
- A maker's claim about its own product is attributed to the maker in the sentence ("Anthropic
  says…"), never stated as this site's finding.
- Quote exactly, and do not truncate a sentence at the comfortable clause; the omitted half is
  usually the qualification.
- Arithmetic over a published number is your arithmetic, and says so.
- If you cannot open the page, cut the claim. There is no measured result anywhere in this
  repository, so no teardown may report one.
- Date every policy or pricing statement, and scope it to the plan or product it covers.

## Before you commit

All four checks exit 0: `python scripts/validate.py`, then in `site/` `npx astro check`,
`npm run build` and `npm test`, then `python -m unittest discover -s tests`. The validator's rule
15 checks that your file exists for a teardown the taxonomy lists, that its frontmatter slug
matches its filename, and that it carries a reviewed date, at least one source and at least one
registry id. Read the built page at `site/dist/teardowns/<slug>/index.html` and confirm the
sections, the quotations and the technique links are where you meant them.
