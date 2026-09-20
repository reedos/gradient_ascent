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
