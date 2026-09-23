import { dutOverview } from './dut-overview';
import { architectures } from './architecture-models';
import { examplesForTechnique, recipeExampleMarkdown } from './recipe-examples';
// Shared machinery for finish-indexes' generated pages: the failure gallery, the glossary's page
// links, the /llms.txt index, and every /*.md endpoint. Everything here reads MDX **source
// text** at build time (the same way CodeFile.astro reads example source), rather than rendering
// the compiled Astro/JSX output, because a clean Markdown version needs the raw component calls
// -- <FailureModes modes={[...]} />, <Lane>, <CostStrip>, <CodeFile> -- to turn into Markdown
// directly. A parser this site can audit beats importing a full MDX/remark toolchain for one
// build step.
//
// Failure: every function here throws, loudly, the moment a component tag it recognizes cannot
// be parsed (an unmatched brace, a modes array that does not evaluate, a mode missing a field).
// That is deliberate -- see the project plan's Scope control and this task's own instructions: a page
// whose failure-mode block cannot be parsed must fail the build, not silently drop that page's
// failure modes from the gallery.
import { getCollection, getEntry } from 'astro:content';
import { url } from './url';
import { parseLiteral } from './literal';
import { measurementFor } from './results-data';
import { measurementMarkdown, costStats, costCaption, compareWith, costComparedTo } from './results';
import { REPO_URL } from './site';
import {
  techniqueBySlug,
  levels,
  tracks,
  recipes,
  threads,
  teardowns,
  named,
  recipeLevels,
  techniquesForRecipe,
  techniquesForTeardown,
  teardownExpiry,
  relationsFor,
  namesForLevel,
} from './content';
import glossaryData from '../../../content/glossary.json';
import { walkthroughMarkdown } from './walkthrough-markdown';

// ---------------------------------------------------------------------------------------------
// Glossary: content/glossary.json, typed and color-linked the same way content.ts links a
// technique to its level color. scripts/validate.py's validate_glossary enforces the shape
// (unique names, resolvable pages, resolvable `see`, 8-60 word definitions) at commit time; this
// module trusts that and only adds the render-time helpers.
// ---------------------------------------------------------------------------------------------

export interface GlossaryEntry {
  term: string;
  aka?: string[];
  definition: string;
  page: string;
  see?: string[];
}

export const glossaryTerms: GlossaryEntry[] = (glossaryData as { terms: GlossaryEntry[] }).terms;

/** The level color a glossary term's page renders in, e.g. "var(--o2)" or "var(--ot)". */
export function glossaryColor(entry: GlossaryEntry): string {
  const technique = techniqueBySlug(entry.page);
  if (!technique) return 'var(--ot)';
  return technique.level === 'tracks' ? 'var(--ot)' : `var(--o${technique.level})`;
}

/**
 * Where a glossary term's name links, and how that page is labeled beside it. `page` is a
 * technique or topic slug for almost every term, and a thread id for the few whose whole point
 * is that one word names two techniques at once (see scripts/validate.py's validate_glossary).
 * One place decides this, so the glossary page, the Markdown endpoints and the search index
 * cannot each build a different URL for the same term.
 */
export function glossaryTarget(entry: GlossaryEntry): { href: string; label?: string } {
  const technique = techniqueBySlug(entry.page);
  if (technique) return { href: url(`/techniques/${entry.page}/`), label: technique.levelLabel };
  const thread = threads.find((t) => t.id === entry.page);
  if (thread) return { href: url(`/threads/${entry.page}/`), label: 'Thread' };
  return { href: url(`/techniques/${entry.page}/`) };
}

/** A stable id for a term's anchor, e.g. "agentic-rag" for "agentic RAG". Shared by the page
 *  that renders the term and every `see` link that points at it. */
