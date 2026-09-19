// /agents.md: the guide an AI agent reads when a person points it at this site. The same blocks
// are shown to a human, word for word, on /agents/.
import type { APIRoute } from 'astro';
import { agentGuide, toMarkdown, GUIDE_TITLE } from '../lib/agents';
import { guideInput } from '../lib/agents-data';

export const GET: APIRoute = ({ site }) =>
  new Response(toMarkdown(GUIDE_TITLE, agentGuide(guideInput(site))), {
    headers: { 'content-type': 'text/markdown; charset=utf-8' },
  });
