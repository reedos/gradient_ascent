// Unit tests for src/lib/frontier.ts, which reads content/frontier.json and renders the frontier
// block's Markdown twin. Synthetic fixtures for the rendering rules; the shape of the real file
// is asserted in tests/test_frontier.py, on the Python side, where the rest of the content rules
// live. Run: npm test (in site/).
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  frontierAsOf,
  frontierFor,
  frontierIsStale,
  frontierLevels,
  frontierMarkdown,
  type FrontierLevel,
} from '../src/lib/frontier.ts';

const fixture: FrontierLevel = {
  order: 9,
  as_of: '2026-09-19',
  open: [
    {
      id: 'a',
      technique: 'chat',
      problem: 'Nobody can tell whether the answer is right without checking it.',
      trying: 'Scoring against a set of questions somebody already knows the answer to.',
      sources: [
        {
          title: 'A Paper',
          url: 'https://example.org/p',
          publisher: 'Example',
          quote: 'this remains unsolved',
          checked: '2026-09-19',
        },
      ],
    },
  ],
};

test('the markdown twin carries the as_of, the problem, what is tried and the quotation', () => {
  const md = frontierMarkdown(fixture);
  assert.match(md, /## What is still unsolved at this level/);
  assert.match(md, /As of 09\/19\/2026/);
  assert.match(md, /Nobody can tell whether the answer is right/);
  // The heading names the page the problem belongs to. A 250-character problem statement makes a
  // terrible heading, which is what it was before.
  assert.match(md, /### chat\n/);
  assert.match(md, /\*\*What people are trying:\*\* Scoring against a set/);
  assert.match(md, /\[A Paper\]\(https:\/\/example\.org\/p\)/);
  assert.match(md, /read 09\/19\/2026: "this remains unsolved"/);
});

test('the heading prefers the page title, falls back to the slug, then to a plain label', () => {
  assert.match(frontierMarkdown(fixture, (s) => (s === 'chat' ? 'One call, one answer' : undefined)), /### One call, one answer\n/);
  const noTechnique: FrontierLevel = { ...fixture, open: [{ ...fixture.open[0], technique: undefined }] };
  assert.match(frontierMarkdown(noTechnique), /### Open problem\n/);
});

test('a source note is rendered under its source, indented', () => {
  const withNote: FrontierLevel = {
    ...fixture,
    open: [{ ...fixture.open[0], sources: [{ ...fixture.open[0].sources[0], note: 'They call it something else.' }] }],
  };
  assert.match(frontierMarkdown(withNote), /\n {2}- They call it something else\./);
});

test('no block and an empty block both render nothing, so a caller can concatenate blind', () => {
  assert.equal(frontierMarkdown(undefined), '');
  assert.equal(frontierMarkdown({ order: 9, as_of: '2026-09-19', open: [] }), '');
});

test('frontierFor drops an entry with no source rather than print an unsupported claim', () => {
  // The real file has none; this pins the behavior for the day somebody adds one.
  const level = frontierFor(0);
  assert.ok(level, 'level 0 has a block');
  for (const entry of level!.open) assert.ok(entry.sources.length > 0, entry.id);
});

test('every level with a block is one of the eight, and they come back in level order', () => {
  const orders = frontierLevels.map((l) => l.order);
  assert.deepEqual(orders, [...orders].sort((a, b) => a - b));
  for (const o of orders) assert.ok(o >= 0 && o <= 7, `level ${o} is on the ladder`);
  assert.equal(new Set(orders).size, orders.length, 'no level appears twice');
});

test('a level with no block comes back undefined, not an empty section', () => {
  assert.equal(frontierFor(42), undefined);
});

test('staleness is measured against a date handed in, so a build is reproducible', () => {
  assert.equal(frontierIsStale('2026-09-19', '2026-11-01'), false);
  assert.equal(frontierIsStale('2026-09-19', '2026-12-19'), true);
  assert.equal(frontierIsStale('2026-09-19', '2026-12-18', 365), false);
  // A date that will not parse is never called stale: a bad field is a content defect for the
  // Python test to catch, not a reason to print a warning at a reader.
  assert.equal(frontierIsStale('not-a-date', '2026-12-19'), false);
});

test('the file records the date it was last worked on', () => {
  assert.match(frontierAsOf, /^\d{4}-\d{2}-\d{2}$/);
});
