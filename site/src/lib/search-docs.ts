// Turns the site's own data into the flat SearchDoc[] both pages/search-index.json.ts (the
// fetchable index) and pages/search.astro (the no-JavaScript fallback listing) render from --
// one function, so the two can never list a different set of things. Heavy imports live here,
// not in search.ts: this module runs at build time only and is never bundled to the client.
import { getEntry } from 'astro:content';
import {
  levels,
  recipes as recipeList,
  recipeLevels,
  teardowns as teardownList,
  techniquesForTeardown,
  teardownExpiry,
  allTechniqueSlugs,
  techniqueBySlug,
  named,
  taxonomy,
} from './content';
import { glossaryTerms, glossaryTarget, parseAllFailureModes, flattenMdxBody } from './indexes';
import { url } from './url';
import type { SearchDoc } from './search';
import { milestones as timelineMilestones, formatDate as formatTimelineDate } from './timeline';

// Keeps any one technique's contribution to the index small: about a paragraph's worth of
// headings and opening sentences, not the whole page. Cheap because it reuses indexes.ts's own
// MDX-to-Markdown flattener (already run once per page for the /*.md endpoints) plus two regular
// expressions, rather than a second parse of the source.
const MAX_BODY_CHARS = 600;

function firstSentence(text: string): string {
  const clean = text
    .replace(/\s+/g, ' ')
    .replace(/[`*_#]/g, '')
    .trim();
  if (!clean) return '';
  const m = clean.match(/^.{0,220}?[.!?](?=\s|$)/);
  return (m ? m[0] : clean.slice(0, 180)).trim();
}

/** "Heading: first sentence" for every `##` section, joined, capped at MAX_BODY_CHARS. */
function sectionSnippets(markdown: string): string | undefined {
  const headingRe = /^##\s+(.+)$/gm;
  const parts: string[] = [];
  let total = 0;
  let match: RegExpExecArray | null;
  while ((match = headingRe.exec(markdown))) {
    const heading = match[1].trim();
    const rest = markdown.slice(headingRe.lastIndex);
    const nextIdx = rest.search(/^##\s+/m);
    const section = nextIdx === -1 ? rest : rest.slice(0, nextIdx);
    const sentence = firstSentence(section);
    const piece = sentence ? `${heading}: ${sentence}` : heading;
    parts.push(piece);
    total += piece.length + 1;
    if (total >= MAX_BODY_CHARS) break;
  }
  return parts.length ? parts.join(' ') : undefined;
}

/** A registry entry's former name, stripped of its "(renamed 2026-07-16)" suffix, so it scores
 *  as a plain alternate title: "NotebookLM (renamed 2026-07-16)" -> "NotebookLM". */
function formerNameOnly(formerly: string | undefined): string | undefined {
  if (!formerly) return undefined;
  const stripped = formerly.replace(/\s*\([^)]*\)\s*$/, '').trim();
  return stripped || undefined;
}

export async function buildSearchDocs(): Promise<SearchDoc[]> {
  const docs: SearchDoc[] = [];

  // Every technique and topic: tier pages, track roots, and track pages (site/src/lib/content.ts
  // enumerates all three as one list already, since /techniques/<slug>/ treats them alike).
  for (const slug of allTechniqueSlugs) {
    const t = techniqueBySlug(slug);
    if (!t) continue;
    const entry = await getEntry('techniques', slug);
    const body = entry ? sectionSnippets(flattenMdxBody(entry.body ?? '', `site/src/content/techniques/${slug}.mdx`)) : undefined;
    docs.push({
      id: `technique:${slug}`,
      kind: 'technique',
      title: t.title,
      meta: t.levelLabel,
      summary: t.summary,
      body,
      level: t.level,
      url: url(`/techniques/${slug}/`),
    });
  }

  // Recipes.
  for (const r of recipeList) {
    const lv = recipeLevels(r);
    const highest = lv.length ? Math.max(...lv) : undefined;
    docs.push({
      id: `recipe:${r.slug}`,
      kind: 'recipe',
      title: r.title,
      meta: highest !== undefined ? `Needs level ${highest}` : 'Recipe',
      summary: r.summary,
      level: highest,
      url: url(`/recipes/${r.slug}/`),
    });
  }

  // Teardowns: the product decoded, its techniques as body text (so "Codex" or "deep research"
  // finds the teardown as well as the registry entry), and its expiry date in the meta line --
  // the one page kind whose usefulness has a date on it.
  for (const t of teardownList) {
    const entry = await getEntry('teardowns', t.slug);
    const reviewed = entry ? entry.data.reviewed.toISOString().slice(0, 10) : undefined;
    const techniques = techniquesForTeardown(t);
    const lv = techniques.map((x) => x.level).filter((l): l is number => typeof l === 'number');
    const body = entry
      ? sectionSnippets(flattenMdxBody(entry.body ?? '', `site/src/content/teardowns/${t.slug}.mdx`))
      : undefined;
    docs.push({
      id: `teardown:${t.slug}`,
      kind: 'teardown',
      title: t.title,
      meta: reviewed ? `Teardown · expires ${teardownExpiry(reviewed)}` : 'Teardown',
      summary: `Decoded into ${techniques.map((x) => x.title).join(', ')}.`,
      body,
      level: lv.length ? Math.max(...lv) : undefined,
      url: url(`/teardowns/${t.slug}/`),
    });
  }

  // Levels: the eight tiers, plus the tracks overview page ("Topics at every level").
  for (const tier of levels) {
    docs.push({
      id: `level:${tier.order}`,
      kind: 'level',
      title: `Level ${String(tier.order).padStart(2, '0')} · ${tier.title}`,
      meta: tier.short,
      summary: tier.description,
      level: tier.order,
      url: url(`/levels/${tier.order}/`),
    });
  }
  docs.push({
    id: 'level:tracks',
    kind: 'level',
    title: taxonomy.tracks_overview.title,
    meta: taxonomy.tracks_overview.who,
    summary: taxonomy.tracks_overview.description,
    level: 'tracks',
    url: url('/levels/tracks/'),
  });

  // The generated views: pages built from the site's own data rather than from an MDX file. They
  // were missing from the index entirely -- a reader searching "map" or "worksheet" found the
  // techniques that mention one, not the view itself. Listed here by hand because that is what
  // they are: a fixed set of views, each with a sentence saying what it shows.
  const views: { id: string; title: string; summary: string; path: string }[] = [
    {
      id: 'map',
      title: 'Map',
      summary:
        "Every technique as a node, laid out by level, with the taxonomy's requires, upgrades-to, combines-with and alternative-to relations as edges.",
      path: '/map/',
    },
    {
      id: 'timeline',
      title: 'Timeline',
      summary:
        'When each level reached the public, marked at the launch of the product that brought it there, with the paper that first described it behind each mark.',
      path: '/timeline/',
    },
    {
      id: 'worksheet',
      title: 'Worksheet',
      summary: 'Answer a few questions about your own job and get the lowest level that passes.',
      path: '/worksheet/',
    },
    {
      id: 'recipes',
      title: 'Recipes',
      summary:
        'Common tasks and the levels they need, with the use case by technique matrix underneath.',
      path: '/recipes/',
    },
    {
      id: 'teardowns',
      title: 'Teardowns',
      summary: 'Products you have used, taken apart into the techniques they are built from.',
      path: '/teardowns/',
    },
    {
      id: 'names',
      title: 'Names',
      summary:
        'Every developer, model, product and tool this site names, with the technique each one demonstrates and the date it was checked.',
      path: '/names/',
    },
    {
      id: 'failures',
      title: 'Failure gallery',
      summary:
        'Every named failure mode across every technique, grouped by level, each with how to notice it and how to test for it.',
      path: '/failures/',
    },
    {
      id: 'glossary',
      title: 'Glossary',
      summary: 'Every term a newcomer meets on this site, defined from the page that explains it.',
      path: '/glossary/',
    },
    {
      id: 'method',
      title: 'Method',
      summary:
        'How a level is defined, how a page is written and reviewed, and what the numbers on this site do and do not mean.',
      path: '/method/',
    },
  ];
  for (const v of views) {
    docs.push({
      id: `view:${v.id}`,
      kind: 'view',
      title: v.title,
      meta: 'View',
      summary: v.summary,
      url: url(v.path),
    });
  }

  // Glossary terms: term, aka, definition, and the target page -- the same page glossary.astro
  // itself links a term's name to, so a search result behaves exactly like clicking the term on
  // the glossary. The URL comes from indexes.ts's glossaryTarget rather than being built here,
  // because a term's `page` may be a thread id ("graph engineering") and not a technique slug.
  for (const g of glossaryTerms) {
    const technique = techniqueBySlug(g.page);
    const target = glossaryTarget(g);
    docs.push({
      id: `glossary:${g.term}`,
      kind: 'glossary',
      title: g.term,
      alt: g.aka,
      meta: target.label,
      summary: g.definition,
      level: technique?.level,
      url: target.href,
    });
  }

  // Registry names: models, products, tools. Linked to the first technique they demonstrate, per
  // the task's own instruction, with /names/ as a second link for "everything this ships in."
  for (const n of named) {
    const firstSlug = n.demonstrates[0];
    const target = firstSlug ? techniqueBySlug(firstSlug) : undefined;
    const demonstratesTitles = n.demonstrates
      .map((s) => techniqueBySlug(s)?.title)
      .filter((x): x is string => Boolean(x));
    docs.push({
      id: `name:${n.id}`,
      kind: 'name',
      title: n.name,
      alt: formerNameOnly(n.formerly) ? [formerNameOnly(n.formerly)!] : undefined,
      meta: [n.maker, n.category].filter(Boolean).join(' · '),
      body: demonstratesTitles.length ? demonstratesTitles.join(', ') : undefined,
      level: target?.level,
      url: target ? url(`/techniques/${target.slug}/`) : url('/names/'),
      secondaryUrl: url('/names/'),
      secondaryLabel: 'All names',
    });
  }

  // Failure modes: name and its page, per the task's field list -- not the notice/test text,
  // which would roughly double the index for detail a result row does not show anyway (the
  // notice and test read in full on the technique page a click lands on). One per technique per
  // named mode -- see indexes.ts's own parser, which is also what builds /failures/, so this
  // list matches that page exactly.
  const modes = await parseAllFailureModes();
  for (const m of modes) {
    docs.push({
      id: `failure:${m.slug}:${m.name}`,
      kind: 'failure',
      title: m.name,
      meta: m.levelLabel,
      level: m.level,
      url: url(`/techniques/${m.slug}/`),
    });
  }

  // Timeline milestones (finish-timeline): additive, its own kind, each linking to its anchor in
  // /timeline/'s full list -- the same id the page renders as <article id={m.id}>, so a search
  // result lands exactly on the entry it names.
  for (const m of timelineMilestones) {
    docs.push({
      id: `milestone:${m.id}`,
      kind: 'milestone',
      title: m.title,
      meta: `${formatTimelineDate(m.date, m.precision)} · Level ${m.level}`,
      summary: m.what,
      body: m.maker,
      level: m.level,
      url: url(`/timeline/#${m.id}`),
    });
  }

  return docs;
}