export function glossarySlug(term: string): string {
  return term
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

// `import.meta.url`-relative fs paths (the way CodeFile.astro reads examples/) only work for a
// .astro component: Astro rewrites those at render time, but Vite's own bundler moves a plain
// .ts module like this one into dist/.prerender/chunks/, and a path built from its bundled
// location no longer points at the real repo. `import.meta.glob` sidesteps that: Vite resolves
// the glob against this file's *source* location at build time and inlines the matched files'
// text as static string assets, so the lookup below works the same in dev and in the prerendered
// build. Keyed by everything from "examples/" or "scripts/" onward -- the two directories every
// <CodeFile file="..."> on the site points into -- since Vite's own glob keys vary in prefix
// (relative segments, or an absolute path) depending on how the glob is written.
const codeFileGlob = import.meta.glob(['../../../examples/**/*.{py,md}', '../../../scripts/**/*.py'], {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;
const codeFilesByPath = new Map<string, string>();
for (const [key, content] of Object.entries(codeFileGlob)) {
  const idx = Math.max(key.indexOf('examples/'), key.indexOf('scripts/'));
  if (idx !== -1) codeFilesByPath.set(key.slice(idx), content);
}

// ---------------------------------------------------------------------------------------------
// Low-level tag scanner: finds `<Name ...>`/`<Name ... />`, tracking string and `{}` nesting so
// an attribute value that itself contains braces or quoted `}`/`>` characters does not confuse
// the scan. This is the one routine every extractor below is built on.
// ---------------------------------------------------------------------------------------------

interface TagMatch {
  start: number;
  end: number; // index just past the tag's closing `>` (and, for a paired tag, past `</Name>`)
  attrsRaw: string;
  selfClosing: boolean;
  inner?: string;
}

function findTag(text: string, name: string, from: number): TagMatch | null {
  const openRe = new RegExp(`<${name}(?=[\\s/>])`, 'g');
  openRe.lastIndex = from;
  const m = openRe.exec(text);
  if (!m) return null;
  const start = m.index;
  let i = start + 1 + name.length;
  let depth = 0;
  let quote: string | null = null;
  while (i < text.length) {
    const ch = text[i];
    if (quote) {
      if (ch === '\\') {
        i += 2;
        continue;
      }
      if (ch === quote) quote = null;
      i++;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') {
      quote = ch;
      i++;
      continue;
    }
    if (ch === '{') {
      depth++;
      i++;
      continue;
    }
    if (ch === '}') {
      depth--;
      i++;
      continue;
    }
    if (depth === 0 && ch === '/' && text[i + 1] === '>') {
      return { start, end: i + 2, attrsRaw: text.slice(start + 1 + name.length, i), selfClosing: true };
    }
    if (depth === 0 && ch === '>') {
      const attrsRaw = text.slice(start + 1 + name.length, i);
      const innerStart = i + 1;
      const closeTag = `</${name}>`;
      const closeIdx = text.indexOf(closeTag, innerStart);
      if (closeIdx === -1) {
        throw new Error(`indexes.ts: <${name}> at offset ${start} has no matching ${closeTag}`);
      }
      return {
        start,
        end: closeIdx + closeTag.length,
        attrsRaw,
        selfClosing: false,
        inner: text.slice(innerStart, closeIdx),
      };
    }
    i++;
  }
  throw new Error(`indexes.ts: <${name} ...> starting at offset ${start} in the same file never closes`);
}

function replaceAllTags(text: string, name: string, fn: (m: TagMatch) => string, where: string): string {
  let out = '';
  let pos = 0;
  for (;;) {
    let m: TagMatch | null;
    try {
      m = findTag(text, name, pos);
    } catch (err) {
      throw new Error(`${where}: ${(err as Error).message}`);
    }
    if (!m) {
      out += text.slice(pos);
      break;
    }
    out += text.slice(pos, m.start);
    let replacement: string;
    try {
      replacement = fn(m);
    } catch (err) {
      throw new Error(`${where}: could not parse <${name}> attributes: ${(err as Error).message}`);
    }
    out += replacement;
    pos = m.end;
  }
  return out;
}

type AttrVal = { kind: 'string' | 'expr' | 'bool'; raw: string };

function parseAttrs(attrsRaw: string): Record<string, AttrVal> {
  const out: Record<string, AttrVal> = {};
  let i = 0;
  const n = attrsRaw.length;
  while (i < n) {
    while (i < n && /\s/.test(attrsRaw[i])) i++;
    if (i >= n) break;
    const nameStart = i;
    while (i < n && /[A-Za-z0-9_-]/.test(attrsRaw[i])) i++;
    const attrName = attrsRaw.slice(nameStart, i);
    if (!attrName) {
      i++;
      continue;
    }
    while (i < n && /\s/.test(attrsRaw[i])) i++;
    if (attrsRaw[i] !== '=') {
      out[attrName] = { kind: 'bool', raw: 'true' };
      continue;
    }
    i++;
    while (i < n && /\s/.test(attrsRaw[i])) i++;
    if (attrsRaw[i] === '"' || attrsRaw[i] === "'") {
      const q = attrsRaw[i];
      i++;
      const vs = i;
      while (i < n && attrsRaw[i] !== q) {
        if (attrsRaw[i] === '\\') i++;
        i++;
      }
      out[attrName] = { kind: 'string', raw: attrsRaw.slice(vs, i) };
      i++;
    } else if (attrsRaw[i] === '{') {
      let depth = 0;
      let quote: string | null = null;
      const vs = i;
      while (i < n) {
        const ch = attrsRaw[i];
        if (quote) {
          if (ch === '\\') {
            i += 2;
            continue;
          }
          if (ch === quote) quote = null;
          i++;
          continue;
        }
        if (ch === '"' || ch === "'" || ch === '`') {
          quote = ch;
          i++;
          continue;
        }
        if (ch === '{') {
          depth++;
          i++;
          continue;
        }
        if (ch === '}') {
          depth--;
          i++;
          if (depth === 0) break;
          continue;
        }
        i++;
      }
      out[attrName] = { kind: 'expr', raw: attrsRaw.slice(vs + 1, i - 1) };
    } else {
      i++;
    }
  }
  return out;
}

/**
 * Read a data literal an MDX file wrote in `{...}` -- an array, object, string, number or
 * boolean. This used to be `new Function("return (" + raw + ")")`. It is now a parser that can
 * only produce data (./literal.ts): no identifiers, no calls, no operators, no template
 * substitutions. Anything else throws, and every caller below turns that into a build failure
 * naming the file, so a prop that is not a literal stops the build rather than silently dropping
 * that page's block from the gallery.
 */
function evalExpr(raw: string): unknown {
  return parseLiteral(raw);
}

function attrString(attrs: Record<string, AttrVal>, name: string): string | undefined {
  const a = attrs[name];
  if (!a) return undefined;
  if (a.kind === 'string') return a.raw;
  if (a.kind === 'expr') return String(evalExpr(a.raw));
  return undefined;
}

function attrExpr(attrs: Record<string, AttrVal>, name: string): unknown {
  const a = attrs[name];
  if (!a) return undefined;
  return a.kind === 'expr' ? evalExpr(a.raw) : a.raw;
}

// ---------------------------------------------------------------------------------------------
// Failure modes: collected across every technique MDX file for the /failures/ gallery, and
// reused when flattening one page's own <FailureModes> block into Markdown.
// ---------------------------------------------------------------------------------------------

export interface FailureMode {
  name: string;
  notice: string;
  test: string;
  slug: string;
  title: string;
  level: number | 'tracks';
  levelLabel: string;
  color: string;
}

function colorOf(level: number | 'tracks'): string {
  return level === 'tracks' ? 'var(--ot)' : `var(--o${level})`;
}

function isFailureModeShape(x: unknown): x is { name: string; notice: string; test: string } {
  return (
    typeof x === 'object' &&
    x !== null &&
    typeof (x as Record<string, unknown>).name === 'string' &&
    typeof (x as Record<string, unknown>).notice === 'string' &&
    typeof (x as Record<string, unknown>).test === 'string'
  );
}

/** The raw `modes={[...]}` array from one file's `<FailureModes>` tag, or `undefined` if the
 *  file has no such tag at all (most tracks pages, order-zero's siblings that skip it, etc.). */
function extractFailureModesRaw(source: string, where: string): { name: string; notice: string; test: string }[] | undefined {
  let tag: TagMatch | null;
  try {
    tag = findTag(source, 'FailureModes', 0);
  } catch (err) {
    throw new Error(`${where}: ${(err as Error).message}`);
  }
  if (!tag) return undefined;
  const attrs = parseAttrs(tag.attrsRaw);
  const modesAttr = attrs.modes;
  if (!modesAttr || modesAttr.kind !== 'expr') {
    throw new Error(`${where}: <FailureModes> has no modes={[...]} prop to parse`);
  }
  let value: unknown;
  try {
    value = evalExpr(modesAttr.raw);
  } catch (err) {
    throw new Error(`${where}: <FailureModes modes={...}> did not evaluate as JavaScript: ${(err as Error).message}`);
  }
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`${where}: <FailureModes modes={...}> did not evaluate to a non-empty array`);
  }
  const bad = value.findIndex((m) => !isFailureModeShape(m));
  if (bad !== -1) {
    throw new Error(`${where}: <FailureModes> mode at index ${bad} is missing a name, notice or test string`);
  }
  return value as { name: string; notice: string; test: string }[];
}

let cachedFailureModes: FailureMode[] | null = null;

/** Every failure mode on the site, parsed from every technique MDX file's raw source (via the
 *  content collection's own `.body`, not the filesystem -- see the `import.meta.glob` comment
 *  above for why a plain module can't read source files by path once Vite has bundled it).
 *  Throws if any file's <FailureModes> block cannot be parsed -- see the module comment. */
export async function parseAllFailureModes(): Promise<FailureMode[]> {
  if (cachedFailureModes) return cachedFailureModes;
  const entries = await getCollection('techniques');
  const out: FailureMode[] = [];
  for (const entry of entries) {
    const slug = entry.id;
    const where = `site/src/content/techniques/${slug}.mdx`;
    const modes = extractFailureModesRaw(entry.body ?? '', where);
    if (!modes) continue;
    const technique = techniqueBySlug(slug);
    if (!technique) {
      throw new Error(`${where}: has a <FailureModes> block but slug "${slug}" is not in the taxonomy`);
    }
    const color = colorOf(technique.level);
    for (const m of modes) {
      out.push({
        ...m,
        slug,
        title: technique.title,
        level: technique.level,
        levelLabel: technique.levelLabel,
        color,
      });
    }
  }
  cachedFailureModes = out;
  return out;
}

export interface FailureModeGroup {
  level: number | 'tracks';
  levelLabel: string;
  color: string;
  modes: FailureMode[];
}

/** Failure modes grouped by level, in level order, tracks last -- the shape /failures/ renders.
 *  Pass the array from `await parseAllFailureModes()`; grouping itself needs no further I/O. */
export function groupFailureModesByLevel(modes: FailureMode[]): FailureModeGroup[] {
  const order: (number | 'tracks')[] = [...levels.map((t) => t.order), 'tracks'];
  const groups: FailureModeGroup[] = [];
  for (const level of order) {
    const inLevel = modes.filter((m) => m.level === level);
    if (inLevel.length === 0) continue;
    groups.push({
      level,
      levelLabel: inLevel[0].levelLabel,
      color: colorOf(level),
      modes: inLevel,
    });
  }
  return groups;
}

// ---------------------------------------------------------------------------------------------
// Markdown flattening: turn one technique or recipe MDX body into clean Markdown. Order between
// passes for *different* component names does not matter -- each pass only touches its own tag
// -- so components are flattened in a fixed, readable order rather than by nesting depth.
// ---------------------------------------------------------------------------------------------

function stripImportsAndTrailingComment(body: string): string {
  let out = body.replace(/^import .+;\s*$/gm, '');
  // The "Primary sources and the reviewed date are rendered by..." reminder at the foot of every
  // MDX file; Sources/Reviewed are rendered separately, from frontmatter, in flattenTechnique.
  out = out.replace(/\{\/\*[\s\S]*?\*\/\}/g, '');
  return out.trim() + '\n';
}

function flattenCite(text: string): string {
  return text.replace(/<Cite\s+n=\{(\d+)\}\s*\/>/g, '[$1]');
}

function flattenLink(text: string, where: string): string {
  return replaceAllTags(
    text,
    'Link',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const href = attrString(attrs, 'href');
      if (!href) throw new Error('Link has no href');
      const label = (m.inner ?? '').trim();
      return `[${label}](${url(href)})`;
    },
    where,
  );
}

