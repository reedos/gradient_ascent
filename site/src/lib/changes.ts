// Typed access to content/changes.json, the record of what changed on this site and why it
// matters to somebody reading it.
//
// The plan puts a living layer on the site, fed by a runner that reads the field and proposes
// updates. That half waits. This is the half that needs no model: a hand-written, dated log, a
// page, and a feed a reader can subscribe to so they learn a page was corrected without coming
// back to check.
//
// Entries are written for a reader. They say what is different and what it is good for, never
// what a commit did, and they never describe how the site is made. docs/CHANGES.md is the
// instruction for adding one.
//
// Everything here is pure: data in, strings out. site/tests/changes.test.ts drives it under plain
// `node --test`, including the Atom rendering, which is the part most likely to break quietly.
import data from '../../../content/changes.json' with { type: 'json' };
import { usDate } from './dates.ts';

export interface ChangePage {
  label: string;
  /** Site-relative path starting with "/". The caller runs it through url(). */
  path: string;
}

export interface Change {
  id: string;
  /** ISO date. Several entries may share one. */
  date: string;
  title: string;
  /** What is different now. */
  what: string;
  /** Why a reader should care. */
  why: string;
  pages: ChangePage[];
}

interface ChangesFile {
  version: number;
  as_of: string;
  note: string;
  changes: Change[];
}

const file = data as ChangesFile;

export const changesAsOf: string = file.as_of;
export const changesNote: string = file.note;

/**
 * Every entry, newest first. Array.prototype.sort is stable, so entries that share a date keep
 * the order they have in the file: the file is the tiebreak, which makes a same-day reordering a
 * visible edit rather than a surprise.
 */
export const changes: Change[] = [...file.changes].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

/** Entries grouped under their date, newest date first, each group in file order. */
export function changesByDate(entries: Change[] = changes): { date: string; entries: Change[] }[] {
  const groups: { date: string; entries: Change[] }[] = [];
  for (const entry of entries) {
    const last = groups[groups.length - 1];
    if (last && last.date === entry.date) last.entries.push(entry);
    else groups.push({ date: entry.date, entries: [entry] });
  }
  return groups;
}

/** The date of the newest entry, which is what a feed reports as its own `updated`. */
export function latestChangeDate(entries: Change[] = changes): string {
  return entries.length ? entries[0].date : changesAsOf;
}

/** XML text escaping. Atom is XML, so an unescaped ampersand in a title breaks the whole feed. */
export function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export interface AtomOptions {
  /** Absolute URL of the /changes/ page. */
  pageUrl: string;
  /** Absolute URL of the feed itself. */
  feedUrl: string;
  /** Resolves a site-relative path to an absolute URL. */
  abs: (path: string) => string;
  title?: string;
  subtitle?: string;
}

/**
 * The Atom 1.0 feed. Written by hand rather than with a library: it is forty lines, and a
 * dependency that renders XML is a dependency that has to be kept current for the life of the
 * site.
 *
 * An entry's id is the page URL plus its fragment, which is stable across republishing and is
 * also where the entry actually lives, so a reader clicking through lands on the right block.
 */
export function atomFeed(entries: Change[], options: AtomOptions): string {
  const { pageUrl, feedUrl, abs } = options;
  const title = options.title ?? 'Gradient Ascent: what changed';
  const subtitle =
    options.subtitle ??
    'Dated changes to the site, written for a reader: what is different, and what it is good for.';
  const updated = `${latestChangeDate(entries)}T00:00:00Z`;

  const lines = [
    '<?xml version="1.0" encoding="utf-8"?>',
    '<feed xmlns="http://www.w3.org/2005/Atom">',
    `  <title>${escapeXml(title)}</title>`,
    `  <subtitle>${escapeXml(subtitle)}</subtitle>`,
    `  <id>${escapeXml(pageUrl)}</id>`,
    `  <link rel="alternate" type="text/html" href="${escapeXml(pageUrl)}"/>`,
    `  <link rel="self" type="application/atom+xml" href="${escapeXml(feedUrl)}"/>`,
    `  <updated>${updated}</updated>`,
    '  <author><name>Gradient Ascent</name></author>',
  ];

  for (const entry of entries) {
    const href = `${pageUrl}#${entry.id}`;
    const links = entry.pages.map((p) => `${p.label}: ${abs(p.path)}`).join('\n');
    const body = `${entry.what}\n\n${entry.why}${links ? `\n\n${links}` : ''}`;
    lines.push(
      '  <entry>',
      `    <title>${escapeXml(entry.title)}</title>`,
      `    <id>${escapeXml(href)}</id>`,
      `    <link rel="alternate" type="text/html" href="${escapeXml(href)}"/>`,
      `    <updated>${entry.date}T00:00:00Z</updated>`,
      `    <content type="text">${escapeXml(body)}</content>`,
      '  </entry>',
    );
  }

  lines.push('</feed>');
  return lines.join('\n') + '\n';
}

/** The Markdown twin of /changes/, at /changes.md. */
export function changesMarkdown(entries: Change[], abs: (path: string) => string): string {
  const parts = [
    '# What changed',
    '',
    changesNote,
    '',
  ];
  for (const group of changesByDate(entries)) {
    // House style is month-day-year everywhere a reader sees a date, the .md twin included. The
    // ISO form stays in content/changes.json and in the feed, where a machine reads it.
    parts.push(`## ${usDate(group.date)}`, '');
    for (const entry of group.entries) {
      parts.push(`### ${entry.title}`, '', entry.what, '', entry.why, '');
      for (const page of entry.pages) parts.push(`- [${page.label}](${abs(page.path)})`);
      parts.push('');
    }
  }
  return parts.join('\n');
}
