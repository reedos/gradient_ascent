// Measured results: a committed result file from scripts/eval_run.py, the model that produced it
// (content/measurements.json), and the display rows a page and its Markdown twin print.
//
// One rule this file exists to keep: every number a page states about a run is read from the
// result file here, at build time. Nothing is typed into a page by hand, so a re-run changes the
// page and a page cannot drift from its run.
//
// Pure: data in, rows out, no Astro and no filesystem. The loader that finds the result files is
// results-data.ts, so site/tests can exercise this under plain `node --test`.
import measurements from '../../../content/measurements.json' with { type: 'json' };
import { usDate } from './dates.ts';

export interface KindScore {
  n: number;
  score: number | null;
  ungraded: number;
}

/** The fields of an eval_run.py result file this site reads. */
export interface ResultFile {
  example: string;
  model_id: string;
  embedder_id: string | null;
  run_date: string;
  commit: string;
  stub: boolean;
  partial: boolean;
  questions_run: number;
  questions_total: number;
  score_overall: number | null;
  score_by_kind: Record<string, KindScore>;
  retrieval_coverage: number | null;
  citation_coverage: number | null;
  model_decided_steps: number;
  tokens_in: number;
  tokens_out: number;
  wall_time_s: number;
  ungraded: number;
  empty_completions?: number;
  /** Questions a cap in the code (steps or tokens), not the model, ended. Loops only. */
  forced_finals?: number;
  grader_calls: number;
  model_settings?: { num_ctx?: number; reasoning_allowance?: number } | null;
}

export interface ModelInfo {
  name: string;
  maker: string;
  class: string;
  how_run: string;
  source: { title: string; publisher: string; url: string; accessed: string };
}

export interface MeasurementEntry {
  page: string;
  example: string;
  model: string;
  /** The model id that graded rubric questions; the result file does not record it. */
  grader: string;
  grader_sample_checked: string;
  grader_note: string;
}

export const models = measurements.models as Record<string, ModelInfo>;
export const modelClasses = measurements.classes as string[];
export const measurementEntries = measurements.results as MeasurementEntry[];

/** The order and wording the site uses for the five question kinds. */
export const KIND_LABELS: [string, string][] = [
  ['lookup', 'Lookup'],
  ['numeric', 'Numeric'],
  ['conflicting', 'Conflicting sources'],
  ['unanswerable', 'Not in the documents'],
  ['multi_hop', 'Multi-hop'],
];

export interface Measurement {
  entry: MeasurementEntry;
  model: ModelInfo;
  result: ResultFile;
  correct: number;
  total: number;
  kinds: { key: string; label: string; correct: number; n: number }[];
  /** Classes named in the site's measurement design that this page has no result for yet. */
  classesNotRun: string[];
  perQuestion: { tokensIn: number; tokensOut: number; seconds: number };
}

const pct = (x: number | null) => (x === null ? 'n/a' : `${Math.round(x * 100)}%`);
export const percent = pct;

/** Correct answers in a kind, from its score and size. A score is correct/n, so this is exact. */
const correctIn = (k: KindScore) => (k.score === null ? 0 : Math.round(k.score * k.n));

/**
 * Build the display rows for one page's result. Throws when the result file cannot be shown as
 * a measurement: a stub or partial run, empty completions, or ungraded answers. Those are refused
 * here as well as in the tests, so a bad file breaks the build instead of reaching a page.
 */
export function buildMeasurement(entry: MeasurementEntry, result: ResultFile): Measurement {
  const where = `${entry.page}: ${entry.model}`;
  const model = models[entry.model];
  if (!model) throw new Error(`${where}: no model in content/measurements.json`);
  if (result.model_id !== entry.model) throw new Error(`${where}: result file is for ${result.model_id}`);
  if (result.stub) throw new Error(`${where}: result file is a stub run`);
  if (result.partial) throw new Error(`${where}: result file is partial`);
  if (result.ungraded) throw new Error(`${where}: ${result.ungraded} answers are ungraded`);
  if (result.empty_completions === undefined || result.empty_completions > 0) {
    throw new Error(`${where}: empty completions are ${result.empty_completions ?? 'not recorded'}`);
  }
  const kinds = KIND_LABELS.filter(([key]) => result.score_by_kind[key]?.n).map(([key, label]) => {
    const k = result.score_by_kind[key];
    return { key, label, correct: correctIn(k), n: k.n };
  });
  const correct = kinds.reduce((s, k) => s + k.correct, 0);
  const total = kinds.reduce((s, k) => s + k.n, 0);
  const ran = new Set(measurementEntries.filter((e) => e.page === entry.page).map((e) => models[e.model]?.class));
  const q = result.questions_run || 1;
  return {
    entry,
    model,
    result,
    correct,
    total,
    kinds,
    classesNotRun: modelClasses.filter((c) => !ran.has(c)),
    perQuestion: {
      tokensIn: Math.round(result.tokens_in / q),
      tokensOut: Math.round(result.tokens_out / q),
      seconds: result.wall_time_s / q,
    },
  };
}

export const thousands = (n: number) => n.toLocaleString('en-US');

/** Cost-strip stats, per question, all from the result file. */
export function costStats(m: Measurement): { label: string; value: string }[] {
  return [
    { label: 'Tokens in, per question', value: thousands(m.perQuestion.tokensIn) },
    { label: 'Tokens out, per question', value: thousands(m.perQuestion.tokensOut) },
    { label: 'Wall time, per question', value: `${m.perQuestion.seconds.toFixed(1)}s` },
    { label: 'Questions in the run', value: String(m.result.questions_run) },
  ];
}

