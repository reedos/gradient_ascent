import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { lessons, learningStages, parseProgress, nextIncomplete } from '../src/lib/learning.ts';
import { labSpecs, parseConfig, runLab, zipFiles } from '../src/lib/learning-labs.ts';

test('six connected stages introduce every concept and have complete browser labs', () => {
  assert.equal(learningStages.length, 6);
  assert.equal(lessons.length, 18);
  assert.equal(new Set(lessons.map(l => l.id)).size, 18);
  learningStages.forEach((s, i) => { assert.equal(lessons.filter(l => l.stage === i).length, 3); assert.equal(s.deliverables.length, 3); });
  assert.deepEqual(Object.keys(labSpecs).sort(), lessons.map(l => l.id).sort());
  const taxonomy = JSON.parse(readFileSync(new URL('../../content/taxonomy.json', import.meta.url), 'utf8'));
  const concepts = [
    ...taxonomy.tiers.flatMap((t: { pages: { slug: string }[] }) => t.pages.map(p => p.slug)),
    ...taxonomy.tracks.flatMap((t: { id: string; pages: { slug: string }[] }) => [t.id, ...t.pages.map(p => p.slug)]),
  ];
  assert.equal(concepts.length, 54);
  assert.deepEqual([...new Set(lessons.flatMap(l => l.concepts))].sort(), [...new Set(concepts)].sort());
});

test('progress rejects corrupt storage, removes unknowns and resumes earliest unfinished lesson', () => {
  for (const raw of [null, 'bad json', '{}', 'null', '42']) assert.deepEqual(parseProgress(raw), []);
  assert.deepEqual(parseProgress(JSON.stringify([lessons[2].id, 'unknown', lessons[0].id, lessons[0].id, {}])), [lessons[0].id, lessons[2].id]);
  assert.equal(nextIncomplete([lessons[0].id, lessons[2].id])?.id, lessons[1].id);
  assert.equal(nextIncomplete(lessons.map(l => l.id)), undefined);
});

for (const lesson of lessons) test(`${lesson.id}: starter exposes a failure, working example passes and repeats exactly`, () => {
  const spec = labSpecs[lesson.id];
  assert.ok(runLab(lesson.id, spec.starter, spec.prompt).checks.some(c => !c.passed));
  const good = runLab(lesson.id, spec.solution, spec.prompt, 'My notes');
  assert.ok(good.checks.every(c => c.passed), JSON.stringify(good.checks));
  assert.deepEqual(runLab(lesson.id, spec.solution, spec.prompt, 'My notes'), good);
  assert.equal(good.files['notes.md'], 'My notes');
  assert.deepEqual(JSON.parse(good.files['config.json']), spec.solution);
  assert.deepEqual(JSON.parse(good.files['checks.json']), good.checks);
});

test('retrieval can succeed while the generated answer still fails', () => {
  const result = runLab('retrieve-and-answer', { ...labSpecs['retrieve-and-answer'].solution, answerDays: 30 }, 'Answer');
  assert.ok(result.checks.find(c => c.label.startsWith('Retrieval'))?.passed);
  assert.equal(result.checks.find(c => c.label.includes('amended'))?.passed, false);
});
test('harness stops a four-request script after three executed steps', () => {
  const output = runLab('agent-and-harness', labSpecs['agent-and-harness'].solution, 'Search').output as { trace: unknown[]; stopReason: string };
  assert.equal(output.trace.length, 3); assert.equal(output.stopReason, 'step-limit');
});
test('a failed branch blocks release and ambiguous success does not cause a retry', () => {
  const workflow = runLab('fixed-workflows', labSpecs['fixed-workflows'].solution, 'Check').output as { release: boolean };
  assert.equal(workflow.release, false);
  const tool = runLab('tools-and-boundaries', labSpecs['tools-and-boundaries'].solution, 'Look up').output as { nextAction: string };
  assert.equal(tool.nextAction, 'return-existing-record');
});
test('changing fixture evidence or inventing evaluation cases cannot pass', () => {
  for (const [id, edits] of [
    ['approval-and-delegation', { currentVersion: 'v1' }],
    ['fixed-workflows', { completedChecks: { policy: true, arithmetic: true } }],
    ['adapt-with-evidence', { heldOut: ['unknown'] }],
    ['measure-a-baseline', { development: ['fake'] }],
  ] as const) assert.ok(runLab(id, { ...labSpecs[id].solution, ...edits }, 'Do it').checks.some(c => !c.passed));
});
test('invalid configuration is rejected without executing code', () => {
  for (const raw of ['null', '[]', '42', '"text"', '{', 'globalThis.alert(1)', ' '.repeat(30001)]) assert.throws(() => parseConfig(raw));
  assert.deepEqual(parseConfig('{"maxSteps":3}'), { maxSteps: 3 });
  assert.throws(() => runLab('missing', {}, ''));
});
test('ZIP files are deterministic, including Unicode and empty content', () => {
  const files = { 'prompt.md': 'Hello → café', 'notes.md': '' };
  assert.deepEqual(zipFiles(files), zipFiles(files));
  assert.equal(new DataView(zipFiles(files).buffer).getUint32(0, true), 0x04034b50);
});
