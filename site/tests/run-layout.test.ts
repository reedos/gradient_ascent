import test from 'node:test';
import assert from 'node:assert/strict';
import harness from '../src/data/runs/agent-harness.json' with { type: 'json' };
import branches from '../src/data/runs/agent-teammates.json' with { type: 'json' };
import { responsiveRunLayouts } from '../src/lib/run-layout.ts';
import type { RunData } from '../src/components/islands/RunDiagram';

test('a linear run reflows without changing its steps, edges, labels, or source data', () => {
  const original = structuredClone(harness);
  const layouts = responsiveRunLayouts(harness as RunData)!;
  assert.ok(layouts.wide.h < 400);
  assert.ok(layouts.narrow.h < 600);
  for (const data of [layouts.wide, layouts.narrow]) {
    assert.deepEqual(data.edges, harness.edges);
    assert.deepEqual(data.steps, harness.steps);
    assert.deepEqual(data.nodes.map(({id,l,k}) => ({id,l,k})), harness.nodes.map(({id,l,k}) => ({id,l,k})));
    for (const n of data.nodes) assert.ok(n.y - 19 >= 0 && n.y + 19 < data.h);
    for (const [i, a] of data.nodes.entries()) for (const b of data.nodes.slice(i + 1)) {
      assert.ok(Math.abs(a.x - b.x) >= 150 || Math.abs(a.y - b.y) >= 60, 'nodes have clear separation');
    }
  }
  assert.deepEqual(harness, original);
});

test('branches, loops, and bent edges retain their authored geometry', () => {
  assert.equal(responsiveRunLayouts(branches as RunData), null);
  const loop = structuredClone(harness) as RunData;
  loop.edges.push({id:'loop',f:'stop',t:'act1',by:'code'});
  assert.equal(responsiveRunLayouts(loop), null);
  const bent = structuredClone(harness) as RunData;
  bent.edges[0].b = 40;
  assert.equal(responsiveRunLayouts(bent), null);
});
