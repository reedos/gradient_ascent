// Unit tests for src/lib/changes.ts: the ordering, the grouping, the Atom feed and the Markdown
// twin. Synthetic fixtures for the rules, and a few assertions over the real file for the things
// that only matter once it has content in it. The shape of content/changes.json is asserted on
// the Python side, in tests/test_changes.py. Run: npm test (in site/).
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  atomFeed,
  changes,
  changesByDate,
  changesMarkdown,
  escapeXml,
  latestChangeDate,
  type Change,
} from '../src/lib/changes.ts';

const abs = (path: string) => `https://example.org/gradient_ascent${path}`;

const fixture: Change[] = [
  {
    id: 'second-on-the-day',
    date: '2026-09-19',
    title: 'The second thing that day',
    what: 'A thing is different.',
    why: 'It matters for this reason.',
    pages: [{ label: 'Home', path: '/' }],
  },
  {
    id: 'first-on-the-day',
    date: '2026-09-19',
    title: 'The first thing that day',
    what: 'Another thing is different.',
    why: 'It matters for that reason.',
    pages: [],
  },
  {
    id: 'older',
    date: '2026-09-18',
    title: 'Something older',
    what: 'An older thing.',
    why: 'An older reason.',
    pages: [{ label: 'Timeline', path: '/timeline/' }],
  },
];

test('entries group under their date, newest date first, file order inside a date', () => {
  const groups = changesByDate(fixture);
  assert.deepEqual(groups.map((g) => g.date), ['2026-09-19', '2026-09-18']);
  assert.deepEqual(groups[0].entries.map((e) => e.id), ['second-on-the-day', 'first-on-the-day']);
});

test('the real file is sorted newest first', () => {
  const dates = changes.map((c) => c.date);
  assert.deepEqual(dates, [...dates].sort().reverse());
});

test('the feed reports the newest entry date as its own updated time', () => {
  assert.equal(latestChangeDate(fixture), '2026-09-19');
  const feed = atomFeed(fixture, { pageUrl: abs('/changes/'), feedUrl: abs('/changes.xml'), abs });
  assert.match(feed, /<updated>2026-09-19T00:00:00Z<\/updated>/);
});

test('the feed is well-formed Atom with one entry per change', () => {
  const feed = atomFeed(fixture, { pageUrl: abs('/changes/'), feedUrl: abs('/changes.xml'), abs });
  assert.ok(feed.startsWith('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">'));
  assert.ok(feed.trimEnd().endsWith('</feed>'));
  assert.equal(feed.match(/<entry>/g)?.length, fixture.length);
  assert.equal(feed.match(/<\/entry>/g)?.length, fixture.length);
  // A self link and an alternate link, which is what a reader's feed tool looks for.
  assert.match(feed, /<link rel="self" type="application\/atom\+xml" href="[^"]+\/changes\.xml"\/>/);
  assert.match(feed, /<link rel="alternate" type="text\/html" href="[^"]+\/changes\/"\/>/);
});

test('every entry id in the feed is the page anchor, so a reader lands on the right block', () => {
  const feed = atomFeed(fixture, { pageUrl: abs('/changes/'), feedUrl: abs('/changes.xml'), abs });
  for (const entry of fixture) {
    assert.ok(feed.includes(`<id>${abs('/changes/')}#${entry.id}</id>`), entry.id);
  }
});

test('an entry carries what changed, why it matters, and the pages it touched', () => {
  const feed = atomFeed(fixture, { pageUrl: abs('/changes/'), feedUrl: abs('/changes.xml'), abs });
  assert.match(feed, /A thing is different\./);
  assert.match(feed, /It matters for this reason\./);
  assert.match(feed, /Home: https:\/\/example\.org\/gradient_ascent\//);
});

test('markup in a title cannot break the feed', () => {
  const nasty: Change[] = [
    {
      id: 'x',
      date: '2026-09-19',
      title: 'Tools & agents <script>alert("x")</script>',
      what: "It's fixed.",
      why: 'Because a > b.',
      pages: [],
    },
  ];
  const feed = atomFeed(nasty, { pageUrl: abs('/changes/'), feedUrl: abs('/changes.xml'), abs });
  assert.ok(!feed.includes('<script>'), 'no raw markup survives into the feed');
  assert.match(feed, /Tools &amp; agents &lt;script&gt;/);
  assert.match(feed, /Because a &gt; b\./);
  assert.equal(escapeXml(`a&b<c>d"e'f`), 'a&amp;b&lt;c&gt;d&quot;e&apos;f');
});

test('the real feed renders and covers every entry', () => {
  const feed = atomFeed(changes, { pageUrl: abs('/changes/'), feedUrl: abs('/changes.xml'), abs });
  assert.equal(feed.match(/<entry>/g)?.length, changes.length);
  assert.ok(changes.length >= 5, 'the log is seeded from the site public life so far');
});

test('the markdown twin carries every entry under its date, with its links', () => {
  const md = changesMarkdown(fixture, abs);
  assert.match(md, /^# What changed/);
  assert.match(md, /## 2026-09-19/);
  assert.match(md, /### The first thing that day/);
  assert.match(md, /\[Timeline\]\(https:\/\/example\.org\/gradient_ascent\/timeline\/\)/);
  assert.ok(md.indexOf('## 2026-09-19') < md.indexOf('## 2026-09-18'), 'newest date first');
});

test('an empty log renders a feed and a page rather than crashing', () => {
  const feed = atomFeed([], { pageUrl: abs('/changes/'), feedUrl: abs('/changes.xml'), abs });
  assert.ok(feed.includes('</feed>'));
  assert.equal(feed.match(/<entry>/g), null);
  assert.deepEqual(changesByDate([]), []);
  assert.match(changesMarkdown([], abs), /^# What changed/);
});