function extractCodeSnippet(
  file: string,
  func: string | undefined,
  cls: string | undefined,
  start: number | undefined,
  end: number | undefined,
): { snippet: string; rangeLabel: string } {
  const full = codeFilesByPath.get(file);
  if (full === undefined) {
    throw new Error(`CodeFile: ${file} is not under examples/ or scripts/, or was not matched by indexes.ts's glob`);
  }
  const lines = full.replace(/\r\n/g, '\n').split('\n');
  let s = start;
  let e = end;
  if (!s && (func || cls)) {
    const openRe = func ? new RegExp(`^def ${func}\\(`) : new RegExp(`^class ${cls}[(:]`);
    const idx = lines.findIndex((l) => openRe.test(l));
    if (idx === -1) throw new Error(`CodeFile: ${func ? `function "${func}"` : `class "${cls}"`} not found in ${file}`);
    s = idx + 1;
    let depth = 0;
    let j = idx;
    do {
      for (const ch of lines[j]) {
        if (ch === '(') depth++;
        else if (ch === ')') depth--;
      }
      j++;
    } while (depth > 0 && j < lines.length);
    while (j < lines.length && !/^\S/.test(lines[j])) j++;
    while (j > idx + 1 && lines[j - 1].trim() === '') j--;
    e = j;
  }
  const snippet = s && e ? lines.slice(s - 1, e).join('\n') : full.replace(/\s+$/, '');
  const rangeLabel = s && e ? ` (lines ${s}-${e})` : '';
  return { snippet, rangeLabel };
}

