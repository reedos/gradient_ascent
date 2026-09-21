// Unit tests for src/lib/capability.ts, the shaping behind the capability chart on /timeline/.
// Synthetic points only, plus one test that the real snapshot is well formed and credited.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { frontier, frontierAt, frontierChange, frontierPath, labeledFrontier, makeScale, sx, sy, yearOf, type CapabilityPoint } from '../src/lib/capability.ts';

const p = (name: string, date: string, eci: number): CapabilityPoint => ({ name, org: 'Lab', date, eci, lo: null, hi: null, open: false });
const pts = [p('a', '2023-01-10', 100), p('b', '2023-06-01', 90), p('c', '2023-06-01', 120), p('d', '2024-02-01', 118), p('e', '2024-09-12', 135), p('f', '2025-03-01', 150)];

test('yearOf is a decimal year with day precision', () => {
  assert.equal(yearOf('2024-01-01'), 2024);
  assert.ok(Math.abs(yearOf('2024-07-02') - 2024.5) < 0.01);
});

test('the frontier keeps only models that set a new high, in date order', () => {
  assert.deepEqual(frontier(pts).map((x) => x.name), ['a', 'c', 'e', 'f']);
});

test('models released on the same day yield one record, the best of that day', () => {
  const family = [p('small', '2023-02-24', 96), p('mid', '2023-02-24', 104), p('big', '2023-02-24', 110), p('next', '2023-03-14', 126)];
  assert.deepEqual(frontier(family).map((x) => x.name), ['big', 'next']);
});

test('frontierAt is the best score on or before a date, and null before the data starts', () => {
  const f = frontier(pts);
  assert.equal(frontierAt(f, '2022-12-31'), null);
  assert.equal(frontierAt(f, '2023-06-01'), 120);
  assert.equal(frontierAt(f, '2024-09-11'), 120);
  assert.equal(frontierAt(f, '2024-09-12'), 135);
});

test('frontierChange subtracts two frontier values and counts whole months', () => {
  const c = frontierChange(frontier(pts), '2023-06-01', '2024-09-11')!;
  assert.deepEqual([c.from, c.to, c.points, c.months], [120, 120, 0, 15]);
  assert.equal(frontierChange(frontier(pts), '2020-01-01', '2024-01-01'), null);
});

test('the scale rounds the score axis out to twenties and maps corners to the plot box', () => {
  const s = makeScale(pts, { startISO: '2023-01-01', endISO: '2026-01-01', width: 1000, height: 400, pad: { l: 40, r: 20, t: 10, b: 50 } });
  assert.deepEqual([s.y0, s.y1], [80, 160]);
  assert.equal(sx(s, 2023), 40);
  assert.equal(sx(s, 2026), 980);
  assert.equal(sy(s, 80), 350);
  assert.equal(sy(s, 160), 10);
});

test('the frontier path is a step line that runs to the end date', () => {
  const s = makeScale(pts, { startISO: '2023-01-01', endISO: '2026-01-01', width: 1000, height: 400, pad: { l: 40, r: 20, t: 10, b: 50 } });
  const d = frontierPath(s, frontier(pts), '2026-01-01');
  assert.match(d, /^M[\d.]+ [\d.]+(H[\d.]+V[\d.]+){3}H980$/);
  assert.equal(frontierPath(s, [], '2026-01-01'), '');
});

test('frontier names thin out by spacing but always keep the first and the last', () => {
  const s = makeScale(pts, { startISO: '2023-01-01', endISO: '2026-01-01', width: 1000, height: 400, pad: { l: 40, r: 20, t: 10, b: 50 } });
  const f = frontier(pts);
  const tight = labeledFrontier(s, f, 10_000).map((x) => x.name);
  assert.deepEqual(tight, ['a', 'f']);
  assert.deepEqual(labeledFrontier(s, f, 1).map((x) => x.name), ['a', 'c', 'e', 'f']);
});

test('the real snapshot is well formed, dated and credited', () => {
  const file = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'content', 'capability.json');
  const snap = JSON.parse(readFileSync(file, 'utf8'));
  assert.match(snap.retrieved, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(snap.source.license, 'CC BY 4.0');
  assert.ok(snap.source.url.startsWith('https://epoch.ai/'));
  assert.ok(snap.points.length > 100);
  for (const pt of snap.points) {
    assert.match(pt.date, /^\d{4}-\d{2}-\d{2}$/, pt.name);
    assert.equal(typeof pt.eci, 'number');
    assert.ok(pt.name.length > 0);
  }
  assert.ok(frontier(snap.points).length >= 5);
});

test('priority callouts preserve genuine records even near the latest label, without promoting other models', () => {
  const points = [p('first', '2023-01-01', 100), p('ordinary', '2024-01-01', 120), p('priority', '2024-01-02', 130), p('not a record', '2024-01-03', 125), p('latest', '2024-01-04', 140)];
  const s = makeScale(points, {startISO:'2023-01-01', endISO:'2024-02-01', width:440, height:370, pad:{l:38,r:14,t:36,b:78}});
  const named = labeledFrontier(s, frontier(points), 125, ['priority', 'not a record']);
  assert.deepEqual(named.map(p => p.name), ['first', 'priority', 'latest']);
});
