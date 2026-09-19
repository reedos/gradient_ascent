// The clean Markdown version of every /recipes/<slug>/ page, at /recipes/<slug>.md. See
// site/src/pages/techniques/[slug].md.ts and site/src/lib/indexes.ts.
import type { APIRoute, GetStaticPaths } from 'astro';
import { recipes } from '../../lib/content';
import { recipeMarkdown } from '../../lib/indexes';

export const getStaticPaths: GetStaticPaths = () => recipes.map((r) => ({ params: { slug: r.slug } }));

export const GET: APIRoute = async ({ params }) => {
  const md = await recipeMarkdown(params.slug!);
  if (!md) return new Response('Not found', { status: 404 });
  return new Response(md, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
