import type { APIRoute } from 'astro';
import { lessons, learningStages } from '../lib/learning';
import { url } from '../lib/url';
export const GET: APIRoute = ({ site }) => new Response([
  '# Learn step by step',
  '18 lessons in six stages. Each lesson has an editable browser workspace, a deterministic simulation, generated files, and explained checks. Each stage ends with a project you can author in the site. No API key or model call is needed. Progress and drafts are stored only in this browser; download files for your own copy.',
  ...learningStages.flatMap((s, i) => [
    `## Stage ${i + 1}: ${s.title}`, s.summary,
    ...lessons.filter(l => l.stage === i).map(l => `- [${l.title}](${new URL(url(`/learn/${l.id}.md`), site)}): ${l.objective}`),
    `### Project: ${s.project}`, ...s.deliverables.map(d => `- ${d}`), `Review criterion: ${s.ready}`,
  ]),
].join('\n\n') + '\n', { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
