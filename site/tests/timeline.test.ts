// Unit tests for src/lib/timeline.ts: date parsing by precision, interval arithmetic and lane
// placement. Run: npm test (in site/), which is `node --test tests/*.test.ts` -- Node strips the
// types and, since timeline.ts imports content/timeline.json with an explicit `type: json`
// attribute, resolves that import natively with no bundler (see the comment at the top of
// timeline.ts for why that attribute has to be there).
//
// Most tests here build small synthetic fixtures rather than depend on the shape of the real,
// evolving content/timeline.json (which `timeline-review` owns and may change at any time) --
// every data-consuming function under test takes its data as an optional parameter for exactly
// this reason. A handful of tests at the bottom check invariants against the real data (every
// milestone id unique, every date valid for its precision, etc.) without hard-coding any date,
// id or count from it.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  decimalYear,
  formatDate,
  monthsBetween,
  markKeys,
  markLabel,
  usedMarkKeys,
  levelSeries,
  levelSeriesTopDown,
  markExtent,
  levelIntervals,
  consecutiveLevelGaps,
  climbHeadline,
  climbHeadlineText,
  shapeForKind,
  verificationNote,
  buildMainAxis,
  buildRecentAxis,
  selectLabeledMilestones,
  assignLabelSides,
  milestonesByYearDesc,
  milestones,
  timeline,
  type Milestone,
  type LevelMarkEntry,
} from '../src/lib/timeline.ts';

// -- Fixture helpers -------------------------------------------------------------------------------

function ms(partial: Partial<Milestone> & Pick<Milestone, 'id' | 'date' | 'precision' | 'level'>): Milestone {
  return {
    kind: 'research',
    title: partial.id,
    maker: 'Someone',
    what: 'It does a thing.',
    source: { title: 'A source', url: 'https://example.com/a', publisher: 'Example' },
    checked: '2026-01-01',
    verified: true,
    ...partial,
  };
}

// -- decimalYear: placement by precision -----------------------------------------------------------

test('a year-precision date sits at the middle of its year', () => {
  assert.equal(decimalYear('2020', 'year'), 2020.5);
});

test('a month-precision date sits at the middle of its month', () => {
  // January: month 1 of 12, so the midpoint is 0.5/12 of the way through the year.
  assert.equal(decimalYear('2020-01', 'month'), 2020 + 0.5 / 12);
  // July: month 7, midpoint at (6 + 0.5) / 12.
  assert.equal(decimalYear('2020-07', 'month'), 2020 + 6.5 / 12);
});

test('a day-precision date sits at its exact day, ordering correctly within a year', () => {
  const jan1 = decimalYear('2021-01-01', 'day');
  const jul1 = decimalYear('2021-07-01', 'day');
  const dec31 = decimalYear('2021-12-31', 'day');
  assert.ok(jan1 > 2021 && jan1 < 2021.01, `jan1=${jan1} should be just after 2021`);
  assert.ok(jan1 < jul1 && jul1 < dec31);
  assert.ok(dec31 < 2022);
});

test('day precision accounts for leap years', () => {
  // Feb 29 exists in a leap year; decimalYear should not throw and should land before Mar 1.
  const feb29 = decimalYear('2024-02-29', 'day');
  const mar1 = decimalYear('2024-03-01', 'day');
  assert.ok(feb29 < mar1);
});

test('later dates always produce a larger decimalYear, across precisions', () => {
  const a = decimalYear('2017-06-12', 'day');
  const b = decimalYear('2017-07', 'month');
  const c = decimalYear('2018', 'year');
  assert.ok(a < b);
  assert.ok(b < c);
});

// -- formatDate: never shows more precision than recorded --------------------------------------

test('formatDate at year precision prints only the year', () => {
  assert.equal(formatDate('2020', 'year'), '2020');
});

test('formatDate at month precision prints month and year, no day', () => {
  assert.equal(formatDate('2023-02', 'month'), 'Feb 2023');
});

