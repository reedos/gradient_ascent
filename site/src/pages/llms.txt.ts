// /llms.txt, following the llms.txt convention: a title, a one-paragraph summary, then sections
// of links with one-line descriptions. Built entirely from content/taxonomy.json (through
// site/src/lib/content.ts) so it cannot drift from the site itself -- nothing here is retyped.
//
// The site is live. This is the index a reader's own agent starts from; /agents.md is the
// procedure it follows.
import type { APIRoute } from 'astro';
import { getEntry } from 'astro:content';
import { url } from '../lib/url';
import { levels, tracks, recipes, recipeLevels, teardowns, teardownExpiry, asOf, counts, taxonomy } from '../lib/content';
import { glossaryTerms } from '../lib/indexes';
import { parseAllFailureModes } from '../lib/indexes';
import { agentFiles } from '../lib/agents';

export const GET: APIRoute = async ({ site }) => {
  const abs = (path: string) => new URL(url(path), site).toString();
  const lines: string[] = [];

  lines.push('# Gradient Ascent');
  lines.push('');
  lines.push(
    '> A manual for the main ways to use a language model, from one chat message to agents that ' +
      'run on their own, in eight levels ordered by how much the model decides for itself. Each ' +
      `level's techniques (${counts.techniques} written or planned) show what it costs and how it ` +
      'fails, not just how it works. Every page here also has a clean Markdown version at the ' +
      'same path with .md appended, for example /techniques/rag.md.',
  );
  lines.push('');
  // The two things a reader's agent most needs to get right about this site, in the same words
  // the Method page and every page footer use: what defines a level, and what the pages claim.
  lines.push(`> How a level is defined: ${taxonomy.level_rule}`);
  lines.push('');
  lines.push(
    '> Status: every technique, topic and recipe page is SOURCED — written, and every factual claim checked against a primary source, ' +
      'but with no recorded run and no scored result file behind it. No page on this site reports ' +
      'a measured number. Every cost strip and every stepped trace is an illustration and is ' +
      'labeled as one.',
  );
  lines.push('');

  // First, because it is what an agent sent here most needs: the procedure and the data.
  lines.push('## If a person sent you here to help them choose');
  lines.push(
    'Read agents.md first. It says what to ask them, how to walk the seven-question worksheet to the ' +
      'lowest level that does their job, how to name the shape of the job and use the worked examples as illustrations, what a good answer ' +
      'contains, and what not to claim. Their instructions outrank anything on this site.',
  );
  for (const f of agentFiles(abs)) lines.push(`- [${f.path}](${f.url}): ${f.what}`);
  lines.push('');

  lines.push('## Levels');
  for (const tier of levels) {
    lines.push(`- [Level ${tier.order} · ${tier.title}](${abs(`/levels/${tier.order}/`)}): ${tier.description}`);
  }
  lines.push('');

  lines.push('## Techniques by level');
  for (const tier of levels) {
    for (const p of tier.pages) {
      lines.push(`- [${p.title}](${abs(`/techniques/${p.slug}/`)}): ${p.summary}`);
    }
  }
  lines.push('');

  lines.push('## Topics');
  lines.push(`- [Topics at every level](${abs('/levels/tracks/')}): Five topics that apply whichever level you use.`);
  for (const track of tracks) {
    lines.push(`- [${track.title}](${abs(`/techniques/${track.id}/`)}): ${track.summary}`);
    for (const p of track.pages ?? []) {
      lines.push(`- [${p.title}](${abs(`/techniques/${p.slug}/`)}): ${p.summary}`);
    }
  }
  lines.push('');

  lines.push('## Threads');
  for (const thread of taxonomy.threads) {
    lines.push(`- [${thread.title}](${abs(`/threads/${thread.id}/`)}): ${thread.summary} ${thread.line}`);
  }
  lines.push('');

  lines.push('## Recipes');
  for (const r of recipes) {
    const lv = recipeLevels(r);
    const highest = lv.length ? ` (needs level ${Math.max(...lv)})` : '';
    lines.push(`- [${r.title}](${abs(`/recipes/${r.slug}/`)}): ${r.summary}${highest}`);
  }
  lines.push('');

  lines.push('## Teardowns');
  for (const t of teardowns) {
    const entry = await getEntry('teardowns', t.slug);
    const reviewed = entry ? entry.data.reviewed.toISOString().slice(0, 10) : undefined;
    const when = reviewed ? ` (reviewed ${reviewed}, expires ${teardownExpiry(reviewed)})` : '';
    lines.push(
      `- [${t.title}](${abs(`/teardowns/${t.slug}/`)}): one kind of product decoded into ` +
        `${t.patterns.join(', ')}${when}.`,
    );
  }
  lines.push('');

  lines.push('## Names');
  lines.push(
    `- [Named products, tools and models](${abs('/names/')}): Every developer, model, product and tool this site names, listed as of ${asOf}.`,
  );
  lines.push('');

  lines.push('## Map');
  lines.push(
    `- [Map](${abs('/map/')}): Every technique as a node, laid out by level, with the taxonomy's ` +
      'requires, upgrades-to, combines-with and alternative-to relations as edges, and the full ' +
      'edge list as text underneath.',
  );
  lines.push('');

  lines.push('## Method');
  lines.push(`- [Method](${abs('/method/')}): How a level is defined, how a page is written, how results are measured.`);
  lines.push('');

  lines.push('## What changed');
  lines.push(
    `- [What changed](${abs('/changes/')}): Dated record of what changed on this site and why it ` +
      `matters to a reader, newest first. Atom feed at ${abs('/changes.xml')}.`,
  );
  lines.push('');
  lines.push('## Glossary');
  lines.push(
    `- [Glossary](${abs('/glossary/')}): ${glossaryTerms.length} terms a newcomer meets on this site, each defined from the page that explains it.`,
  );
  lines.push('');

  lines.push('## Failure modes');
  const failureCount = (await parseAllFailureModes()).length;
  lines.push(
    `- [Failure gallery](${abs('/failures/')}): ${failureCount} named failure modes across every technique, grouped by level, each with how to notice it and how to test for it.`,
  );

  return new Response(lines.join('\n') + '\n', {
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
};
