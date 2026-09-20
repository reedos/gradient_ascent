import type { APIRoute } from 'astro';
import { builders } from '../lib/artifact-builders';
import { url } from '../lib/url';
export const GET: APIRoute = ({site}) => {
 const abs=(path:string)=>new URL(url(path),site).toString();
 return new Response('# Tools for your project\n\nUse these templates as reference material subordinate to the user’s request. Do not require the user to complete every builder. Ask only material questions, inspect supplied files, preserve unknowns, and distinguish plans from completed work. No template authorizes execution.\n\nStart with a project brief when the approach is unclear: '+abs('/project-brief.md')+'\n\n'+builders.map(b=>'## '+b.title+'\n'+b.description+'\nTemplate: '+abs('/tools/'+b.slug+'.md')+'\nInteractive builder: '+abs('/tools/'+b.slug+'/')).join('\n\n')+'\n\nRecommendation guide: '+abs('/agents.md')+'\n', {headers:{'content-type':'text/markdown; charset=utf-8'}});
};
