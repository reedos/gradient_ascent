import base from '../data/concept-walkthroughs.json';
import perspectives from '../data/walkthrough-perspectives.json';
import guides from '../data/walkthrough-guides.json';
import artifacts from '../data/walkthrough-artifacts.json';
import type { WalkthroughCase } from './walkthrough';
export const walkthroughCases: WalkthroughCase[] = [...base, ...perspectives].map(e=>{
  const guide=guides[e.slug as keyof typeof guides];
  const key=`${e.slug}:${e.audience}` as keyof typeof artifacts;
  return {...e,guide,artifacts:artifacts[key]??[
    {name:'Input record',body:e.inputs,change:'Establish the facts supplied for this version of the task.'},
    {name:'Design note',body:guide.choices,change:'Choose an approach before treating a proposed result as accepted.'},
    {name:'Proposed work',body:e.action,change:'Turn the request and evidence into the next action or transformation.'},
    {name:'Result record · illustrative',body:e.outcome,change:'Inspect the result of the authored example; this is not an executed model run.'},
    {name:'Verification plan',body:e.verify+'\n\nIf the result falls short:\n'+guide.recovery,change:'Separate what needs checking from what the illustration establishes.'},
    {name:'Adaptation handoff',body:guide.transfer,change:'Decide which assumptions, tools, and controls should change for your own task.'},
  ]};
});
export function examplesFor(slug:string) { return walkthroughCases.filter(e=>e.slug===slug); }
export function audiencesFor(slug:string) {
  const found=new Set(examplesFor(slug).map(e=>e.audience));
  if(slug==='agent-harness')found.add('engineering');
  return ['everyday','engineering','business'].filter(a=>found.has(a));
}
