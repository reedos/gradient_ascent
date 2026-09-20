// Typed access to the site's single sources of copy: content/taxonomy.json and
// content/landscape.json, one directory up from the Astro project. Nothing here copies data —
// every helper reads the imported JSON directly, so the site and prototype.build_look.py can
// never drift apart.
import taxonomyData from '../../../content/taxonomy.json';
import landscapeData from '../../../content/landscape.json';

export type Status = 'planned' | 'stub' | 'sourced' | 'measured';
export type Kind = 'model' | 'product' | 'tool';
export type Lane = 'use' | 'build';

export interface TaxonomyPage {
  slug: string;
  title: string;
  summary: string;
  status: Status;
  covers?: string[];
  graph_engineering?: string;
  examples_as_of?: string;
  examples?: string[];
  note?: string;
}

export interface Tier {
  id: string;
  order: number;
  title: string;
  short: string;
  who: string;
  description: string;
  control: string;
  pages: TaxonomyPage[];
}

export interface Track {
  id: string;
  title: string;
  summary: string;
  status: Status;
  why?: string;
  covers?: string[];
  pages?: TaxonomyPage[];
}

/**
 * Which audience a recipe's page is written for. `general` is the everyday jobs the site opened
 * with; `engineering` is the electronics test, measurement and design work that runs on the
 * bench described in `docs/THE-BENCH.md`. The recipes index groups by this, and
 * `scripts/validate.py` rule 17 requires every recipe to carry one of the declared values.
 */
export type Domain = 'general' | 'engineering';

export interface Recipe {
  slug: string;
  title: string;
  summary: string;
  running_task?: boolean;
  domain: Domain;
  uses: string[];
  /** Set only once a recipe has its own written page; absent means "outline only". */
  status?: Status;
}

/**
 * A stage groups tiers into one of the four ways of working with a model, plus order zero, for
 * the home-page climb chart. `levels`, concatenated across stages in order, covers every tier
 * order 0..n-1 exactly once (enforced by `scripts/validate.py`).
 */
export interface Stage {
  id: string;
  title: string;
  levels: number[];
  kinds: string;
  line: string;
}

/**
 * A thread: one idea that runs through several technique pages, at different levels. It carries
 * the same `summary` and `status` fields every other page kind does — see `threads` in
 * content/taxonomy.json — so `threads/[id].astro` can render it without a local cast.
 */
export interface Thread {
  id: string;
  title: string;
  /** The one sentence the thread exists to teach, printed above the body. */
  line: string;
  summary: string;
  status: Status;
  pages: string[];
}

export type RelationType = 'requires' | 'upgrades_to' | 'combines_with' | 'alternative_to';

export interface Relation {
  from: string;
  type: RelationType;
  to: string;
  when?: string;
  question?: string;
  note?: string;
}

/**
 * A teardown: one kind of real product, decoded into the techniques underneath it. The taxonomy
 * owns the list (slug, title and the technique slugs it decodes); the MDX file under
 * site/src/content/teardowns/ owns the writing, the products it names and its sources. the project plan's
 * Scope control caps the live set and expires each one after `expires_days`, so a teardown that
 * has not been re-reviewed inside that window is badged stale and drops out of the places the
 * site recommends a teardown from. See docs/WRITING-A-TEARDOWN.md.
 */
export interface Teardown {
  slug: string;
  title: string;
  patterns: string[];
}

export interface Taxonomy {
  version: number;
  statuses: Status[];
  lanes: Record<Lane, string>;
  relation_types: Record<RelationType, string>;
  tiers: Tier[];
  stages: Stage[];
  tracks_overview: { title: string; who: string; description: string };
  tracks: Track[];
  threads: Thread[];
  domains: Domain[];
  recipes: Recipe[];
  relations: Relation[];
  /** The one sentence that defines what starts a new level. The Method page, the worksheet and
   *  /llms.txt all print this string rather than each keeping their own paraphrase. */
  level_rule: string;
  teardowns: { cap: number; expires_days: number; first: Teardown[] };
}

export interface LandscapeEntry {
  id: string;
  name: string;
  developer?: string;
  by?: string;
  category: string;
  demonstrates: string[];
  released?: string;
  source: string;
  checked: string;
  verified: boolean;
  formerly?: string;
  /** ISO date (or a bare year) the maker stops running it. May be in the future. */
  retired?: string;
  /** Registry id of the entry that replaced it. */
  superseded_by?: string;
}