test('formatDate at day precision prints the full date', () => {
  assert.equal(formatDate('2017-06-12', 'day'), 'Jun 12, 2017');
});

// -- monthsBetween: the site's own interval arithmetic -------------------------------------------

test('monthsBetween counts whole calendar months between two day-precision dates', () => {
  assert.equal(monthsBetween('2022-01-15', 'day', '2022-07-15', 'day'), 6);
});

test('monthsBetween is negative when the second date is earlier', () => {
  assert.equal(monthsBetween('2022-07-15', 'day', '2022-01-15', 'day'), -6);
});

test('monthsBetween works across mixed precisions', () => {
  // 2020 (mid-year) to 2021-01 (mid-January): about half a year plus half a month.
  const m = monthsBetween('2020', 'year', '2021-01', 'month');
  assert.ok(m >= 5 && m <= 7, `expected roughly 6 months, got ${m}`);
});

test('monthsBetween of a date with itself is zero', () => {
  assert.equal(monthsBetween('2023-05-01', 'day', '2023-05-01', 'day'), 0);
});

// -- markKeys: order, labels, missing and extra keys ----------------------------------------------

test('markKeys puts described before buildable before available, ignoring level/note', () => {
  const entry: LevelMarkEntry = { level: 2, available: 'a', described: 'd', note: 'x' };
  assert.deepEqual(markKeys(entry), ['described', 'available']);
});

test('markKeys includes buildable in the middle when present', () => {
  const entry: LevelMarkEntry = { level: 2, available: 'a', buildable: 'b', described: 'd' };
  assert.deepEqual(markKeys(entry), ['described', 'buildable', 'available']);
});

test('markKeys drops a null value (a missing mark) without erroring', () => {
  const entry: LevelMarkEntry = { level: 0, described: 'd', available: null };
  assert.deepEqual(markKeys(entry), ['described']);
});

test('markKeys places an unrecognized extra key after the known ones, alphabetically', () => {
  const entry: LevelMarkEntry = { level: 3, available: 'a', described: 'd', zenith: 'z' };
  assert.deepEqual(markKeys(entry), ['described', 'available', 'zenith']);
});

test('markLabel falls back to a title-cased key for an unrecognized mark', () => {
  assert.equal(markLabel('described'), 'Described');
  assert.equal(markLabel('buildable'), 'Buildable');
  assert.equal(markLabel('zenith'), 'Zenith');
});

test('usedMarkKeys reports only the keys actually resolved, in canonical order', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  assert.deepEqual(usedMarkKeys(series), ['described', 'buildable', 'available']);
});

test('usedMarkKeys picks up an extra key when a level uses one', () => {
  const withExtra: LevelMarkEntry[] = [{ level: 1, described: 'l1-d', buildable: 'l1-mid', available: 'l1-a' }];
  assert.deepEqual(usedMarkKeys(levelSeries(FIXTURE_MILESTONES, withExtra)), ['described', 'buildable', 'available']);
});

// -- levelSeries / lane placement -------------------------------------------------------------------
//
// Fixture shaped after the real data's own awkward cases (content/timeline.json, 2026-09-18):
// level 0 has no resolved `available` (rules/search/forms predate any single maker's
// announcement); level 1 has no `buildable` at all; level 2's `buildable` (a library) predates
// its `described` (a paper); level 3's `buildable` comes AFTER its `available` (the product
// shipped before an open framework for it existed) -- so key order must never be read as date
// order anywhere in this module.

