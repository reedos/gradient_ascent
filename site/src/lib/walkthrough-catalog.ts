import base from '../data/concept-walkthroughs.json';
import perspectives from '../data/walkthrough-perspectives.json';
import guides from '../data/walkthrough-guides.json';
import type { WalkthroughCase } from './walkthrough';
export const walkthroughCases: WalkthroughCase[] = [...base, ...perspectives].map(e=>({
  ...e, guide: guides[e.slug as keyof typeof guides],
}));
export function examplesFor(slug:string) { return walkthroughCases.filter(e=>e.slug===slug); }
export function audiencesFor(slug:string) {
  const found=new Set(examplesFor(slug).map(e=>e.audience));
  if(slug==='agent-harness')found.add('engineering');
  return ['everyday','engineering','business'].filter(a=>found.has(a));
}