export interface Landscape {
  version: number;
  as_of: string;
  note: string;
  developers: { id: string; name: string }[];
  models: LandscapeEntry[];
  products: LandscapeEntry[];
  tools: LandscapeEntry[];
}

export const taxonomy = taxonomyData as unknown as Taxonomy;
export const landscape = landscapeData as unknown as Landscape;

export const levels: Tier[] = [...taxonomy.tiers].sort((a, b) => a.order - b.order);
export const tracks: Track[] = taxonomy.tracks;
export const recipes: Recipe[] = taxonomy.recipes;

/** The recipes in one domain, in taxonomy order. The index page's two headings read off this. */
export function recipesInDomain(domain: Domain): Recipe[] {
  return recipes.filter((r) => r.domain === domain);
}
export const stages: Stage[] = taxonomy.stages;
export const threads: Thread[] = taxonomy.threads;

export interface NamedEntry {
  id: string;
  name: string;
  kind: Kind;
  maker: string;
  category: string;
  demonstrates: string[];
  formerly?: string;
  source: string;
  checked: string;
  verified: boolean;
  /**
   * Badge text for an entry that is retired or superseded; absent for a current one. The "Out
   * there" block lists what a technique is shipping in, so an entry that has stopped running —
   * or that a successor replaced — has to say so where it is rendered, not only in the registry.
   */
  retirement?: string;
}

const developerName: Record<string, string> = Object.fromEntries(
  landscape.developers.map((d) => [d.id, d.name]),
);

const allEntries: LandscapeEntry[] = [
  ...landscape.models,
  ...landscape.products,
  ...landscape.tools,
];
const entryName: Record<string, string> = Object.fromEntries(allEntries.map((e) => [e.id, e.name]));

/**
 * "Retired 2026-09-16 · now Claude", "Retires 2026-12-11", "Superseded by Microsoft Agent
 * Framework", or undefined. `retired` may be a future date — Custom GPTs stop running in
 * December — so the tense follows the registry's own `as_of` rather than claiming a product is
 * already gone. A bare year ("2026") is never read as future.
 */
export function retirementLabel(entry: LandscapeEntry): string | undefined {
  const successor = entry.superseded_by ? entryName[entry.superseded_by] : undefined;
  if (entry.retired) {
    const future = /^\d{4}-\d{2}-\d{2}$/.test(entry.retired) && entry.retired > landscape.as_of;
    const head = `${future ? 'Retires' : 'Retired'} ${entry.retired}`;
    return successor ? `${head} · now ${successor}` : head;
  }
  if (successor) return `Superseded by ${successor}`;
  return undefined;
}

export const named: NamedEntry[] = (
  [
    ['model', landscape.models],
    ['product', landscape.products],
    ['tool', landscape.tools],
  ] as [Kind, LandscapeEntry[]][]
).flatMap(([kind, entries]) =>
  entries.map((entry) => ({
    id: entry.id,
    name: entry.name,
    kind,
    maker: entry.developer ? developerName[entry.developer] : (entry.by ?? ''),
    category: entry.category,
    demonstrates: entry.demonstrates,
    formerly: entry.formerly,
    source: entry.source,
    checked: entry.checked,
    verified: entry.verified,
    ...(retirementLabel(entry) ? { retirement: retirementLabel(entry) } : {}),
  })),
);

export const asOf = landscape.as_of;

/**
 * How much of the registry has actually been checked against a maker's own page. Pages print
 * this rather than a sentence about it, so the figure cannot go stale the way the hand-written
 * "most are not yet checked" line did after the first verification pass.
 */
export const namesChecked = {
  total: named.length,
  verified: named.filter((n) => n.verified).length,
};

/** Every technique-like page: a tier's page, a track root, or a track's own sub-page. */
export interface TechniqueRef {
  slug: string;
  title: string;
  summary: string;
  status: Status;
  /** The tier order (0..7) this page belongs to, or "tracks" for anything under Topics. */
  level: number | 'tracks';
  /** Human label for the level, e.g. "Level 02 · Context" or "Topics at every level". */
  levelLabel: string;
  covers?: string[];
}

const techniqueIndex = new Map<string, TechniqueRef>();

for (const tier of levels) {
  for (const page of tier.pages) {
    techniqueIndex.set(page.slug, {
      slug: page.slug,
      title: page.title,
      summary: page.summary,
      status: page.status,
      level: tier.order,
      levelLabel: `Level ${String(tier.order).padStart(2, '0')} · ${tier.title}`,
      covers: page.covers,
    });
  }
}

