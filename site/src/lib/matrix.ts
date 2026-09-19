// The use-case x pattern matrix promised in the project plan's Content model: recipes down the side,
// techniques across, a filled cell where that recipe uses that technique. Only the shaping lives
// here, and it takes its data as plain arguments -- no import of content.ts, no JSON import -- so
// site/tests/matrix.test.ts can run it under plain `node --test` with no bundler, the same
// arrangement lib/timeline.ts and lib/search.ts use.
//
// One judgment is baked in: a technique NO recipe uses gets no column. The site has 54 technique
// and topic pages; a grid with a column for each would be mostly empty, would not fit any screen,
// and would say less than the columns that earn their place. The count of dropped columns is
// returned so the page can say so out loud rather than quietly showing a subset.

export type MatrixLevel = number | 'tracks';

export interface MatrixTechnique {
  slug: string;
  title: string;
  level: MatrixLevel;
}

export interface MatrixRecipe {
  slug: string;
  title: string;
  uses: string[];
}

export interface MatrixGroup {
  level: MatrixLevel;
  label: string;
  /** Column color token, e.g. "var(--o3)" or "var(--ot)". */
  color: string;
  techniques: MatrixTechnique[];
}

export interface MatrixRow {
  slug: string;
  title: string;
  /** One entry per column, in column order: true where this recipe uses that technique. */
  cells: boolean[];
  /** The techniques this recipe uses, in column order -- the phone fallback's pill list. */
  used: MatrixTechnique[];
  /** The highest numbered level this recipe reaches; undefined if it uses topic pages only. */
  highest?: number;
}

export interface Matrix {
  groups: MatrixGroup[];
  /** Every column, flattened in group order: the order every row's `cells` follows. */
  columns: MatrixTechnique[];
  rows: MatrixRow[];
  /** How many recipes use each column, in column order. */
  columnCounts: number[];
  /** Techniques that no recipe uses, and so have no column. */
  unusedCount: number;
}

export function levelColor(level: MatrixLevel): string {
  return level === 'tracks' ? 'var(--ot)' : `var(--o${level})`;
}

export function levelLabel(level: MatrixLevel): string {
  return level === 'tracks' ? 'Topics' : `Level ${level}`;
}

/** Numbered levels ascending, topics last: the column order, and the order a pill list reads in. */
function compareLevels(a: MatrixLevel, b: MatrixLevel): number {
  if (a === 'tracks') return b === 'tracks' ? 0 : 1;
  if (b === 'tracks') return -1;
  return a - b;
}

/**
 * Build the matrix. `techniques` is every technique page the site has; `recipes` is every recipe.
 * Columns keep the order they arrive in within a level, so the taxonomy's own ordering of a
 * level's pages is what the grid shows.
 */
export function buildMatrix(recipes: MatrixRecipe[], techniques: MatrixTechnique[]): Matrix {
  const bySlug = new Map(techniques.map((t) => [t.slug, t]));
  const used = new Set<string>();
  for (const recipe of recipes) {
    for (const slug of recipe.uses) {
      if (bySlug.has(slug)) used.add(slug);
    }
  }

  const columnsUnsorted = techniques.filter((t) => used.has(t.slug));
  const levelsPresent = [...new Set(columnsUnsorted.map((t) => t.level))].sort(compareLevels);
  const groups: MatrixGroup[] = levelsPresent.map((level) => ({
    level,
    label: levelLabel(level),
    color: levelColor(level),
    techniques: columnsUnsorted.filter((t) => t.level === level),
  }));
  const columns = groups.flatMap((g) => g.techniques);

  const rows: MatrixRow[] = recipes.map((recipe) => {
    const uses = new Set(recipe.uses);
    const cells = columns.map((c) => uses.has(c.slug));
    const usedHere = columns.filter((c) => uses.has(c.slug));
    const numbered = usedHere.map((c) => c.level).filter((l): l is number => typeof l === 'number');
    return {
      slug: recipe.slug,
      title: recipe.title,
      cells,
      used: usedHere,
      ...(numbered.length ? { highest: Math.max(...numbered) } : {}),
    };
  });

  const columnCounts = columns.map((_, i) => rows.reduce((n, row) => n + (row.cells[i] ? 1 : 0), 0));

  return {
    groups,
    columns,
    rows,
    columnCounts,
    unusedCount: techniques.length - columns.length,
  };
}