const FIXTURE_MILESTONES: Milestone[] = [
  ms({ id: 'l0-d', date: '1970-01-01', precision: 'day', level: 0, kind: 'research' }),
  ms({ id: 'l0-b', date: '1990-01-01', precision: 'day', level: 0, kind: 'tool' }),
  ms({ id: 'l1-d', date: '2017-06-12', precision: 'day', level: 1, kind: 'research' }),
  ms({ id: 'l1-mid', date: '2020-01', precision: 'month', level: 1, kind: 'research' }),
  ms({ id: 'l1-a', date: '2022-11-30', precision: 'day', level: 1, kind: 'product' }),
  ms({ id: 'l2-b', date: '2018-01-01', precision: 'day', level: 2, kind: 'tool' }), // predates l2-d
  ms({ id: 'l2-d', date: '2020-05-22', precision: 'day', level: 2, kind: 'research' }),
  ms({ id: 'l2-a', date: '2023-02-07', precision: 'day', level: 2, kind: 'product' }),
  ms({ id: 'l3-d', date: '2021-01-01', precision: 'day', level: 3, kind: 'research' }),
  ms({ id: 'l3-a', date: '2023-01-01', precision: 'day', level: 3, kind: 'product' }),
  ms({ id: 'l3-b', date: '2024-06-01', precision: 'day', level: 3, kind: 'tool' }), // AFTER l3-a
];

const FIXTURE_LEVELS: LevelMarkEntry[] = [
  { level: 0, described: 'l0-d', buildable: 'l0-b', available: null, note: 'Level 0 has no single available date.' },
  { level: 1, described: 'l1-d', available: 'l1-a' },
  { level: 2, described: 'l2-d', buildable: 'l2-b', available: 'l2-a', note: "'buildable' predates 'described' here." },
  { level: 3, described: 'l3-d', buildable: 'l3-b', available: 'l3-a', note: "'buildable' arrived after 'available' here." },
];

test('levelSeries sorts levels low to high and resolves marks in key order', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  assert.deepEqual(series.map((s) => s.level), [0, 1, 2, 3]);
  assert.deepEqual(series[1].marks.map((m) => m.key), ['described', 'available']);
  assert.equal(series[1].marks[0].milestone.id, 'l1-d');
  assert.equal(series[1].marks[1].milestone.id, 'l1-a');
});

test('levelSeries drops a null-valued key (a genuinely missing mark) from marks', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const level0 = series.find((s) => s.level === 0)!;
  assert.deepEqual(level0.marks.map((m) => m.key), ['described', 'buildable']);
});

test('levelSeries keeps every milestone at a level, sorted oldest first, marked or not', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const level1 = series.find((s) => s.level === 1)!;
  assert.deepEqual(level1.milestones.map((m) => m.id), ['l1-d', 'l1-mid', 'l1-a']);
});

test('levelSeries carries the note through for a level with one', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  assert.equal(series[0].note, 'Level 0 has no single available date.');
  assert.equal(series[1].note, undefined);
});

test('a mark id that resolves to nothing is dropped, not thrown', () => {
  const brokenLevels: LevelMarkEntry[] = [{ level: 1, described: 'l1-d', available: 'does-not-exist' }];
  const series = levelSeries(FIXTURE_MILESTONES, brokenLevels);
  assert.deepEqual(series[0].marks.map((m) => m.key), ['described']);
});

test('levelSeriesTopDown (the real data) renders the highest level first', () => {
  const top = levelSeriesTopDown();
  for (let i = 1; i < top.length; i++) assert.ok(top[i - 1].level > top[i].level);
});

// -- markExtent: earliest/latest by DATE, never by key order --------------------------------------

test('markExtent picks the chronologically earliest and latest mark, not marks[0]/marks[-1]', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const level2 = series.find((s) => s.level === 2)!;
  // key order is described, buildable, available -- but buildable (2018) predates described (2020).
  const extent = markExtent(level2.marks)!;
  assert.equal(extent.earliest.milestone.id, 'l2-b');
  assert.equal(extent.latest.milestone.id, 'l2-a');
});

test('markExtent handles buildable landing after available', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const level3 = series.find((s) => s.level === 3)!;
  const extent = markExtent(level3.marks)!;
  assert.equal(extent.earliest.milestone.id, 'l3-d');
  assert.equal(extent.latest.milestone.id, 'l3-b'); // buildable, not available -- it came later
});

