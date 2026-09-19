// Layout for /map/: a static, deterministic placement of every technique page as a node in an
// eight-band ladder (level 7 at the top, level 0 at the bottom, matching the home page's climb
// curve) plus a ninth band for the five cross-cutting topics, with the taxonomy's typed relations
// drawn as edges between them. No physics, no client layout pass: every position here is computed
// once at build time from nothing but the taxonomy's own order, so the same input always produces
// the same picture (site/tests/map.test.ts checks that directly).
//
// Deliberately self-contained, the way lib/timeline.ts is and lib/content.ts is not: it imports
// ONLY content/taxonomy.json, with the explicit `type: json` import attribute plain Node requires
// (site/tests/map.test.ts runs this file with `node --test`, no bundler, no Vite). It does not
// import lib/content.ts -- that file's own JSON import has no such attribute and only resolves
// inside Astro's Vite pipeline -- so its types are not reused either; the shapes below are a
// deliberately small re-statement of the same taxonomy.json fields, not a second source of truth
// (there is exactly one taxonomy.json, read here and in lib/content.ts).
import taxonomyData from '../../../content/taxonomy.json' with { type: 'json' };

export type Status = 'planned' | 'stub' | 'sourced' | 'measured';
export type RelationType = 'requires' | 'upgrades_to' | 'combines_with' | 'alternative_to';

export interface MapPageIn {
  slug: string;
  title: string;
  summary: string;
  status: Status;
}

export interface MapTierIn {
  order: number;
  title: string;
  pages: MapPageIn[];
}

export interface MapTrackIn {
  id: string;
  title: string;
  summary: string;
  status: Status;
  pages?: MapPageIn[];
}

export interface MapRelationIn {
  from: string;
  type: RelationType;
  to: string;
  when?: string;
  question?: string;
}

export interface MapTaxonomyIn {
  tiers: MapTierIn[];
  tracks: MapTrackIn[];
  tracks_overview: { title: string };
  relations: MapRelationIn[];
  relation_types?: Record<RelationType, string>;
}

// -- Geometry constants, shared by the layout function and the component that draws it ------------

/** Text is never measured (there is no browser at build time): a node's width is estimated from
 *  its title's character count, generously enough that the longest real title -- "Retrieval-
 *  augmented generation (RAG)", 36 characters -- still fits inside NODE_W_MAX with room to spare. */
const CHAR_W = 6.3;
const NODE_PAD_X = 22;
export const NODE_W_MIN = 92;
export const NODE_W_MAX = 260;
export const NODE_H = 34;
export const COL_GAP = 16;
export const ROW_GAP = 92;
export const PAD_X = 10;
// Centers a level band's node vertically within its ROW_GAP-tall row.
export const PAD_Y = (ROW_GAP - NODE_H) / 2;
/**
 * The canvas is sized from the LEVEL bands only -- never the topics band, which wraps into rows
 * instead of widening the canvas (see the topics-layout comment in computeMapLayout). 1120 is not
 * a round guess: `main` in global.css is `max-width:1392px` with 48px of padding each side, so at
 * a 1360px viewport its content is about 1264px wide; `.map-labels` (map.css) takes a fixed 132px
 * of that for the band-label column, leaving roughly 1130px for the drawing itself. 1120 sits just
 * under that, so the drawing needs no horizontal scroll at that width -- confirmed against the
 * real taxonomy's widest level band (five pages, "Context") below in the module-scope sanity
 * check, and by site/tests/map.test.ts, which asserts the real canvas width stays under 1150.
 */
export const CANVAS_LEVEL_W = 1120;
/** No inter-node gap within a level band grows past this, so a sparse band (three or four pages)
 *  reads as a centered group with comfortable spacing rather than stretched thin across the whole
 *  1100px canvas -- only a band with enough pages to need it actually reaches this cap. */
export const MAX_GAP = 90;
/** One topic's row height inside the topics band (its node, centered, plus top/bottom margin) --
 *  tighter than ROW_GAP because these are wrapped rows inside one band, not separate bands. */
export const TOPICS_ROW_GAP = 46;
/** Empty space above and below a topics-row node within its own TOPICS_ROW_GAP-tall row -- the
 *  topics-row equivalent of PAD_Y, and how far a same-row edge in that band may safely arc (see
 *  computeEdgeGeometry) before it would reach into the row above or below. */
export const TOPICS_ROW_MARGIN = (TOPICS_ROW_GAP - NODE_H) / 2;

