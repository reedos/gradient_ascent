// The capability chart's shaping: Epoch AI's Epoch Capabilities Index by model release date, the
// frontier line over it, and this site's own level dates marked along the bottom. Pure functions
// over plain data, so they run under `node --test` with synthetic points.
//
// This site computes no score. It draws Epoch's numbers, draws the running maximum of them, and
// does one subtraction for the caption (how far the frontier moved before and after a date).

export interface CapabilityPoint {
  name: string;
  org: string | null;
  /** ISO date, the model's release date as Epoch records it. */
  date: string;
  eci: number;
  lo: number | null;
  hi: number | null;
  open: boolean;
}

export interface CapabilitySnapshot {
  version: number;
  retrieved: string;
  source: { title: string; publisher: string; url: string; data_url: string; license: string; license_url: string; citation: string };
  what_it_is: string;
  note: string;
  points: CapabilityPoint[];
}

/** ISO date to a decimal year, day precision. */
export function yearOf(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number);
  const start = Date.UTC(y, 0, 1);
  const end = Date.UTC(y + 1, 0, 1);
  return y + (Date.UTC(y, (m || 1) - 1, d || 1) - start) / (end - start);
}

/** The models that set a new high when they were released, in date order. */
export function frontier(points: CapabilityPoint[]): CapabilityPoint[] {
  // Several models can share a release day (a family of sizes). Only the best of that day can
  // set a record; its smaller siblings never held the top spot.
  const bestOfDay = new Map<string, CapabilityPoint>();
  for (const p of points) {
    const cur = bestOfDay.get(p.date);
    if (!cur || p.eci > cur.eci) bestOfDay.set(p.date, p);
  }
  const sorted = [...bestOfDay.values()].sort((a, b) => (a.date < b.date ? -1 : 1));
  const out: CapabilityPoint[] = [];
  let best = -Infinity;
  for (const p of sorted) {
    if (p.eci > best) {
      best = p.eci;
      out.push(p);
    }
  }
  return out;
}

/** The frontier's value on a date: the best score among models released on or before it. */
export function frontierAt(front: CapabilityPoint[], iso: string): number | null {
  let v: number | null = null;
  for (const p of front) {
    if (p.date <= iso) v = p.eci;
    else break;
  }
  return v;
}

export interface Scale {
  x0: number;
  x1: number;
  y0: number;
  y1: number;
  /** Plot box in SVG units. */
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export function makeScale(points: CapabilityPoint[], opts: { startISO: string; endISO: string; width: number; height: number; pad: { l: number; r: number; t: number; b: number } }): Scale {
  const ys = points.map((p) => p.eci);
  const y0 = Math.floor(Math.min(...ys) / 20) * 20;
  const y1 = Math.ceil(Math.max(...ys) / 20) * 20;
  return {
    x0: yearOf(opts.startISO),
    x1: yearOf(opts.endISO),
    y0,
    y1,
    left: opts.pad.l,
    right: opts.width - opts.pad.r,
    top: opts.pad.t,
    bottom: opts.height - opts.pad.b,
  };
}

export const sx = (s: Scale, year: number): number => s.left + ((year - s.x0) / (s.x1 - s.x0)) * (s.right - s.left);
export const sy = (s: Scale, eci: number): number => s.bottom - ((eci - s.y0) / (s.y1 - s.y0)) * (s.bottom - s.top);

/** The frontier as an SVG step path: flat until the next record, then straight up to it. */
export function frontierPath(s: Scale, front: CapabilityPoint[], endISO: string): string {
  if (front.length === 0) return '';
  const r = (n: number) => Math.round(n * 10) / 10;
  let d = `M${r(sx(s, yearOf(front[0].date)))} ${r(sy(s, front[0].eci))}`;
  for (let i = 1; i < front.length; i++) {
    const x = r(sx(s, yearOf(front[i].date)));
    d += `H${x}V${r(sy(s, front[i].eci))}`;
  }
  return `${d}H${r(sx(s, yearOf(endISO)))}`;
}

/**
 * Which frontier models get a printed name. All of them would collide, so a name is kept only if
 * it sits at least `minGap` SVG units to the right of the last kept one; the first and the last
 * are always kept. Deterministic.
 */
export function labeledFrontier(s: Scale, front: CapabilityPoint[], minGap: number): CapabilityPoint[] {
  if (front.length <= 2) return [...front];
  const keep: CapabilityPoint[] = [front[0]];
  const lastX = sx(s, yearOf(front[front.length - 1].date));
  for (let i = 1; i < front.length - 1; i++) {
    const x = sx(s, yearOf(front[i].date));
    const prev = sx(s, yearOf(keep[keep.length - 1].date));
    if (x - prev >= minGap && lastX - x >= minGap) keep.push(front[i]);
  }
  keep.push(front[front.length - 1]);
  return keep;
}

export interface FrontierChange {
  fromISO: string;
  toISO: string;
  from: number;
  to: number;
  points: number;
  months: number;
}

/** How far the frontier moved between two dates. The site's own subtraction, labeled as such. */
export function frontierChange(front: CapabilityPoint[], fromISO: string, toISO: string): FrontierChange | null {
  const a = frontierAt(front, fromISO);
  const b = frontierAt(front, toISO);
  if (a === null || b === null) return null;
  const months = Math.round((yearOf(toISO) - yearOf(fromISO)) * 12);
  return { fromISO, toISO, from: a, to: b, points: Math.round((b - a) * 10) / 10, months };
}