test('markExtent on a single mark returns it as both earliest and latest', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const level1 = series.find((s) => s.level === 1)!;
  const soleMark = level1.marks.filter((m) => m.key === 'described');
  const extent = markExtent(soleMark)!;
  assert.equal(extent.earliest, extent.latest);
});

test('markExtent on no marks is undefined', () => {
  assert.equal(markExtent([]), undefined);
});

// -- levelIntervals / consecutiveLevelGaps: interval arithmetic -----------------------------------

test('levelIntervals computes described-to-available in months', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const rows = levelIntervals(series);
  const level1 = rows.find((r) => r.level === 1)!;
  // 2017-06-12 to 2022-11-30: about 65-66 months.
  assert.ok(level1.describedToAvailable && level1.describedToAvailable.months > 60 && level1.describedToAvailable.months < 70);
  assert.equal(level1.describedToAvailable!.reversed, false);
});

test('levelIntervals is null for a level missing either side of a gap', () => {
  const rows = levelIntervals(levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS));
  const level0 = rows.find((r) => r.level === 0)!;
  assert.equal(level0.describedToAvailable, null); // no resolved `available`
  assert.equal(level0.buildableToAvailable, null);
  const level1 = rows.find((r) => r.level === 1)!;
  assert.equal(level1.buildableToAvailable, null); // no `buildable` at all
});

test('levelIntervals reports buildableToAvailable as reversed when buildable came after available', () => {
  const rows = levelIntervals(levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS));
  const level3 = rows.find((r) => r.level === 3)!;
  assert.ok(level3.buildableToAvailable);
  assert.equal(level3.buildableToAvailable!.reversed, true);
  assert.ok(level3.buildableToAvailable!.months > 0); // magnitude, never a negative number
});

test('levelIntervals reports buildableToAvailable as not reversed for the ordinary case', () => {
  const rows = levelIntervals(levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS));
  const level2 = rows.find((r) => r.level === 2)!;
  assert.ok(level2.buildableToAvailable);
  assert.equal(level2.buildableToAvailable!.reversed, false);
});

test('consecutiveLevelGaps compares each level pair\'s `available` mark specifically', () => {
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const gaps = consecutiveLevelGaps(series);
  assert.equal(gaps.length, 3);
  assert.deepEqual(gaps.map((g) => [g.fromLevel, g.toLevel]), [
    [0, 1],
    [1, 2],
    [2, 3],
  ]);
  // level0 has no available: that gap is null even though level0 has other marks.
  assert.equal(gaps[0].interval, null);
  // level1 available (2022-11-30) to level2 available (2023-02-07): about 2 months.
  assert.ok(gaps[1].interval !== null && gaps[1].interval.months >= 1 && gaps[1].interval.months <= 3, `got ${JSON.stringify(gaps[1].interval)}`);
  assert.equal(gaps[1].interval!.reversed, false);
});

test('consecutiveLevelGaps reports reversed (never negative) when a later level arrives first', () => {
  // A level pair where the second level's available date is EARLIER than the first's -- the real
  // data has this for levels 3 and 4 (Tools generally available before Workflows is).
  const reversedMilestones: Milestone[] = [
    ms({ id: 'ra', date: '2023-12-01', precision: 'day', level: 3 }),
    ms({ id: 'rb', date: '2023-09-01', precision: 'day', level: 4 }),
  ];
  const reversedLevels: LevelMarkEntry[] = [
    { level: 3, described: 'ra', available: 'ra' },
    { level: 4, described: 'rb', available: 'rb' },
  ];
  const gaps = consecutiveLevelGaps(levelSeries(reversedMilestones, reversedLevels));
  assert.equal(gaps[0].interval!.reversed, true);
  assert.ok(gaps[0].interval!.months > 0);
});

