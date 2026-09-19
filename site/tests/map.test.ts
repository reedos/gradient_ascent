// Unit tests for src/lib/map.ts: the /map/ page's build-time layout. Run: npm test (in site/),
// which is `node --test tests/*.test.ts` -- Node strips the types and, since map.ts imports
// content/taxonomy.json with an explicit `type: json` attribute, resolves that import natively
// with no bundler (see the comment at the top of map.ts for why that attribute has to be there).
//
// Most tests build a small synthetic taxonomy fixture rather than depend on the shape of the
// real, evolving content/taxonomy.json -- computeMapLayout takes its data as a parameter for
// exactly this reason. A handful of tests at the bottom check invariants against the real data
// without hard-coding any slug, title or count from it.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeMapLayout,
  edgesByBand,
  computeEdgeGeometry,
  edgePathD,
  taxonomy as realTaxonomy,
  mapLayout as realLayout,
  NODE_H,
  PAD_X,
  CANVAS_LEVEL_W,
  MAX_GAP,
  COL_GAP,
  TOPICS_ROW_MARGIN,
  type MapTaxonomyIn,
  type MapNode,
} from '../src/lib/map.ts';

// -- Fixture ----------------------------------------------------------------------------------------

function fixture(): MapTaxonomyIn {
  return {
    tiers: [
      {
        order: 0,
        title: 'No model',
        pages: [{ slug: 'order-zero', title: 'When not to use a model', summary: 's', status: 'sourced' }],
      },
      {
        order: 1,
        title: 'One call',
        pages: [
          { slug: 'chat', title: 'Chat', summary: 's', status: 'sourced' },
          { slug: 'prompt-engineering', title: 'Prompt engineering', summary: 's', status: 'sourced' },
        ],
      },
      {
        order: 2,
        title: 'Context',
        pages: [{ slug: 'rag', title: 'Retrieval-augmented generation (RAG)', summary: 's', status: 'sourced' }],
      },
    ],
    tracks: [
      {
        id: 'evals',
        title: 'Evals',
        summary: 's',
        status: 'sourced',
        pages: [{ slug: 'eval-frameworks', title: 'Evaluation frameworks', summary: 's', status: 'sourced' }],
      },
      {
        id: 'safety',
        title: 'Safety, privacy and governance',
        summary: 's',
        status: 'sourced',
        pages: [
          { slug: 'guardrails', title: 'Guardrails', summary: 's', status: 'sourced' },
          { slug: 'red-teaming', title: 'Red teaming', summary: 's', status: 'sourced' },
        ],
      },
    ],
    tracks_overview: { title: 'Topics at every level' },
    relations: [
      { from: 'prompt-engineering', type: 'requires', to: 'chat' },
      { from: 'rag', type: 'requires', to: 'prompt-engineering' },
      { from: 'rag', type: 'upgrades_to', to: 'guardrails', when: 'answers need a safety check' },
      { from: 'chat', type: 'combines_with', to: 'guardrails' },
      { from: 'rag', type: 'alternative_to', to: 'eval-frameworks', question: 'do you need retrieval at all?' },
    ],
    relation_types: {
      requires: 'Read the target first.',
      upgrades_to: 'Climb to the target when this fails.',
      combines_with: 'Commonly used together.',
      alternative_to: 'Solves the same problem a different way.',
    },
  };
}

