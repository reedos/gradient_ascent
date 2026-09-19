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