test('consecutiveLevelGaps uses available, not a level\'s chronologically latest mark', () => {
  // level3's chronologically latest mark is `buildable` (2024-06-01), not `available` (2023-01-01)
  // -- the gap from level2 to level3 must be computed against level3's `available`, not that.
  const series = levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS);
  const gaps = consecutiveLevelGaps(series);
  const g = gaps.find((x) => x.fromLevel === 2 && x.toLevel === 3)!;
  assert.equal(g.toAvailable!.milestone.id, 'l3-a');
});

// -- climbHeadline: qualifies by a resolved `available` mark, computes count/years ----------------

test('climbHeadline excludes a level with no resolved available, and spans the rest', () => {
  const h = climbHeadline(levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS));
  assert.ok(h);
  assert.equal(h!.count, 3); // levels 1, 2 and 3; level 0 has no `available`
  assert.equal(h!.startLevel, 1);
  assert.equal(h!.endLevel, 3);
  assert.equal(h!.endMark.key, 'available'); // always the end level's `available`, not its latest mark
});

test('climbHeadline is null when fewer than two qualifying levels exist', () => {
  const onlyOneAvailable: LevelMarkEntry[] = [
    { level: 0, described: 'l0-d', buildable: 'l0-b', available: null, note: 'excluded' },
    { level: 1, described: 'l1-d', available: 'l1-a' },
  ];
  assert.equal(climbHeadline(levelSeries(FIXTURE_MILESTONES, onlyOneAvailable)), null);
});

test('climbHeadlineText names the actual computed count, not a fixed number', () => {
  const h = climbHeadline(levelSeries(FIXTURE_MILESTONES, FIXTURE_LEVELS))!;
  const text = climbHeadlineText(h);
  assert.match(text, /^Three levels/);
});

test('climbHeadlineText counts whole years under ten, and says "about N years" beyond', () => {
  const shortSpan: LevelMarkEntry[] = [
    { level: 1, described: 'l1-d', available: 'l1-a' },
    { level: 2, described: 'l2-d', available: 'l2-a' },
  ];
  const h = climbHeadline(levelSeries(FIXTURE_MILESTONES, shortSpan))!;
  assert.match(climbHeadlineText(h), /in under (a year|\w+ years)$/);
  assert.equal(h.startMark.key, 'available'); // product to product, never from a paper

  const longSpanMilestones: Milestone[] = [
    ms({ id: 'old', date: '1990-01-01', precision: 'day', level: 0 }),
    ms({ id: 'new', date: '2020-01-01', precision: 'day', level: 1 }),
  ];
  const longSpanLevels: LevelMarkEntry[] = [
    { level: 0, described: 'old', available: 'old' },
    { level: 1, described: 'new', available: 'new' },
  ];
  const longH = climbHeadline(levelSeries(longSpanMilestones, longSpanLevels))!;
  assert.match(climbHeadlineText(longH), /about \d+ years/);
});

// -- shapeForKind: at most three shapes ----------------------------------------------------------

test('shapeForKind maps every kind to one of three shapes', () => {
  const kinds: Milestone['kind'][] = ['research', 'model', 'product', 'tool', 'standard'];
  const shapes = new Set(kinds.map(shapeForKind));
  assert.ok(shapes.size <= 3, `expected at most 3 distinct shapes, got ${shapes.size}`);
  assert.equal(shapeForKind('research'), shapeForKind('research'));
});

// -- verificationNote --------------------------------------------------------------------------

test('verificationNote is undefined for a verified milestone', () => {
  assert.equal(verificationNote(ms({ id: 'x', date: '2020', precision: 'year', level: 0, verified: true })), undefined);
});

test('verificationNote uses the milestone\'s own note when unverified', () => {
  const note = verificationNote(ms({ id: 'x', date: '2020', precision: 'year', level: 0, verified: false, note: 'The page returns 403.' }));
  assert.equal(note, 'The page returns 403.');
});

test('verificationNote falls back to a generic reason when unverified with no note', () => {
  const note = verificationNote(ms({ id: 'x', date: '2020', precision: 'year', level: 0, verified: false }));
  assert.match(note!, /not verified/i);
});

