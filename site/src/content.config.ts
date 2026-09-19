import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// A primary source, as recorded in frontmatter for a page's <Sources> block: {title, url,
// publisher, date, accessed}. Every factual claim about the world cites one of these; `Cite`
// marks the spot in the prose, `Sources` renders the numbered list they point back to.
const sourceSchema = z.object({
  title: z.string(),
  url: z.url(),
  publisher: z.string().optional(),
  date: z.string().optional(),
  accessed: z.string(),
});

// A written technique page. Nothing was authored here before rag.mdx; techniques/[slug].astro
// falls back to an honest "not written yet" stub when no matching entry exists in this
// collection, and reads status from content/taxonomy.json regardless (draft vs. published is a
// taxonomy fact, not a frontmatter one, so the two can never disagree).
const techniques = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/techniques' }),
  schema: z.object({
    slug: z.string(),
    reviewed: z.coerce.date(),
    sources: z.array(sourceSchema),
    /** Which src/data/runs/<id>.json this page's <Run> steps through, for cross-checking. */
    run: z.string().optional(),
    /** Tier order 0..7, for cross-checking against the page's taxonomy entry. */
    level: z.number().optional(),
    /** Which lanes this page actually writes; both by default. */
    lanes: z.array(z.enum(['use', 'build'])).optional(),
  }),
});

// A written recipe page. recipes/[slug].astro falls back to its generated "techniques this
// recipe uses" panel alone when no entry exists here.
const recipes = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/recipes' }),
  schema: z.object({
    slug: z.string(),
    reviewed: z.coerce.date(),
    sources: z.array(sourceSchema).default([]),
  }),
});

// A written teardown: one kind of real product, decoded into this site's techniques. The list of
// teardowns, their titles and the techniques each one decodes live in content/taxonomy.json's
// `teardowns` block; this collection holds the writing. The schema is fixed (see
// docs/WRITING-A-TEARDOWN.md): a teardown is about named products, so `products` may not be
// empty and every id in it must be a registry entry, and it decodes what makers say about their
// own systems, so `sources` may not be empty either. scripts/validate.py enforces both against
// the files on disk, and that every teardown in the taxonomy has a file and vice versa.
const teardowns = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/teardowns' }),
  schema: z.object({
    slug: z.string(),
    /** Registry ids (content/landscape.json) of the products this teardown decodes. */
    products: z.array(z.string()).min(1),
    reviewed: z.coerce.date(),
    sources: z.array(sourceSchema).min(1),
  }),
});

// A written thread page: a cross-cutting idea that runs through several technique pages (see
// content/taxonomy.json's `threads`). threads/[id].astro falls back to an outline listing the
// thread's pages when no entry exists here, the same way techniques/[slug].astro does.
const threads = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/threads' }),
  schema: z.object({
    id: z.string(),
    reviewed: z.coerce.date(),
    sources: z.array(sourceSchema).default([]),
  }),
});

export const collections = { techniques, recipes, teardowns, threads };
