import { useEffect, useState } from 'react';

const initialPrompt = 'Create a project for the new DUT using our Python test framework. Read CLAUDE.md and DUT_BRIEF.md, start from the closest past project, and reuse existing tools. Show me the plan before creating files. Do not change the shared framework or connect to instruments.';
const phases = ['Understand', 'Plan', 'Approval', 'Generate', 'Check', 'Hand over'];
const concepts = ['Context engineering', 'Agent loop', 'Human approval', 'Tools + permissions', 'Guardrails + evaluation', 'Observability'];
const why = [
  'The agent needs the relevant references and DUT differences before it can make a useful plan. A past project supplies patterns, not permission to copy its limits.',
  'The model proposes the work. The harness keeps that proposal separate from executing it.',
  'A person decides whether the proposed scope is acceptable. Approving this plan does not authorize framework changes or live instrument access.',
  'The agent edits project files using its tools. The resulting Python code will use framework functions when the user runs it later.',
  'Checks provide specific evidence. Valid syntax and configuration do not establish that a measurement is correct.',
  'A useful handoff records what exists, what was checked, and what remains unverified. Hardware results can become context for the next revision.',
];
const responses = [
  'I have the reusable instructions, DUT brief, and a candidate reference project. I’ll compare the DUT differences against the framework documentation before proposing changes. I will ask about missing requirements rather than copy values from the old project.',
  'Here is the proposed plan: adapt the closest suitable project, create the project configuration and test files, and reuse the framework’s measurement and CSV-export functions. I’ll run only approved checks without hardware access. Please review the plan before I generate anything.',
  'I’m waiting for your decision on PROJECT_PLAN.md. No implementation files have been created. Framework changes and new project-local tools would need separate approval.',
  'The plan is approved. In this demonstration, I create the project files and documentation inside the DUT project folder. The framework remains unchanged. I do not connect to instruments.',
  'The illustrated syntax and configuration checks pass. These are scripted sample results, not checks executed against your framework. Measurement correctness and instrument behavior remain unverified.',
  'The review package is ready. Review the files and requirements checklist, then run the project yourself in your instrument environment. Return logs and observations for a scoped revision. PROJECT_STATUS.md separates generated work from verified behavior.',
];
const artifacts = [
  {file:'Context selected for this task', text:'CLAUDE.md\n  Reuse framework tools · ask before expanding scope\n\nDUT_BRIEF.md\n  New DUT requirements and differences\n\nReference project + framework documentation\n  Existing structure, interfaces, and conventions'},
  {file:'PROJECT_PLAN.md · draft', text:'# Proposed work\n\n1. Confirm reference project fits this DUT.\n2. Adapt Python tests and YAML/JSON configuration.\n3. Reuse measurement, units, and CSV functions.\n4. Run approved non-hardware checks.\n5. Deliver documentation and review checklist.\n\nNo framework edits. No instrument access.'},
  {file:'Approval record · pending', text:'Requested scope: DUT project files only\nFramework modification: not authorized\nNew project-local tool: not authorized\nLive instrument access: not authorized\n\nWaiting for the user’s decision.'},
  {file:'Project files · illustrative structure', text:'new_dut/\n  tests.py             DUT-specific test sequence\n  instruments.yaml     Framework instrument configuration\n  parameters.yaml      Approved parameters and limits\n  README.md            Capabilities and run instructions\n  PROJECT_STATUS.md    Work and validation record\n\nActual filenames follow your framework conventions.'},
  {file:'Validation record · simulated', text:'Python syntax               SAMPLE PASS\nConfiguration structure     SAMPLE PASS\nRequirements review         PENDING USER REVIEW\nInstrument behavior         NOT TESTED\nMeasurement correctness     NOT VERIFIED\n\nNo code or hardware checks execute in this walkthrough.'},
  {file:'PROJECT_STATUS.md · review package', text:'# Created\nProject code, configuration, and documentation\n\n# Checked\nSample syntax and configuration results only\n\n# Awaiting the user\nReview against DUT requirements\nRun with real instruments\nSupply logs, results, and observations\n\n# Boundaries\nNo framework changes or new helpers authorized'},
];

