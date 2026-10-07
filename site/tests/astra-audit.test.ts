import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { buildMeasurement, compareWith, costCaption, measurementMarkdown, measurementEntries, type ResultFile } from '../src/lib/results.ts';

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8');
const recorded = (entry = measurementEntries[0]): ResultFile => JSON.parse(read(
  `../../evals/results/${entry.example}/${entry.model.replace(/[^A-Za-z0-9_.-]/g, '_')}.json`));

test('displayed correct counts agree with independent per-question verdicts', () => {
  for (const entry of measurementEntries) {
    const r = recorded(entry);
    const m = buildMeasurement(entry, r);
    assert.equal(m.total, r.questions.length);
    assert.equal(m.correct, r.questions.filter(q => q.correct === true).length);
    for (const kind of m.kinds) {
      const rows = r.questions.filter(q => q.kind === kind.key);
      assert.equal(kind.n, rows.length);
      assert.equal(kind.correct, rows.filter(q => q.correct === true).length);
    }
  }
});

test('a same-size run with different question identities cannot be labeled same questions', () => {
  const entry = measurementEntries[0];
  const a = buildMeasurement(entry, recorded());
  const r = recorded();
  r.questions[0].id = 'different-question';
  assert.throws(() => compareWith(a, buildMeasurement(entry, r), 'comparison'), /question/);
});

test('a truncated question list cannot be published as a complete measurement', () => {
  const r = recorded();
  r.questions.pop();
  assert.throws(() => buildMeasurement(measurementEntries[0], r), /question/);
});

test('synthetic measurement integrity cases reject false evidence without rejecting row order', () => {
  const cases = JSON.parse(read('../../evals/measurement-integrity.json')).cases;
  const entry = measurementEntries[0];
  const original = buildMeasurement(entry, recorded());
  for (const c of cases) {
    const r = recorded();
    switch (c.mutation) {
      case 'drop-question': r.questions.pop(); break;
      case 'duplicate-id': r.questions[1].id = r.questions[0].id; break;
      case 'null-verdict': r.questions[0].correct = null; break;
      case 'inflate-summary': r.score_by_kind.numeric.score = r.score_by_kind.numeric.score === 1 ? 0 : 1; break;
      case 'replace-id': r.questions[0].id = 'replacement'; break;
      case 'reverse-rows': r.questions.reverse(); break;
      default: assert.fail(`Unknown integrity case: ${c.id}`);
    }
    if (c.expected === 'reject') assert.throws(() => buildMeasurement(entry, r), /question|summary/, c.id);
    else if (c.expected === 'reject-comparison') {
      assert.throws(() => compareWith(original, buildMeasurement(entry, r), 'mutated'), /question/, c.id);
    } else assert.doesNotThrow(() => compareWith(original, buildMeasurement(entry, r), 'reordered'), c.id);
  }
});

test('one recorded model run never claims to measure its entire model class', () => {
  for (const entry of measurementEntries) {
    const filename = entry.model.replace(/[^A-Za-z0-9_.-]/g, '_');
    const result = JSON.parse(read(`../../evals/results/${entry.example}/${filename}.json`));
    const m = buildMeasurement(entry, result);
    for (const prose of [costCaption(m), measurementMarkdown(m, 'https://example.test')]) {
      assert.doesNotMatch(prose, /holds? for (?:this|the).*class/i);
      assert.match(prose, /does not establish performance for other models/i);
    }
    assert.doesNotMatch(read(`../src/content/techniques/${entry.page}.mdx`), /hold for that model's class/);
  }
  assert.doesNotMatch(read('../src/components/page/MeasuredResult.astro'), /holds for the.*class only/);
});

test('the explainer uses the IF amber accent and neutral surface tokens', () => {
  const css = read('../src/styles/global.css');
  assert.match(css, /--accent:\s*#e6ba82;/);
  assert.match(css, /--bg:\s*#000;/);
  assert.match(css, /--panel:\s*#0b1015;/);
  assert.match(css, /--panel2:\s*#121920;/);
  for (let level = 0; level <= 7; level++) {
    assert.match(css, new RegExp(`--o${level}:\\s*var\\(--accent\\);`));
  }
});
