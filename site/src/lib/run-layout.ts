import type { RunData } from '../components/islands/RunDiagram';

/** Reflow only unambiguous linear chains; preserve authored branches and loops. */
export function responsiveRunLayouts(data: RunData): { wide: RunData; narrow: RunData } | null {
  const ordered = [...data.nodes].sort((a, b) => a.y - b.y);
  if (ordered.length < 5 || new Set(ordered.map(n => n.x)).size !== 1 ||
      new Set(ordered.map(n => n.y)).size !== ordered.length || data.edges.length !== ordered.length - 1 ||
      data.edges.some(e => e.b) ||
      !ordered.slice(1).every((n, i) => data.edges.some(e => e.f === ordered[i].id && e.t === n.id))) return null;
  const wideNodes = ordered.map((n, i) => {
    const row = Math.floor(i / 3), col = i % 3;
    return { ...n, x: 90 + (row % 2 ? 2 - col : col) * 200, y: 40 + row * 100 };
  });
  return {
    wide: { ...data, nodes: wideNodes, h: Math.ceil(ordered.length / 3) * 100 - 20 },
    narrow: { ...data, nodes: ordered.map((n, i) => ({ ...n, x: 170, y: 30 + i * 72 })), h: 60 + (ordered.length - 1) * 72 },
  };
}