function nodeWidth(title: string): number {
  const w = Math.round(title.length * CHAR_W + NODE_PAD_X);
  return Math.min(NODE_W_MAX, Math.max(NODE_W_MIN, w));
}

export interface MapNode {
  slug: string;
  title: string;
  summary: string;
  status: Status;
  /** Row index, top to bottom: 0 is level 7, 7 is level 0, 8 is the topics band. */
  band: number;
  /** The tier order 0..7 this node belongs to, or "tracks" for a topic page. */
  level: number | 'tracks';
  levelLabel: string;
  /** The track id this node's cluster belongs to -- only set for topics-band nodes. */
  group?: string;
  /** Which of the topics band's wrapped rows this node sits in, 0-based -- one row per track, the
   *  track's root page first, then its own sub-pages. Unset for a level-band node (those have
   *  only one row, their band's own). */
  row?: number;
  /** Left-to-right position within its row, 0-based. */
  col: number;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
}

export interface MapEdge {
  key: string;
  from: string;
  type: RelationType;
  to: string;
  when?: string;
  question?: string;
}

export interface MapBand {
  index: number;
  /** Full label, e.g. "Level 07 · Always-on agents" or "Topics at every level". */
  label: string;
  /** Just the tier's own title ("Always-on agents") or "Topics" -- for a narrow sidebar where the
   *  full `label` does not fit and does not need to (the level number renders on its own line). */
  shortTitle: string;
  kind: 'level' | 'topics';
  level?: number;
  /** Number of wrapped rows -- always 1 for a level band, one per track for the topics band. */
  rows: number;
  /** Top of this band's visual slot (label sidebar row, background rule) -- NOT a node's own y,
   *  which sits centered inside this slot (see PAD_Y for a level band, TOPICS_ROW_GAP for a
   *  topics-band row). */
  y: number;
  /** Height of the whole slot: ROW_GAP for a level band, `rows * TOPICS_ROW_GAP` (plus the
   *  canvas's own bottom margin) for the topics band. */
  h: number;
}

export interface MapLayout {
  nodes: MapNode[];
  edges: MapEdge[];
  bands: MapBand[];
  width: number;
  height: number;
}

function levelLabelFor(order: number, title: string): string {
  return `Level ${String(order).padStart(2, '0')} · ${title}`;
}

/** One node's shape before it has an x: everything the layout functions below need to place it. */
interface PendingNode {
  slug: string;
  title: string;
  summary: string;
  status: Status;
  group?: string;
  w: number;
}

/** One placed node: a `PendingNode` plus the x a row-layout function gave it. */
interface PlacedNode {
  item: PendingNode;
  x: number;
}

/**
 * Lays out one level band's nodes left to right across `available` px, stretching the gaps
 * BETWEEN them evenly -- capped at `maxGap` -- rather than the nodes themselves. A band whose
 * nodes need the full width at the cap (the real taxonomy's widest, "Context", five pages) ends up
 * flush from margin to margin; a sparser band's smaller group is centered in the space left over
 * once its gaps hit the cap, so it reads as a deliberate cluster rather than stretched thin. A
 * single node (level 0, one page) is a special case: it sits at the left margin, aligned with
 * every other band's first node, rather than centered in a row that has nothing to center against.
 */
function layoutJustifiedRow(items: PendingNode[], available: number, maxGap: number): PlacedNode[] {
  const count = items.length;
  if (count === 0) return [];
  if (count === 1) return [{ item: items[0], x: PAD_X }];

  const contentW = items.reduce((sum, it) => sum + it.w, 0);
  const baseGapTotal = (count - 1) * COL_GAP;
  const extra = Math.max(0, available - contentW - baseGapTotal);
  const extraPerGap = extra / (count - 1);
  const cappedExtra = Math.min(extraPerGap, Math.max(0, maxGap - COL_GAP));
  const gap = COL_GAP + cappedExtra;
  const groupWidth = contentW + (count - 1) * gap;
  const leftover = Math.max(0, available - groupWidth);

  let x = PAD_X + leftover / 2;
  const placed: PlacedNode[] = [];
  items.forEach((it, i) => {
    if (i > 0) x += gap;
    placed.push({ item: it, x });
    x += it.w;
  });
  return placed;
}

/** Lays out a topics-band row (a track's root page, then its own sub-pages) left to right at the
 *  ordinary column gap, starting at the left margin -- no stretching: item 1 of the coordinator's
 *  fix ("do not let the topics decide [the canvas width]") means these never need to fill
 *  anything, and a wrapped row reads as a cluster on its own without being spread out. */