function rectsOverlap(a: { x: number; y: number; w: number; h: number }, b: { x: number; y: number; w: number; h: number }): boolean {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

// -- Every node placed once, inside its band --------------------------------------------------------

test('every page in the taxonomy gets exactly one node', () => {
  const layout = computeMapLayout(fixture());
  // 1 + 2 + 1 tier pages, plus 1 + 2 track pages, plus 2 track roots.
  assert.equal(layout.nodes.length, 1 + 2 + 1 + 1 + 2 + 2);
  const slugs = layout.nodes.map((n) => n.slug);
  assert.equal(new Set(slugs).size, slugs.length, 'no slug appears twice');
});

test('every node sits inside the vertical span of the band it claims', () => {
  const layout = computeMapLayout(fixture());
  const bandByIndex = new Map(layout.bands.map((b) => [b.index, b]));
  for (const node of layout.nodes) {
    const band = bandByIndex.get(node.band);
    assert.ok(band, `node ${node.slug} claims band ${node.band}, which does not exist`);
    // band.y/h is the band's whole visual slot; the node sits somewhere inside it, not
    // necessarily flush with the top -- a level band centers its one row (PAD_Y down), and the
    // topics band holds several rows stacked inside its own, taller slot.
    assert.ok(node.y >= band!.y && node.y + node.h <= band!.y + band!.h, `node ${node.slug} spills outside band ${node.band}`);
  }
});

test('level bands run top to bottom from level 7 to level 0, topics last', () => {
  const layout = computeMapLayout(fixture());
  const levelBands = layout.bands.filter((b) => b.kind === 'level');
  const orders = levelBands.map((b) => b.level);
  assert.deepEqual(orders, [...orders].sort((a, b) => (b as number) - (a as number)), 'level bands must be descending by order');
  assert.equal(orders[orders.length - 1], Math.min(...(orders as number[])), 'the lowest level is the last level band');
  const topicsBand = layout.bands.find((b) => b.kind === 'topics')!;
  assert.ok(topicsBand.index > Math.max(...levelBands.map((b) => b.index)), 'the topics band is drawn below every level band');
});

test('level bands are exactly ROW_GAP apart and the topics band starts right after the last one', () => {
  const layout = computeMapLayout(fixture());
  const levelBands = layout.bands.filter((b) => b.kind === 'level').sort((a, b) => a.index - b.index);
  for (let i = 0; i < levelBands.length; i++) {
    assert.equal(levelBands[i].y, i * levelBands[i].h);
  }
  const topics = layout.bands.find((b) => b.kind === 'topics')!;
  const lastLevel = levelBands[levelBands.length - 1];
  assert.equal(topics.y, lastLevel.y + lastLevel.h);
});

// -- Topics band: wrapped rows, one per track, not one long row ------------------------------------

test('the topics band has exactly one row per track, root page first then its own sub-pages', () => {
  const layout = computeMapLayout(fixture());
  const topicsBand = layout.bands.find((b) => b.kind === 'topics')!;
  assert.equal(topicsBand.rows, 2, 'two tracks in the fixture');

  const topicNodes = layout.nodes.filter((n) => n.level === 'tracks');
  const rows = new Set(topicNodes.map((n) => n.row));
  assert.equal(rows.size, 2, 'every topic node should land in one of two rows');

  const evalsRow = topicNodes.filter((n) => n.group === 'evals').sort((a, b) => a.col - b.col);
  assert.deepEqual(
    evalsRow.map((n) => n.slug),
    ['evals', 'eval-frameworks'],
    'the root comes first, then its sub-pages, in taxonomy order',
  );
  const safetyRow = topicNodes.filter((n) => n.group === 'safety').sort((a, b) => a.col - b.col);
  assert.deepEqual(safetyRow.map((n) => n.slug), ['safety', 'guardrails', 'red-teaming']);

  // Each track's own nodes share one row and no other track's nodes share it.
  const evalsRows = new Set(evalsRow.map((n) => n.row));
  const safetyRows = new Set(safetyRow.map((n) => n.row));
  assert.equal(evalsRows.size, 1);
  assert.equal(safetyRows.size, 1);
  assert.notEqual([...evalsRows][0], [...safetyRows][0]);
});

test('a topics row is left-aligned at the margin, not stretched or centered', () => {
  const layout = computeMapLayout(fixture());
  const safetyRow = layout.nodes.filter((n) => n.group === 'safety').sort((a, b) => a.col - b.col);
  assert.equal(safetyRow[0].x, PAD_X);
  for (let i = 0; i < safetyRow.length - 1; i++) {
    assert.equal(safetyRow[i + 1].x, safetyRow[i].x + safetyRow[i].w + COL_GAP, 'consecutive topic-row nodes sit exactly one COL_GAP apart');
  }
});

// -- No two nodes overlap -----------------------------------------------------------------------

test('no two nodes overlap, in the fixture', () => {
  const layout = computeMapLayout(fixture());
  for (let i = 0; i < layout.nodes.length; i++) {
    for (let j = i + 1; j < layout.nodes.length; j++) {
      assert.ok(!rectsOverlap(layout.nodes[i], layout.nodes[j]), `${layout.nodes[i].slug} overlaps ${layout.nodes[j].slug}`);
    }
  }
});

test('no two nodes overlap, on the real taxonomy', () => {
  for (let i = 0; i < realLayout.nodes.length; i++) {
    for (let j = i + 1; j < realLayout.nodes.length; j++) {
      assert.ok(!rectsOverlap(realLayout.nodes[i], realLayout.nodes[j]), `${realLayout.nodes[i].slug} overlaps ${realLayout.nodes[j].slug}`);
    }
  }
});

test('same-band nodes never overlap even when adjacent titles are long', () => {
  const tax = fixture();
  tax.tiers[0].pages = [
    { slug: 'a', title: 'A very long title indeed, much longer than most', summary: 's', status: 'sourced' },
    { slug: 'b', title: 'Another quite long title that also runs on', summary: 's', status: 'sourced' },
  ];
  const layout = computeMapLayout(tax);
  const a = layout.nodes.find((n) => n.slug === 'a')!;
  const b = layout.nodes.find((n) => n.slug === 'b')!;
  assert.ok(!rectsOverlap(a, b));
  assert.ok(a.x + a.w <= b.x || b.x + b.w <= a.x, 'wide neighbors must not be pushed into each other');
});

// -- Every edge endpoint resolves -----------------------------------------------------------------

test('every edge in the layout has both endpoints among the nodes', () => {
  const layout = computeMapLayout(fixture());
  const slugs = new Set(layout.nodes.map((n) => n.slug));
  assert.ok(layout.edges.length > 0);
  for (const edge of layout.edges) {
    assert.ok(slugs.has(edge.from), `edge ${edge.key} has an unresolved "from": ${edge.from}`);
    assert.ok(slugs.has(edge.to), `edge ${edge.key} has an unresolved "to": ${edge.to}`);
  }
});

test('a relation whose endpoint is not on the map is dropped, not drawn to nowhere', () => {
  const tax = fixture();
  tax.relations.push({ from: 'chat', type: 'requires', to: 'nonexistent-slug' });
  const layout = computeMapLayout(tax);
  assert.ok(layout.edges.every((e) => e.to !== 'nonexistent-slug'));
});

test('every edge endpoint resolves, on the real taxonomy', () => {
  const slugs = new Set(realLayout.nodes.map((n) => n.slug));
  assert.equal(realLayout.edges.length, realTaxonomy.relations.length, 'every real relation should resolve to a drawn edge');
  for (const edge of realLayout.edges) {
    assert.ok(slugs.has(edge.from));
    assert.ok(slugs.has(edge.to));
  }
});

// -- Deterministic output -----------------------------------------------------------------------

test('computeMapLayout is deterministic: same input, same output, every time', () => {
  const a = computeMapLayout(fixture());
  const b = computeMapLayout(fixture());
  assert.deepEqual(a, b);
  const c = computeMapLayout(fixture());
  assert.deepEqual(JSON.stringify(a), JSON.stringify(c));
});

// -- Level-band width: fixed at CANVAS_LEVEL_W, never grown by the topics band ---------------------

test('the canvas width is fixed at CANVAS_LEVEL_W regardless of the topics band', () => {
  const tax = fixture();
  // Give one track a few more sub-pages, comfortably realistic in count and title length (the
  // real taxonomy's widest track, "operator-craft", has a root plus four sub-pages) -- if the
  // topics band could still widen the canvas, this would grow it. It must not.
  tax.tracks[1].pages = [
    ...(tax.tracks[1].pages ?? []),
    { slug: 'extra-1', title: 'A third sub-page', summary: 's', status: 'sourced' },
    { slug: 'extra-2', title: 'A fourth sub-page here', summary: 's', status: 'sourced' },
  ];
  const layout = computeMapLayout(tax);
  assert.equal(layout.width, CANVAS_LEVEL_W);
});

test('a lone node (level 0) sits at the left margin', () => {
  const layout = computeMapLayout(fixture());
  const orderZero = layout.nodes.find((n) => n.slug === 'order-zero')!;
  assert.equal(orderZero.x, PAD_X);
});

test('a lone node aligns with the first node of a band that is not capped-and-centered', () => {
  // "aligned with the first node of the other bands": true of any band that reaches the cap (or
  // needs the full width outright) -- those start at PAD_X too, by construction. Build one here
  // (six nodes wide enough to need the width) alongside the fixture's single-node level 0.
  const tax = fixture();
  tax.tiers[1].pages = Array.from({ length: 6 }, (_, i) => ({ slug: `p${i}`, title: 'Structured output', summary: 's', status: 'sourced' as const }));
  const layout = computeMapLayout(tax);
  const orderZero = layout.nodes.find((n) => n.slug === 'order-zero')!;
  const level1First = layout.nodes.filter((n) => n.level === 1).sort((a, b) => a.col - b.col)[0];
  assert.equal(orderZero.x, level1First.x);
});

test('a sparse level band is centered with a gap capped at MAX_GAP, not stretched edge to edge', () => {
  const layout = computeMapLayout(fixture());
  const level1 = layout.nodes.filter((n) => n.level === 1).sort((a, b) => a.col - b.col);
  assert.equal(level1.length, 2);
  const gap = level1[1].x - (level1[0].x + level1[0].w);
  assert.ok(gap <= MAX_GAP + 0.01, `gap ${gap} exceeds MAX_GAP ${MAX_GAP}`);
  // Two short pages ("Chat", "Prompt engineering") in a 1100px-available canvas cannot possibly
  // need the full width even at the cap, so the pair should not reach the right margin.
  assert.ok(level1[1].x + level1[1].w < CANVAS_LEVEL_W - PAD_X - 1, 'a two-node band should not stretch to the right margin');
  // And it should be centered: roughly equal space on both sides of the (capped) group.
  const leftGap = level1[0].x - PAD_X;
  const rightGap = CANVAS_LEVEL_W - PAD_X - (level1[1].x + level1[1].w);
  assert.ok(Math.abs(leftGap - rightGap) < 1, `expected a centered group, left=${leftGap} right=${rightGap}`);
});

test('a band with enough nodes to need the full width is not capped, and reaches the right margin', () => {
  // Six pages titled like real technique names (not four-letter "Chat"s): six of these are wide
  // enough that even at MAX_GAP between each, they still need the full available width.
  const tax = fixture();
  tax.tiers[1].pages = Array.from({ length: 6 }, (_, i) => ({ slug: `p${i}`, title: 'Structured output', summary: 's', status: 'sourced' as const }));
  const layout = computeMapLayout(tax);
  const nodes = layout.nodes.filter((n) => n.level === 1).sort((a, b) => a.col - b.col);
  const last = nodes[nodes.length - 1];
  const gap = nodes[1].x - (nodes[0].x + nodes[0].w);
  assert.ok(gap < MAX_GAP - 0.01, `expected an uncapped gap (${gap}) below MAX_GAP (${MAX_GAP}) for this test to mean anything`);
  assert.ok(Math.abs(last.x + last.w - (CANVAS_LEVEL_W - PAD_X)) < 1, `expected the group to reach the right margin, stopped at ${last.x + last.w}`);
});

test('no inter-node gap within a level band ever exceeds MAX_GAP', () => {
  const layout = computeMapLayout(fixture());
  for (const band of layout.bands.filter((b) => b.kind === 'level')) {
    const nodes = layout.nodes.filter((n) => n.band === band.index).sort((a, b) => a.col - b.col);
    for (let i = 0; i < nodes.length - 1; i++) {
      const gap = nodes[i + 1].x - (nodes[i].x + nodes[i].w);
      assert.ok(gap <= MAX_GAP + 0.01, `band ${band.index}: gap ${gap} between ${nodes[i].slug} and ${nodes[i + 1].slug} exceeds MAX_GAP`);
    }
  }
});

// -- Bottom-up reordering: a level band's nodes are ordered by their neighbors below --------------

test('orderByBelow (via computeMapLayout) swaps two nodes to match their neighbors below', () => {
  const tax = fixture();
  // Level 0 gets three nodes, left to right: a-first, m-mid, z-last. Level 1 starts as
  // [chat, prompt-engineering] in that order; give BOTH a requires-relation below, pointing the
  // opposite way from their starting order ("chat" -> the rightmost level-0 page, "prompt-
  // engineering" -> the leftmost) so the expected swap does not depend on the fallback score any
  // unscored item would otherwise get.
  tax.tiers[0].pages = [
    { slug: 'a-first', title: 'A', summary: 's', status: 'sourced' },
    { slug: 'm-mid', title: 'M', summary: 's', status: 'sourced' },
    { slug: 'z-last', title: 'Z', summary: 's', status: 'sourced' },
  ];
  tax.relations.push({ from: 'chat', type: 'requires', to: 'z-last' }, { from: 'prompt-engineering', type: 'requires', to: 'a-first' });
  const layout = computeMapLayout(tax);
  const level1 = layout.nodes.filter((n) => n.level === 1).sort((a, b) => a.col - b.col);
  // "chat" points at the RIGHTMOST level-0 page and "prompt-engineering" at the LEFTMOST, so
  // after reordering, prompt-engineering should be level 1's leftmost node and chat its rightmost
  // -- the reverse of the order they started in.
  assert.deepEqual(
    level1.map((n) => n.slug),
    ['prompt-engineering', 'chat'],
  );
});

test('orderByBelow leaves an unscored item roughly in its original position, not collapsed to one end', () => {
  const tax = fixture();
  tax.tiers[0].pages = [{ slug: 'only-below', title: 'Only', summary: 's', status: 'sourced' }];
  tax.tiers[1].pages = [
    { slug: 'unscored-1', title: 'Unscored one', summary: 's', status: 'sourced' },
    { slug: 'scored', title: 'Scored', summary: 's', status: 'sourced' },
    { slug: 'unscored-2', title: 'Unscored two', summary: 's', status: 'sourced' },
  ];
  tax.relations.push({ from: 'scored', type: 'requires', to: 'only-below' });
  const layout = computeMapLayout(tax);
  const level1 = layout.nodes.filter((n) => n.level === 1).sort((a, b) => a.col - b.col);
  // Nothing pulls "unscored-1" or "unscored-2" anywhere in particular, so they should keep their
  // original relative order around "scored" rather than both landing on the same side of it.
  const order = level1.map((n) => n.slug);
  assert.ok(order.indexOf('unscored-1') < order.indexOf('unscored-2'), `expected unscored-1 before unscored-2, got ${order}`);
});

test('orderByBelow only looks at the band directly below, not two bands down', () => {
  // A "requires" edge from level 2 straight to level 0 (skipping level 1) must not move anything
  // in level 1 -- computeMapLayout should still be deterministic and non-overlapping either way,
  // but the level-1 order should be unaffected by a relation that does not touch it.
  const tax = fixture();
  const before = computeMapLayout(fixture()).nodes.filter((n) => n.level === 1).map((n) => n.slug);
  tax.relations.push({ from: 'rag', type: 'requires', to: 'order-zero' }); // level 2 -> level 0, skips level 1
  const after = computeMapLayout(tax).nodes.filter((n) => n.level === 1).map((n) => n.slug);
  assert.deepEqual(before, after);
});

// -- edgesByBand: the data behind the plain-text edge list ----------------------------------------

test('edgesByBand groups every edge under the band its "from" node belongs to', () => {
  const layout = computeMapLayout(fixture());
  const grouped = edgesByBand(layout);
  const total = grouped.reduce((sum, g) => sum + g.edges.length, 0);
  assert.equal(total, layout.edges.length, 'every edge appears in exactly one band group');
  for (const { band, edges } of grouped) {
    for (const edge of edges) {
      assert.equal(edge.fromNode.band, band.index);
      assert.equal(edge.toNode.slug, edge.to);
    }
  }
});

test('edgesByBand carries the "when" and "question" text through unchanged', () => {
  const layout = computeMapLayout(fixture());
  const grouped = edgesByBand(layout);
  const upgrade = grouped.flatMap((g) => g.edges).find((e) => e.type === 'upgrades_to')!;
  assert.equal(upgrade.when, 'answers need a safety check');
  const alt = grouped.flatMap((g) => g.edges).find((e) => e.type === 'alternative_to')!;
  assert.equal(alt.question, 'do you need retrieval at all?');
});

// -- Same-row edges arc clear of whatever sits between their endpoints -----------------------------

test('an edge between two different rows keeps the midpoint-control-point curve and is never "arced"', () => {
  const layout = computeMapLayout(fixture());
  const bySlug = new Map(layout.nodes.map((n) => [n.slug, n]));
  const rag = bySlug.get('rag')!; // level 2
  const promptEng = bySlug.get('prompt-engineering')!; // level 1
  const g = computeEdgeGeometry(rag, promptEng, []);
  assert.equal(g.arcsOverIntervening, false);
  const my = (g.y1 + g.y2) / 2;
  assert.equal(g.c1y, my);
  assert.equal(g.c2y, my);
});

test('a same-row edge between neighbors, with nothing between them, does not arc', () => {
  const layout = computeMapLayout(fixture());
  const level1 = layout.nodes.filter((n) => n.level === 1).sort((a, b) => a.col - b.col);
  const rowNodes = layout.nodes.filter((n) => n.y === level1[0].y);
  const g = computeEdgeGeometry(level1[0], level1[1], rowNodes);
  assert.equal(g.arcsOverIntervening, false);
});

test('a same-row edge between non-adjacent nodes arcs clear of the node between them, not through it', () => {
  const tax = fixture();
  tax.tiers[1].pages.push({ slug: 'third', title: 'A third page', summary: 's', status: 'sourced' });
  const layout = computeMapLayout(tax);
  const level1 = layout.nodes.filter((n) => n.level === 1).sort((a, b) => a.col - b.col);
  assert.equal(level1.length, 3);
  const [first, middle, last] = level1;
  const rowNodes = layout.nodes.filter((n) => n.y === first.y);

  const g = computeEdgeGeometry(first, last, rowNodes);
  assert.equal(g.arcsOverIntervening, true, 'a node sits between "first" and "last"; the edge must know that');
  assert.ok(g.y1 - g.c1y > NODE_H / 2, `control point 1 only clears ${g.y1 - g.c1y}px, need more than ${NODE_H / 2}`);
  assert.ok(g.y2 - g.c2y > NODE_H / 2, `control point 2 only clears ${g.y2 - g.c2y}px, need more than ${NODE_H / 2}`);
  const neighbourGeometry = computeEdgeGeometry(first, middle, rowNodes);
  assert.ok(g.y1 - g.c1y > g.y1 - neighbourGeometry.c1y, 'a non-adjacent arc should rise higher than an adjacent one');

  const midX = middle.x + middle.w / 2;
  assert.ok(midX > first.x + first.w / 2 && midX < last.x + last.w / 2);
});

test('two topics-band nodes in different rows are treated as different rows, not "same band"', () => {
  const layout = computeMapLayout(fixture());
  const evalsRoot = layout.nodes.find((n) => n.slug === 'evals')!;
  const safetyRoot = layout.nodes.find((n) => n.slug === 'safety')!;
  assert.equal(evalsRoot.band, safetyRoot.band, 'both are in the topics band');
  assert.notEqual(evalsRoot.row, safetyRoot.row, 'but in different rows');
  const g = computeEdgeGeometry(evalsRoot, safetyRoot, []);
  assert.equal(g.arcsOverIntervening, false, 'different rows: must use the between-rows curve, not arc as if same-row');
});

test('a same-row arc inside a topics row never rises high enough to reach the row above it', () => {
  const layout = computeMapLayout(fixture());
  const safetyRow = layout.nodes.filter((n) => n.group === 'safety').sort((a, b) => a.col - b.col);
  const g = computeEdgeGeometry(safetyRow[0], safetyRow[2], safetyRow); // non-adjacent: arcs the most
  // The node sits TOPICS_ROW_MARGIN below its own row's slot top; the arc must not rise past that
  // slot top, or it would reach into whatever sits in the row above (another topic's row, or the
  // last level band).
  const slotTop = safetyRow[0].y - TOPICS_ROW_MARGIN;
  assert.ok(g.c1y >= slotTop, `control point rose to ${g.c1y}, above this row's own slot top (${slotTop})`);
});

test('edgePathD renders a cubic bezier "d" string from an EdgeGeometry', () => {
  const g = { x1: 1, y1: 2, c1x: 3, c1y: 4, c2x: 5, c2y: 6, x2: 7, y2: 8, arcsOverIntervening: false };
  assert.equal(edgePathD(g), 'M1.0,2.0 C3.0,4.0 5.0,6.0 7.0,8.0');
});

test('on the real taxonomy, at least one same-row edge arcs over an intervening node', () => {
  // A concrete regression check for the bug this fixes: before, every same-row edge was a flat
  // line straight through whatever sat between its endpoints. Confirms the real data actually
  // exercises that path, without hard-coding which slugs.
  const bySlug = new Map(realLayout.nodes.map((n) => [n.slug, n]));
  const byRowY = new Map<number, MapNode[]>();
  for (const n of realLayout.nodes) byRowY.set(n.y, [...(byRowY.get(n.y) ?? []), n]);

  let arcedCount = 0;
  for (const e of realLayout.edges) {
    const from = bySlug.get(e.from)!;
    const to = bySlug.get(e.to)!;
    if (from.y !== to.y) continue;
    const g = computeEdgeGeometry(from, to, byRowY.get(from.y) ?? []);
    if (g.arcsOverIntervening) arcedCount++;
  }
  assert.ok(arcedCount > 0, 'expected at least one same-row relation with a node between its endpoints');
});

// -- Real-data invariants, without hard-coding any count from taxonomy.json -----------------------

test('the real layout has one node for every tier page and every track page (root and sub-page)', () => {
  const expected =
    realTaxonomy.tiers.reduce((sum, tier) => sum + tier.pages.length, 0) +
    realTaxonomy.tracks.reduce((sum, track) => sum + 1 + (track.pages?.length ?? 0), 0);
  assert.equal(realLayout.nodes.length, expected);
});

test('every real node has a positive width and the standard height', () => {
  for (const node of realLayout.nodes) {
    assert.ok(node.w > 0);
    assert.equal(node.h, NODE_H);
  }
});

test('the real layout width and height cover every node', () => {
  for (const node of realLayout.nodes) {
    assert.ok(node.x + node.w <= realLayout.width, `${node.slug} extends past the computed width`);
    assert.ok(node.y + node.h <= realLayout.height, `${node.slug} extends past the computed height`);
  }
});

// -- The coordinator's specific regression checks --------------------------------------------------

test('the real canvas width is fixed at CANVAS_LEVEL_W and stays at most 1150', () => {
  assert.equal(realLayout.width, CANVAS_LEVEL_W);
  assert.ok(realLayout.width <= 1150, `canvas width ${realLayout.width} exceeds 1150`);
});

test('the real topics band has exactly one row per track', () => {
  const topicsBand = realLayout.bands.find((b) => b.kind === 'topics')!;
  assert.equal(topicsBand.rows, realTaxonomy.tracks.length);
  const rows = new Set(realLayout.nodes.filter((n) => n.level === 'tracks').map((n) => n.row));
  assert.equal(rows.size, realTaxonomy.tracks.length);
});

test('every real node\'s right edge is inside the canvas', () => {
  for (const node of realLayout.nodes) {
    assert.ok(node.x + node.w <= realLayout.width, `${node.slug}'s right edge (${node.x + node.w}) is past the canvas width (${realLayout.width})`);
  }
});
