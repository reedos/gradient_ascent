import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { conceptDiagrams, conceptEdges, conceptLayout } from '../src/lib/concept-diagrams.ts';
import { concreteNames, practiceExamples } from '../src/lib/concept-examples.ts';
import type { NamedEntry } from '../src/lib/content.ts';

const taxonomy = JSON.parse(readFileSync(new URL('../../content/taxonomy.json', import.meta.url), 'utf8'));
const slugs = [
  ...taxonomy.tiers.flatMap((t: { pages: { slug: string }[] }) => t.pages.map(p => p.slug)),
  ...taxonomy.tracks.flatMap((t: { id: string; pages: { slug: string }[] }) => [t.id, ...t.pages.map(p => p.slug)]),
];

test('every concept reachable from the taxonomy has an illustration and a practical example', () => {
  assert.deepEqual(Object.keys(conceptDiagrams).sort(), [...slugs].sort());
  assert.deepEqual(Object.keys(practiceExamples).sort(), [...slugs].sort());
  for (const slug of slugs) {
    const d = conceptDiagrams[slug];
    for (const mobile of [false, true]) {
      const layout = conceptLayout(d, mobile);
      for (const n of layout.nodes) {
        assert.ok(n.x >= 0 && n.y >= 0 && n.x + n.width <= layout.width && n.y + n.height <= layout.height, `${slug} node outside canvas`);
      }
    }
    const edges = conceptEdges(d.shape, d.nodes.length);
    for (const e of edges) assert.ok(d.nodes[e.from] && d.nodes[e.to], `${slug} broken connection`);
    assert.equal(new Set(edges.flatMap(e => [e.from, e.to])).size, d.nodes.length, `${slug} disconnected node`);
  }
});

test('RAG combines sources with the question before generating the cited answer', () => {
  assert.deepEqual(conceptEdges(conceptDiagrams.rag.shape, 5), [
    { from: 0, to: 2 }, { from: 1, to: 2 }, { from: 2, to: 3 }, { from: 3, to: 4 },
  ]);
});

test('example selection retains all current verified names, prioritizes mainstays, and does not mutate the registry', () => {
  const entry = (id: string, overrides = {}): NamedEntry => ({id, name: id, kind: 'tool', maker: 'Maker', category: 'framework', demonstrates: ['agent-harness'], source: 'https://example.com', checked: '2026-09-19', verified: true, ...overrides});
  const input = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'claude-agent-sdk', 'deep-agents'].map(id => entry(id));
  input.push(entry('unchecked', {verified: false}), entry('retired', {retirement: 'Retired'}));
  const original = structuredClone(input);
  const selected = concreteNames('agent-harness', input);
  assert.equal(selected.length, 9);
  assert.equal(selected[0].id, 'claude-agent-sdk');
  assert.equal(selected[1].id, 'deep-agents');
  assert.ok(selected[0].explanation);
  assert.deepEqual(input, original);
});
