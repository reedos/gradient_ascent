import { test } from 'node:test';
import assert from 'node:assert/strict';
import { projectBrief, briefFields } from '../src/lib/project-brief.ts';
test('brief preserves requirements and unknowns without choosing a concept or authorizing execution', () => {
  const result = projectBrief({goal:'Collect α measurements', approval:'Never touch the shared framework'}, 'https://example.org/guide/');
  assert.match(result, /Collect α measurements/);
  assert.match(result, /Never touch the shared framework/);
  assert.equal((result.match(/Not specified/g) || []).length, briefFields.length - 2);
  assert.match(result, /https:\/\/example.org\/guide\/agents.md/);
  assert.match(result, /cannot fetch/);
  assert.match(result, /not a required progression|not quality or a required progression/);
  assert.match(result, /coding agent that builds or adapts tools/);
  assert.match(result, /authorization to send, change, or operate/);
  assert.doesNotMatch(result, /## Concept to consider/);
});
test('a linked concept is only a candidate, with a fetchable reference', () => {
  const result = projectBrief({}, 'https://example.org/guide', { title:'Workflow graphs', markdown:'https://example.org/guide/techniques/workflow-graphs.md' });
  assert.match(result, /Concept to consider, not a predetermined choice/);
  assert.match(result, /workflow-graphs.md/);
  assert.match(result, /Do not assume a concept fits/);
});
