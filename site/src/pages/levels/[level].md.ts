// The clean Markdown version of every /levels/<order>/ page (plus /levels/tracks/), at
// /levels/<order>.md. Built straight from taxonomy data -- a level page has no MDX source of its
// own, so there is nothing to flatten, only to assemble. See site/src/lib/indexes.ts.
import type { APIRoute, GetStaticPaths } from 'astro';
import { levels } from '../../lib/content';
import { levelMarkdown } from '../../lib/indexes';

export const getStaticPaths: GetStaticPaths = () => [
  ...levels.map((t) => ({ params: { level: String(t.order) } })),
  { params: { level: 'tracks' } },
];

export const GET: APIRoute = async ({ params }) => {
  const raw = params.level!;
  const order = raw === 'tracks' ? ('tracks' as const) : Number(raw);
  const md = levelMarkdown(order);
  if (!md) return new Response('Not found', { status: 404 });
  return new Response(md, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
