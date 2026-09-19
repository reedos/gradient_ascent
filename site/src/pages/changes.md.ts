// /changes.md: the clean Markdown twin of /changes/, the same way every other page on the site
// has one. A reader's own agent can read this to find out whether a page it cited has been
// corrected since.
import type { APIRoute } from 'astro';
import { url } from '../lib/url';
import { changes, changesMarkdown } from '../lib/changes';

export const GET: APIRoute = ({ site }) => {
  const abs = (path: string) => new URL(url(path), site).toString();
  return new Response(changesMarkdown(changes, abs), {
    headers: { 'content-type': 'text/markdown; charset=utf-8' },
  });
};
