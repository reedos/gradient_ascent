// /changes.xml: the Atom 1.0 feed of what changed on the site, from the same
// content/changes.json the page reads. A reader who subscribes learns that a page was corrected
// without having to come back and look.
//
// Atom rather than RSS: it requires a stable id and an unambiguous `updated` timestamp per entry,
// which is exactly what a log of corrections needs. The rendering is in src/lib/changes.ts so it
// can be tested without a build.
import type { APIRoute } from 'astro';
import { url } from '../lib/url';
import { atomFeed, changes } from '../lib/changes';

export const GET: APIRoute = ({ site }) => {
  const abs = (path: string) => new URL(url(path), site).toString();
  const body = atomFeed(changes, {
    pageUrl: abs('/changes/'),
    feedUrl: abs('/changes.xml'),
    abs,
  });
  return new Response(body, { headers: { 'content-type': 'application/atom+xml; charset=utf-8' } });
};
