import { useEffect, useLayoutEffect, useState } from 'preact/hooks';
import type { LearningStage } from '../../lib/learning';
import { downloadFiles } from '../../lib/download';

export default function LearningProject({ stage, index }: { stage: LearningStage; index: number }) {
  const key = `ga:project:v1:${index}`;
  const [answers, setAnswers] = useState<string[]>(stage.deliverables.map(() => ''));
  const [ready, setReady] = useState(false);
  const [checked, setChecked] = useState(false);
  const [status, setStatus] = useState('Loading project…');
  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw) {
        const saved = JSON.parse(raw);
        if (!Array.isArray(saved) || saved.length !== stage.deliverables.length || saved.some(x => typeof x !== 'string' || x.length > 30000)) throw new Error();
        setAnswers(saved);
      }
      setStatus('Saved in this browser. Download a copy before moving to another device.');
    } catch { setStatus('Browser storage is unavailable or unreadable. Download your project before leaving.'); }
    setReady(true);
  }, [key]);
  useLayoutEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(key, JSON.stringify(answers)); }
    catch { setStatus('Could not save in this browser. Download your project before leaving.'); }
  }, [answers, key, ready]);
  return <section class="stage-project learning-lab" id="stage-project" aria-labelledby="project-title">
    <div class="eyebrow">Stage {index + 1} project · Build it here</div>
    <h2 id="project-title">{stage.project}</h2>
    <p>Write your project in your own words below. You can use a table or arrows to explain a workflow. Use invented or public data. Nothing is sent or executed.</p>
    {stage.deliverables.map((task, i) => <div class="project-deliverable">
      <label for={`deliverable-${i}`}>{i + 1}. {task}</label>
      <textarea id={`deliverable-${i}`} disabled={!ready} maxLength={30000} value={answers[i]} placeholder="Build this part of your project here…"
        onInput={e => { setAnswers(answers.map((a, n) => n === i ? e.currentTarget.value : a)); setChecked(false); }} />
    </div>)}
    <p><strong>Review your work:</strong> {stage.ready}</p>
    <p class="lab-help">The completeness check only checks for nonempty files. Review their meaning yourself against the criterion above; there is no model grading.</p>
    <div class="lab-actions">
      <button type="button" disabled={!ready} onClick={() => setChecked(true)}>Check completeness</button>
      <button type="button" disabled={!ready} onClick={() => downloadFiles(`stage-${index + 1}-project.zip`, Object.fromEntries([
        ['README.md', `# ${stage.project}\n\n${stage.summary}\n\nReview criterion: ${stage.ready}\n\nLearner-authored work. No model grading or external execution.\n`],
        ...stage.deliverables.map((task, i) => [`part-${i + 1}.md`, `# ${task}\n\n${answers[i]}\n`]),
      ]))}>Download project (.zip)</button>
    </div>
    <div aria-live="polite">{checked && <p>{answers.filter(a => a.trim()).length} of {answers.length} parts contain text. {answers.every(a => a.trim()) ? 'All parts are present; review their accuracy and reasoning before marking this lesson complete.' : 'Fill in the remaining parts, then review your reasoning.'}</p>}</div>
    <p class="lab-help">{status}</p>
  </section>;
}