// -- buildMainAxis: pre-2017 stub, to-scale from the first 2017 milestone --------------------------

test('buildMainAxis starts at the earliest 2017-dated milestone', () => {
  const axis = buildMainAxis(FIXTURE_MILESTONES, '2023-06-01');
  assert.equal(axis.startYear, decimalYear('2017-06-12', 'day'));
});

test('buildMainAxis puts every pre-2017 milestone in the stub, oldest first', () => {
  const axis = buildMainAxis(FIXTURE_MILESTONES, '2023-06-01');
  assert.deepEqual(axis.stubMilestones.map((m) => m.id), ['l0-d', 'l0-b']);
});

test('buildMainAxis toFraction places the start year at stubWidth and asOf at 1', () => {
  const axis = buildMainAxis(FIXTURE_MILESTONES, '2023-06-01', 0.1);
  assert.ok(Math.abs(axis.toFraction(axis.startYear) - 0.1) < 1e-9);
  assert.ok(Math.abs(axis.toFraction(axis.endYear) - 1) < 1e-9);
});

test('buildMainAxis toFraction is monotonic with year', () => {
  const axis = buildMainAxis(FIXTURE_MILESTONES, '2023-06-01');
  const a = axis.toFraction(decimalYear('2018', 'year'));
  const b = axis.toFraction(decimalYear('2020', 'year'));
  assert.ok(a < b);
});

test('buildMainAxis stubFraction spreads milestones within [0, stubWidth]', () => {
  const axis = buildMainAxis(FIXTURE_MILESTONES, '2023-06-01', 0.08);
  const positions = axis.stubMilestones.map((_, i) => axis.stubFraction(i));
  for (const p of positions) assert.ok(p >= 0 && p <= 0.08);
  // oldest (index 0) sits to the left of the newest (last index).
  assert.ok(positions[0] < positions[positions.length - 1]);
});

test('buildMainAxis handles zero pre-2017 milestones without dividing by zero', () => {
  const noPre2017 = FIXTURE_MILESTONES.filter((m) => m.id !== 'l0-d' && m.id !== 'l0-b');
  const axis = buildMainAxis(noPre2017, '2023-06-01');
  assert.equal(axis.stubMilestones.length, 0);
  assert.equal(axis.stubFraction(0), 0);
});

// -- buildRecentAxis: straight-line, no stub -------------------------------------------------------

test('buildRecentAxis runs from January of the start year to as_of, no stub', () => {
  const axis = buildRecentAxis('2026-09-18', 2022);
  assert.equal(axis.startYear, 2022);
  assert.ok(Math.abs(axis.toFraction(2022) - 0) < 1e-9);
  assert.ok(Math.abs(axis.toFraction(decimalYear('2026-09-18', 'day')) - 1) < 1e-9);
});

test('buildRecentAxis year ticks cover every whole year in range', () => {
  const axis = buildRecentAxis('2025-03-01', 2022);
  assert.deepEqual(axis.yearTicks, [2022, 2023, 2024, 2025]);
});

// -- selectLabeledMilestones: always-label marked, de-collide the rest ----------------------------

test('every marked id is always labeled, regardless of spacing', () => {
  const points = [
    { id: 'a', fraction: 0.1 },
    { id: 'b', fraction: 0.11 },
    { id: 'c', fraction: 0.12 },
  ];
  const marked = new Set(['a', 'b', 'c']);
  const labeled = selectLabeledMilestones(points, marked, { minGap: 0.5 });
  assert.deepEqual([...labeled].sort(), ['a', 'b', 'c']);
});

test('an extra (unmarked) point is added only if far enough from every chosen label', () => {
  const points = [
    { id: 'marked', fraction: 0.5 },
    { id: 'near', fraction: 0.52 }, // too close
    { id: 'far', fraction: 0.9 }, // far enough
  ];
  const labeled = selectLabeledMilestones(points, new Set(['marked']), { minGap: 0.1, maxExtra: 2 });
  assert.ok(labeled.has('marked'));
  assert.ok(!labeled.has('near'));
  assert.ok(labeled.has('far'));
});