function flattenCodeFile(text: string, where: string): string {
  return replaceAllTags(
    text,
    'CodeFile',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const file = attrString(attrs, 'file');
      if (!file) throw new Error('CodeFile has no file=');
      const func = attrString(attrs, 'func');
      const cls = attrString(attrs, 'cls');
      const start = attrs.start ? Number(evalExpr(attrs.start.raw)) : undefined;
      const end = attrs.end ? Number(evalExpr(attrs.end.raw)) : undefined;
      const lang = attrString(attrs, 'lang') ?? 'python';
      const { snippet, rangeLabel } = extractCodeSnippet(file, func, cls, start, end);
      return `\n\`${file}\`${rangeLabel}\n\n\`\`\`${lang}\n${snippet}\n\`\`\`\n`;
    },
    where,
  );
}

function flattenRun(text: string, where: string): string {
  return replaceAllTags(
    text,
    'Run',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const label = attrString(attrs, 'label') ?? 'this run';
      return `\n_The web page for this technique includes an interactive step-through of ${label}. The same steps are described in the sections below._\n`;
    },
    where,
  );
}

function extractModesFromTag(m: TagMatch): { name: string; notice: string; test: string }[] {
  const attrs = parseAttrs(m.attrsRaw);
  const modesAttr = attrs.modes;
  if (!modesAttr || modesAttr.kind !== 'expr') throw new Error('FailureModes has no modes={[...]} prop');
  const value = evalExpr(modesAttr.raw);
  if (!Array.isArray(value)) throw new Error('FailureModes modes did not evaluate to an array');
  return value as { name: string; notice: string; test: string }[];
}

