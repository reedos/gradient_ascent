// /method.md: the premise, the principles and the method as text. The page at /method/ shows a
// person the same words. The site's own principles are cited from technique pages, so an agent
// has to be able to read them without parsing markup.
import type { APIRoute } from 'astro';
import { toMarkdown } from '../lib/agents';
import { absFor } from '../lib/agents-data';
import { methodBlocks, methodSections, METHOD_TITLE } from '../lib/method';

export const GET: APIRoute = ({ site }) =>
  new Response(toMarkdown(METHOD_TITLE, methodBlocks(methodSections(absFor(site)))), {
    headers: { 'content-type': 'text/markdown; charset=utf-8' },
  });
