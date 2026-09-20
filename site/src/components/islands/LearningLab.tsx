import { useEffect, useLayoutEffect, useState } from 'preact/hooks';
import { labSpecs, parseConfig, runLab, type LabResult } from '../../lib/learning-labs';
import { downloadFiles } from '../../lib/download';

export default function LearningLab({ lesson }: { lesson: string }) {
  const spec = labSpecs[lesson];
  const key = `ga:lab:v1:${lesson}`;
  const [config, setConfig] = useState(JSON.stringify(spec.starter, null, 2));
  const [prompt, setPrompt] = useState(spec.prompt);
  const [notes, setNotes] = useState('');
  const [file, setFile] = useState('config.json');
  const [result, setResult] = useState<LabResult | null>(null);
  const [outputFile, setOutputFile] = useState('simulated-output.json');
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [storage, setStorage] = useState('Loading workspace…');
  const [notice, setNotice] = useState('');
  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw) {
        const saved = JSON.parse(raw);
        if (!saved || !['config', 'prompt', 'notes'].every(k => typeof saved[k] === 'string' && saved[k].length <= 30000)) throw new Error();
        setConfig(saved.config); setPrompt(saved.prompt); setNotes(saved.notes);
      }
      setStorage('Saved in this browser. Download a copy to keep or move your work.');
    } catch { setStorage('Browser storage is unavailable or unreadable. Download your work before leaving.'); }
    setReady(true);
  }, [key]);
  useLayoutEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(key, JSON.stringify({ config, prompt, notes })); }
    catch { setStorage('Could not save in this browser. Download your work before leaving.'); }
  }, [config, prompt, notes, ready, key]);
  const edit = (value: string) => {
    if (file === 'config.json') setConfig(value);
    else if (file === 'prompt.md') setPrompt(value);
    else setNotes(value);
    setResult(null); setError(''); setNotice('Edited. Run again to generate current results.');
  };
  const run = () => {
    try {
      setResult(runLab(lesson, parseConfig(config), prompt, notes)); setError(''); setNotice('');
    } catch (e) { setResult(null); setError(`Could not run: ${e instanceof Error ? e.message : 'Check your JSON configuration.'}`); }
  };
  return <section class="learning-lab" aria-labelledby={`lab-${lesson}`}>
    <div class="eyebrow">Build it here · Deterministic simulation</div>
    <h2 id={`lab-${lesson}`}>Application configuration</h2>
    <p>{spec.brief}</p>
    <div class="lab-scenario"><strong>Scenario</strong><p>{spec.scenario}</p></div>
    <p class="lab-help">1. Edit the configuration. 2. Run the simulation. 3. Use the checks to revise it. The starter intentionally has problems; the working example shows one solution.</p>
    <p class="lab-help">JSON uses quoted field names, square brackets for lists, and unquoted numbers, true, false, or null. Edit values after the colon. The prompt and notes are your own files; prompt wording is exported but is not interpreted by this simulator.</p>
    <label for={`file-${lesson}`}>File to edit</label>
    <select id={`file-${lesson}`} value={file} onChange={e => setFile(e.currentTarget.value)}>
      <option>config.json</option><option>prompt.md</option><option>notes.md</option>
    </select>
    <label for={`editor-${lesson}`} class="lab-file-label">{file}</label>
    <textarea id={`editor-${lesson}`} class="lab-editor" spellcheck={false} maxLength={30000} disabled={!ready}
      value={file === 'config.json' ? config : file === 'prompt.md' ? prompt : notes} onInput={e => edit(e.currentTarget.value)} />
    <div class="lab-actions">
      <button type="button" disabled={!ready} onClick={run}>Run simulation</button>
      <button type="button" disabled={!ready} onClick={() => { setConfig(JSON.stringify(spec.solution, null, 2)); setFile('config.json'); setResult(null); setError(''); setNotice('Working configuration loaded. Run it to inspect the result. Your prompt and notes are preserved.'); }}>Load working example</button>
      <button type="button" disabled={!ready} onClick={() => { setConfig(JSON.stringify(spec.starter, null, 2)); setFile('config.json'); setResult(null); setError(''); setNotice('Starter configuration restored. Your prompt and notes are preserved.'); }}>Restore starter</button>
    </div>
    <p class="lab-help">{storage} Use invented or public data.</p>
    <p class="lab-help">No model or external tool is called. These checks cover this scenario only; passing them does not certify a real system.</p>
    {error && <p role="alert" class="lab-error">{error}</p>}
    <div aria-live="polite" aria-atomic="true">{notice && <p>{notice}</p>}{result && <p class="lab-summary">{result.checks.filter(c => c.passed).length} of {result.checks.length} checks passed.</p>}</div>
    {result && <div class="lab-results">
      <ul class="lab-checks">{result.checks.map(c => <li class={c.passed ? 'check-pass' : 'check-fail'}><strong>{c.passed ? 'Pass' : 'Revise'} · {c.label}</strong><p>{c.explanation}</p></li>)}</ul>
      <label for={`output-${lesson}`}>Generated file to inspect</label>
      <select id={`output-${lesson}`} value={outputFile} onChange={e => setOutputFile(e.currentTarget.value)}>{Object.keys(result.files).map(name => <option>{name}</option>)}</select>
      <pre class="lab-output" tabIndex={0} aria-label={outputFile}>{result.files[outputFile]}</pre>
      <button type="button" onClick={() => downloadFiles(`${lesson}.zip`, result.files)}>Download workspace (.zip)</button>
    </div>}
    {!result && <button type="button" disabled={!ready} onClick={() => downloadFiles(`${lesson}-draft.zip`, { 'config.json': config, 'prompt.md': prompt, 'notes.md': notes, 'scenario.txt': spec.scenario })}>Download draft files (.zip)</button>}
  </section>;
}
