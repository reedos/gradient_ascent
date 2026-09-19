// The server-side half of lib/agents.ts: reads the real content and hands the pure builders what
// they need. Kept apart so agents.ts imports nothing and stays testable under `node --test`.
import {
  levels,
  tracks,
  recipes,
  recipeLevels,
  teardowns,
  taxonomy,
  counts,
  asOf,
  techniqueBySlug,
  levelOfSlug,
} from './content';
import { glossaryTerms } from './indexes';
import { milestones } from './timeline';
import { resolveWorksheet } from './worksheet';
import { url } from './url';
import shapesData from '../../../content/shapes.json';
import { orderedShapes, shapesFor, type Shape, type ShapesFile } from './shapes';
import type { AgentLevel, AgentShape, AgentWorksheet, GuideInput, UseCase } from './agents';

export const shapes: Shape[] = orderedShapes((shapesData as unknown as ShapesFile).shapes);

export function absFor(site: URL | undefined): (path: string) => string {
  return (path: string) => new URL(url(path), site).toString();
}

export function agentLevels(): AgentLevel[] {
  return levels.map((l) => ({ order: l.order, title: l.title, who: l.who, description: l.description }));
}

export function agentWorksheet(): AgentWorksheet {
  const w = resolveWorksheet();
  return { first_question: w.first_question, core_questions: w.core_questions, cross_questions: w.cross_questions };
}

function allPages(): { status?: string }[] {
  return [...levels.flatMap((l) => l.pages), ...tracks.flatMap((t) => t.pages ?? []), ...recipes];
}

/** The shapes with every slug resolved to a title and an address. */
export function agentShapes(site: URL | undefined): AgentShape[] {
  const abs = absFor(site);
  return shapes.map((sh) => ({
    id: sh.id,
    title: sh.title,
    what: sh.what,
    signals: sh.signals,
    usual_level: sh.usual_level,
    lower_when: sh.lower_when,
    higher_when: sh.higher_when,
    elsewhere: sh.elsewhere,
    techniques: sh.techniques.map((slug) => ({ slug, title: techniqueBySlug(slug)?.title ?? slug, markdown: abs(`/techniques/${slug}.md`) })),
    recipes: sh.recipes.map((slug) => {
      const r = recipes.find((x) => x.slug === slug);
      return { slug, title: r?.title ?? slug, domain: (r as { domain?: string } | undefined)?.domain ?? 'general', markdown: abs(`/recipes/${slug}.md`) };
    }),
    teardowns: sh.teardowns.map((slug) => ({ slug, title: teardowns.find((x) => x.slug === slug)?.title ?? slug, markdown: abs(`/teardowns/${slug}.md`) })),
  }));
}

export function guideInput(site: URL | undefined): GuideInput {
  return {
    abs: absFor(site),
    levelRule: taxonomy.level_rule,
    levels: agentLevels(),
    counts: {
      techniques: counts.techniques,
      recipes: counts.recipes,
      teardowns: counts.teardowns,
      names: counts.named,
      milestones: milestones.length,
      terms: glossaryTerms.length,
    },
    namesAsOf: asOf,
    allDraft: allPages().every((p) => p.status !== 'published'),
    domainCounts: useCases(site).reduce<Record<string, number>>((acc, c) => {
      acc[c.domain] = (acc[c.domain] ?? 0) + 1;
      return acc;
    }, {}),
    shapes: agentShapes(site),
  };
}

function techniqueRefs(slugs: string[], abs: (p: string) => string): UseCase['techniques'] {
  return slugs.map((slug) => {
    const ref = techniqueBySlug(slug);
    const level = levelOfSlug(slug);
    return {
      slug,
      title: ref?.title ?? slug,
      level: typeof level === 'number' ? level : 'topic',
      url: abs(`/techniques/${slug}/`),
      markdown: abs(`/techniques/${slug}.md`),
    };
  });
}

/** Every recipe and teardown as one list an agent can match a job against. */
export function useCases(site: URL | undefined): UseCase[] {
  const abs = absFor(site);
  const fromRecipes: UseCase[] = recipes.map((r) => {
    const lv = recipeLevels(r);
    return {
      kind: 'recipe',
      slug: r.slug,
      title: r.title,
      summary: r.summary,
      // `domain` arrives with the engineering recipes; a recipe without one is a general one.
      domain: (r as { domain?: string }).domain ?? 'general',
      shapes: shapesFor(shapes, r.slug).map((x) => x.id),
      needs_level: lv.length ? Math.max(...lv) : null,
      levels: lv,
      techniques: techniqueRefs(r.uses, abs),
      url: abs(`/recipes/${r.slug}/`),
      markdown: abs(`/recipes/${r.slug}.md`),
    };
  });
  const fromTeardowns: UseCase[] = teardowns.map((t) => {
    const lv = t.patterns.map((s) => levelOfSlug(s)).filter((x): x is number => typeof x === 'number');
    return {
      kind: 'teardown',
      slug: t.slug,
      title: t.title,
      summary: 'A kind of product people already use, taken apart into the techniques it is built from, from its makers’ own pages.',
      domain: 'general',
      shapes: shapesFor(shapes, t.slug).map((x) => x.id),
      needs_level: lv.length ? Math.max(...lv) : null,
      levels: [...new Set(lv)].sort((a, b) => a - b),
      techniques: techniqueRefs(t.patterns, abs),
      url: abs(`/teardowns/${t.slug}/`),
      markdown: abs(`/teardowns/${t.slug}.md`),
    };
  });
  return [...fromRecipes, ...fromTeardowns];
}
