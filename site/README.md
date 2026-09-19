# Gradient Ascent — site

Astro + MDX + React islands + Tailwind, static output.

## Develop

```
npm install
npm run dev
```

## Build

```
npm run build
npm run preview
```

`npx astro check` type-checks the project.

## Where the content comes from

Nothing here is a copy. `src/lib/content.ts` imports `../../../content/taxonomy.json` and
`../../../content/landscape.json` directly and exports typed helpers; every page and island reads
through those helpers. Edit the JSON in `content/`, not a duplicate in `site/`.

Written technique pages, when they exist, live in `src/content/techniques/<slug>.mdx` (an Astro
content collection). Until a slug has one, `src/pages/techniques/[slug].astro` renders an honest
stub generated from the taxonomy and the registry.

Run definitions for the trace player live in `src/data/runs/*.json`.
