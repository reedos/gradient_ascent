// /llms-full.txt: every written page as Markdown in one file, for an agent that would rather make
// one request than seventy. Same text as the per-page .md twins, in the site's own order.
import type { APIRoute } from 'astro';
import { levels, tracks, recipes, teardowns, threads } from '../lib/content';
import { techniqueMarkdown, recipeMarkdown, teardownMarkdown, threadMarkdown } from '../lib/indexes';
import { agentGuide, worksheetBlocks, shapesBlocks, toMarkdown, GUIDE_TITLE, WORKSHEET_TITLE, SHAPES_TITLE } from '../lib/agents';
import { guideInput, agentWorksheet, agentLevels, agentShapes, absFor } from '../lib/agents-data';

export const GET: APIRoute = async ({ site }) => {
  const parts: string[] = [
    toMarkdown(GUIDE_TITLE, agentGuide(guideInput(site))),
    toMarkdown(SHAPES_TITLE, shapesBlocks(agentShapes(site), absFor(site))),
    toMarkdown(WORKSHEET_TITLE, worksheetBlocks(agentWorksheet(), agentLevels(), absFor(site))),
  ];
  const techniqueSlugs = [
    ...levels.flatMap((l) => l.pages.map((p) => p.slug)),
    ...tracks.flatMap((t) => [t.id, ...(t.pages ?? []).map((p) => p.slug)]),
  ];
  for (const slug of [...new Set(techniqueSlugs)]) {
    const md = await techniqueMarkdown(slug);
    if (md) parts.push(md);
  }
  for (const r of recipes) {
    const md = await recipeMarkdown(r.slug);
    if (md) parts.push(md);
  }
  for (const t of teardowns) {
    const md = await teardownMarkdown(t.slug);
    if (md) parts.push(md);
  }
  for (const t of threads) {
    const md = await threadMarkdown(t.id);
    if (md) parts.push(md);
  }
  return new Response(parts.join('\n\n---\n\n'), { headers: { 'content-type': 'text/plain; charset=utf-8' } });
};
