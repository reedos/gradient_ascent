// The clean Markdown version of every /threads/<id>/ page, at /threads/<id>.md, the twin
// techniques/[slug].md.ts and recipes/[slug].md.ts already provide for their own pages. llms.txt
// tells a reader's agent that every page has one at the same path with .md appended, so a thread
// without this file would make that sentence false.
import type { APIRoute, GetStaticPaths } from 'astro';
import { taxonomy } from '../../lib/content';
import { threadMarkdown } from '../../lib/indexes';

export const getStaticPaths: GetStaticPaths = () =>
  taxonomy.threads.map((thread) => ({ params: { id: thread.id } }));

export const GET: APIRoute = async ({ params }) => {
  const md = await threadMarkdown(params.id!);
  if (!md) return new Response('Not found', { status: 404 });
  return new Response(md, { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
