import { useEffect, useRef, useState } from 'react';
import { responsiveRunLayouts } from '../../lib/run-layout';

/**
 * The diagram and the trace player as one component: nodes, edges, steps, scrubber, play,
 * a count of how many steps so far were chosen by the model, the legend, the "Use it / Build
 * it" lane switch and the "when to move up / what it cost" block. Ported from the prototype's
 * DIAGRAMS/renderDiagram/setStep/renderLane. Takes one or more run definitions as props (the
 * prototype's Level 2 RAG vs Level 5 Agentic RAG filter lives here too, since it is part of the
 * same trace player). Every run carries `illustrative: true`; the notice below the diagram says
 * so, matching the prototype.
 */

/**
 * The fixed shapes of the project plan's visual system. `human` is a person in the flow — an approver, a
 * reviewer — and is drawn as a rounded solid node with a PERSON kicker and a small figure, so it
 * reads apart from `io` (rounded, dashed: where the run starts and ends) at a glance and at
 * 390 px. Same stroke weight and same colors as every other node: nothing here is new ink.
 */
export type NodeKind = 'io' | 'code' | 'model' | 'tool' | 'store' | 'human';
export interface RunNode {
  id: string;
  x: number;
  y: number;
  l: string;
  k: NodeKind;
  w?: number;
  h?: number;
}
export interface RunEdge {
  id: string;
  f: string;
  t: string;
  by: 'code' | 'model';
  b?: number;
}
export interface RunStep {
  e: string;
  h: string;
  d: string;
  m: string;
}
export interface RunLane {
  t: string;
  p?: string;
  code?: string;
  names: string[];
}
export interface RunData {
  illustrative: boolean;
  /** Set only where the diagram plays more model-decided steps than the example's trace
   *  records, because one model call selected more than one transition. Printed under the
   *  tally; scripts/validate.py requires it whenever the two counts differ. */
  trace_note?: string;
  h: number;
  title: string;
  sub: string;
  pill: string;
  nodes: RunNode[];
  edges: RunEdge[];
  steps: RunStep[];
  /** Home-page comparison only. A technique page's run file leaves these four out. */
  climbT?: string;
  climb?: string;
  use?: RunLane;
  build?: RunLane;
}
export interface RunDef {
  key: string;
  label: string;
  data: RunData;
  /** Whether the pill should read as a model-chosen category (accent styling). */
  accentPill?: boolean;
}

interface Props {
  runs: RunDef[];
  /**
   * Whether to render the player's own "Use it / Build it" panel. The home page has no other
   * lane switch, so it wants one. A technique page wraps its whole body in <Lanes>, and a
   * second switch 30 px below the first -- with its own copy of the Use it opening paragraph
   * and its own list of names -- was two controls doing different things under one label.
   * Run.astro passes false; the block's content lives in the page's own lanes and in the
   * generated "Out there" section instead.
   */
  lanes?: boolean;
}

type Pt = [number, number];

function edgePoint(n: RunNode, tx: number, ty: number): Pt {
  const w = (n.w ?? 132) / 2,
    h = (n.h ?? 38) / 2,
    dx = tx - n.x,
    dy = ty - n.y;
  const s = Math.min(w / Math.abs(dx || 1e-6), h / Math.abs(dy || 1e-6));
  return [n.x + dx * s, n.y + dy * s];
}

function edgeGeometry(D: RunData, e: RunEdge) {
  const a = D.nodes.find((n) => n.id === e.f)!;
  const b = D.nodes.find((n) => n.id === e.t)!;
  const mx = (a.x + b.x) / 2,
    my = (a.y + b.y) / 2,
    dx = b.x - a.x,
    dy = b.y - a.y,
    len = Math.hypot(dx, dy) || 1,
    bend = e.b || 0;
  const cx = mx - (dy / len) * bend,
    cy = my + (dx / len) * bend;
  const p1 = edgePoint(a, cx, cy),
    p2raw = edgePoint(b, cx, cy);
  const ux = p2raw[0] - cx,
    uy = p2raw[1] - cy,
    ul = Math.hypot(ux, uy) || 1;
  const p2: Pt = [p2raw[0] - (ux / ul) * 4, p2raw[1] - (uy / ul) * 4];
  return { p1, c: [cx, cy] as Pt, p2 };
}
const f1 = (n: number) => n.toFixed(1);
function pathString(p1: Pt, c: Pt, p2: Pt): string {
  return `M${f1(p1[0])},${f1(p1[1])} Q${f1(c[0])},${f1(c[1])} ${f1(p2[0])},${f1(p2[1])}`;
}
function bezierPoint(p1: Pt, c: Pt, p2: Pt, t: number): Pt {
  const u = 1 - t;
  return [u * u * p1[0] + 2 * u * t * c[0] + t * t * p2[0], u * u * p1[1] + 2 * u * t * c[1] + t * t * p2[1]];
}

