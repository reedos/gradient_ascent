import type { APIRoute } from 'astro';
import { lessons, learningStages } from '../../lib/learning';
import { labSpecs } from '../../lib/learning-labs';
import { conversations } from '../../lib/learning-conversations';
import { url } from '../../lib/url';
export function getStaticPaths() { return lessons.map(lesson => ({ params: { lesson: lesson.id }, props: { lesson } })); }
export const GET: APIRoute = ({ props, site }) => {
  const lesson = props.lesson as typeof lessons[number];
  const stage = learningStages[lesson.stage], lab = labSpecs[lesson.id];
  const conversation = conversations[lesson.id];
  return new Response([
    `# ${lesson.title}`, lesson.objective, `Stage ${lesson.stage + 1}: ${stage.title}`, ...lesson.teaching,
    '## Worked example', lesson.example, '## Check your understanding', lesson.exercise,
    '## Explained answer', lesson.answer, '## Practice in plain English', conversation.task, lab.scenario,
    'The browser version has prefilled messages and scripted replies that appear progressively. No live model is called. Editing a message does not change its scripted reply.',
    '### Your opening message', conversation.starter, '### Scripted reply', conversation.firstReply,
    '### Notice this', conversation.review, '### Your suggested follow-up', conversation.choices[0].example,
    '### Scripted revision', conversation.choices[0].reply, '### What to take away', conversation.choices[0].feedback,
    '## Optional application configuration', lab.brief, '```json\n' + JSON.stringify(lab.starter, null, 2) + '\n```',
    '## Related concepts', ...lesson.concepts.map(slug => `- [${slug}](${new URL(url(`/techniques/${slug}.md`), site)})`),
    ...(lessons.filter(l => l.stage === lesson.stage).at(-1)?.id === lesson.id ? [
      `## Stage project: ${stage.project}`, ...stage.deliverables.map(d => `- ${d}`), `Review criterion: ${stage.ready}`,
    ] : []),
  ].join('\n\n') + '\n', { headers: { 'content-type': 'text/markdown; charset=utf-8' } });
};
