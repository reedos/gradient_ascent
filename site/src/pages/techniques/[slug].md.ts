// The clean Markdown version of every /techniques/<slug>/ page, at /techniques/<slug>.md, for a
// reader's own agent (the project plan's ninth audience). Generated from the same MDX source the HTML
// page renders, flattened by site/src/lib/indexes.ts -- see that file's module comment for how
// components turn into Markdown and what happens when one cannot be parsed.
import type { APIRoute, GetStaticPaths } from 'astro';
import { allTechniqueSlugs } from '../../lib/content';
import { techniqueMarkdown } from '../../lib/indexes';

export const getStaticPaths: GetStaticPaths = () => allTechniqueSlugs.map((slug) => ({ params: { slug } }));

export const GET: APIRoute = async ({ params }) => {
  const md = await techniqueMarkdown(params.slug!);
  if (!md) return new Response('Not found', { status: 404 });
  return new Response(md, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