function layoutPackedRow(items: PendingNode[]): PlacedNode[] {
  let x = PAD_X;
  const placed: PlacedNode[] = [];
  items.forEach((it, i) => {
    if (i > 0) x += COL_GAP;
    placed.push({ item: it, x });
    x += it.w;
  });
  return placed;
}

/**
 * Reorders one level band's items by the average CENTER x of their `requires`/`upgrades_to`
 * neighbors in the band directly below (already placed, since bands are laid out bottom-up --
 * see computeMapLayout). An item with no such neighbor keeps roughly its original position
 * instead of collapsing to one end, by using its own original left-to-right SLOT center (the
 * middle of the `available`-width span its original index would occupy among `count` equally
 * sized slots) as a same-scale stand-in score, so it neither out-ranks nor gets out-ranked by a
 * real neighbor-based score merely because a naive placeholder sat at one extreme. One
 * deterministic pass (no iteration to a fixed point): it only ever looks at the band immediately
 * below, which is what turns a `requires` or `upgrades_to` edge between adjacent bands into a
 * short, near-vertical curve instead of a long diagonal -- it does not attempt to also straighten
 * an edge that skips a band.
 */
function orderByBelow(items: PendingNode[], belowCenterBySlug: Map<string, number>, relations: MapRelationIn[], available: number): PendingNode[] {
  const count = items.length;
  const scoreFor = (slug: string): number | undefined => {
    const xs: number[] = [];
    for (const rel of relations) {
      if (rel.type !== 'requires' && rel.type !== 'upgrades_to') continue;
      if (rel.from === slug && belowCenterBySlug.has(rel.to)) xs.push(belowCenterBySlug.get(rel.to)!);
      if (rel.to === slug && belowCenterBySlug.has(rel.from)) xs.push(belowCenterBySlug.get(rel.from)!);
    }
    return xs.length > 0 ? xs.reduce((a, b) => a + b, 0) / xs.length : undefined;
  };

  const scored = items.map((it, i) => ({
    it,
    i,
    score: scoreFor(it.slug) ?? ((i + 0.5) / count) * available,
  }));
  scored.sort((a, b) => a.score - b.score || a.i - b.i); // original index: a deterministic tiebreak
  return scored.map((s) => s.it);
}

/**
 * Builds the whole map layout from a taxonomy shape. Pure and deterministic: called twice on the
 * same input (even two structurally-equal but distinct objects) it returns the same positions,
 * the same node order and the same edge list, in the same order every time -- nothing here reads
 * the clock, iterates a Set/Map in an order that depends on insertion from another source, or
 * consults anything outside its argument.
 */
