import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import { conversations, initialConversation, restoreConversation, conversationFiles, type ConversationDraft } from '../../lib/learning-conversations';
import { labSpecs } from '../../lib/learning-labs';
import { downloadFiles } from '../../lib/download';

export default function ConversationPractice({ lesson }: { lesson: string }) {
  const spec = conversations[lesson];
  const key = `ga:conversation:v1:${lesson}`;
  const [draft, setDraft] = useState<ConversationDraft>(() => initialConversation(lesson));
  const [ready, setReady] = useState(false);
  const [storage, setStorage] = useState('Loading your practice…');
  const [typing, setTyping] = useState<null | { turn: number; text: string; shown: number }>(null);
  const [announcement, setAnnouncement] = useState('');
  const latestReply = useRef<HTMLDivElement>(null);
  const scrollNext = useRef(false);
  useEffect(() => {
    try { setDraft(restoreConversation(lesson, localStorage.getItem(key))); setStorage('Saved in this browser.'); }
    catch { setStorage('Could not restore browser storage. Download a copy before leaving.'); }
    setReady(true);
  }, [key, lesson]);
  useLayoutEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(key, JSON.stringify(draft)); }
    catch { setStorage('Could not save in this browser. Download a copy before leaving.'); }
  }, [draft, ready, key]);
  useLayoutEffect(() => {
    if (scrollNext.current && latestReply.current) {
      latestReply.current.scrollIntoView({ block: 'center', behavior: 'instant' });
      scrollNext.current = false;
    }
  }, [draft.sentOpening, draft.attempts.length]);
  useEffect(() => {
    if (!typing) return;
    if (typing.shown >= typing.text.length) {
      setAnnouncement(`Simulated reply complete. ${typing.text}`);
      setTyping(null);
      return;
    }
    const timer = window.setTimeout(() => setTyping(current => current ? { ...current, shown: Math.min(current.text.length, current.shown + 5) } : null), 25);
    return () => window.clearTimeout(timer);
  }, [typing]);
  const begun = draft.sentOpening !== null;
  const finished = draft.attempts.length > 0;
  const message = begun ? draft.followUp : draft.opening;
  const animate = (turn: number, text: string) => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setAnnouncement(`Simulated reply complete. ${text}`); return; }
    setAnnouncement('Simulated reply is appearing.');
    setTyping({ turn, text, shown: 0 });
  };
  const send = () => {
    if (!ready || typing || finished || !message.trim()) return;
    scrollNext.current = true;
    if (!begun) {
      setDraft({ ...draft, sentOpening: draft.opening, followUp: spec.choices[0].example });
      animate(0, spec.firstReply);
    } else {
      setDraft({ ...draft, attempts: [{ message: draft.followUp, branch: 0 }] });
      animate(1, spec.choices[0].reply);
    }
  };
  const reply = (text: string, turn: number) => <div ref={turn === (finished ? 1 : 0) ? latestReply : undefined} class="practice-message practice-assistant" aria-label="Simulated assistant reply" aria-busy={typing?.turn === turn}>
    <span class="practice-speaker">Practice assistant <small>· scripted reply</small></span>
    <p>{typing?.turn === turn ? typing.text.slice(0, typing.shown) : text}{typing?.turn === turn && <span class="typing-cursor" aria-hidden="true">▍</span>}</p>
  </div>;
  return <section class="learning-lab conversation-practice" aria-labelledby={`conversation-${lesson}`}>
    <div class="eyebrow">Try the conversation · Simulated chat</div>
    <h2 id={`conversation-${lesson}`}>Practice in plain English</h2>
    <p>{spec.task} Your message is ready below—press Send to begin.</p>
    <p class="lab-help">Replies are scripted, with a typing effect. No live model is called, and editing the message does not change the reply yet.</p>
    <details class="practice-material"><summary>View the practice material</summary><p>{labSpecs[lesson].scenario}</p></details>
    {begun && <div class="practice-transcript">
      <div class="practice-message practice-user"><span class="practice-speaker">You</span><p>{draft.sentOpening}</p></div>
      {reply(spec.firstReply, 0)}
      {(!typing || typing.turn !== 0) && <aside class="practice-coach"><strong>Notice this</strong><p>{spec.review}</p></aside>}
      {draft.attempts.map((a, i) => <div key={i}>
        <div class="practice-message practice-user"><span class="practice-speaker">You</span><p>{a.message}</p></div>
        {reply(spec.choices[a.branch].reply, 1)}
        {!typing && <aside class="practice-coach"><strong>What to take away</strong><p>{spec.choices[a.branch].feedback}</p></aside>}
      </div>)}
    </div>}
    <div class="sr-only" role="status" aria-live="polite">{announcement}</div>
    {typing && <button type="button" class="practice-skip" onClick={() => { setAnnouncement(`Simulated reply complete. ${typing.text}`); setTyping(null); }}>Show full reply now</button>}
    {!finished && <form class="practice-composer" onSubmit={e => { e.preventDefault(); send(); }}>
      <label for={`message-${lesson}`}>{begun ? 'Your follow-up' : 'Your message'}</label>
      <textarea id={`message-${lesson}`} disabled={!ready || !!typing} maxLength={10000} value={message}
        onInput={e => setDraft({ ...draft, [begun ? 'followUp' : 'opening']: e.currentTarget.value })}
        onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); send(); } }} />
      <div class="practice-send-row"><span>{begun ? 'A suggested follow-up is ready. You can edit it in your own words.' : 'Use the suggested message or edit it in your own words.'}</span><button type="submit" disabled={!ready || !!typing || !message.trim()}>Send <span aria-hidden="true">↑</span></button></div>
    </form>}
    {finished && !typing && <p class="practice-complete">You’ve reached the end of this example. Compare the first reply with the revision, then continue to the next lesson.</p>}
    <details class="practice-material"><summary>Your notes and downloads</summary>
      <label for={`practice-notes-${lesson}`}>What would you check or ask differently?</label>
      <textarea id={`practice-notes-${lesson}`} disabled={!ready} maxLength={10000} value={draft.notes} onInput={e => setDraft({ ...draft, notes: e.currentTarget.value })} />
      <div class="lab-actions"><button type="button" disabled={!ready || !!typing} onClick={() => downloadFiles(`${lesson}-conversation.zip`, conversationFiles(lesson, draft, labSpecs[lesson].scenario))}>Download conversation (.zip)</button>
      {begun && <button type="button" disabled={!!typing} onClick={() => { setDraft({ ...initialConversation(lesson), notes: draft.notes }); setAnnouncement('Example restarted. Your notes are preserved.'); }}>Replay example</button>}</div>
      <p class="lab-help">{storage} The written messages are not automatically graded.</p>
    </details>
  </section>;
}