// The node box is a fixed 132 units and the label was a single <text> at 11.5px, so any label
// past roughly 22 characters rendered outside its own box at every width -- a dozen run files
// were doing it, and a writer had no way to know the limit except by screenshotting. Labels now
// wrap onto two lines inside the box, and shrink only if two lines still do not fit. The full
// string is always in a <title>, so nothing is lost to a reader who hovers or uses a screen
// reader even when a label is squeezed.
const LINE_MAX = 118; // 132 less a little breathing room at each edge
const CHAR_W = 5.95; // ~0.52em at 11.5px in the site's own face; checked against the built SVGs
const MIN_FONT = 9.5;

/** One line, or the two-line split whose longer half is shortest. Splits on spaces only. */
export function wrapLabel(l: string, maxWidth = LINE_MAX): string[] {
  if (l.length * CHAR_W <= maxWidth) return [l];
  const words = l.split(' ');
  if (words.length < 2) return [l];
  let best: [string, string] | null = null;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(' ');
    const b = words.slice(i).join(' ');
    if (!best || Math.max(a.length, b.length) < Math.max(best[0].length, best[1].length)) {
      best = [a, b];
    }
  }
  return best!;
}

/** 11.5, or smaller when even the wrapped lines overrun the box. Never below MIN_FONT. */
export function labelFontSize(lines: string[], maxWidth = LINE_MAX): number {
  const widest = Math.max(...lines.map((s) => s.length)) * CHAR_W;
  if (widest <= maxWidth) return 11.5;
  return Math.max(MIN_FONT, Math.round((11.5 * maxWidth) / widest / 0.1) * 0.1);
}

function NodeShape({ n }: { n: RunNode }) {
  const width = n.w ?? 132, height = n.h ?? 38;
  const x = n.x - width / 2,
    y = n.y - height / 2;
  const kick = n.k === 'model' ? 'MODEL' : n.k === 'tool' ? 'TOOL' : n.k === 'human' ? 'PERSON' : '';
  const textWidth = n.w ? width - 28 : LINE_MAX;
  const lines = wrapLabel(n.l, textWidth);
  const font = labelFontSize(lines, textWidth);
  // Two lines straddle the single-line baseline so the block stays vertically centered in the box.
  const lead = font * (n.h ? 1.2 : 0.96);
  return (
    <g className={`nd ${n.k}`} data-id={n.id}>
      {n.k === 'store' ? (
        <path d={`M${x},${y + 6} v${height - 12} a${width / 2},7 0 0 0 ${width},0 v-${height - 12} a${width / 2},7 0 0 0 -${width},0 a${width / 2},7 0 0 0 ${width},0`} />
      ) : (
        <rect x={x} y={y} width={width} height={height} rx={n.k === 'io' || n.k === 'human' ? height / 2 : 6} />
      )}
      {n.k === 'human' && (
        // head and shoulders, inside the node's left edge, clear of the centered label
        <g className="fig">
          <circle cx={x + 12} cy={n.y - 3} r={3} />
          <path d={`M${x + 6},${n.y + 8} a6,6 0 0 1 12,0`} />
        </g>
      )}
      {kick && (
        <text className="k" x={n.x} y={n.y - (n.h ? 16 : 8)}>
          {kick}
        </text>
      )}
      <text
        x={n.x}
        y={n.y + (kick ? 6 : n.k === 'store' ? 5 : 0.5)}
        style={font === 11.5 ? undefined : { fontSize: `${font}px` }}
      >
        <title>{n.l}</title>
        {lines.length === 1
          ? n.l
          : lines.map((line, i) => (
              <tspan key={line + i} x={n.x} dy={i === 0 ? -lead / 2 : lead}>
                {line}
              </tspan>
            ))}
      </text>
    </g>
  );
}

const pad = (n: number) => String(n).padStart(2, '0');

