// /shapes.md: the job shapes as text, for a reader's own agent. The page at /shapes/ shows a
// person the same list.
import type { APIRoute } from 'astro';
import { shapesBlocks, toMarkdown, SHAPES_TITLE } from '../lib/agents';
import { agentShapes, absFor } from '../lib/agents-data';

export const GET: APIRoute = ({ site }) =>
  new Response(toMarkdown(SHAPES_TITLE, shapesBlocks(agentShapes(site), absFor(site))), {
    headers: { 'content-type': 'text/markdown; charset=utf-8' },
  });
