// Typed access to content/frontier.json: what is unsolved at each level, what people are trying,
// and a primary source for each. The plan asks every level page for a "frontier block", and this
// is where it comes from.
//
// Two rules this file exists to keep:
//   1. It ages. Every level carries its own `as_of`, and both the page and its Markdown twin
//      print it, so a reader can see how old the block is without trusting the site's word that
//      it is current.
//   2. It is sourced. An entry with no source has nothing behind it, so `frontierFor` drops one
//      rather than render an unsupported claim, and the test over the real file asserts there are
//      none to drop.
//
// The rendering is pure: data in, string out, no Astro and no filesystem, so site/tests can
// exercise it under plain `node --test`.
import data from '../../../content/frontier.json';
import { usDate } from './dates';

export interface FrontierSource {
  title: string;
  url: string;
  publisher: string;
  /** The words read on the raw page, exactly. Rendered under the link. */
  quote: string;
  /** ISO date the quotation was last checked against the page. */
  checked: string;
  /** An honest caveat about the source, e.g. that a paper's own wording differs from ours. */
  note?: string;
}

export interface FrontierEntry {
  id: string;
  /** Slug of the technique page this problem belongs to, when it has one. */
  technique?: string;
  problem: string;
  trying: string;
  sources: FrontierSource[];
}

export interface FrontierLevel {
  order: number;
  as_of: string;
  open: FrontierEntry[];
}

interface FrontierFile {
  version: number;
  as_of: string;
  note: string;
  levels: FrontierLevel[];
}

const file = data as FrontierFile;

/** The date the file as a whole was last worked on. Individual levels carry their own. */
export const frontierAsOf: string = file.as_of;

/** Every level that has a block, in level order. */
export const frontierLevels: FrontierLevel[] = [...file.levels].sort((a, b) => a.order - b.order);

/**
 * The block for one level, with unsourced entries removed. A level with no block, or whose
 * entries are all unsourced, comes back undefined so a caller can render nothing at all rather
 * than an empty heading.
 */
export function frontierFor(order: number): FrontierLevel | undefined {
  const level = file.levels.find((l) => l.order === order);
  if (!level) return undefined;
  const open = level.open.filter((e) => e.sources.length > 0);
  if (!open.length) return undefined;
  return { ...level, open };
}

/** True when the block is older than `days` on `today`. Both dates are ISO. */
export function frontierIsStale(asOf: string, today: string, days = 90): boolean {
  const a = Date.parse(`${asOf}T00:00:00Z`);
  const t = Date.parse(`${today}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(t)) return false;
  return (t - a) / 86_400_000 > days;
}

/**
 * The Markdown twin of a level's frontier block, for /levels/<order>.md. Headings match the
 * rendered page's, so a reader's agent and a reader see the same structure. Returns an empty
 * string when the level has no block, so a caller can concatenate it unconditionally.
 */
export function frontierMarkdown(
  level: FrontierLevel | undefined,
  /** Resolves a technique slug to its page title, for the heading. Slug is used if it returns
   *  nothing, and "Open problem" if an entry names no technique at all. */
  titleFor: (slug: string) => string | undefined = () => undefined,
): string {
  if (!level || !level.open.length) return '';
  const parts: string[] = [
    `\n## What is still unsolved at this level\n`,
    `_As of ${usDate(level.as_of)}. This block ages faster than the rest of the page._\n`,
  ];
  for (const entry of level.open) {
    const heading = entry.technique ? titleFor(entry.technique) ?? entry.technique : 'Open problem';
    parts.push(`\n### ${heading}\n`);
    parts.push(`${entry.problem}\n`);
    parts.push(`**What people are trying:** ${entry.trying}\n`);
    for (const source of entry.sources) {
      parts.push(
        `- [${source.title}](${source.url}) · ${source.publisher} · read ${usDate(source.checked)}: "${source.quote}"`,
      );
      if (source.note) parts.push(`  - ${source.note}`);
    }
  }
  return parts.join('\n') + '\n';
}
