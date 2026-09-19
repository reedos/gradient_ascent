// Unit tests for src/lib/shapes.ts, and one check of the real content/shapes.json against the real
// taxonomy: every reference resolves and every recipe illustrates at least one shape.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { orderedShapes, shapesFor, shapeProblems, type Shape } from '../src/lib/shapes.ts';

const shape = (over: Partial<Shape>): Shape => ({
  id: 'x',
  title: 'X',
  what: 'w',
  signals: ['s'],
  usual_level: 3,
  lower_when: 'l',
  higher_when: 'h',
  techniques: [],
  recipes: [],
  teardowns: [],
  elsewhere: ['e'],
  ...over,
});

test('shapes are ordered lowest usual level first, file order within a level', () => {
  const out = orderedShapes([shape({ id: 'c', usual_level: 5 }), shape({ id: 'a', usual_level: 3 }), shape({ id: 'b', usual_level: 3 }), shape({ id: 'z', usual_level: 0 })]);
  assert.deepEqual(out.map((s) => s.id), ['z', 'a', 'b', 'c']);
});

test('a recipe or a teardown finds every shape it illustrates', () => {
  const shapes = [shape({ id: 'a', recipes: ['r1'] }), shape({ id: 'b', recipes: ['r1', 'r2'] }), shape({ id: 'c', teardowns: ['t1'] })];
  assert.deepEqual(shapesFor(shapes, 'r1').map((s) => s.id), ['a', 'b']);
  assert.deepEqual(shapesFor(shapes, 't1').map((s) => s.id), ['c']);
  assert.deepEqual(shapesFor(shapes, 'nope'), []);
});

test('problems: unknown references, a recipe with no shape, a duplicate id', () => {
  const shapes = [shape({ id: 'a', techniques: ['rag', 'ghost'], recipes: ['r1', 'gone'], teardowns: ['lost'] }), shape({ id: 'a' })];
  const p = shapeProblems(shapes, { techniques: ['rag'], recipes: ['r1', 'r2'], teardowns: [] });
  assert.deepEqual(p.unknownTechniques, [['a', 'ghost']]);
  assert.deepEqual(p.unknownRecipes, [['a', 'gone']]);
  assert.deepEqual(p.unknownTeardowns, [['a', 'lost']]);
  assert.deepEqual(p.recipesWithNoShape, ['r2']);
  assert.deepEqual(p.duplicateIds, ['a']);
});

test('the real shapes file resolves against the real taxonomy, and no recipe is left without a shape', () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const read = (name: string) => JSON.parse(readFileSync(join(here, '..', '..', 'content', name), 'utf8'));
  const shapes: Shape[] = read('shapes.json').shapes;
  const tax = read('taxonomy.json');
  type Pages = { id: string; pages?: { slug: string }[] };
  // A topic track has a page of its own as well as the pages under it.
  const techniques: string[] = [
    ...tax.tiers.flatMap((t: Pages) => (t.pages ?? []).map((x) => x.slug)),
    ...tax.tracks.flatMap((t: Pages) => [t.id, ...(t.pages ?? []).map((x) => x.slug)]),
  ];
  const p = shapeProblems(shapes, {
    techniques,
    recipes: tax.recipes.map((r: { slug: string }) => r.slug),
    teardowns: tax.teardowns.first.map((t: { slug: string }) => t.slug),
  });
  assert.deepEqual(p, { unknownTechniques: [], unknownRecipes: [], unknownTeardowns: [], recipesWithNoShape: [], duplicateIds: [] });
  for (const s of shapes) {
    assert.ok(s.usual_level >= 0 && s.usual_level <= 7, s.id);
    assert.ok(s.elsewhere.length >= 3, `${s.id} should name jobs from at least three other fields`);
    assert.ok(s.signals.length >= 2, s.id);
  }
});