export default function DutWalkthrough({ embedded = false }: { embedded?: boolean }) {
  const [mode, setMode] = useState('watch');
  const [step, setStep] = useState(0);
  const [started, setStarted] = useState(false);
  const [prompt, setPrompt] = useState(initialPrompt);
  const [approved, setApproved] = useState(false);
  const [revision, setRevision] = useState(false);
  const [variant, setVariant] = useState('complete');
  const [answer, setAnswer] = useState('');
  const [visible, setVisible] = useState(0);
  const [showArtifact, setShowArtifact] = useState(false);
  const blocked = mode === 'change' && variant !== 'complete';
  const reply = step === 2 && approved ? 'The plan is approved for DUT project files only. I can proceed within that scope. New helpers, framework edits, and instrument access are still not authorized.' : revision ? 'You requested a revision. I will clarify and revise PROJECT_PLAN.md before asking again. Implementation remains paused; no project files have been generated.' : responses[step];
  useEffect(() => {
    setVisible(0);
    if (!started || mode !== 'watch') return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setVisible(reply.length); return; }
    const timer = setInterval(() => setVisible(n => {
      if (n >= reply.length) { clearInterval(timer); return reply.length; }
      return Math.min(n + 6, reply.length);
    }), 24);
    return () => clearInterval(timer);
  }, [step, started, reply, mode]);
  function restart() { setStep(0); setStarted(false); setApproved(false); setRevision(false); setShowArtifact(false); }
  function go(next: number) { setStep(next); setRevision(false); }

  const Heading = embedded ? 'h3' : 'h1';
  return <div className={'dut-pilot' + (embedded ? ' dut-embedded' : '')}>
    <div className="pilot-kicker">{embedded ? 'GUIDED WORKED EXAMPLE' : 'GUIDED WORKED EXAMPLE'} <span>Scripted simulation · no model calls or hardware access</span></div>
    <header className="pilot-intro"><div><Heading>From DUT brief to reviewable project.</Heading><p>Follow one task. See what the agent proposes, what the harness controls, and where you decide.</p></div><button className="pilot-quiet" onClick={restart}>Restart walkthrough ↺</button></header>
    <div className="walk-audience"><span className="pilot-chip">Engineering &amp; technical work</span><small>Create a DUT project within the shared framework’s conventions and approval boundaries.</small></div>
    <div className="pilot-modes" role="group" aria-label="Learning mode">{[['watch','01','Watch it'],['change','02','Change something'],['try','03','Try a decision']].map(([key,num,label]) => <button aria-pressed={mode===key} onClick={()=>setMode(key)}><small>{num}</small>{label}</button>)}</div>

    {mode === 'watch' && <>
      <section className="pilot-request"><label htmlFor="dut-request">Your request</label><div><textarea id="dut-request" value={prompt} readOnly={started} onChange={e=>setPrompt(e.currentTarget.value)} rows={3}/><button className="pilot-primary" disabled={!prompt.trim() || started} onClick={()=>setStarted(true)}>{started ? 'Request sent ✓' : 'Send request →'}</button></div><small>Prefilled English request. You can edit it; this walkthrough always demonstrates the same scripted workflow.</small></section>
      <div className="pilot-workspace">
        <section className="pilot-map" aria-label="Workflow diagram"><div className="pilot-panel-head"><span>THE WORKFLOW</span><small>{started ? `Step ${step+1} of 6` : 'Ready when you are'}</small></div>
          <div className="pilot-context"><strong>Context</strong><span>Instructions + DUT brief + reference project</span></div>
          <ol className="pilot-stages">{phases.map((phase,i)=><li className={started && i===step ? 'current' : started && i<step ? 'complete' : ''}><button disabled={!started || i>step} aria-current={started && i===step ? 'step' : undefined} onClick={()=>go(i)}><span>{started&&i<step?'✓':String(i+1).padStart(2,'0')}</span><div><strong>{phase}</strong><small>{['Select relevant references','Propose files and checks','Wait for your decision','Write within approved scope','Report evidence honestly','You review and test'][i]}</small></div></button></li>)}</ol>
          <div className="pilot-boundary"><strong>Always in effect</strong><span>Project-only scope</span><span>Framework changes need authorization</span><span>No live instrument access</span><small>Intended controls, illustrated here.</small></div>
        </section>
        <section className="pilot-work"><div className="pilot-panel-head"><span>THE VISIBLE WORK</span><span className="pilot-chip">{started ? concepts[step] : 'Start with a task'}</span></div>
          {!started ? <div className="pilot-empty"><span>01 → 06</span><h2>A project takes shape, one decision at a time.</h2><p>Send the request above. Then follow the agent’s work and make the approval decision yourself.</p><div className="pilot-preview-files">Brief → Plan → Approval → Files → Evidence</div></div> : <>
            <div className="pilot-message"><span className="pilot-avatar">A</span><div><small>AGENT · SCRIPTED REPLY</small><p aria-hidden="true">{reply.slice(0,visible)}{visible<reply.length&&<span className="pilot-caret">▍</span>}</p><span className="pilot-sr" role="status">{visible>=reply.length ? reply : 'Sample response appearing.'}</span>{visible<reply.length&&<button className="pilot-quiet" onClick={()=>setVisible(reply.length)}>Show full reply</button>}</div></div>
            <div className="pilot-artifact"><button className="pilot-artifact-title" onClick={()=>setShowArtifact(!showArtifact)} aria-expanded={showArtifact}><span>▤ {step===2 && approved ? 'Approval record · approved for project scope' : step===2 && revision ? 'Approval record · revision requested' : artifacts[step].file}</span><span>{showArtifact ? 'Hide −' : 'Inspect +'}</span></button><p>{['The selected references become context for the model.','The proposed work is a document you can review.','An explicit decision is required before implementation.','A visible file list makes the scope reviewable.','Each result says exactly what it does and does not establish.','The status document carries evidence into the next revision.'][step]}</p>{showArtifact&&<pre>{step===2 && approved ? artifacts[step].text.replace('Waiting for the user’s decision.', 'User approved the project plan. Other boundaries remain in effect.') : step===2 && revision ? artifacts[step].text.replace('Waiting for the user’s decision.', 'User requested a revision. Implementation remains paused.') : artifacts[step].text}</pre>}</div>
            {step===2&&<div className="pilot-approval"><strong>{revision ? 'Revision requested · still paused' : approved ? 'Plan approved · project scope only' : 'Your decision is needed'}</strong><p>Review the plan before allowing project generation. This does not approve a new helper or a framework edit.</p><div><button className="pilot-primary" onClick={()=>{setApproved(true);setRevision(false);}}>Approve this plan</button><button onClick={()=>{setApproved(false);setRevision(true);}}>Request a revision</button></div></div>}
            <div className="pilot-explanation"><small>WHY THIS MATTERS</small><h2>{concepts[step]}</h2><p>{why[step]}</p></div>
            <div className="pilot-controls"><button disabled={step===0} onClick={()=>go(step-1)}>← Back</button><span>{step+1} / 6</span>{step<5?<button className="pilot-primary" disabled={step===2&&!approved} onClick={()=>go(step+1)}>{step===2&&!approved?'Waiting for approval':`Next: ${phases[step+1]} →`}</button>:<button className="pilot-primary" onClick={()=>setMode('change')}>Change something →</button>}</div>
          </>}
        </section>
      </div>
    </>}

    {mode==='change'&&<section className="pilot-experiment"><span className="pilot-chip">Same task · different condition</span><h2>What changes the agent’s next move?</h2><p>Choose a condition. Compare the action, the control, and the visible outcome.</p><div className="pilot-choices">{[['complete','Requirements are complete'],['missing','A test limit is missing'],['helper','A new helper seems necessary']].map(([key,label])=><button aria-pressed={variant===key} onClick={()=>setVariant(key)}>{label}</button>)}</div><div className="pilot-outcomes"><div><small>AGENT PROPOSES</small><h3>{variant==='missing'?'Ask for the limit':variant==='helper'?'Request a new helper':'Prepare a plan'}</h3><p>{variant==='missing'?'“What limit should apply to this DUT? I will not copy the old project’s value.”':variant==='helper'?'“The existing functions may not cover this requirement. Here is the gap and the helper I propose.”':'“I have the necessary requirements. Here are the files and checks I propose.”'}</p></div><div><small>CONTROL IN EFFECT</small><h3>{variant==='missing'?'No invented requirements':variant==='helper'?'Separate human approval':'Plan approval'}</h3><p>{variant==='helper'?'Project write access does not authorize a new utility. A configured policy check should pause creation pending approval.':variant==='missing'?'Keep the unknown visible and pause affected work until the user supplies it.':'The user reviews the proposed scope before any implementation starts.'}</p></div><div className="pilot-result"><small>VISIBLE OUTCOME</small><h3>{blocked?'Paused for a decision':'Ready for plan review'}</h3><p>{variant==='helper'?'No helper created. The request and rationale are recorded.':variant==='missing'?'No guessed limit. The open question appears in the status record.':'A draft PROJECT_PLAN.md is available. No implementation files exist yet.'}</p></div></div><p className="pilot-note">These are predetermined teaching cases. The walkthrough does not inspect your framework or enforce real filesystem permissions.</p><button className="pilot-primary" onClick={()=>setMode('try')}>Try a decision →</button></section>}

    {mode==='try'&&<section className="pilot-experiment"><span className="pilot-chip">Your turn</span><h2>You approved the project plan. A helper is missing.</h2><p>The agent wants to add a new unit-conversion utility inside the project folder. What should happen next?</p><div className="pilot-answer-options">{[['write','Create it: the project plan was approved.'],['ask','Explain the gap and request separate approval.'],['framework','Add the helper to the shared framework instead.']].map(([key,label])=><button aria-pressed={answer===key} onClick={()=>setAnswer(key)}>{label}</button>)}</div>{answer&&<div className={'pilot-feedback '+(answer==='ask'?'correct':'')} role="status"><strong>{answer==='ask'?'Yes. Approval has a scope.':'That would cross the agreed boundary.'}</strong><p>{answer==='ask'?'The agent should first check existing framework tools, explain why they are insufficient, and wait for specific approval. A writable folder does not authorize every change.':'Plan approval does not authorize a new project-local tool or a shared framework edit. Both need their own explicit decision.'}</p><small>Concepts connected: context → tool reuse → guardrail → human approval → permission boundary.</small></div>}<button className="pilot-quiet" onClick={()=>{setMode('watch');restart();}}>Replay the example ↺</button></section>}
  </div>;
}
