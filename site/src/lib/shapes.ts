// Job shapes: the kinds of work people bring to a language model, described by what the work is
// and not by what it is about. content/shapes.json holds them; this module is pure shaping, so it
// runs under `node --test` with synthetic data.
//
// Why they exist. The owner asked whether pointing a reader (or a reader's agent) at "the closest
// recipe" builds things too narrow, and it did: a recipe is one worked story, and matching a job
// to the nearest story invites bending the job to fit. A shape is the general thing. "Sort
// incoming items and send each where it belongs" is one shape whether the items are tenant
// emails, support tickets or failed production units. So a job is matched to a shape, the
// worksheet settles its level, and a recipe is an illustration of the shape, never the answer.

export interface Shape {
  id: string;
  title: string;
  what: string;
  signals: string[];
  /** Where the worksheet most often settles for this shape. A starting expectation only. */
  usual_level: number;
  lower_when: string;
  higher_when: string;
  techniques: string[];
  recipes: string[];
  teardowns: string[];
  /** Jobs from unrelated fields with the same shape. */
  elsewhere: string[];
}

export interface ShapesFile {
  version: number;
  note: string;
  shapes: Shape[];
}

/** Shapes in the order a reader meets the levels: lowest usual level first, file order within. */
export function orderedShapes(shapes: Shape[]): Shape[] {
  return shapes.map((s, i) => ({ s, i })).sort((a, b) => a.s.usual_level - b.s.usual_level || a.i - b.i).map((x) => x.s);
}

/** The shapes a recipe or teardown illustrates. */
export function shapesFor(shapes: Shape[], slug: string): Shape[] {
  return shapes.filter((s) => s.recipes.includes(slug) || s.teardowns.includes(slug));
}

export interface ShapeProblems {
  unknownTechniques: [string, string][];
  unknownRecipes: [string, string][];
  unknownTeardowns: [string, string][];
  recipesWithNoShape: string[];
  duplicateIds: string[];
}

/** What is wrong with the shapes file, given what exists. Empty lists mean nothing is. */
export function shapeProblems(shapes: Shape[], known: { techniques: string[]; recipes: string[]; teardowns: string[] }): ShapeProblems {
  const tech = new Set(known.techniques);
  const rec = new Set(known.recipes);
  const td = new Set(known.teardowns);
  const seen = new Set<string>();
  const out: ShapeProblems = { unknownTechniques: [], unknownRecipes: [], unknownTeardowns: [], recipesWithNoShape: [], duplicateIds: [] };
  for (const s of shapes) {
    if (seen.has(s.id)) out.duplicateIds.push(s.id);
    seen.add(s.id);
    for (const t of s.techniques) if (!tech.has(t)) out.unknownTechniques.push([s.id, t]);
    for (const r of s.recipes) if (!rec.has(r)) out.unknownRecipes.push([s.id, r]);
    for (const t of s.teardowns) if (!td.has(t)) out.unknownTeardowns.push([s.id, t]);
  }
  const covered = new Set(shapes.flatMap((s) => s.recipes));
  out.recipesWithNoShape = known.recipes.filter((r) => !covered.has(r));
  return out;
}
