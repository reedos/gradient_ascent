import { useMemo } from 'react';
import { url } from '../../lib/url';

/**
 * The isometric hero: eight stepped slabs, widest at the base, each marked with a small glyph
 * of what happens at that level. Ported line-for-line from prototype/look.src.html's iso/tile/
 * cube/node/ring/GLYPHS/renderArt functions, from string-building to React.
 *
 * Each slab is a real link to /levels/<n>/ (works with JavaScript off). With JS on, clicking a
 * slab also tells LevelExplorer to select that level in place and scrolls the levels section
 * into view, via a small window CustomEvent ("ga:selectLevel") LevelExplorer listens for.
 */

type Point = [number, number];

const ISO = { T: [214, -24] as Point, U: [145, 80] as Point, V: [-142, 80] as Point };

function iso(a: number, b: number, z = 0): Point {
  return [ISO.T[0] + a * ISO.U[0] + b * ISO.V[0], ISO.T[1] + a * ISO.U[1] + b * ISO.V[1] - z];
}
const f1 = (n: number) => n.toFixed(1);
const pts = (l: Point[]) => l.map((p) => `${f1(p[0])},${f1(p[1])}`).join(' ');
const seg = (p: Point, q: Point, dash = false) =>
  `<path d="M${pts([p])} L${pts([q])}" fill="none" stroke="currentColor"${dash ? ' stroke-dasharray="3.5 3.5"' : ''}/>`;
function head(p: Point, q: Point): string {
  const dx = q[0] - p[0],
    dy = q[1] - p[1],
    l = Math.hypot(dx, dy),
    ux = dx / l,
    uy = dy / l,
    bx = q[0] - ux * 7,
    by = q[1] - uy * 7;
  return `<path d="M${f1(bx - uy * 3.2)},${f1(by + ux * 3.2)} L${pts([q])} L${f1(bx + uy * 3.2)},${f1(by - ux * 3.2)}" fill="none" stroke="currentColor"/>`;
}
const arrow = (p: Point, q: Point, dash = false) => seg(p, q, dash) + head(p, q);
function tile(a: number, b: number, h: number, z = 0, op = 0.16): string {
  const c: Point[] = [iso(a - h, b - h, z), iso(a + h, b - h, z), iso(a + h, b + h, z), iso(a - h, b + h, z)];
  return `<polygon points="${pts(c)}" fill="var(--bg)" fill-opacity=".5"/><polygon points="${pts(c)}" fill="currentColor" fill-opacity="${op}" stroke="currentColor"/>`;
}
function cube(a: number, b: number, h: number, t: number): string {
  const W = iso(a - h, b + h),
    S = iso(a + h, b + h),
    E = iso(a + h, b - h),
    W2 = iso(a - h, b + h, t),
    S2 = iso(a + h, b + h, t),
    E2 = iso(a + h, b - h, t);
  return (
    `<polygon points="${pts([W2, S2, S, W])}" fill="currentColor" fill-opacity=".3" stroke="currentColor"/>` +
    `<polygon points="${pts([S2, E2, E, S])}" fill="currentColor" fill-opacity=".12" stroke="currentColor"/>` +
    tile(a, b, h, t, 0.4)
  );
}
function node(a: number, b: number, r = 4.5, z = 15, withRing = false): string {
  const p = iso(a, b),
    q = iso(a, b, z);
  return (
    `<ellipse cx="${f1(p[0])}" cy="${f1(p[1])}" rx="${r * 1.3}" ry="${r * 0.7}" fill="currentColor" fill-opacity=".18"/>` +
    `<path d="M${pts([p])} L${pts([q])}" stroke="currentColor" stroke-opacity=".55"/>` +
    (withRing ? `<circle cx="${f1(q[0])}" cy="${f1(q[1])}" r="${r + 4.5}" fill="none" stroke="currentColor" stroke-opacity=".5"/>` : '') +
    `<circle cx="${f1(q[0])}" cy="${f1(q[1])}" r="${r}" fill="currentColor"/>`
  );
}
function ring(rho: number, t0: number, t1: number, dash = false): string {
  let d = '';
  for (let k = 0; k <= 36; k++) {
    const t = (t0 + (k / 36) * (t1 - t0)) * Math.PI;
    const p = iso(0.5 + rho * Math.cos(t), 0.5 + rho * Math.sin(t));
    d += (k ? 'L' : 'M') + f1(p[0]) + ',' + f1(p[1]);
  }
  return `<path d="${d}" fill="none" stroke="currentColor"${dash ? ' stroke-dasharray="3.5 3.5"' : ''}/>`;
}
const onRing = (rho: number, t: number): [number, number] => [0.5 + rho * Math.cos(t * Math.PI), 0.5 + rho * Math.sin(t * Math.PI)];

