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
import { agentWorksheet, agentLevels, useCases, agentShapes } from '../../lib/agents-data';

const NAMES = ['taxonomy', 'landscape', 'glossary', 'timeline', 'capability', 'worksheet', 'use-cases', 'shapes'] as const;

export const getStaticPaths: GetStaticPaths = () => NAMES.map((name) => ({ params: { name } }));

export const GET: APIRoute = ({ params, site }) => {
  const name = params.name as (typeof NAMES)[number];
  let body: unknown;
  if (name === 'taxonomy') body = taxonomy;
  else if (name === 'landscape') body = landscape;
  else if (name === 'glossary') body = glossary;
  else if (name === 'timeline') body = timeline;
  else if (name === 'capability') body = capability;
  else if (name === 'shapes') {
    body = {
      note: 'The kinds of job, by the shape of the work and not its subject. Match a job on what the work is; split a request that joins several shapes. usual_level is an expectation the worksheet tests, never a verdict. A recipe is one worked instance of a shape: take its reasoning and leave its subject.',
      shapes: agentShapes(site),
    };
  } else if (name === 'worksheet') {
    body = {
      note: 'The worksheet decision tree. Ask core_questions in order starting at first_question; stop at the first answer whose action is "settle". Then ask every cross_question; a non-null caution is advice to pass on.',
      levels: agentLevels(),
      ...agentWorksheet(),
    };
  } else {
    body = {
      note: 'Every recipe and teardown. Each illustrates one or more job shapes (see shapes.json); it is a worked story, not a catalog entry, so match a job to a shape first and use these for their reasoning. needs_level is the level that particular story settled on. Read the markdown address before drawing on one.',
      use_cases: useCases(site),
    };
  }
  return new Response(JSON.stringify(body, null, 1), { headers: { 'content-type': 'application/json; charset=utf-8' } });
};
