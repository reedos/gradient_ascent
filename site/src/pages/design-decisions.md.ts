import type { APIRoute } from 'astro';
import { designDecisions } from '../lib/design-decisions';
export const GET:APIRoute=()=>new Response('# Design decisions\n\nLevels are this guide’s teaching framework, not an industry standard or mandatory progression.\n\n'+designDecisions.map(d=>`## ${d.title}\n\n${d.question}\n\n${d.baseline}\n\n${d.distinction}\n\n${d.depth}\n\nCheck: ${d.measure}\n\nSource: [${d.sourceName}](${d.source})`).join('\n\n'),{headers:{'content-type':'text/markdown; charset=utf-8'}});