const GLYPHS: (() => string)[] = [
  () =>
    tile(0.5, 0.5, 0.25, 0, 0.1) +
    [0.34, 0.5, 0.66].map((b) => tile(0.33, b, 0.035, 0, 0.5) + seg(iso(0.42, b), iso(0.7, b))).join(''),
  () => arrow(iso(0.08, 0.5), iso(0.38, 0.5)) + arrow(iso(0.62, 0.5), iso(0.92, 0.5)) + node(0.5, 0.5, 6, 16, true),
  () =>
    tile(0.28, 0.5, 0.14, 0, 0.12) +
    tile(0.28, 0.5, 0.14, 6, 0.18) +
    tile(0.28, 0.5, 0.14, 12, 0.26) +
    seg(iso(0.2, 0.44, 12), iso(0.36, 0.44, 12)) +
    seg(iso(0.2, 0.56, 12), iso(0.32, 0.56, 12)) +
    arrow(iso(0.46, 0.5), iso(0.64, 0.5)) +
    node(0.76, 0.5, 6, 16, true),
  () =>
    seg(iso(0.16, 0.5), iso(0.4, 0.5)) +
    seg(iso(0.4, 0.5), iso(0.64, 0.28)) +
    seg(iso(0.4, 0.5), iso(0.64, 0.72)) +
    seg(iso(0.64, 0.28), iso(0.88, 0.5)) +
    seg(iso(0.64, 0.72), iso(0.88, 0.5)) +
    ([[0.16, 0.5], [0.4, 0.5], [0.64, 0.28], [0.64, 0.72], [0.88, 0.5]] as Point[])
      .map((p) => tile(p[0], p[1], 0.07, 0, 0.32))
      .join(''),
  () =>
    ([[0.7, 0.22], [0.8, 0.55], [0.62, 0.82]] as Point[]).map((p) => seg(iso(0.3, 0.5), iso(p[0], p[1]), true)).join('') +
    ([[0.7, 0.22], [0.8, 0.55], [0.62, 0.82]] as Point[]).map((p) => cube(p[0], p[1], 0.07, 13)).join('') +
    node(0.3, 0.5, 6, 16, true),
  () => {
    const a = onRing(0.33, 1.33),
      b = onRing(0.33, 1.37),
      c1 = onRing(0.33, 0.15),
      c2 = onRing(0.33, 0.8);
    return (
      ring(0.33, -0.35, 1.37, true) +
      head(iso(a[0], a[1]), iso(b[0], b[1])) +
      cube(c1[0], c1[1], 0.055, 10) +
      cube(c2[0], c2[1], 0.055, 10) +
      node(0.5, 0.5, 6, 18, true)
    );
  },
  () => {
    const w = [0, 1, 2, 3, 4].map((k) => onRing(0.34, (k / 5) * 2 + 0.1));
    return (
      w.map((p) => seg(iso(0.5, 0.5), iso(p[0], p[1]), true)).join('') +
      w.map((p, k) => seg(iso(p[0], p[1]), iso(w[(k + 1) % 5][0], w[(k + 1) % 5][1]), true)).join('') +
      w.map((p) => node(p[0], p[1], 4.2, 13)).join('') +
      node(0.5, 0.5, 6.5, 22, true)
    );
  },
  () => {
    let ticks = '';
    for (let k = 0; k < 12; k++) {
      const p = onRing(0.3, k / 6),
        q = onRing(k % 3 ? 0.345 : 0.37, k / 6);
      ticks += seg(iso(p[0], p[1]), iso(q[0], q[1]));
    }
    const h1 = onRing(0.2, 1.5),
      h2 = onRing(0.26, 0.17);
    return ring(0.3, 0, 2, true) + ticks + seg(iso(0.5, 0.5), iso(h1[0], h1[1])) + seg(iso(0.5, 0.5), iso(h2[0], h2[1])) + node(0.5, 0.5, 6, 18, true);
  },
];

