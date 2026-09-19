// @ts-check
import { defineConfig } from 'astro/config';

import mdx from '@astrojs/mdx';
import preact from '@astrojs/preact';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://reedos.github.io',
  base: '/gradient_ascent/',
  trailingSlash: 'always',
  output: 'static',

  // audit-weight, wave 6: tried setting compressHTML explicitly to `true` (Astro's "lossless"
  // whitespace removal) against the v7 default of 'jsx' (JSX's own whitespace rules). Measured on
  // a full build, `true` made every page LARGER, not smaller -- /failures/ +3,670 B, /map/
  // +2,050 B, / +1,256 B, none of which touch this audit's territory, so the only variable was
  // this setting. The default 'jsx' mode is already the better choice for this site and is left
  // as the default rather than pinned, so a future Astro upgrade's own default keeps applying.

  // Preact + compat in place of React (2026-09-18 experiment): the three islands (LevelStack,
  // LevelExplorer, RunDiagram) import from 'react' unchanged; compat mode aliases those imports
  // to preact/compat so the components don't need touching. See the project plan Task 4.2.
  integrations: [mdx(), preact({ compat: true })],

  vite: {
    plugins: [tailwindcss()],
    server: {
      fs: {
        allow: ['..'],
      },
    },
  },
});
