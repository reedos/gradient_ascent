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
const threads = [
  { id: 'graph-engineering', title: 'Graph engineering' },
  { id: 'a-new-thread', title: 'A new thread' },
];
const groups = buildNav(levels, tracks, threads);

test('navigation follows visitor intent and keeps secondary references available', () => {
 assert.deepEqual(groups.map(g=>g.label),['Understand','Explore','Apply','Reference']);
 const paths=groups.flatMap(g=>g.sections.flatMap(s=>s.items.map(i=>i.path)));
 assert.equal(new Set(paths).size,paths.length);
 for(const path of ['/techniques/','/map/','/examples/','/apply/','/tools/','/agents/','/changes/','/techniques/evals/']) assert(paths.includes(path));
 for(const path of paths) assert.match(path,/^\/.*\/$/);
});
test('existing concept and level URLs retain level context while tasks and tools get their own destinations',()=>{
 assert.deepEqual(navContext('/techniques/coding-agents/',levels,tracks),{group:'levels',level:5});
 assert.deepEqual(navContext('/levels/1/',levels,tracks),{group:'levels',level:1});
 for(const path of ['/techniques/','/map/','/worksheet/','/techniques/guardrails/']) assert.equal(navContext(path,levels,tracks).group,'levels');
 for(const path of ['/examples/','/recipes/support-desk/','/shapes/','/threads/graph-engineering/','/teardowns/coding-agent/']) assert.equal(navContext(path,levels,tracks).group,'techniques');
 for(const path of ['/apply/','/tools/','/tools/workflow/','/agents/']) assert.equal(navContext(path,levels,tracks).group,'practice');
 for(const path of ['/names/','/glossary/','/changes/','/failures/']) assert.equal(navContext(path,levels,tracks).group,'reference');
 for(const path of ['/','/search/','/unknown/']) assert.deepEqual(railItems(groups,navContext(path,levels,tracks)),[]);
});
test('local rails stay compact and level order is preserved',()=>{
 assert.deepEqual(railItems(groups,{group:'levels',level:5}).map(i=>i.level),[0,1,5]);
 assert.deepEqual(railItems(groups,{group:'practice'}).map(i=>i.path),['/apply/','/tools/','/agents/']);
 assert.equal(railItems(groups,{group:'levels'})[0].path,'/techniques/');
});
test('active links preserve child-page and level selection',()=>{
 const items=groups.flatMap(g=>g.sections.flatMap(s=>s.items));
 const level=items.find(i=>i.level===5)!;
 assert(isCurrent(level,'/techniques/coding-agents/',{group:'levels',level:5}));
 assert(!isCurrent(level,'/levels/1/',{group:'levels',level:1}));
 assert(isCurrent(items.find(i=>i.path==='/recipes/')!,'/recipes/support-desk/',{group:'techniques'}));
});
test('all supplied threads remain discoverable, including unknown future threads',()=>{
 const items=groups.flatMap(g=>g.sections.flatMap(s=>s.items));
 for(const t of threads) assert(items.some(i=>i.path===`/threads/${t.id}/` && i.hint));
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