function FlowSvg({ D, S, seen, markerPrefix, pulseT, className = '' }: {
  D: RunData; S: RunStep; seen: Set<string>; markerPrefix: string; pulseT: number; className?: string;
}) {
  const minX = Math.min(0, ...D.nodes.map(n => n.x - (n.w ?? 132) / 2 - 12));
  const maxX = Math.max(340, ...D.nodes.map(n => n.x + (n.w ?? 132) / 2 + 12));
  const E = D.edges.find(e => e.id === S.e)!;
  const geo = edgeGeometry(D, E);
  const pulse = bezierPoint(geo.p1, geo.c, geo.p2, pulseT);
  return (
          <svg className={className} viewBox={`${minX} 0 ${maxX - minX} ${D.h}`} role="img" aria-label={`Diagram of ${D.title}`}>
            <defs>
              {(['idle', 'code', 'model'] as const).map((kind) => (
                <marker
                  key={kind}
                  id={`${markerPrefix}-${kind}`}
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerUnits="userSpaceOnUse"
                  markerWidth="8"
                  markerHeight="8"
                  orient="auto-start-reverse"
                >
                  <path className={`mk-${kind}`} d="M0,1 L9,5 L0,9 z" />
                </marker>
              ))}
            </defs>
            {D.edges.map((e) => {
              const now = e.id === S.e;
              const was = seen.has(e.id);
              const g = edgeGeometry(D, e);
              const markerState = now || was ? e.by : 'idle';
              return (
                <path
                  key={e.id}
                  className={`ed ${e.by}${now ? ' now' : ''}${was && !now ? ' seen' : ''}`}
                  data-id={e.id}
                  d={pathString(g.p1, g.c, g.p2)}
                  markerEnd={`url(#${markerPrefix}-${markerState})`}
                />
              );
            })}
            {D.nodes.map((n) => (
              <NodeShape n={{ ...n }} key={n.id} />
            ))}
            <circle className={`pulse${E.by === 'model' ? ' model' : ''}`} r={3.5} cx={pulse[0]} cy={pulse[1]} />
          </svg>
  );
}

