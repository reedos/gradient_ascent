// The site search scorer: a small, dependency-free ranker over a flat list of documents built
// at compile time (see search-docs.ts, which turns the site's own data into SearchDoc[], and
// pages/search-index.json.ts, which serves that list as JSON). This module is deliberately kept
// free of any import into content.ts/indexes.ts -- it is the part that ships to the browser
// (via components/islands/Search.tsx) and the part unit-tested directly in site/tests/, so it
// only knows about plain data, never about the taxonomy or the registry.
//
// Ranking, in order: an exact title/term match, then a prefix match, then every query word
// found in the title, then every query word found once the summary is added, then every query
// word found once the body is added. A query word of five letters or more that is not found
// exactly may still match a token within one edit (one insertion, deletion or substitution) --
// cheap because it is only tried once the exact/prefix checks for that word have already failed,
// and only against tokens that are themselves five letters or more. A doc that needed a typo
// match to complete a tier sorts after every doc that did not need one, at the same tier.

export type SearchKind =
  | 'technique'
  | 'recipe'
  | 'teardown'
  | 'level'
  | 'view'
  | 'glossary'
  | 'name'
  | 'failure'
  | 'milestone';

export interface SearchDoc {
  /** Stable, unique across the whole index, e.g. "technique:rag" or "glossary:RAG". */
  id: string;
  kind: SearchKind;
  title: string;
  /** Former names or aka's -- scored exactly like the title, so an old name still finds the
   *  current entry ("NotebookLM" finds Gemini Notebook, "Le Chat" finds Mistral Vibe). */
  alt?: string[];
  /** Small subtitle line: a level label, "maker · category", "Needs level 3". Not scored. */
  meta?: string;
  /** Summary or definition -- second-priority match text, and what renders under the title. */
  summary?: string;
  /** Section headings and first sentences, or a failure mode's test -- third-priority text,
   *  not rendered in the result row. */
  body?: string;
  url: string;
  /** For the level color dot; 'tracks' renders the neutral topics color. */
  level?: number | 'tracks';
  /** A name's registry page, shown as a second, smaller link beside the primary one. */
  secondaryUrl?: string;
  secondaryLabel?: string;
}

export interface ScoredDoc extends SearchDoc {
  tier: number;
}

export const KIND_ORDER: SearchKind[] = [
  'technique',
  'recipe',
  'teardown',
  'level',
  'view',
  'glossary',
  'name',
  'failure',
  'milestone',
];

export const KIND_LABEL: Record<SearchKind, string> = {
  technique: 'Techniques and topics',
  recipe: 'Recipes',
  teardown: 'Teardowns',
  level: 'Levels',
  view: 'Views',
  glossary: 'Glossary',
  name: 'Names',
  failure: 'Failure modes',
  milestone: 'Timeline',
};

// -- Tiers, best (lowest) first. A typo match adds TYPO_PENALTY so it sorts after every doc at
// the same tier that matched for real. --------------------------------------------------------
export const TIER_EXACT = 0;
export const TIER_PREFIX = 1;
export const TIER_TITLE = 2;
export const TIER_SUMMARY = 3;
export const TIER_BODY = 4;
const TYPO_PENALTY = 0.5;

/** Case and diacritics folded, e.g. "NotebookLM" and "notebooklm" and "café" and "cafe" compare
 *  equal. */
