// The client-side search's whole data source: every SearchDoc, built once at compile time by
// search-docs.ts from the site's own content.ts/indexes.ts, served as one small JSON file so the
// Search island can fetch it once and search entirely in the browser -- no query ever leaves the
// machine, no third-party service, no server round trip after the first load.
import type { APIRoute } from 'astro';
import { buildSearchDocs } from '../lib/search-docs';

export const GET: APIRoute = async () => {
  const docs = await buildSearchDocs();
  return new Response(JSON.stringify(docs), {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