export default function RunDiagram({ runs, lanes = true }: Props) {
  const [runIndex, setRunIndex] = useState(0);
  const [step, setStepRaw] = useState(0);
  const [lane, setLane] = useState<'use' | 'build'>('use');
  const [playing, setPlaying] = useState(false);
  const [pulseT, setPulseT] = useState(1);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const rafRef = useRef<number | null>(null);

  // SVG marker ids are document-wide, not scoped to their own <svg>. A recipe page renders two
  // RunDiagram islands, so a fixed "mk-code" appeared three times per page and the second
  // diagram's arrows pointed at the first diagram's markers. Keying them by the run set this
  // instance shows makes them unique per island and stable between server render and hydration.
  const markerPrefix = `mk-${runs.map((r) => r.key).join('-')}`;

  const run = runs[runIndex];
  const D = run.data;
  const S = D.steps[step];
  const E = D.edges.find((e) => e.id === S.e)!;
  const seen = new Set(D.steps.slice(0, step).map((s) => s.e));
  const mcount = D.steps.slice(0, step + 1).filter((s) => D.edges.find((e) => e.id === s.e)!.by === 'model').length;

  function stop() {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setPlaying(false);
  }

  function chooseRun(i: number) {
    stop();
    setRunIndex(i);
    setStepRaw(0);
    setLane('use');
  }

  function goToStep(i: number) {
    setStepRaw(Math.max(0, Math.min(D.steps.length - 1, i)));
  }

  function prev() {
    stop();
    goToStep(step - 1);
  }
  function next() {
    stop();
    goToStep(step + 1);
  }
  function scrub(e: React.ChangeEvent<HTMLInputElement>) {
    stop();
    goToStep(Number(e.currentTarget.value));
  }
  function play() {
    if (timerRef.current) {
      stop();
      return;
    }
    if (step === D.steps.length - 1) goToStep(0);
    setPlaying(true);
    timerRef.current = setInterval(() => {
      setStepRaw((s) => {
        if (s >= D.steps.length - 1) {
          stop();
          return s;
        }
        return s + 1;
      });
    }, 1500);
  }

  useEffect(() => stop, [runIndex]);

  // Animate the pulse along the current edge each time the step changes.
  useEffect(() => {
    const reduce = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setPulseT(1);
      return;
    }
    setPulseT(0);
    const t0 = performance.now();
    function tick(t: number) {
      const k = Math.min(1, (t - t0) / 520);
      const ez = 1 - Math.pow(1 - k, 3);
      setPulseT(ez);
      if (k < 1) rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runIndex, step]);

  const layouts = responsiveRunLayouts(D);
  const laneData = D[lane];

  return (
    <>
      {runs.length > 1 && (
        <div className="filters" role="group" aria-label="Which level to run">
          {runs.map((r, i) => (
            <button key={r.key} className="filter" aria-pressed={i === runIndex} onClick={() => chooseRun(i)}>
              {r.label}
            </button>
          ))}
        </div>
      )}
      <div className="outlook-grid run-player">
        <div className="panel dia">
          <div className="panel-heading">
            <div>
              <h3>{D.title}</h3>
              <p>{D.sub}</p>
            </div>
            <span className={`pill${run.accentPill ? ' model' : ''}`}>{D.pill}</span>
          </div>
          {layouts ? <>
            <FlowSvg D={layouts.wide} S={S} seen={seen} markerPrefix={`${markerPrefix}-wide`} pulseT={pulseT} className="run-svg-wide" />
            <FlowSvg D={layouts.narrow} S={S} seen={seen} markerPrefix={`${markerPrefix}-narrow`} pulseT={pulseT} className="run-svg-narrow" />
          </> : <FlowSvg D={D} S={S} seen={seen} markerPrefix={markerPrefix} pulseT={pulseT} />}

          <div className="tally">
            <b className={mcount === 0 ? 'zero' : ''}>{mcount}</b>
            <span>
              of {step + 1} {step ? 'steps' : 'step'} so far chosen by the model
            </span>
          </div>
          {D.trace_note && <p className="step-notice">{D.trace_note}</p>}
          <div className="legend">
            <span>
              <i />
              your code chose this step
            </span>
            <span>
              <i className="m" />
              the model chose this step
            </span>
          </div>
        </div>
        <div className="panel run-trace">
          <div className="panel-heading">
            <div>
              <h3>The run, step by step</h3>
              <p>
                {D.illustrative
                  ? 'This trace is an illustration. On the finished site every trace will be a recording of a real run.'
                  : 'Recorded run.'}
              </p>
            </div>
          </div>
          <div className="controls">
            <button onClick={prev} disabled={step === 0} aria-label="Previous step">
              &#8592;
            </button>
            <button onClick={play}>{playing ? 'Pause' : 'Play'}</button>
            <button onClick={next} disabled={step === D.steps.length - 1} aria-label="Next step">
              &#8594;
            </button>
            <input type="range" min={0} max={D.steps.length - 1} step={1} value={step} onChange={scrub} aria-label="Move through the run" />
          </div>
          <div className="step">
            <div className="step-top">
              <span className="step-i">
                STEP {pad(step + 1)} / {pad(D.steps.length)}
              </span>
              <span className={`pill${E.by === 'model' ? ' model' : ''}`}>{E.by === 'model' ? 'The model chose' : 'Your code chose'}</span>
            </div>
            <h4>{S.h}</h4>
            <pre>{S.d}</pre>
            <div className="step-m">{S.m}</div>
          </div>
        </div>
      </div>
      {/* The climb note and the lane panel belong to the home page's two-run comparison. A
          technique page gets "Move up when" from the taxonomy's relations instead, so showing
          the note there said the same thing twice. */}
      {lanes && (
      <div className="lane-grid">
        <div className="connection">
          <strong>{D.climbT}</strong>
          {D.climb}
        </div>
        {laneData && (
        <div className="panel lane">
          <div className="panel-heading">
            <div>
              <h3>{laneData.t}</h3>
            </div>
            <div className="filters" role="group" aria-label="Reading lane" style={{ margin: 0 }}>
              <button className="filter" aria-pressed={lane === 'use'} onClick={() => setLane('use')}>
                Use it
              </button>
              <button className="filter" aria-pressed={lane === 'build'} onClick={() => setLane('build')}>
                Build it
              </button>
            </div>
          </div>
          {lane === 'use' ? <p>{laneData.p}</p> : <pre>{laneData.code}</pre>}
          <div className="names">
            {laneData.names.map((n) => (
              <span key={n}>{n}</span>
            ))}
          </div>
        </div>
        )}
      </div>
      )}
    </>
  );
}