function flattenFailureModes(text: string, where: string): string {
  return replaceAllTags(
    text,
    'FailureModes',
    (m) => {
      const modes = extractModesFromTag(m);
      return modes
        .map((mode) => `\n### ${mode.name}\n\n- **How to notice it:** ${mode.notice}\n- **How to test for it:** ${mode.test}\n`)
        .join('');
    },
    where,
  );
}

function flattenCostStrip(text: string, where: string): string {
  return replaceAllTags(
    text,
    'CostStrip',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const stats = (attrExpr(attrs, 'stats') ?? []) as { label: string; value: string }[];
      const comparedTo = attrExpr(attrs, 'comparedTo') as { label: string; note: string } | undefined;
      const illustrative = attrs.illustrative ? Boolean(evalExpr(attrs.illustrative.raw)) : true;
      const parts: string[] = [];
      if (illustrative) {
        parts.push(
          '\n_Illustrative, not measured: no result file exists for this technique yet, so every number below is a worked example._\n',
        );
      }
      parts.push('\n' + stats.map((s) => `- **${s.label}:** ${s.value}`).join('\n') + '\n');
      if (comparedTo) {
        parts.push(`\n**Compared with ${comparedTo.label}.** ${comparedTo.note}\n`);
      }
      return parts.join('');
    },
    where,
  );
}

function flattenMeasured(text: string, where: string): string {
  let out = replaceAllTags(
    text,
    'MeasuredResult',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const measured = measurementFor(attrString(attrs, 'page') ?? '');
      const other = attrString(attrs, 'compare');
      const cmp = other ? compareWith(measured, measurementFor(other), attrString(attrs, 'compareLabel') ?? other) : undefined;
      return measurementMarkdown(measured, REPO_URL, cmp);
    },
    where,
  );
  out = replaceAllTags(
    out,
    'MeasuredCost',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const measured = measurementFor(attrString(attrs, 'page') ?? '');
      const stats = costStats(measured).map((s) => `- **${s.label}:** ${s.value}`).join('\n');
      const other = attrString(attrs, 'compare');
      const cmp = other ? costComparedTo(measured, compareWith(measured, measurementFor(other), attrString(attrs, 'compareLabel') ?? other)) : undefined;
      return `\n_${costCaption(measured)}_\n\n${stats}\n` + (cmp ? `\n**Compared with ${cmp.label}.** ${cmp.note}\n` : '');
    },
    where,
  );
  return out;
}

function flattenRunIt(text: string, where: string): string {
  return replaceAllTags(
    text,
    'RunIt',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const rows: [string, string][] = [
        ['What to monitor', attrString(attrs, 'monitor') ?? ''],
        ['Cost at volume', attrString(attrs, 'costAtVolume') ?? ''],
        ['How it fails in production', attrString(attrs, 'failsInProduction') ?? ''],
        ['What to log', attrString(attrs, 'whatToLog') ?? ''],
      ];
      return '\n' + rows.map(([label, body]) => `**${label}.** ${body}`).join('\n\n') + '\n';
    },
    where,
  );
}

const TRY_IT_LABEL: Record<string, string> = { use: 'Use it', build: 'Build it', either: 'Either lane' };

function flattenTryIt(text: string, where: string): string {
  return replaceAllTags(
    text,
    'TryIt',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const items = (attrExpr(attrs, 'items') ?? []) as { lane: string; body: string }[];
      return '\n' + items.map((it, i) => `${i + 1}. **${TRY_IT_LABEL[it.lane] ?? it.lane}.** ${it.body}`).join('\n') + '\n';
    },
    where,
  );
}

