import type { APIRoute } from 'astro';
import { lessons, learningStages } from '../../lib/learning';
import { labSpecs } from '../../lib/learning-labs';
import { url } from '../../lib/url';
export function getStaticPaths() { return lessons.map(lesson => ({ params: { lesson: lesson.id }, props: { lesson } })); }
export const GET: APIRoute = ({ props, site }) => {
  const lesson = props.lesson as typeof lessons[number];
  const stage = learningStages[lesson.stage], lab = labSpecs[lesson.id];
  return new Response([
    `# ${lesson.title}`, lesson.objective, `Stage ${lesson.stage + 1}: ${stage.title}`, ...lesson.teaching,
    '## Worked example', lesson.example, '## Check your understanding', lesson.exercise,
    '## Explained answer', lesson.answer, '## Browser workspace', lab.brief, lab.scenario,
    'Deterministic simulation only. No model calls. Edit, run, save, and download in the HTML version of this lesson.',
    '### Starter configuration', '```json\n' + JSON.stringify(lab.starter, null, 2) + '\n```',
    '### Prompt (exported, not interpreted by the simulator)', lab.prompt,
    '## Related concepts', ...lesson.concepts.map(slug => `- [${slug}](${new URL(url(`/techniques/${slug}.md`), site)})`),
    ...(lessons.filter(l => l.stage === lesson.stage).at(-1)?.id === lesson.id ? [
      `## Stage project: ${stage.project}`, ...stage.deliverables.map(d => `- ${d}`), `Review criterion: ${stage.ready}`,
    ] : []),
  ].join('\n\n') + '\n', { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
