// Unit tests for the search scorer (src/lib/search.ts). Run: npm test (in site/), which is
// `node --test tests/` -- Node strips the types rather than compiling them, so the import below
// carries its .ts extension the same way tests/literal.test.ts does.
import test from 'node:test';
import assert from 'node:assert/strict';
import { search, matchTier, groupResults, normalize, words, type SearchDoc } from '../src/lib/search.ts';

function doc(partial: Partial<SearchDoc> & Pick<SearchDoc, 'id' | 'kind' | 'title' | 'url'>): SearchDoc {
  return partial;
}

// -- normalize / words --------------------------------------------------------------------------

test('normalize folds case and diacritics', () => {
  assert.equal(normalize('NotebookLM'), 'notebooklm');
  assert.equal(normalize('café'), 'cafe');
  assert.equal(normalize('Le Chat'), 'le chat');
});

test('words splits on non-alphanumerics after folding', () => {
  assert.deepEqual(words('Agentic RAG (deep research)'), ['agentic', 'rag', 'deep', 'research']);
});

// -- exact / prefix / word tiers -----------------------------------------------------------------

test('an exact title match is TIER_EXACT', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'RAG', url: '/x/' });
  assert.equal(matchTier(d, 'RAG'), 0);
  assert.equal(matchTier(d, 'rag'), 0); // case-folded
});

test('a prefix of the title beats a mid-title word match', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'Agentic RAG', url: '/x/' });
  assert.equal(matchTier(d, 'Agent'), 1); // prefix of the whole title
});

test('all query words present in the title, in any order, is TIER_TITLE', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'Agentic RAG', url: '/x/' });
  assert.equal(matchTier(d, 'rag agentic'), 2);
});

test('a title match ranks ahead of a summary-only match, which ranks ahead of a body-only match', () => {
  const inTitle = doc({ id: '1', kind: 'technique', title: 'Routing', summary: 'x', url: '/a/' });
  const inSummary = doc({ id: '2', kind: 'technique', title: 'Something else', summary: 'about routing', url: '/b/' });
  const inBody = doc({ id: '3', kind: 'technique', title: 'Another', summary: 'no match here', body: 'discusses routing', url: '/c/' });
  const results = search([inBody, inSummary, inTitle], 'routing');
  assert.deepEqual(results.map((r) => r.id), ['1', '2', '3']);
});

test('a word must match every query word: partial coverage excludes the doc', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'Routing', summary: 'sends input to a handler', url: '/x/' });
  assert.equal(matchTier(d, 'routing zebra'), null);
});

test('a query with only whitespace, or empty, matches nothing', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'Routing', url: '/x/' });
  assert.equal(matchTier(d, ''), null);
  assert.equal(matchTier(d, '   '), null);
});

// -- former names (aka / alt) --------------------------------------------------------------------

test('a former product name finds its current entry: NotebookLM -> Gemini Notebook', () => {
  const gemini = doc({
    id: 'name:gemini-notebook',
    kind: 'name',
    title: 'Gemini Notebook',
    alt: ['NotebookLM'],
    url: '/techniques/rag/',
  });
  assert.equal(matchTier(gemini, 'NotebookLM'), 0); // exact match on the alt name
  assert.equal(matchTier(gemini, 'notebooklm'), 0); // case-folded
});

test('a former product name finds its current entry: Le Chat -> Mistral Vibe', () => {
  const vibe = doc({
    id: 'name:le-chat',
    kind: 'name',
    title: 'Mistral Vibe',
    alt: ['Le Chat'],
    url: '/techniques/chat/',
  });
  assert.equal(matchTier(vibe, 'Le Chat'), 0);
  assert.equal(matchTier(vibe, 'le'), 1); // prefix of the alt name
});

test('an alt name participates in the title-words tier too', () => {
  const d = doc({ id: '1', kind: 'name', title: 'Mistral Vibe', alt: ['Le Chat'], url: '/x/' });
  assert.equal(matchTier(d, 'chat vibe'), 2); // "chat" only in alt, "vibe" only in title
});