function flattenHowToEval(text: string, where: string): string {
  return replaceAllTags(
    text,
    'HowToEval',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const questionCount = attrs.questionCount ? Number(evalExpr(attrs.questionCount.raw)) : 0;
      const kinds = (attrs.kinds ? evalExpr(attrs.kinds.raw) : []) as string[];
      const inner = (m.inner ?? '').trim();
      const intro = questionCount > 0 || kinds.length > 0 ? `\n_Scored on ${questionCount} questions across kinds: ${kinds.join(', ')}._\n\n` : '\n';
      return `${intro}${inner}\n`;
    },
    where,
  );
}

function flattenWhenNot(text: string, where: string): string {
  return replaceAllTags(
    text,
    'WhenNot',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const title = attrString(attrs, 'title') ?? 'When you do not need this';
      const inner = (m.inner ?? '').trim();
      return `\n## ${title}\n\n${inner}\n`;
    },
    where,
  );
}

function flattenLanes(text: string, where: string): string {
  let out = replaceAllTags(
    text,
    'Lane',
    (m) => {
      const attrs = parseAttrs(m.attrsRaw);
      const title = attrString(attrs, 'name') === 'build' ? 'Implementation details' : 'Practical guidance';
      const inner = (m.inner ?? '').trim();
      return `\n## ${title}\n\n${inner}\n`;
    },
    where,
  );
  out = out.replace(/<Lanes(?:\s[^>]*)?>/g, '').replace(/<\/Lanes>/g, '');
  return out;
}

/** Flatten one technique or recipe MDX body into plain Markdown: no JSX, no HTML tags. */
export function flattenMdxBody(rawBody: string, where: string): string {
  let text = stripImportsAndTrailingComment(rawBody);
  // Legacy web bookmarks carry no content in the plain Markdown export.
  text = text.replace(/^<span id="how-to-eval-it"><\/span>\s*$/gm, '');
  text = flattenCite(text);
  text = flattenLink(text, where);
  text = flattenCodeFile(text, where);
  text = flattenRun(text, where);
  text = replaceAllTags(text, 'DutHarnessLesson', () => `\n**Overview:** ${dutOverview.overview}\n\n**Task:** ${dutOverview.task}\n\n**What to look for:** ${dutOverview.outcome}\n\n**Adapt it:** ${dutOverview.transfer}\n` + '\n**Guided walkthrough:** Follow the DUT project through context, plan, approval, generation, non-hardware checks, and human handoff. Change a missing requirement or new-helper condition, then decide whether a new helper needs separate approval. Responses and check results are scripted illustrations, not model calls or executed validation.\n', where);
  text = replaceAllTags(text, 'TestAutomationHarness', () => '\n**Architecture:** User supplies reusable CLAUDE.md instructions and a DUT-specific DUT_BRIEF.md, plus access to framework documentation, source, past projects, and a template → agent asks questions and drafts PROJECT_PLAN.md → user approval → agent produces Python files, YAML/JSON configuration, Markdown documentation including PROJECT_STATUS.md, and non-hardware check results → user reviews and tests on real instruments → logs and observations return to the agent for revision and status updates. Brief, plan, and status filenames are example conventions. Permissions are configured separately from Markdown. Framework changes and new project-local tools require explicit approval; read-only framework access remains to be confirmed. Intended controls around each action: guardrails inspect proposed actions and generated files; permissions and sandboxing restrict execution; observability records edits, commands, approvals, check results, and blocked actions; stop controls bound revision work. Human review evaluates requirements, framework reuse, and approval compliance. The approved plan, relevant files, and feedback become context for the next call.\n', where);
  text = flattenFailureModes(text, where);
  text = flattenMeasured(text, where);
  text = flattenCostStrip(text, where);
  text = flattenRunIt(text, where);
  text = flattenTryIt(text, where);
  text = flattenHowToEval(text, where);
  text = flattenWhenNot(text, where);
  text = flattenLanes(text, where);
  // Disclosure is a browser presentation choice; Markdown retains all of its content.
  text = text.replace(/^<details className="(?:optional-detail|recipe-detail)">\s*$/gm, '')
    .replace(/^<summary>([^<>]+)<\/summary>\s*$/gm, '### $1\n')
    .replace(/^<\/details>\s*$/gm, '');
  // Collapse the blank-line runs the passes above tend to leave behind.
  text = text.replace(/\n{3,}/g, '\n\n').trim() + '\n';
  // A `<`/`>` inside a fenced or inline code span is prose (angle-bracket placeholder notation
  // in a code example, e.g. `` `PART: <something>` ``), not a leftover HTML/JSX tag -- only a
  // stray one outside both counts as this flattener having missed a component.
  const withoutCode = text.replace(/```[\s\S]*?```/g, '').replace(/`[^`]*`/g, '');
  if (/[<>]/.test(withoutCode)) {
    const bad = withoutCode.match(/[^\n]*[<>][^\n]*/);
    throw new Error(`${where}: flattened Markdown still contains a raw '<' or '>' outside a code span: ${bad?.[0]?.slice(0, 120)}`);
  }
  return text;
}

function sourcesMarkdown(sources: { title: string; url: string; publisher?: string; date?: string; accessed?: string }[]): string {
  if (sources.length === 0) return '';
  const lines = sources.map((s, i) => {
    const bits = [s.publisher, s.date].filter(Boolean).join(', ');
    const accessed = s.accessed ? ` (accessed ${s.accessed})` : '';
    return `${i + 1}. [${s.title}](${s.url})${bits ? ` — ${bits}` : ''}${accessed}`;
  });
  return `\n## Sources\n\n${lines.join('\n')}\n`;
}

