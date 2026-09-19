// The worksheet's pure decision logic and the shapes it walks. This module imports NOTHING, on
// purpose: the worksheet island calls evaluateCore/evaluateCross/currentStep/maxQuestions in the
// browser, so anything this file reaches is shipped to every reader. worksheet.ts sits on top and
// does the server-side half (reading content/worksheet.json, resolving relation references
// against the taxonomy, building each level's result data); it re-exports everything here so an
// .astro page can keep importing one module.
//
// Splitting the two is not tidiness. When the island imported the evaluators from worksheet.ts,
// that module's `import { taxonomy } from './content'` pulled the whole of taxonomy.json and
// landscape.json into the client bundle -- 86 KB of JavaScript for a page that needs a few
// kilobytes of strings, and with it every internal `note` field the taxonomy carries for the
// site's own authors. Keep this file import-free.

export type CoreAction = 'settle' | 'next';

export interface RelationRef {
  from: string;
  to: string;
}

export interface CautionRef {
  text: string;
  relates_to?: string[];
}

export interface CrossAnswer {
  id: string;
  label: string;
  caution?: CautionRef | null;
}

export interface CrossQuestion {
  id: string;
  prompt: string;
  answers: CrossAnswer[];
}

/** A core answer with its reason fully resolved to a plain string: a relation reference has
 *  already become the taxonomy's own `when` sentence. This, not the raw shape, is what ships to
 *  the client. */
export interface ResolvedCoreAnswer {
  id: string;
  label: string;
  action: CoreAction;
  level?: number;
  next?: string;
  reason: string;
}

export interface ResolvedCoreQuestion {
  id: string;
  level_tested: number;
  prompt: string;
  help?: string;
  answers: ResolvedCoreAnswer[];
}

export interface ResolvedWorksheetData {
  intro: { eyebrow: string; heading: string; aside: string };
  first_question: string;
  core_questions: ResolvedCoreQuestion[];
  cross_questions: CrossQuestion[];
}

/** An [questionId, answerId] pair, in the order the question was answered. */
export type AnswerPair = [string, string];

export interface Reason {
  questionId: string;
  questionPrompt: string;
  answerId: string;
  answerLabel: string;
  text: string;
}

export interface Caution {
  questionId: string;
  questionPrompt: string;
  answerId: string;
  answerLabel: string;
  text: string;
  relatesTo: string[];
}

export interface CoreResult {
  level: number;
  reasons: Reason[];
  /** False if the given answers ran out (an unanswered or invalid question) before any answer
   *  settled a level -- the caller still has questions left to ask. */
  settled: boolean;
}

/**
 * Walks the core-question tree from `first_question`, following `answers` in order. Stops at the
 * first "settle" answer. Stops (unsettled) at the first question with no matching answer, so a
 * partial or tampered answer list degrades to "keep asking" rather than throwing. Pure: the same
 * `data` and `answers` always produce the same result.
 */
export function evaluateCore(data: ResolvedWorksheetData, answers: AnswerPair[]): CoreResult {
  const byId = new Map(data.core_questions.map((q) => [q.id, q]));
  const given = new Map(answers);
  const reasons: Reason[] = [];
  let qid: string | undefined = data.first_question;
  let level = 0;
  let settled = false;

  while (qid) {
    const q: ResolvedCoreQuestion | undefined = byId.get(qid);
    if (!q) break;
    const answerId = given.get(qid);
    if (answerId === undefined) break;
    const a = q.answers.find((x) => x.id === answerId);
    if (!a) break;
    reasons.push({ questionId: q.id, questionPrompt: q.prompt, answerId: a.id, answerLabel: a.label, text: a.reason });
    if (a.action === 'settle') {
      level = a.level ?? level;
      settled = true;
      qid = undefined;
    } else {
      qid = a.next;
    }
  }
  return { level, reasons, settled };
}

/** The cautions from the cross-cutting answers given so far, in the order asked. Answers whose
 *  chosen option carries no caution (the "nothing to flag" option) contribute nothing. */
