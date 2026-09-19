// Unit tests for the literal parser that replaced `new Function(...)` in src/lib/indexes.ts.
// Run: npm test (in site/), which is `node --test tests/` -- Node strips the types rather than
// compiling them, so the import below carries its .ts extension and the module under test uses
// no syntax that type-stripping cannot erase.
import test from 'node:test';
import assert from 'node:assert/strict';
import { parseLiteral, LiteralParseError } from '../src/lib/literal.ts';

// -- What the site's own MDX actually writes ---------------------------------------------------

test('a FailureModes array, as rag.mdx writes it', () => {
  const raw = `[
    { name: 'Stale index', notice: "The answer is right for an old version.", test: 'Change a fact.' },
    { name: 'Chunk boundaries split a fact', notice: 'A number and its sentence land in two chunks.', test: "Check multi-hop questions." },
  ]`;
  const value = parseLiteral(raw) as { name: string; notice: string; test: string }[];
  assert.equal(value.length, 2);
  assert.equal(value[0].name, 'Stale index');
  assert.equal(value[1].test, 'Check multi-hop questions.');
});

test('a CostStrip stats array with a number and a boolean', () => {
  assert.deepEqual(parseLiteral(`[{ label: 'Tokens in', value: '~1,850' }]`), [
    { label: 'Tokens in', value: '~1,850' },
  ]);
  assert.equal(parseLiteral('2'), 2);
  assert.equal(parseLiteral('{false}'.slice(1, -1)), false);
  assert.equal(parseLiteral('true'), true);
  assert.equal(parseLiteral('null'), null);
});

test('a TryIt items array with nested quotes and an apostrophe', () => {
  const raw = `[{ lane: 'use', body: "Open a chat app's file feature and ask a question." }]`;
  assert.deepEqual(parseLiteral(raw), [
    { lane: 'use', body: "Open a chat app's file feature and ask a question." },
  ]);
});

test('a HowToEval kinds array of plain strings', () => {
  assert.deepEqual(parseLiteral(`['lookup', 'multi-hop', 'numeric']`), ['lookup', 'multi-hop', 'numeric']);
});

// -- The JSON5-shaped conveniences MDX authors use ---------------------------------------------

test('trailing commas, in arrays and in objects', () => {
  assert.deepEqual(parseLiteral('[1, 2, 3,]'), [1, 2, 3]);
  assert.deepEqual(parseLiteral(`{ a: 1, b: 2, }`), { a: 1, b: 2 });
});

test('quoted and unquoted keys are both accepted', () => {
  assert.deepEqual(parseLiteral(`{ "a": 1, 'b': 2, c: 3, $d: 4, _e: 5 }`), { a: 1, b: 2, c: 3, $d: 4, _e: 5 });
});

test('a backtick string with no substitution', () => {
  assert.equal(parseLiteral('`plain text`'), 'plain text');
});

test('comments and whitespace between tokens', () => {
  const raw = `[
    // the first one
    1,
    /* and the second */ 2
  ]`;
  assert.deepEqual(parseLiteral(raw), [1, 2]);
});

test('escapes: newline, tab, quote, backslash, \\u and \\x', () => {
  assert.equal(parseLiteral(String.raw`"a\nb"`), 'a\nb');
  assert.equal(parseLiteral(String.raw`"a\tb"`), 'a\tb');
  assert.equal(parseLiteral(String.raw`'it\'s'`), "it's");
  assert.equal(parseLiteral(String.raw`"back\\slash"`), 'back\\slash');
  assert.equal(parseLiteral(String.raw`"—"`), '—');
  assert.equal(parseLiteral(String.raw`"\u{1f600}"`), '\u{1f600}');
  assert.equal(parseLiteral(String.raw`"\x41"`), 'A');
});

test('numbers: negative, decimal, exponent, hex', () => {
  assert.equal(parseLiteral('-4'), -4);
  assert.equal(parseLiteral('+4'), 4);
  assert.equal(parseLiteral('1.5'), 1.5);
  assert.equal(parseLiteral('1e3'), 1000);
  assert.equal(parseLiteral('2E-2'), 0.02);
  assert.equal(parseLiteral('0x1f'), 31);
  assert.equal(parseLiteral('-0x10'), -16);
});

test('empty array and empty object', () => {
  assert.deepEqual(parseLiteral('[]'), []);
  assert.deepEqual(parseLiteral('{}'), {});
});

test('nested arrays and objects', () => {
  assert.deepEqual(parseLiteral(`{ a: [ { b: [1, { c: 'd' }] } ] }`), { a: [{ b: [1, { c: 'd' }] }] });
});

test('characters that used to confuse a naive scan survive inside strings', () => {
  assert.deepEqual(parseLiteral(`[{ t: 'a } b { c', u: "x > y < z", v: 'a, b' }]`), [
    { t: 'a } b { c', u: 'x > y < z', v: 'a, b' },
  ]);
});

// -- Everything that is not data is refused ----------------------------------------------------

function refuses(raw: string, because: string) {
  test(`refuses ${because}`, () => {
    assert.throws(
      () => parseLiteral(raw),
      (err: unknown) => {
        assert.ok(err instanceof LiteralParseError, `expected LiteralParseError, got ${String(err)}`);
        assert.match((err as Error).message, /at character \d+/);
        return true;
      },
    );
  });
}

refuses('process.env.HOME', 'a property lookup');
refuses(`[require('node:fs')]`, 'a call');
refuses('globalThis', 'a bare identifier');
refuses('1 + 1', 'an operator');
refuses('[1, 2].map(String)', 'a method call');
refuses('(() => 1)()', 'an arrow function');
refuses('function f() {}', 'a function declaration');
refuses('`a ${b} c`', 'a template substitution');
refuses('new Date()', 'a constructor call');
refuses('{ a: undefined }', 'undefined, which is an identifier, not a literal');
refuses('[1, 2] ; drop()', 'trailing text after the value');
refuses('{ a: 1 } {}', 'a second value');
refuses('[', 'an unterminated array');
refuses('{ a: 1', 'an unterminated object');
refuses(`'unterminated`, 'an unterminated string');
refuses('{ : 1 }', 'a missing property name');
refuses('{ a 1 }', 'a missing colon');
refuses('[1 2]', 'a missing comma');
refuses('', 'an empty expression');
refuses('   ', 'whitespace only');
refuses('/* only a comment */', 'a comment with no value');
refuses('0x', 'a hex prefix with no digits');
refuses('1e', 'an exponent with no digits');
refuses(String.raw`"\uZZZZ"`, 'a bad unicode escape');
refuses(String.raw`"\01"`, 'an octal escape');
refuses('[1, 2,,]', 'a hole in an array');

test('a refusal names the offending character position', () => {
  const err = (() => {
    try {
      parseLiteral('[1, 2, oops]');
    } catch (e) {
      return e as LiteralParseError;
    }
    throw new Error('expected a throw');
  })();
  assert.equal(err.index, 7);
  assert.match(err.message, /identifier "oops"/);
});

test('the literal is data, not a live object: a prototype key is a plain own property', () => {
  const value = parseLiteral(`{ "__proto__": { "polluted": true }, "a": 1 }`) as Record<string, unknown>;
  assert.equal((({}) as Record<string, unknown>).polluted, undefined);
  assert.equal(value.a, 1);
});