export function computeMapLayout(tax: MapTaxonomyIn): MapLayout {
  const tiers = [...tax.tiers].sort((a, b) => b.order - a.order); // level 7 first (top band)
  const available = CANVAS_LEVEL_W - 2 * PAD_X;

  // Level bands are laid out and ordered bottom-up (level 0 first): each band's node order is
  // informed by the already-fixed x positions of the band directly below it (orderByBelow), and a
  // band's positions have to exist before the band above it can use them. The public `bands` and
  // `nodes` arrays are still assembled top-to-bottom afterward, from this map.
  const byOrder = new Map<number, { tier: MapTierIn; placed: PlacedNode[] }>();
  let belowCenterBySlug: Map<string, number> | null = null;
  for (const tier of [...tiers].reverse()) {
    // level 0 first
    const pending: PendingNode[] = tier.pages.map((page) => ({
      slug: page.slug,
      title: page.title,
      summary: page.summary,
      status: page.status,
      w: nodeWidth(page.title),
    }));
    const ordered = belowCenterBySlug ? orderByBelow(pending, belowCenterBySlug, tax.relations, available) : pending;
    const placed = layoutJustifiedRow(ordered, available, MAX_GAP);
    byOrder.set(tier.order, { tier, placed });
    belowCenterBySlug = new Map(placed.map((p) => [p.item.slug, p.x + p.item.w / 2]));
  }

  const bands: MapBand[] = [];
  const nodes: MapNode[] = [];

  tiers.forEach((tier, bandIndex) => {
    const y = bandIndex * ROW_GAP; // this band's visual slot; the node itself sits PAD_Y inside it
    const label = levelLabelFor(tier.order, tier.title);
    bands.push({ index: bandIndex, label, shortTitle: tier.title, kind: 'level', level: tier.order, rows: 1, y, h: ROW_GAP });
    const { placed } = byOrder.get(tier.order)!;
    placed.forEach(({ item, x }, i) => {
      nodes.push({
        slug: item.slug,
        title: item.title,
        summary: item.summary,
        status: item.status,
        band: bandIndex,
        level: tier.order,
        levelLabel: label,
        col: i,
        x,
        y: y + PAD_Y,
        w: item.w,
        h: NODE_H,
        color: `var(--o${tier.order})`,
      });
    });
  });

  // The topics band: every track root plus its own sub-pages, one row per track, the root first
  // then its sub-pages, left-aligned (layoutPackedRow) -- not one long 20-node row (which is what
  // forced the whole canvas as wide as the topics band before this fix), and not justified to fill
  // the canvas (a topic's row is a cluster, not a band). A track root (e.g. "safety") is itself a
  // real /techniques/safety/ page -- see site/src/pages/techniques/[slug].astro's `subPages` block
  // -- so it gets a node like any other.
  const topicsBandIndex = tiers.length;
  const topicsSlotTop = topicsBandIndex * ROW_GAP;
  const topicsLabel = tax.tracks_overview.title;

  tax.tracks.forEach((track, row) => {
    const entries: MapPageIn[] = [
      { slug: track.id, title: track.title, summary: track.summary, status: track.status },
      ...(track.pages ?? []),
    ];
    const pending: PendingNode[] = entries.map((page) => ({
      slug: page.slug,
      title: page.title,
      summary: page.summary,
      status: page.status,
      group: track.id,
      w: nodeWidth(page.title),
    }));
    const placed = layoutPackedRow(pending);
    const rowY = topicsSlotTop + row * TOPICS_ROW_GAP + TOPICS_ROW_MARGIN;
    placed.forEach(({ item, x }, i) => {
      nodes.push({
        slug: item.slug,
        title: item.title,
        summary: item.summary,
        status: item.status,
        band: topicsBandIndex,
        level: 'tracks',
        levelLabel: topicsLabel,
        group: item.group,
        row,
        col: i,
        x,
        y: rowY,
        w: item.w,
        h: NODE_H,
        color: 'var(--ot)',
      });
    });
  });

  const topicsSlotH = tax.tracks.length * TOPICS_ROW_GAP + PAD_Y; // + the canvas's own bottom margin
  bands.push({
    index: topicsBandIndex,
    label: topicsLabel,
    shortTitle: 'Topics',
    kind: 'topics',
    rows: tax.tracks.length,
    y: topicsSlotTop,
    h: topicsSlotH,
  });

  const known = new Set(nodes.map((n) => n.slug));
  // Every relation in content/taxonomy.json resolves (scripts/validate.py enforces it), but a
  // synthetic test fixture may deliberately omit an endpoint to check this guard, so an edge whose
  // endpoint is not on the map is dropped rather than drawn to nowhere.
  const edges: MapEdge[] = tax.relations
    .filter((rel) => known.has(rel.from) && known.has(rel.to))
    .map((rel) => ({
      key: `${rel.type}:${rel.from}:${rel.to}`,
      from: rel.from,
      type: rel.type,
      to: rel.to,
      when: rel.when,
      question: rel.question,
    }));

  // A hard guarantee, not an assumption: every level-band node sits inside [0, CANVAS_LEVEL_W] by
  // construction (layoutJustifiedRow never exceeds `available`), and every real topics row does
  // too (the widest, "operator-craft", needs under 950px against an 1100px available width) -- but
  // this stays cheap insurance against a future edit (a much longer, unwrapped title; a track with
  // many more sub-pages) silently pushing a node's right edge past the canvas.
  const width = Math.max(CANVAS_LEVEL_W, ...(nodes.length ? nodes.map((n) => n.x + n.w + PAD_X) : [CANVAS_LEVEL_W]));
  const height = topicsSlotTop + topicsSlotH;

  return { nodes, edges, bands, width, height };
}

/** A node's center point -- every edge starts and ends here. */
function centerOf(n: MapNode): { cx: number; cy: number } {
  return { cx: n.x + n.w / 2, cy: n.y + n.h / 2 };
}