export function costCaption(m: Measurement): string {
  return (
    `Measured: averages over the ${m.result.questions_run}-question run on ${m.model.name}, a model in the ` +
    `${m.model.class} class, on one local GPU. Tokens out include the model's hidden reasoning, ` +
    `which it spends before answering. Holds for this model class only.`
  );
}

export interface Comparison {
  /** How the other page is named in the comparison, e.g. "RAG (level 2)". */
  label: string;
  other: Measurement;
  rows: { label: string; correct: number; otherCorrect: number; n: number }[];
}

/**
 * The same questions, the same model, two techniques. Refuses anything else: a comparison across
 * models or question sets would credit the technique with a difference the model or the questions
 * made, which is the claim this site's measurement design forbids.
 */
export function compareWith(m: Measurement, other: Measurement, label: string): Comparison {
  if (other.entry.model !== m.entry.model) throw new Error(`compare ${m.entry.page} with ${other.entry.page}: different models`);
  if (other.result.questions_total !== m.result.questions_total) throw new Error(`compare ${m.entry.page} with ${other.entry.page}: different question sets`);
  const rows = m.kinds.map((k) => {
    const o = other.kinds.find((x) => x.key === k.key);
    if (!o) throw new Error(`compare ${m.entry.page} with ${other.entry.page}: ${k.key} is missing from one run`);
    return { label: k.label, correct: k.correct, otherCorrect: o.correct, n: k.n };
  });
  return { label, other, rows };
}

/** The cost strip's comparison line, both sides read from their result files. */
export function costComparedTo(m: Measurement, c: Comparison): { label: string; note: string } {
  const a = m.perQuestion;
  const b = c.other.perQuestion;
  return {
    label: `${c.label}, same model`,
    note:
      `Per question, ${c.label} took ${thousands(b.tokensIn)} tokens in, ${thousands(b.tokensOut)} out and ` +
      `${b.seconds.toFixed(1)}s on ${m.model.name}; this page took ${thousands(a.tokensIn)} in, ` +
      `${thousands(a.tokensOut)} out and ${a.seconds.toFixed(1)}s, on the same ${m.result.questions_run} questions.`,
  };
}

/** The whole result as plain Markdown, for the page's `.md` twin. No `<` or `>` anywhere. */
export function measurementMarkdown(m: Measurement, repoUrl: string, c?: Comparison): string {
  const r = m.result;
  const table = c
    ? [
        `| Question kind | This page | ${c.label}, same model |`,
        '| --- | --- | --- |',
        ...c.rows.map((k) => `| ${k.label} | ${k.correct} of ${k.n} | ${k.otherCorrect} of ${k.n} |`),
      ]
    : ['| Question kind | Correct |', '| --- | --- |', ...m.kinds.map((k) => `| ${k.label} | ${k.correct} of ${k.n} |`)];
  const lines = [
    `### Measured result: ${m.model.name}`,
    '',
    `**${m.correct} of ${m.total} correct** on the site's ${m.total}-question set, run ${usDate(r.run_date.slice(0, 10))} with ${m.model.name} by ${m.model.maker}, a model in the ${m.model.class} class. ${m.model.how_run}`,
    '',
    ...(c ? [`${c.label} scored ${c.other.correct} of ${c.other.total} on the same questions with the same model.`, ''] : []),
    ...table,
    '',
    `- **Retrieval coverage:** ${pct(r.retrieval_coverage)} of the sections the questions need reached the prompt.`,
    `- **Citation coverage:** ${pct(r.citation_coverage)} of the sections the questions need were cited in the answer.`,
    `- **Model-decided steps:** ${r.model_decided_steps}. ${r.model_decided_steps === 0 ? 'Code chose every step; the model only wrote the answer.' : 'Steps where the model chose what happened next.'}`,
    `- **Empty replies:** ${r.empty_completions ?? 0}. **Ungraded answers:** ${r.ungraded}.`,
    ...(r.forced_finals !== undefined ? [`- **Ended by a cap:** ${r.forced_finals} of ${r.questions_run} questions, where the step or token budget in the code stopped the loop and forced an answer.`] : []),
    `- **Grader:** ${graderName(m)}, on ${r.grader_calls} rubric questions, the rest by exact match. Checked by a person on ${usDate(m.entry.grader_sample_checked)}: ${m.entry.grader_note}`,
    '',
    m.classesNotRun.length
      ? `This holds for the ${m.model.class} class only. Not yet run: ${m.classesNotRun.join('; ')}.`
      : 'This has been run on every model class the site measures.',
    '',
    `Result file: ${repoUrl}/blob/main/evals/results/${m.entry.example}/${resultFileName(m.entry.model)} · recorded trace: ${repoUrl}/blob/main/examples/${m.entry.example}/trace.json`,
    '',
  ];
  return lines.join('\n');
}

export function graderName(m: Measurement): string {
  if (m.entry.grader === m.entry.model) return 'the same model';
  return models[m.entry.grader]?.name ?? m.entry.grader;
}

/** The file name eval_run.py writes for a model id (its `_safe_name`). */
export function resultFileName(modelId: string): string {
  return `${modelId.replace(/[^A-Za-z0-9_.-]/g, '_')}.json`;
}
