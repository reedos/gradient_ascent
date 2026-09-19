// Unit tests for src/lib/matrix.ts, the shaping behind the recipe x technique matrix on
// /recipes/. Run: npm test (in site/), which is `node --test tests/*.test.ts`. Everything here is
// a synthetic fixture: matrix.ts takes its data as arguments precisely so these tests never
// depend on the real content/taxonomy.json, which other agents change under them.
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildMatrix, levelColor, levelLabel, type MatrixRecipe, type MatrixTechnique } from '../src/lib/matrix.ts';

const techniques: MatrixTechnique[] = [
  { slug: 'chat', title: 'Chat', level: 1 },
  { slug: 'rag', title: 'RAG', level: 2 },
  { slug: 'memory', title: 'Memory', level: 2 },
  { slug: 'routing', title: 'Routing', level: 3 },
  { slug: 'evals', title: 'Evals', level: 'tracks' },
  { slug: 'lonely', title: 'Used by nobody', level: 4 },
];

const recipes: MatrixRecipe[] = [
  { slug: 'qa', title: 'Document Q&A', uses: ['chat', 'rag', 'evals'] },
  { slug: 'triage', title: 'Inbox triage', uses: ['routing'] },
];

test('columns are only the techniques some recipe uses', () => {
  const m = buildMatrix(recipes, techniques);
  assert.deepEqual(
    m.columns.map((c) => c.slug),
    ['chat', 'rag', 'routing', 'evals'],
  );
  assert.equal(m.unusedCount, 2); // memory and lonely
});

test('columns are grouped by level, numbered levels ascending and topics last', () => {
  const m = buildMatrix(recipes, techniques);
  assert.deepEqual(
    m.groups.map((g) => g.level),
    [1, 2, 3, 'tracks'],
  );
  assert.deepEqual(
    m.groups.map((g) => g.label),
    ['Level 1', 'Level 2', 'Level 3', 'Topics'],
  );
  assert.deepEqual(m.groups.at(-1)!.techniques.map((t) => t.slug), ['evals']);
  // The flattened column list is exactly the groups' techniques, in group order.
  assert.deepEqual(
    m.columns.map((c) => c.slug),
    m.groups.flatMap((g) => g.techniques.map((t) => t.slug)),
  );
});

test('a row cell is filled exactly where that recipe uses that column', () => {
  const m = buildMatrix(recipes, techniques);
  const [qa, triage] = m.rows;
  assert.deepEqual(qa.cells, [true, true, false, true]);
  assert.deepEqual(triage.cells, [false, false, true, false]);
  assert.equal(qa.cells.length, m.columns.length);
});

test('a row lists the techniques it uses in column order, for the phone fallback', () => {
  const m = buildMatrix(recipes, techniques);
  assert.deepEqual(
    m.rows[0].used.map((t) => t.slug),
    ['chat', 'rag', 'evals'],
  );
});

test('a row reports the highest numbered level it reaches, ignoring topics', () => {
  const m = buildMatrix(recipes, techniques);
  assert.equal(m.rows[0].highest, 2); // chat 1, rag 2, evals is a topic
  assert.equal(m.rows[1].highest, 3);
  const topicsOnly = buildMatrix([{ slug: 'x', title: 'X', uses: ['evals'] }], techniques);
  assert.equal(topicsOnly.rows[0].highest, undefined);
});

test('column counts say how many recipes use each column', () => {
  const m = buildMatrix(recipes, techniques);
  assert.deepEqual(m.columnCounts, [1, 1, 1, 1]);
  const both = buildMatrix(
    [...recipes, { slug: 'third', title: 'Third', uses: ['rag', 'routing'] }],
    techniques,
  );
  assert.deepEqual(both.columnCounts, [1, 2, 2, 1]);
});

test('a recipe naming a technique that does not exist neither adds a column nor fills one', () => {
  const m = buildMatrix([{ slug: 'odd', title: 'Odd', uses: ['ghost', 'rag'] }], techniques);
  assert.deepEqual(m.columns.map((c) => c.slug), ['rag']);
  assert.deepEqual(m.rows[0].cells, [true]);
  assert.deepEqual(m.rows[0].used.map((t) => t.slug), ['rag']);
});

test('no recipes means no columns and no rows', () => {
  const m = buildMatrix([], techniques);
  assert.deepEqual(m.columns, []);
  assert.deepEqual(m.rows, []);
  assert.deepEqual(m.groups, []);
  assert.equal(m.unusedCount, techniques.length);
});

test('a level number keeps its own colour token and topics keep the neutral one', () => {
  assert.equal(levelColor(3), 'var(--o3)');
  assert.equal(levelColor('tracks'), 'var(--ot)');
  assert.equal(levelLabel(0), 'Level 0');
  assert.equal(levelLabel('tracks'), 'Topics');
});