const pad = (n: number) => String(n).padStart(2, '0');

export interface LevelStackItem {
  order: number;
  title: string;
  short: string;
}

interface Props {
  levels: LevelStackItem[];
}

const SIDE = 'm72 56 142 82 145-82v16l-145 82L72 72z';
const TOP = 'm72 56 142-80 145 80-145 82z';
const INSET = 'm91 56 123-69 126 69-126 70z';
const GAP = 63;
const Y0 = 478;

function selectLevel(order: number) {
  window.dispatchEvent(new CustomEvent('ga:selectLevel', { detail: { level: order } }));
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.getElementById('levels')?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
}

export default function LevelStack({ levels }: Props) {
  const grid = useMemo(() => {
    let g = '';
    for (let k = 0; k < 12; k++) {
      const x = -40 + 35 * k;
      g += `<path d="M${x} 395l250 145M${x + 70} 540l250-145"/>`;
    }
    return g;
  }, []);

  const defs = useMemo(
    () =>
      levels
        .map((o) => {
          const c = `var(--o${o.order})`;
          return `<linearGradient id="f${o.order}" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${c}" stop-opacity=".22"/><stop offset="1" stop-color="${c}" stop-opacity=".035"/></linearGradient>`;
        })
        .join(''),
    [levels],
  );

  return (
    <svg
      className="stack-svg"
      viewBox="0 0 585 710"
      role="group"
      aria-label="The eight levels as a stepped stack, widest at the base, each marked with a symbol of what happens at that level"
    >
      <defs dangerouslySetInnerHTML={{ __html: defs }} />
      <radialGradient id="halo">
        <stop stopColor="var(--accent)" stopOpacity=".16" />
        <stop offset="1" stopColor="var(--accent)" stopOpacity="0" />
      </radialGradient>
      <ellipse cx={225} cy={440} rx={260} ry={270} fill="url(#halo)" />
      <g transform={`translate(0 ${Y0 - 354})`} fill="none" stroke="var(--muted)" strokeOpacity={0.12} strokeWidth={0.6} dangerouslySetInnerHTML={{ __html: grid }} />
      <path d="M214 20v670" stroke="var(--muted)" strokeOpacity={0.3} strokeDasharray="3 5" />
      {levels.map((o) => {
        const c = `var(--o${o.order})`;
        const Y = Y0 - o.order * GAP;
        const s = 1 - o.order * 0.054;
        const cx = (214 + 145 * s).toFixed(1);
        return (
          <a
            key={o.order}
            className="slab"
            href={url(`/levels/${o.order}/`)}
            aria-label={`Level ${o.order}: ${o.title}`}
            style={{ color: c }}
            onClick={(e) => {
              if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
              e.preventDefault();
              selectLevel(o.order);
            }}
          >
            <g transform={`translate(0 ${Y})`}>
              <g transform={`translate(214 57) scale(${s.toFixed(3)}) translate(-214 -57)`}>
                <path d={SIDE} fill={c} fillOpacity={0.12} stroke={c} strokeOpacity={0.4} />
                <path className="slab-top" d={TOP} fill={`url(#f${o.order})`} stroke={c} strokeOpacity={0.65} />
                <path d={INSET} fill="none" stroke={c} strokeOpacity={0.15} strokeDasharray="2 4" />
                <g className="glyph" transform="translate(0 18)" dangerouslySetInnerHTML={{ __html: GLYPHS[o.order]() }} />
              </g>
              <circle cx={cx} cy={56} r={2.5} fill={c} />
              <path d={`M${+cx + 7} 56H382l12-9h16`} fill="none" stroke={c} strokeOpacity={0.45} />
              <rect x={410} y={22} width={170} height={58} fill="transparent" />
              <text x={418} y={39} fontSize={10} fill={c} opacity={0.75}>
                {pad(o.order)}
              </text>
              <text x={418} y={57} fontSize={14.5} fill="var(--text)">
                {o.title} &#8599;
              </text>
              <text x={418} y={73} fontSize={10} fill="var(--muted)">
                {o.short}
              </text>
            </g>
          </a>
        );
      })}
    </svg>
  );
}