export interface EdgeGeometry {
  x1: number;
  y1: number;
  /** Cubic bezier control points. For an edge between two different rows these sit at the
   *  vertical midpoint between the two endpoints (a gentle S-curve). For a same-row edge they sit
   *  directly above (or below) each endpoint instead, so the curve stays elevated across the
   *  whole span rather than only at its middle -- see `arcsOverIntervening`. */
  c1x: number;
  c1y: number;
  c2x: number;
  c2y: number;
  x2: number;
  y2: number;
  /** True when `from` and `to` sit in the same row (the same level band, or the same topics-band
   *  track row) AND at least one other node in that row sits horizontally between them -- the
   *  case a straight (or midpoint-only) line would run straight through. False for every edge
   *  between different rows, and for a same-row edge between neighbors with nothing between them
   *  to avoid. Keyed on the row (its y), not the band: two topics-band nodes can share a `band`
   *  index while sitting in different track rows, which is not the same-row case this handles. */
  arcsOverIntervening: boolean;
}

/**
 * Computes one edge's curve. `rowNodes` is every OTHER node that shares `from`/`to`'s row (order
 * does not matter) -- used only to detect whether something sits between them; pass `[]` for an
 * edge between different rows, or when the caller already knows there is nothing to check.
 */
export function computeEdgeGeometry(from: MapNode, to: MapNode, rowNodes: MapNode[]): EdgeGeometry {
  const { cx: x1, cy: y1 } = centerOf(from);
  const { cx: x2, cy: y2 } = centerOf(to);

  if (y1 !== y2) {
    const my = (y1 + y2) / 2;
    return { x1, y1, c1x: x1, c1y: my, c2x: x2, c2y: my, x2, y2, arcsOverIntervening: false };
  }

  const lo = Math.min(x1, x2);
  const hi = Math.max(x1, x2);
  const between = rowNodes.some((n) => n.slug !== from.slug && n.slug !== to.slug && centerOf(n).cx > lo && centerOf(n).cx < hi);

  // Always upward (toward lower y): every row keeps at least PAD_Y (a level band) or
  // TOPICS_ROW_MARGIN (a topics row -- much tighter, 6px, since those are wrapped rows inside one
  // band, not separate bands) of empty space above and below its nodes. Capping the rise at just
  // under that row's own margin keeps an arc from ever reaching into the row above, whichever kind
  // of row this is; the topmost band has nothing above it to reach into at all either way.
  const margin = from.level === 'tracks' ? TOPICS_ROW_MARGIN : PAD_Y;
  const arcHeight = Math.min(NODE_H / 2 + (between ? 8 : 2), NODE_H / 2 + margin - 1);
  const cy = y1 - arcHeight; // y1 === y2 here, both endpoints share a row
  return { x1, y1, c1x: x1, c1y: cy, c2x: x2, c2y: cy, x2, y2, arcsOverIntervening: between };
}

/** Renders an `EdgeGeometry` as an SVG cubic-bezier path's `d` attribute. */
export function edgePathD(g: EdgeGeometry): string {
  const f = (n: number) => n.toFixed(1);
  return `M${f(g.x1)},${f(g.y1)} C${f(g.c1x)},${f(g.c1y)} ${f(g.c2x)},${f(g.c2y)} ${f(g.x2)},${f(g.y2)}`;
}

export interface ResolvedEdge extends MapEdge {
  fromNode: MapNode;
  toNode: MapNode;
}

/**
 * Every edge, grouped by the band its `from` node sits in and ordered the way the bands are drawn
 * (level 7 down to level 0, then topics) -- the data behind the plain-text edge list under the
 * drawing, which has to carry every `when` and `question` and has to stand on its own for a reader
 * with no image and no JavaScript.
 */
export function edgesByBand(layout: MapLayout): { band: MapBand; edges: ResolvedEdge[] }[] {
  const bySlug = new Map(layout.nodes.map((n) => [n.slug, n]));
  return layout.bands.map((band) => {
    const edges = layout.edges
      .filter((e) => bySlug.get(e.from)?.band === band.index)
      .map((e) => ({ ...e, fromNode: bySlug.get(e.from)!, toNode: bySlug.get(e.to)! }))
      .sort(
        (a, b) =>
          (a.fromNode.row ?? 0) - (b.fromNode.row ?? 0) ||
          a.fromNode.col - b.fromNode.col ||
          a.type.localeCompare(b.type) ||
          a.toNode.title.localeCompare(b.toNode.title),
      );
    return { band, edges };
  });
}

export const RELATION_LABEL: Record<RelationType, string> = {
  requires: 'Requires',
  upgrades_to: 'Upgrades to',
  combines_with: 'Combines with',
  alternative_to: 'Alternative to',
};

export const taxonomy = taxonomyData as unknown as MapTaxonomyIn;
export const relationTypes = taxonomy.relation_types ?? ({} as Record<RelationType, string>);
export const mapLayout: MapLayout = computeMapLayout(taxonomy);
