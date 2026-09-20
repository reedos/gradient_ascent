import { useEffect, useState } from 'react';
import ConceptWalkthrough from './ConceptWalkthrough';
import DutWalkthrough from './DutWalkthrough';
import { audienceLabels, type WalkthroughCase } from '../../lib/walkthrough';

export default function WalkthroughPerspectives({examples,dedicatedDut=false}: {examples:WalkthroughCase[];dedicatedDut?:boolean}) {
  const [ready,setReady]=useState(false);
  const initial=dedicatedDut?'engineering':examples[0].audience;
  const available=['everyday','engineering','business'].filter(a=>(dedicatedDut&&a==='engineering')||examples.some(e=>e.audience===a));
  const [audience,setAudience]=useState(initial);
  useEffect(()=>{setReady(true);const requested=new URL(location.href).searchParams.get('audience');if(requested&&available.includes(requested))setAudience(requested);},[]);
  function select(next:string) {
    setAudience(next);
    const url=new URL(location.href);url.searchParams.set('audience',next);history.replaceState(null,'',url);
  }
  const selected=examples.find(e=>e.audience===audience);
  return <section className="perspective-shell" id="guided-example" aria-label="Worked example perspectives">
    {available.length>1?<div className="perspective-picker"><span>CHOOSE YOUR PERSPECTIVE</span><div role="group" aria-label="Example perspective">{available.map(a=><button key={a} type="button" disabled={!ready} aria-pressed={audience===a} onClick={()=>select(a)}>{audienceLabels[a]}</button>)}</div><p>Same concept, different task and consequences. Switching starts a fresh walkthrough; prior answers and approvals do not carry over.</p></div>:<p className="perspective-single">A focused {audienceLabels[audience].toLowerCase()} example. Additional perspectives appear where they provide a useful contrast.</p>}
    {dedicatedDut&&audience==='engineering'?<DutWalkthrough key="dut-engineering" embedded/>:selected&&<ConceptWalkthrough key={`${selected.slug}-${selected.audience}`} lesson={selected}/>}
  </section>;
}