export function normalize(input: string): string {
  return input
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

/** Normalized, then split into alphanumeric words. */
export function words(input: string): string[] {
  return normalize(input)
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

/** True if `a` and `b` differ by at most one insertion, deletion or substitution. O(n): walks
 *  both strings once rather than the full edit-distance table, which is all a one-edit check
 *  needs. */
function withinOneEdit(a: string, b: string): boolean {
  if (a === b) return true;
  const la = a.length;
  const lb = b.length;
  if (Math.abs(la - lb) > 1) return false;
  if (la === lb) {
    let mismatches = 0;
    for (let i = 0; i < la; i++) {
      if (a[i] !== b[i]) {
        mismatches++;
        if (mismatches > 1) return false;
      }
    }
    return mismatches === 1;
  }
  const [shorter, longer] = la < lb ? [a, b] : [b, a];
  let i = 0;
  let j = 0;
  let usedSkip = false;
  while (i < shorter.length && j < longer.length) {
    if (shorter[i] === longer[j]) {
      i++;
      j++;
      continue;
    }
    if (usedSkip) return false;
    usedSkip = true;
    j++;
  }
  return true;
}

interface WordMatch {
  ok: boolean;
  typo: boolean;
}

/** Does query word `qw` match something in `tokens`: exactly, as a whole-word prefix (so "agen"
 *  finds "agent"), or -- only for a word of five letters or more, against a token also five
 *  letters or more -- within one edit. */
function wordMatchesTokens(qw: string, tokens: string[]): WordMatch {
  for (const t of tokens) {
    if (t === qw || t.startsWith(qw)) return { ok: true, typo: false };
  }
  if (qw.length >= 5) {
    for (const t of tokens) {
      if (t.length >= 5 && withinOneEdit(qw, t)) return { ok: true, typo: true };
    }
  }
  return { ok: false, typo: false };
}

/** Every query word must match somewhere in `tokens` (multi-word queries match all words). */
function allWordsMatch(queryWords: string[], tokens: string[]): WordMatch {
  let typo = false;
  for (const qw of queryWords) {
    const r = wordMatchesTokens(qw, tokens);
    if (!r.ok) return { ok: false, typo: false };
    if (r.typo) typo = true;
  }
  return { ok: true, typo };
}

/** The best tier a doc reaches for `query`, or null if it does not match at all. Exported mainly
 *  for the unit tests; `search()` is what a caller normally wants. */
export function matchTier(doc: SearchDoc, query: string): number | null {
  const nq = normalize(query).trim();
  if (!nq) return null;
  const queryWords = words(query);
  if (queryWords.length === 0) return null;

  const normTitle = normalize(doc.title);
  const altNorms = (doc.alt ?? []).map(normalize);

  if (normTitle === nq || altNorms.includes(nq)) return TIER_EXACT;
  if (normTitle.startsWith(nq) || altNorms.some((a) => a.startsWith(nq))) return TIER_PREFIX;

  const titleTokens = [...words(doc.title), ...(doc.alt ?? []).flatMap(words)];
  const summaryTokens = words(doc.summary ?? '');
  const bodyTokens = words(doc.body ?? '');

  let m = allWordsMatch(queryWords, titleTokens);
  if (m.ok) return TIER_TITLE + (m.typo ? TYPO_PENALTY : 0);

  m = allWordsMatch(queryWords, [...titleTokens, ...summaryTokens]);
  if (m.ok) return TIER_SUMMARY + (m.typo ? TYPO_PENALTY : 0);

  m = allWordsMatch(queryWords, [...titleTokens, ...summaryTokens, ...bodyTokens]);
  if (m.ok) return TIER_BODY + (m.typo ? TYPO_PENALTY : 0);

  return null;
}

/** Every doc that matches `query`, best first; ties break alphabetically by title so the order
 *  is stable and predictable. */
export function search(docs: SearchDoc[], query: string): ScoredDoc[] {
  const out: ScoredDoc[] = [];
  for (const doc of docs) {
    const tier = matchTier(doc, query);
    if (tier !== null) out.push({ ...doc, tier });
  }
  out.sort((a, b) => a.tier - b.tier || a.title.localeCompare(b.title));
  return out;
}

export interface ResultGroup {
  kind: SearchKind;
  label: string;
  items: ScoredDoc[];
}

/** Scored results bucketed into the six kinds, in the fixed display order, empty kinds omitted.
 *  Relative order within a kind is whatever `search()` produced. */
export function groupResults(results: ScoredDoc[]): ResultGroup[] {
  return KIND_ORDER.map((kind) => ({
    kind,
    label: KIND_LABEL[kind],
    items: results.filter((r) => r.kind === kind),
  })).filter((g) => g.items.length > 0);
}
