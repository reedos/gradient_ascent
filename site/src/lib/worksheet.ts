// The worksheet's server side. content/worksheet.json holds the questions and answers as data
// (see its own "note" field); this module is the one place that walks it, resolves a taxonomy
// relation reference into that relation's own `when` sentence, and builds each level's result
// data. The pure evaluator functions and every shape they take live in ./worksheet-core, which
// imports nothing -- that is the module the browser island loads, so the taxonomy and the
// registry stay on the server. Everything from worksheet-core is re-exported here, so a page can
// keep importing one module.
//
// Two layers, on purpose. The *raw* shape (straight off the JSON) can reference a taxonomy
// relation by id instead of copying its "when" sentence, so the two can never drift apart -- but
// resolving that reference means importing content.ts, which pulls in the whole taxonomy and
// registry. The site's other islands never ship that import to the client (see LevelExplorer's
// NameChip and RunDiagram's RunDef: both take pre-resolved, page-slim props instead), so this
// module resolves everything server-side into a *resolved* shape -- plain strings only, no
// relation refs -- and that is what gets handed to the client as a prop. The pure evaluators are
// the one thing both the page (the no-JS fallback, and the server-rendered initial state) and the
// island (client-side, once JavaScript answers a question) call: same inputs, same output.
import worksheetData from '../../../content/worksheet.json';
import { taxonomy, levels as tierList, recipes as allRecipes, recipeLevels } from './content';
import type {
  CoreAction,
  CrossQuestion,
  LevelInfo,
  RelationRef,
  ResolvedWorksheetData,
  WorksheetRecipe,
  WorksheetTechnique,
} from './worksheet-core';

export * from './worksheet-core';

interface RawCoreAnswer {
  id: string;
  label: string;
  action: CoreAction;
  level?: number;
  next?: string;
  reason?: string;
  relation?: RelationRef;
}

interface RawCoreQuestion {
  id: string;
  level_tested: number;
  prompt: string;
  help?: string;
  answers: RawCoreAnswer[];
}

interface RawWorksheetData {
  version: number;
  intro: { eyebrow: string; heading: string; aside: string };
  first_question: string;
  core_questions: RawCoreQuestion[];
  cross_questions: CrossQuestion[];
}

const rawWorksheet = worksheetData as unknown as RawWorksheetData;

/**
 * The `when` sentence of the taxonomy's own upgrades_to relation matching `ref`, or undefined if
 * content/taxonomy.json carries no such relation.
 */
function relationWhen(ref: RelationRef): string | undefined {
  const rel = taxonomy.relations.find((r) => r.from === ref.from && r.to === ref.to && r.type === 'upgrades_to');
  return rel?.when;
}

/**
 * Builds the resolved worksheet data once, server-side: every answer's relation reference (if
 * any) becomes its final reason text. Call this on the page and pass the result to the island as
 * a prop; nothing downstream of this needs content.ts again.
 */
export function resolveWorksheet(): ResolvedWorksheetData {
  return {
    intro: rawWorksheet.intro,
    first_question: rawWorksheet.first_question,
    core_questions: rawWorksheet.core_questions.map((q) => ({
      id: q.id,
      level_tested: q.level_tested,
      prompt: q.prompt,
      help: q.help,
      answers: q.answers.map((a) => ({
        id: a.id,
        label: a.label,
        action: a.action,
        level: a.level,
        next: a.next,
        reason: a.relation ? relationWhen(a.relation) ?? a.reason ?? '' : a.reason ?? '',
      })),
    })),
    cross_questions: rawWorksheet.cross_questions,
  };
}

/** One level's result-view data: its techniques, the recipes whose highest level is exactly this
 *  one, and what the next level up would add. Server-side only -- built once per level and
 *  passed to the island as a plain prop, the same way index.astro builds levelDetails for
 *  LevelExplorer. */
export function buildLevelInfo(order: number): LevelInfo {
  const tier = tierList.find((t) => t.order === order);
  if (!tier) throw new Error(`no tier at order ${order}`);
  const next = tierList.find((t) => t.order === order + 1);
  const recipesHere = allRecipes.filter((r) => {
    const lv = recipeLevels(r);
    return lv.length > 0 && Math.max(...lv) === order;
  });
  const techniques: WorksheetTechnique[] = tier.pages.map((p) => ({
    slug: p.slug,
    title: p.title,
    summary: p.summary,
    status: p.status,
  }));
  const recipes: WorksheetRecipe[] = recipesHere.map((r) => ({
    slug: r.slug,
    title: r.title,
    summary: r.summary,
    levels: recipeLevels(r),
  }));
  return {
    order: tier.order,
    title: tier.title,
    who: tier.who,
    description: tier.description,
    color: `var(--o${tier.order})`,
    techniques,
    recipes,
    ...(next ? { next: { order: next.order, title: next.title, who: next.who, description: next.description } } : {}),
  };
}

export function allLevelInfo(): LevelInfo[] {
  return tierList.map((t) => buildLevelInfo(t.order));
}

/** The recipes whose highest level is exactly `order` -- the same set buildLevelInfo attaches to
 *  a worksheet result, exposed so /levels/<order>/ can list them too and the two pages cannot
 *  disagree about which recipes top out where. */
export function recipesForLevel(order: number): WorksheetRecipe[] {
  return buildLevelInfo(order).recipes;
}
