// Unit tests for src/lib/nav.ts, the one definition of the site's navigation that the header's
// menus, the section rail, the phone sheet and the footer sitemap all read. Synthetic fixtures
// for the shaping; one test reads the real pages directory so a menu can never point at a route
// that does not exist. Run: npm test (in site/).
import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { buildNav, navContext, railItems, isCurrent, type NavLevel, type NavTrack } from '../src/lib/nav.ts';

const levels: NavLevel[] = [
  { order: 1, title: 'One call', short: 'One question, one answer', slugs: ['chat'] },
  { order: 0, title: 'No model', slugs: ['order-zero'] },
  { order: 5, title: 'Agents', slugs: ['single-agent', 'coding-agents'] },
];
const tracks: NavTrack[] = [
  { id: 'evals', title: 'Evals', slugs: ['eval-frameworks'] },
  { id: 'safety', title: 'Safety', slugs: ['guardrails'] },
];
const groups = buildNav(levels, tracks);

test('four groups, in the order the site reads', () => {
  assert.deepEqual(groups.map((g) => g.id), ['levels', 'techniques', 'practice', 'reference']);
  for (const g of groups) assert.ok(g.blurb.length > 10, `${g.id} has a blurb`);
});

test('levels are listed lowest first and carry their number', () => {
  const items = groups[0].sections[0].items;
  assert.deepEqual(items.map((i) => i.level), [0, 1, 5]);
  assert.equal(items[1].path, '/levels/1/');
  assert.equal(items[1].hint, 'One question, one answer');
});

test('every topic gets a menu entry under techniques', () => {
  const topicItems = groups[1].sections[1].items;
  assert.deepEqual(topicItems.map((i) => i.path), ['/techniques/evals/', '/techniques/safety/']);
});

test('no path is listed twice, and every path is site-relative with a trailing slash', () => {
  const paths = groups.flatMap((g) => g.sections.flatMap((s) => s.items.map((i) => i.path)));
  assert.equal(new Set(paths).size, paths.length);
  for (const p of paths) assert.match(p, /^\/.*\/$/);
});

test('a technique page at a level belongs to LEVELS and knows its level', () => {
  assert.deepEqual(navContext('/techniques/coding-agents/', levels, tracks), { group: 'levels', level: 5 });
  assert.deepEqual(navContext('/levels/1/', levels, tracks), { group: 'levels', level: 1 });
});

test('a topic page, the index, the map and a thread belong to TECHNIQUES', () => {
  for (const p of ['/techniques/guardrails/', '/techniques/evals/', '/techniques/', '/map/', '/threads/graph-engineering/']) {
    assert.deepEqual(navContext(p, levels, tracks), { group: 'techniques' }, p);
  }
});

test('practice and reference pages resolve, including their children', () => {
  for (const p of ['/worksheet/', '/shapes/', '/recipes/', '/recipes/support-desk/', '/teardowns/coding-agent/', '/failures/']) {
    assert.equal(navContext(p, levels, tracks).group, 'practice', p);
  }
  for (const p of ['/timeline/', '/names/', '/glossary/', '/method/', '/changes/', '/agents/']) {
    assert.equal(navContext(p, levels, tracks).group, 'reference', p);
  }
});

test('the reference group lists the change log, so the footer sitemap carries it too', () => {
  const reference = groups.find((g) => g.id === 'reference')!;
  const paths = reference.sections.flatMap((s) => s.items.map((i) => i.path));
  assert.ok(paths.includes('/changes/'), 'reference lists /changes/');
  // It sits after Method and before the agent page: a reader looking for what is new reads the
  // record of the site before the instructions for their own tooling.
  assert.deepEqual(paths.slice(-3), ['/method/', '/changes/', '/agents/']);
});

test('home, search and unknown paths have no section, so no rail', () => {
  for (const p of ['/', '/search/', '/nope/']) {
    const ctx = navContext(p, levels, tracks);
    assert.deepEqual(ctx, {});
    assert.deepEqual(railItems(groups, ctx), []);
  }
});

test('the rail shows the ladder on a level page and the group\'s own pages elsewhere', () => {
  assert.deepEqual(railItems(groups, { group: 'levels', level: 5 }).map((i) => i.level), [0, 1, 5]);
  assert.deepEqual(railItems(groups, { group: 'practice' }).map((i) => i.path), ['/worksheet/', '/shapes/', '/recipes/', '/teardowns/', '/failures/']);
  // Techniques: the browse links only; five topics would not fit a rail and live in the menu.
  assert.deepEqual(railItems(groups, { group: 'techniques' }).map((i) => i.path), ['/techniques/', '/map/', '/threads/graph-engineering/']);
});

test('isCurrent: a level item follows the context, an index stays current on its children', () => {
  const ctx = navContext('/techniques/coding-agents/', levels, tracks);
  const lvl5 = groups[0].sections[0].items.find((i) => i.level === 5)!;
  const lvl1 = groups[0].sections[0].items.find((i) => i.level === 1)!;
  assert.equal(isCurrent(lvl5, '/techniques/coding-agents/', ctx), true);
  assert.equal(isCurrent(lvl1, '/techniques/coding-agents/', ctx), false);

  const recipes = groups[2].sections[0].items.find((i) => i.path === '/recipes/')!;
  assert.equal(isCurrent(recipes, '/recipes/support-desk/', { group: 'practice' }), true);

  const all = groups[1].sections[0].items.find((i) => i.path === '/techniques/')!;
  assert.equal(isCurrent(all, '/techniques/', { group: 'techniques' }), true);
  assert.equal(isCurrent(all, '/techniques/guardrails/', { group: 'techniques' }), false);
});

test('every fixed menu path is a real route in src/pages', () => {
  const pages = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'pages');
  const taxonomy = JSON.parse(readFileSync(join(pages, '..', '..', '..', 'content', 'taxonomy.json'), 'utf8'));
  const slugs = new Set<string>([
    ...taxonomy.tiers.flatMap((t: { pages: { slug: string }[] }) => t.pages.map((p) => p.slug)),
    ...taxonomy.tracks.flatMap((t: { id: string; pages?: { slug: string }[] }) => [t.id, ...(t.pages ?? []).map((p) => p.slug)]),
  ]);
  const threads = new Set<string>(taxonomy.threads.map((t: { id: string }) => t.id));
  const real = buildNav(
    taxonomy.tiers.map((t: { order: number; title: string; pages: { slug: string }[] }) => ({ order: t.order, title: t.title, slugs: t.pages.map((p) => p.slug) })),
    taxonomy.tracks.map((t: { id: string; title: string; pages?: { slug: string }[] }) => ({ id: t.id, title: t.title, slugs: (t.pages ?? []).map((p) => p.slug) })),
  );
  for (const item of real.flatMap((g) => g.sections.flatMap((s) => s.items))) {
    const parts = item.path.split('/').filter(Boolean);
    if (parts[0] === 'levels') { assert.ok(taxonomy.tiers.some((t: { order: number }) => String(t.order) === parts[1]), item.path); continue; }
    if (parts[0] === 'techniques' && parts[1]) { assert.ok(slugs.has(parts[1]), item.path); continue; }
    if (parts[0] === 'threads') { assert.ok(threads.has(parts[1]), item.path); continue; }
    const file = join(pages, ...parts);
    assert.ok(existsSync(`${file}.astro`) || existsSync(join(file, 'index.astro')), `no page for ${item.path}`);
  }
});