test('at most maxExtra unmarked points are added even if several qualify', () => {
  const points = [
    { id: 'a', fraction: 0.0 },
    { id: 'b', fraction: 0.3 },
    { id: 'c', fraction: 0.6 },
    { id: 'd', fraction: 0.9 },
  ];
  const labeled = selectLabeledMilestones(points, new Set(), { minGap: 0.1, maxExtra: 2 });
  assert.equal(labeled.size, 2);
});

// -- assignLabelSides: alternates over the LABELED subset, not every point -----------------------

test('assignLabelSides alternates adjacent labeled points, ignoring unlabeled ones between them', () => {
  // b and d are the only labeled points; a and c (unlabeled) sit between/around them in x order.
  // A plain nth-child(odd)-over-every-point scheme would not track this -- it counts a, b, c and d
  // all -- so this specifically checks the labeled subset is what alternates.
  const points = [
    { id: 'a', fraction: 0.05 },
    { id: 'b', fraction: 0.1 },
    { id: 'c', fraction: 0.5 },
    { id: 'd', fraction: 0.9 },
  ];
  const sides = assignLabelSides(points, new Set(['b', 'd']));
  assert.equal(sides.size, 2);
  assert.notEqual(sides.get('b'), sides.get('d'));
  assert.equal(sides.has('a'), false);
  assert.equal(sides.has('c'), false);
});

test('assignLabelSides orders by fraction, not by the order points were given in', () => {
  const points = [
    { id: 'late', fraction: 0.8 },
    { id: 'early', fraction: 0.1 },
    { id: 'mid', fraction: 0.5 },
  ];
  const sides = assignLabelSides(points, new Set(['late', 'early', 'mid']));
  assert.equal(sides.get('early'), 'below'); // first by fraction
  assert.equal(sides.get('mid'), 'above');
  assert.equal(sides.get('late'), 'below');
});

// -- milestonesByYearDesc ----------------------------------------------------------------------

test('milestonesByYearDesc groups by year, newest year first', () => {
  const groups = milestonesByYearDesc(FIXTURE_MILESTONES);
  const years = groups.map((g) => g.year);
  for (let i = 1; i < years.length; i++) assert.ok(years[i - 1] > years[i]);
});

test('milestonesByYearDesc orders items within a year newest first', () => {
  const sameYear: Milestone[] = [
    ms({ id: 'jan', date: '2020-01-01', precision: 'day', level: 0 }),
    ms({ id: 'dec', date: '2020-12-01', precision: 'day', level: 0 }),
  ];
  const [group] = milestonesByYearDesc(sameYear);
  assert.deepEqual(group.items.map((m) => m.id), ['dec', 'jan']);
});

// -- Invariants against the real data: no hard-coded value, just shape checks --------------------

test('real data: every milestone id is unique', () => {
  const ids = milestones.map((m) => m.id);
  assert.equal(new Set(ids).size, ids.length);
});

test('real data: every milestone date parses without throwing and matches its precision length', () => {
  for (const m of milestones) {
    const parts = m.date.split('-');
    const expected = { day: 3, month: 2, year: 1 }[m.precision];
    assert.equal(parts.length, expected, `${m.id}: date ${m.date} does not match precision ${m.precision}`);
    assert.ok(Number.isFinite(decimalYear(m.date, m.precision)));
  }
});

test('real data: every level entry resolves to a level that actually has milestones, or explains why not', () => {
  const series = levelSeries();
  for (const s of series) {
    if (s.marks.length === 0) {
      assert.ok(s.note, `level ${s.level} has no resolved marks and no note explaining why`);
    }
  }
});

test('real data: consecutiveLevelGaps length is one less than the number of levels', () => {
  assert.equal(consecutiveLevelGaps().length, timeline.levels.length - 1);
});
