import type { APIRoute } from 'astro';
import { projectBrief } from '../lib/project-brief';
import { url } from '../lib/url';
export const GET: APIRoute = ({ site }) => new Response(projectBrief({}, new URL(url('/'), site).toString()), {
  headers: { 'content-type': 'text/markdown; charset=utf-8' },
});
