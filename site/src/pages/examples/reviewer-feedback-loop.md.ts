import type { APIRoute } from 'astro';
import { absFor } from '../../lib/agents-data';
import { reviewMarkdown } from '../../lib/reviewer-loop';
export const GET: APIRoute = ({ site }) => new Response(reviewMarkdown(absFor(site)), {
  headers: { 'content-type': 'text/markdown; charset=utf-8' },
});