/** The full Markdown document for one /techniques/<slug>/ page, matching the anatomy
 *  techniques/[slug].astro renders in HTML: hero, body, sources, reviewed date. */
export async function techniqueMarkdown(slug: string): Promise<string | undefined> {
  const technique = techniqueBySlug(slug);
  if (!technique) return undefined;
  const entry = await getEntry('techniques', slug);
  const parts: string[] = [];
  parts.push(`# ${technique.title}\n`);
  parts.push(`_${technique.levelLabel} · ${technique.status}_\n`);
  parts.push(`${technique.summary}\n`);
  const architecture=architectures[slug];
  if(architecture){
    parts.push(`## Conceptual architecture: ${architecture.title}\n\n${architecture.subtitle}\n`);
    parts.push(architecture.nodes.map(n=>`- **${n.title}:** ${n.detail}`).join('\n'));
    parts.push('\nConnections:\n'+architecture.edges.map(e=>`- ${architecture.nodes[e.from].title} → ${e.label} → ${architecture.nodes[e.to].title}`).join('\n'));
    parts.push('\n'+architecture.distinction+'\n'+architecture.checks.map(([label,body])=>`- **${label}:** ${body}`).join('\n'));
  }
  const labs=examplesForTechnique(slug);
  if(labs.length)parts.push('\n## Try this in a recipe\n'+labs.map(l=>`- [${l.title}](${url(`/recipes/${l.recipe}.md`)}): ${l.summary}`).join('\n'));
  parts.push(walkthroughMarkdown(slug));
  if (entry) {
    const where = `site/src/content/techniques/${slug}.mdx`;
    parts.push(flattenMdxBody(entry.body ?? '', where));
    parts.push(sourcesMarkdown(entry.data.sources ?? []));
    const reviewed = entry.data.reviewed.toISOString().slice(0, 10);
    parts.push(`\nLast reviewed ${reviewed}.\n`);
  } else {
    parts.push('\nThis page is an outline: the diagram, a run to step through, runnable code, failure modes and an eval have not been written yet.\n');
  }
  return parts.join('\n');
}

/** The full Markdown document for one /threads/<id>/ page, matching what threads/[id].astro
 *  renders: title, summary, the organizing sentence, the body, the pages it runs through. */
export async function threadMarkdown(id: string): Promise<string | undefined> {
  const thread = threads.find((t) => t.id === id);
  if (!thread) return undefined;
  const entry = await getEntry('threads', id);
  const parts: string[] = [];
  parts.push(`# ${thread.title}\n`);
  parts.push(`_Thread · ${thread.status}_\n`);
  parts.push(`${thread.summary}\n`);
  parts.push(walkthroughMarkdown(id));
  parts.push(`\n> ${thread.line}\n`);
  if (entry) {
    parts.push(flattenMdxBody(entry.body ?? '', `site/src/content/threads/${id}.mdx`));
    parts.push(sourcesMarkdown(entry.data.sources ?? []));
  }
  parts.push('\n## Pages that carry it\n');
  for (const slug of thread.pages) {
    const page = techniqueBySlug(slug);
    if (page) parts.push(`- [${page.title}](${url(`/techniques/${slug}/`)}) (${page.status}): ${page.summary}`);
  }
  if (entry) {
    parts.push(`\nLast reviewed ${entry.data.reviewed.toISOString().slice(0, 10)}.\n`);
  }
  return parts.join('\n');
}