export function evaluateCross(data: ResolvedWorksheetData, answers: AnswerPair[]): Caution[] {
  const given = new Map(answers);
  const cautions: Caution[] = [];
  for (const q of data.cross_questions) {
    const answerId = given.get(q.id);
    if (answerId === undefined) continue;
    const a = q.answers.find((x) => x.id === answerId);
    if (!a || !a.caution) continue;
    cautions.push({
      questionId: q.id,
      questionPrompt: q.prompt,
      answerId: a.id,
      answerLabel: a.label,
      text: a.caution.text,
      relatesTo: a.caution.relates_to ?? [],
    });
  }
  return cautions;
}

export interface WorksheetResult extends CoreResult {
  cautions: Caution[];
}

export function evaluate(data: ResolvedWorksheetData, coreAnswers: AnswerPair[], crossAnswers: AnswerPair[]): WorksheetResult {
  const core = evaluateCore(data, coreAnswers);
  return { ...core, cautions: evaluateCross(data, crossAnswers) };
}

/** One step in the worksheet: the question to ask next, or "cross" once the level has settled
 *  and a cross-cutting question remains, or "result" once everything is answered. */
export type Step =
  | { phase: 'core'; question: ResolvedCoreQuestion }
  | { phase: 'cross'; question: CrossQuestion }
  | { phase: 'result' };

/**
 * Where the worksheet is, given the answers so far: still walking the core tree, working through
 * the fixed cross-cutting list, or done. Used by the island to know what to render, and by the
 * static fallback to build its reading-order anchors.
 */
export function currentStep(data: ResolvedWorksheetData, coreAnswers: AnswerPair[], crossAnswers: AnswerPair[]): Step {
  const core = evaluateCore(data, coreAnswers);
  if (!core.settled) {
    const byId = new Map(data.core_questions.map((q) => [q.id, q]));
    const given = new Map(coreAnswers);
    let qid: string | undefined = data.first_question;
    while (qid) {
      const q = byId.get(qid);
      if (!q) break;
      const answerId = given.get(qid);
      if (answerId === undefined) return { phase: 'core', question: q };
      const a = q.answers.find((x) => x.id === answerId);
      if (!a) return { phase: 'core', question: q };
      qid = a.action === 'settle' ? undefined : a.next;
    }
    return { phase: 'core', question: data.core_questions[0] };
  }
  const given = new Map(crossAnswers);
  const next = data.cross_questions.find((q) => given.get(q.id) === undefined);
  if (next) return { phase: 'cross', question: next };
  return { phase: 'result' };
}

/** Total questions a full walk asks at most: the longest root-to-leaf path through the core
 *  tree, plus every cross question -- used only for the progress line ("question N of up to M"),
 *  since the real count depends on where the core tree settles. */
export function maxQuestions(data: ResolvedWorksheetData): number {
  const byId = new Map(data.core_questions.map((q) => [q.id, q]));
  function depth(qid: string, seen: Set<string>): number {
    if (seen.has(qid)) return 0; // guard against a cyclic data bug
    const q = byId.get(qid);
    if (!q) return 0;
    let best = 1;
    for (const a of q.answers) {
      if (a.action === 'next' && a.next) {
        best = Math.max(best, 1 + depth(a.next, new Set(seen).add(qid)));
      }
    }
    return best;
  }
  return depth(data.first_question, new Set()) + data.cross_questions.length;
}

// -- Result-view shapes. buildLevelInfo (worksheet.ts) fills these in server-side. --

export type WorksheetStatus = 'planned' | 'stub' | 'draft' | 'published';

export interface WorksheetTechnique {
  slug: string;
  title: string;
  summary: string;
  status: WorksheetStatus;
}

export interface WorksheetRecipe {
  slug: string;
  title: string;
  summary: string;
  levels: number[];
}

export interface LevelInfo {
  order: number;
  title: string;
  who: string;
  description: string;
  color: string;
  techniques: WorksheetTechnique[];
  recipes: WorksheetRecipe[];
  /** What the next level up would add and what it costs, from that tier's own description.
   *  Undefined at level 7: there is no next level. */
  next?: { order: number; title: string; who: string; description: string };
}