// -- typo tolerance (one edit, words of five letters or more) ------------------------------------

test('a one-letter substitution on a five-letter-or-more word still matches, at a penalty', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'Routing', url: '/x/' });
  const exact = matchTier(d, 'routing')!;
  const typo = matchTier(d, 'rooting')!; // t -> o, same length
  assert.ok(typo > exact, 'a typo match should rank below the exact match at the same tier');
  assert.ok(typo < 3, 'the typo match should still land in the title tier (2.x), not fall to the next tier');
});

test('a one-letter insertion/deletion still matches within one edit', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'Routing', url: '/x/' });
  assert.notEqual(matchTier(d, 'routting'), null); // one extra letter (insertion)
  assert.notEqual(matchTier(d, 'outing'), null); // one missing letter (deletion), still 6+ long
});

test('typo tolerance does not apply to words under five letters', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'RAG', url: '/x/' });
  assert.equal(matchTier(d, 'RAF'), null); // 3-letter word, one edit from "RAG", not tolerated
});

test('two edits on a long word is not tolerated', () => {
  const d = doc({ id: '1', kind: 'technique', title: 'Routing', url: '/x/' });
  assert.equal(matchTier(d, 'rooming'), null); // 2 substitutions away from "routing"
});

// -- multi-word AND across fields ------------------------------------------------------------------

test('multi-word queries require every word, which can come from different fields', () => {
  const d = doc({
    id: '1',
    kind: 'technique',
    title: 'Structured output',
    summary: 'A reply constrained to a fixed shape.',
    body: 'Useful for routing a response to a handler.',
    url: '/x/',
  });
  // "structured" is in the title, "handler" only in the body -- needs the body tier.
  assert.equal(matchTier(d, 'structured handler'), 4);
});

// -- ranking end to end -----------------------------------------------------------------------

test('search() sorts best matches first across a mixed set', () => {
  const docs: SearchDoc[] = [
    doc({ id: 'body', kind: 'technique', title: 'Memory', summary: 'x', body: 'context engineering is related', url: '/a/' }),
    doc({ id: 'exact', kind: 'technique', title: 'Context engineering', summary: 'x', url: '/b/' }),
    doc({ id: 'prefix', kind: 'technique', title: 'Context engineering for agents', summary: 'x', url: '/c/' }),
    doc({ id: 'unrelated', kind: 'technique', title: 'Voice agents', summary: 'no overlap', url: '/d/' }),
  ];
  const results = search(docs, 'context engineering');
  assert.deepEqual(results.map((r) => r.id), ['exact', 'prefix', 'body']);
});

test('ties within a tier break alphabetically by title', () => {
  const docs: SearchDoc[] = [
    doc({ id: '1', kind: 'technique', title: 'Zeta routing', url: '/a/' }),
    doc({ id: '2', kind: 'technique', title: 'Alpha routing', url: '/b/' }),
  ];
  const results = search(docs, 'routing');
  assert.deepEqual(results.map((r) => r.id), ['2', '1']);
});

// -- grouping ----------------------------------------------------------------------------------

test('groupResults buckets by kind in the fixed order, omitting empty kinds', () => {
  const docs: SearchDoc[] = [
    doc({ id: '1', kind: 'failure', title: 'RAG retrieves the wrong passage', url: '/a/' }),
    doc({ id: '2', kind: 'technique', title: 'RAG', url: '/b/' }),
    doc({ id: '3', kind: 'glossary', title: 'RAG', url: '/c/' }),
  ];
  const results = search(docs, 'rag');
  const groups = groupResults(results);
  assert.deepEqual(
    groups.map((g) => g.kind),
    ['technique', 'glossary', 'failure'],
  );
  assert.equal(groups.find((g) => g.kind === 'technique')?.items.length, 1);
});

test('groupResults returns nothing for an empty result list', () => {
  assert.deepEqual(groupResults([]), []);
});