for (const track of tracks) {
  techniqueIndex.set(track.id, {
    slug: track.id,
    title: track.title,
    summary: track.summary,
    status: track.status,
    level: 'tracks',
    levelLabel: taxonomy.tracks_overview.title,
    covers: track.covers,
  });
  for (const page of track.pages ?? []) {
    techniqueIndex.set(page.slug, {
      slug: page.slug,
      title: page.title,
      summary: page.summary,
      status: page.status,
      level: 'tracks',
      levelLabel: taxonomy.tracks_overview.title,
      covers: page.covers,
    });
  }
}

/** Every slug that gets a /techniques/<slug>/ stub page: tier pages, track roots, track pages. */
export const allTechniqueSlugs: string[] = [...techniqueIndex.keys()];

export function techniqueBySlug(slug: string): TechniqueRef | undefined {
  return techniqueIndex.get(slug);
}

export function levelOfSlug(slug: string): number | 'tracks' | undefined {
  return techniqueIndex.get(slug)?.level;
}

/** Slugs that belong to one tier (by order 0..7), or the five track root ids for "tracks". */
function slugsForLevel(level: number | 'tracks'): string[] {
  if (level === 'tracks') return tracks.map((t) => t.id);
  const tier = levels.find((t) => t.order === level);
  return tier ? tier.pages.map((p) => p.slug) : [];
}

/** Names grouped by kind for one level (or "tracks"), sorted the way the prototype does. */
export function namesForLevel(level: number | 'tracks'): Record<Kind, NamedEntry[]> {
  return namesFor(slugsForLevel(level));
}

/** The four fields a name is actually rendered with. Kept separate from NamedEntry so the
 *  level explorer island ships only these and not the registry's source URLs and flags. */
export interface NameChip {
  name: string;
  maker: string;
  category: string;
  formerly?: string;
  retirement?: string;
}

