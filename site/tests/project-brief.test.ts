import { test } from 'node:test';
import assert from 'node:assert/strict';
import { projectBrief, briefFields } from '../src/lib/project-brief.ts';
test('brief preserves requirements and unknowns without choosing a concept or authorizing execution', () => {
  const result = projectBrief({goal:'Collect α measurements', approval:'Never touch the shared framework'}, 'https://example.org/guide/');
  assert.match(result, /Collect α measurements/);
  assert.match(result, /Never touch the shared framework/);
  assert.doesNotMatch(result, /Not specified/);
  assert.doesNotMatch(result, /## What should be ready when it finishes/);
  assert.match(result, /https:\/\/example.org\/guide\/agents.md/);
  assert.match(result, /cannot fetch/);
  assert.match(result, /not a required progression|not quality or a required progression/);
  assert.match(result, /coding agent that builds or adapts tools/);
  assert.match(result, /authorization to send, change, or operate/);
  assert.doesNotMatch(result, /## Concept to consider/);
});

test('free-text facts are preserved without contradictory empty fields; blank templates retain questions', () => {
  const brief = projectBrief({goal:'Finished carousels on my phone',notes:'Never delete originals; draft location unknown'},'https://example.org');
  assert.match(brief,/Finished carousels on my phone/);
  assert.match(brief,/Never delete originals; draft location unknown/);
  assert.doesNotMatch(brief,/Not specified|## What must the system never do/);
  const blank=projectBrief({},'https://example.org');
  for(const field of briefFields) assert.ok(blank.includes(field.label));
});
test('a linked concept is only a candidate, with a fetchable reference', () => {
  const result = projectBrief({}, 'https://example.org/guide', { title:'Workflow graphs', markdown:'https://example.org/guide/techniques/workflow-graphs.md' });
  assert.match(result, /Concept to consider, not a predetermined choice/);
  assert.match(result, /workflow-graphs.md/);
  assert.match(result, /Do not assume a concept fits/);
});

for (const scenario of [
  { name:'Wildlife photos', trigger:'Select an outing folder', finished:'Ready-to-post carousels on my phone', humanRole:'Review finished carousels only', prohibited:'Never delete originals', examples:'input.jpg: current input; carousel.jpg: desired output' },
  { name:'Weekly status report', trigger:'Every Friday', finished:'Complete report draft with source links', humanRole:'Approve final content and recipients', prohibited:'Never send before approval', examples:'last-week.md: current output; project.csv: current input' },
  { name:'DUT project', trigger:'Provide a DUT brief', finished:'Reviewable project files and documentation', humanRole:'Review and perform hardware testing', prohibited:'Never modify the shared framework without authorization', examples:'DUT_BRIEF.md: instructions; prior-project/: current input' },
]) test(`preserves desired experience and file roles: ${scenario.name}`, () => {
  const text = projectBrief({...scenario, automation:'Prepare the result automatically; I review it.', priorities:'Reduce hands-on time'}, 'https://example.org/site');
  for (const key of ['trigger','finished','humanRole','prohibited','examples'] as const) assert(text.includes(scenario[key]));
  assert.match(text, /every recurring action I must do/);
  assert.match(text, /not at their expense/);
  assert.match(text, /first usable release must demonstrate/);
  assert.match(text, /Current outputs show the baseline, not necessarily the target/);
  assert.match(text, /does not embed files or grant access/);
  assert.doesNotMatch(text, /recommend the lowest level|Consider ordinary software or no AI first/);
});

test('planning guidance limits question load and separates evidence from proposals', () => {
  const text = projectBrief({context:'Evaluate my existing workflow'}, 'https://example.org');
  assert.match(text, /Evaluate my existing workflow/);
  assert.match(text, /one main decision per question/);
  assert.match(text, /carry noncritical gaps forward/);
  assert.match(text, /500–800 words or less/);
  assert.match(text, /do not append a long appendix by default/);
  assert.match(text, /Define the timing boundary explicitly/);
  assert.match(text, /does not prove that the proposed integration works/);
});
