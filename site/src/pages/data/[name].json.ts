// /data/<name>.json: the site's own data, published. The human pages are built from these files,
// so an agent reading them sees exactly what the site knows and nothing it does not. Two are
// shaped for a reader's agent (use-cases, and the worksheet with every reason resolved to text);
// the rest are the content files as they stand.
import type { APIRoute, GetStaticPaths } from 'astro';
import taxonomy from '../../../../content/taxonomy.json';
import landscape from '../../../../content/landscape.json';
import glossary from '../../../../content/glossary.json';
import timeline from '../../../../content/timeline.json';
import capability from '../../../../content/capability.json';
import { agentWorksheet, agentLevels, useCases } from '../../lib/agents-data';

const NAMES = ['taxonomy', 'landscape', 'glossary', 'timeline', 'capability', 'worksheet', 'use-cases'] as const;

export const getStaticPaths: GetStaticPaths = () => NAMES.map((name) => ({ params: { name } }));

export const GET: APIRoute = ({ params, site }) => {
  const name = params.name as (typeof NAMES)[number];
  let body: unknown;
  if (name === 'taxonomy') body = taxonomy;
  else if (name === 'landscape') body = landscape;
  else if (name === 'glossary') body = glossary;
  else if (name === 'timeline') body = timeline;
  else if (name === 'capability') body = capability;
  else if (name === 'worksheet') {
    body = {
      note: 'The worksheet decision tree. Ask core_questions in order starting at first_question; stop at the first answer whose action is "settle". Then ask every cross_question; a non-null caution is advice to pass on.',
      levels: agentLevels(),
      ...agentWorksheet(),
    };
  } else {
    body = {
      note: 'Every recipe and teardown. needs_level is the level to settle on before the use case fits. Read the markdown address before recommending one.',
      use_cases: useCases(site),
    };
  }
  return new Response(JSON.stringify(body, null, 1), { headers: { 'content-type': 'application/json; charset=utf-8' } });
};
