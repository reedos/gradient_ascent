import type { APIRoute } from 'astro';
import notes from '../../../docs/QUALITY_PROTOTYPE.md?raw';
export const GET:APIRoute=()=>new Response(notes,{headers:{'content-type':'text/markdown; charset=utf-8'}});
