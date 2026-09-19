// The clean Markdown version of every /levels/<order>/ page (plus /levels/tracks/), at
// /levels/<order>.md. Built straight from taxonomy data -- a level page has no MDX source of its
// own, so there is nothing to flatten, only to assemble. See site/src/lib/indexes.ts.
//
// The frontier block is appended here rather than inside levelMarkdown because it comes from a
// different content file (content/frontier.json) with its own `as_of`, and the rendered page
// composes it the same way: the level body first, then what is unsolved at that level.
import type { APIRoute, GetStaticPaths } from 'astro';
import { levels, techniqueBySlug } from '../../lib/content';
import { levelMarkdown } from '../../lib/indexes';
import { frontierFor, frontierMarkdown } from '../../lib/frontier';

export const getStaticPaths: GetStaticPaths = () => [
  ...levels.map((t) => ({ params: { level: String(t.order) } })),
  { params: { level: 'tracks' } },
];

export const GET: APIRoute = async ({ params }) => {
  const raw = params.level!;
  const order = raw === 'tracks' ? ('tracks' as const) : Number(raw);
  const md = levelMarkdown(order);
  if (!md) return new Response('Not found', { status: 404 });
  const frontier =
    order === 'tracks' ? '' : frontierMarkdown(frontierFor(order), (slug) => techniqueBySlug(slug)?.title);
  return new Response(md + frontier, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
