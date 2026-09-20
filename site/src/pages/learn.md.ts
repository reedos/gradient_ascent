import type { APIRoute } from 'astro';
import { lessons, learningStages } from '../lib/learning';
import { url } from '../lib/url';
export const GET: APIRoute = ({ site }) => new Response([
  '# Learn step by step',
  '18 lessons in six stages. Each lesson starts with a prefilled English message: press Send, review a scripted reply, then send a suggested follow-up. Replies appear progressively; no live model is called, and edited messages do not change the scripted output. Configuration exercises are optional. Each stage ends with a project you can write in the site. Progress and drafts stay in this browser; download files for your own copy.',
  ...learningStages.flatMap((s, i) => [
    `## Stage ${i + 1}: ${s.title}`, s.summary,
    ...lessons.filter(l => l.stage === i).map(l => `- [${l.title}](${new URL(url(`/learn/${l.id}.md`), site)}): ${l.objective}`),
    `### Project: ${s.project}`, ...s.deliverables.map(d => `- ${d}`), `Review criterion: ${s.ready}`,
  ]),
].join('\n\n') + '\n', { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
