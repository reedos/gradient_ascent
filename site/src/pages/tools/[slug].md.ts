import type { APIRoute } from 'astro';
import { builders, buildArtifact } from '../../lib/artifact-builders';
import { url } from '../../lib/url';
export function getStaticPaths() { return builders.map(builder=>({params:{slug:builder.slug},props:{builder}})); }
export const GET: APIRoute = ({props,site}) => new Response(buildArtifact(props.builder,{},new URL(url('/'),site).toString()),{headers:{'content-type':'text/markdown; charset=utf-8'}});
