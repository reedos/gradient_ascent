import test from 'node:test';
import assert from 'node:assert/strict';
import { acronymMatches } from '../src/lib/acronyms.ts';

test('recognizes acronyms, plurals, and slash-separated formats', () => {
  assert.deepEqual(acronymMatches('DUTs use APIs and YAML/JSON.').map(m => [m.text, m.key]),
    [['DUTs', 'DUT'], ['APIs', 'API'], ['YAML', 'YAML'], ['JSON', 'JSON']]);
});
test('leaves words, identifiers, and lowercase text alone; matching is repeatable', () => {
  for (let i = 0; i < 2; i++) {
    assert.deepEqual(acronymMatches('RAGet DUT_BRIEF api json SCPI_driver'), []);
    assert.deepEqual(acronymMatches('Use an LLM.').map(m => m.index), [7]);
  }
});


test('matches reading terms regardless of case, with the longer concept taking precedence', () => {
  assert.deepEqual(acronymMatches('Agentic RAG uses retrieval; GraphRAG uses knowledge graphs.').map(m => m.key),
    ['agentic RAG', 'retrieval', 'GraphRAG', 'knowledge graph']);
  assert.deepEqual(acronymMatches('Context windows hold tokens.').map(m => m.key), ['context window', 'token']);
  assert.deepEqual(acronymMatches('Retrieval-augmented generation (RAG)').map(m => m.key), ['retrieval-augmented generation', 'RAG']);
});
