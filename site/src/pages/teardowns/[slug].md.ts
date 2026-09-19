// The clean Markdown version of every /teardowns/<slug>/ page, at /teardowns/<slug>.md. See
// site/src/pages/techniques/[slug].md.ts and site/src/lib/indexes.ts.
import type { APIRoute, GetStaticPaths } from 'astro';
import { teardowns } from '../../lib/content';
import { teardownMarkdown } from '../../lib/indexes';

export const getStaticPaths: GetStaticPaths = () => teardowns.map((t) => ({ params: { slug: t.slug } }));

export const GET: APIRoute = async ({ params }) => {
  const md = await teardownMarkdown(params.slug!);
  if (!md) return new Response('Not found', { status: 404 });
  return new Response(md, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