function chip(n: NamedEntry): NameChip {
  return {
    name: n.name,
    maker: n.maker,
    category: n.category,
    ...(n.formerly ? { formerly: n.formerly.replace(/ \(.*/, '') } : {}),
    ...(n.retirement ? { retirement: n.retirement } : {}),
  };
}

/** One level's names, already grouped, labeled and slimmed for the client. */
export interface NameGroup {
  label: string;
  entries: NameChip[];
}

export function nameGroupsForLevel(level: number | 'tracks'): NameGroup[] {
  const names = namesForLevel(level);
  const defs: [Kind, string][] = [
    ['product', level === 0 ? 'Products' : 'Products that work this way'],
    ['tool', level === 0 ? 'What to use instead of a model' : 'Tools for building it'],
    ['model', 'Models'],
  ];
  return defs
    .map(([kind, label]) => ({ label, entries: names[kind].map(chip) }))
    .filter((g) => g.entries.length > 0);
}

/** Names grouped by kind whose `demonstrates` intersects the given technique slugs. */
export function namesFor(slugs: string[]): Record<Kind, NamedEntry[]> {
  const set = new Set(slugs);
  const mine = named.filter((n) => n.demonstrates.some((s) => set.has(s)));
  const byKind = (kind: Kind) => mine.filter((n) => n.kind === kind).sort((a, b) => a.name.localeCompare(b.name));
  return { product: byKind('product'), tool: byKind('tool'), model: byKind('model') };
}

export interface Relations {
  requires: TechniqueRef[];
  requiredBy: TechniqueRef[];
  upgradesTo: { page: TechniqueRef; when: string }[];
  combinesWith: TechniqueRef[];
  alternativeTo: { page: TechniqueRef; question: string }[];
}

export function relationsFor(slug: string): Relations {
  const resolve = (s: string) => techniqueIndex.get(s);
  const requires: TechniqueRef[] = [];
  const requiredBy: TechniqueRef[] = [];
  const upgradesTo: { page: TechniqueRef; when: string }[] = [];
  const combinesWith: TechniqueRef[] = [];
  const alternativeTo: { page: TechniqueRef; question: string }[] = [];

  for (const rel of taxonomy.relations) {
    if (rel.from === slug) {
      const target = resolve(rel.to);
      if (!target) continue;
      if (rel.type === 'requires') requires.push(target);
      else if (rel.type === 'upgrades_to') upgradesTo.push({ page: target, when: rel.when ?? '' });
      else if (rel.type === 'combines_with') combinesWith.push(target);
      else if (rel.type === 'alternative_to') alternativeTo.push({ page: target, question: rel.question ?? '' });
    }
    if (rel.to === slug && rel.type === 'requires') {
      const source = resolve(rel.from);
      if (source) requiredBy.push(source);
    }
    // alternative_to is symmetric in meaning; surface the reverse direction too.
    if (rel.to === slug && rel.type === 'alternative_to') {
      const source = resolve(rel.from);
      if (source) alternativeTo.push({ page: source, question: rel.question ?? '' });
    }
    if (rel.to === slug && rel.type === 'combines_with') {
      const source = resolve(rel.from);
      if (source) combinesWith.push(source);
    }
  }

  return { requires, requiredBy, upgradesTo, combinesWith, alternativeTo };
}

/** Deduped tier numbers touched by a recipe's techniques, low to high (track pages have none). */
export function recipeLevels(recipe: Recipe): number[] {
  const out: number[] = [];
  for (const slug of recipe.uses) {
    const ref = techniqueIndex.get(slug);
    if (ref && typeof ref.level === 'number' && !out.includes(ref.level)) out.push(ref.level);
  }
  return out.sort((a, b) => a - b);
}

export function recipesUsing(slug: string): Recipe[] {
  return recipes.filter((r) => r.uses.includes(slug));
}

export function techniquesForRecipe(recipe: Recipe): TechniqueRef[] {
  return recipe.uses.map((slug) => techniqueIndex.get(slug)).filter((x): x is TechniqueRef => Boolean(x));
}

// ---------------------------------------------------------------------------------------------
// Teardowns. The taxonomy's `teardowns` block is the whole list: `cap` is how many may be live at
// once and `expires_days` how long one stays live after the date it was last reviewed (the project plan,
// Scope control, rule 5). Both numbers are read here rather than repeated in a page, so changing
// the policy is one edit to content/taxonomy.json.
// ---------------------------------------------------------------------------------------------

export const teardowns: Teardown[] = taxonomy.teardowns.first;
export const teardownCap: number = taxonomy.teardowns.cap;
export const teardownExpiryDays: number = taxonomy.teardowns.expires_days;

export function teardownBySlug(slug: string): Teardown | undefined {
  return teardowns.find((t) => t.slug === slug);
}

/** The technique pages one teardown decodes, in the order the taxonomy lists them. */
export function techniquesForTeardown(teardown: Teardown): TechniqueRef[] {
  return teardown.patterns
    .map((slug) => techniqueIndex.get(slug))
    .filter((x): x is TechniqueRef => Boolean(x));
}

/** The teardowns that decode a given technique — what a technique page links back to. */
export function teardownsDecoding(slug: string): Teardown[] {
  return teardowns.filter((t) => t.patterns.includes(slug));
}

/** The day a teardown reviewed on `reviewedISO` goes stale: reviewed + `expires_days`. */
export function teardownExpiry(reviewedISO: string): string {
  const at = new Date(`${reviewedISO}T00:00:00Z`);
  at.setUTCDate(at.getUTCDate() + teardownExpiryDays);
  return at.toISOString().slice(0, 10);
}

/** True once the expiry date has passed, computed at build time against the build's own date. */
export function teardownIsStale(reviewedISO: string, now: Date = new Date()): boolean {
  return now.toISOString().slice(0, 10) > teardownExpiry(reviewedISO);
}

/** Matches scripts/validate.py's "techniques" count: tier pages plus track pages, not the five
 *  track roots themselves (those are topics, not techniques). */
const techniqueCount =
  levels.reduce((sum, tier) => sum + tier.pages.length, 0) +
  tracks.reduce((sum, track) => sum + (track.pages?.length ?? 0), 0);

export const counts = {
  techniques: techniqueCount,
  /** The five track roots. They are pages under /techniques/ too, but they are topics, not
   *  techniques, which is why `techniques` above leaves them out. */
  topics: tracks.length,
  threads: threads.length,
  /** Every file served under /techniques/: the techniques plus the five topic roots. A reader or
   *  an agent that lists the directory counts this, so anything that says "technique pages"
   *  rather than "techniques" has to use this number or the site contradicts itself. */
  techniquePages: techniqueCount + tracks.length,
  recipes: recipes.length,
  teardowns: teardowns.length,
  named: named.length,
};