/** The full Markdown document for one /recipes/<slug>/ page. */
export async function recipeMarkdown(slug: string): Promise<string | undefined> {
  const recipe = recipes.find((r) => r.slug === slug);
  if (!recipe) return undefined;
  const entry = await getEntry('recipes', slug);
  const lv = recipeLevels(recipe);
  const highest = lv.length ? Math.max(...lv) : undefined;
  const parts: string[] = [];
  parts.push(`# ${recipe.title}\n`);
  parts.push(`_Recipe${highest !== undefined ? ` · needs level ${highest}` : ''}_\n`);
  parts.push(`${recipe.summary}\n`);
  parts.push(recipeExampleMarkdown(slug));
  if (entry) {
    const where = `site/src/content/recipes/${slug}.mdx`;
    parts.push(flattenMdxBody(entry.body ?? '', where));
    parts.push(sourcesMarkdown(entry.data.sources ?? []));
    const reviewed = entry.data.reviewed.toISOString().slice(0, 10);
    parts.push(`\nLast reviewed ${reviewed}.\n`);
  } else {
    const techniques = techniquesForRecipe(recipe);
    parts.push('\nThis recipe page is an outline. Techniques this recipe uses:\n');
    parts.push(techniques.map((t) => `- [${t.title}](${url(`/techniques/${t.slug}/`)}): ${t.summary}`).join('\n') + '\n');
  }
  return parts.join('\n');
}

/** The full Markdown document for one /teardowns/<slug>/ page: the products it decodes, the
 *  body, the techniques underneath it, its sources, and the date it expires. */
export async function teardownMarkdown(slug: string): Promise<string | undefined> {
  const teardown = teardowns.find((t) => t.slug === slug);
  if (!teardown) return undefined;
  const entry = await getEntry('teardowns', slug);
  const parts: string[] = [];
  parts.push(`# ${teardown.title}\n`);
  parts.push('_Teardown_\n');
  if (entry) {
    const products = entry.data.products
      .map((id: string) => named.find((n) => n.id === id))
      .filter((n): n is (typeof named)[number] => Boolean(n));
    if (products.length) {
      parts.push(`Decoded from ${products.map((p) => `${p.name} (${p.maker})`).join(', ')}.\n`);
    }
    parts.push(flattenMdxBody(entry.body ?? '', `site/src/content/teardowns/${slug}.mdx`));
    parts.push(sourcesMarkdown(entry.data.sources ?? []));
  } else {
    parts.push('\nThis teardown has not been written yet.\n');
  }
  parts.push('\n## Techniques it decodes into\n');
  for (const t of techniquesForTeardown(teardown)) {
    parts.push(`- [${t.title}](${url(`/techniques/${t.slug}/`)}) (${t.status}): ${t.summary}`);
  }
  if (entry) {
    const reviewed = entry.data.reviewed.toISOString().slice(0, 10);
    parts.push(`\nLast reviewed ${reviewed}. This teardown expires ${teardownExpiry(reviewed)}.\n`);
  }
  return parts.join('\n');
}

/** The full Markdown document for one /levels/<order>/ or /levels/tracks/ page, built entirely
 *  from taxonomy data (level pages have no MDX source of their own). */
export function levelMarkdown(order: number | 'tracks'): string | undefined {
  const parts: string[] = [];
  if (order === 'tracks') {
    parts.push('# Topics at every level\n');
    parts.push('These topics apply whichever level you use.\n');
    for (const track of tracks) {
      parts.push(`\n## ${track.title}\n\n${track.summary} (status: ${track.status})\n`);
      for (const p of track.pages ?? []) {
        parts.push(`- [${p.title}](${url(`/techniques/${p.slug}/`)}): ${p.summary} (${p.status})`);
      }
    }
  } else {
    const tier = levels.find((t) => t.order === order);
    if (!tier) return undefined;
    parts.push(`# Level ${String(order).padStart(2, '0')} · ${tier.title}\n`);
    parts.push(`_${tier.short}_\n`);
    parts.push(`${tier.description}\n`);
    parts.push(`\n## Who decides the next step\n\n${tier.who}\n`);
    parts.push('\n## What is at this level\n');
    for (const p of tier.pages) {
      parts.push(`- [${p.title}](${url(`/techniques/${p.slug}/`)}) (${p.status}): ${p.summary}`);
    }
    const upgrades = tier.pages.flatMap((p) => relationsFor(p.slug).upgradesTo.map((u) => ({ from: p, ...u })));
    if (upgrades.length) {
      parts.push('\n## Upgrade conditions\n');
      for (const u of upgrades) {
        parts.push(`- **${u.from.title} → ${u.page.title}:** ${u.when}`);
      }
    }
    const named = namesForLevel(order);
    const groups: [string, typeof named.product][] = [
      ['Products', named.product],
      ['Tools', named.tool],
      ['Models', named.model],
    ];
    const nonEmpty = groups.filter(([, g]) => g.length > 0);
    if (nonEmpty.length) {
      parts.push('\n## Named products, tools and models\n');
      for (const [label, entries] of nonEmpty) {
        parts.push(`\n### ${label}\n`);
        for (const e of entries) parts.push(`- ${e.name} — ${e.maker} · ${e.category}`);
      }
    }
  }
  return parts.join('\n') + '\n';
}

export { url };
