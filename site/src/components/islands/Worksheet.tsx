import { useEffect, useRef, useState } from 'react';
import { url } from '../../lib/url';
// worksheet-core, NOT worksheet: this module runs in the browser, and lib/worksheet.ts imports
// the taxonomy and the registry. Importing the evaluators from there put 86 KB of site data --
// including the taxonomy's internal author notes -- into this island's bundle.
import {
  evaluateCore,
  evaluateCross,
  currentStep,
  maxQuestions,
} from '../../lib/worksheet-core';
import type {
  AnswerPair,
  ResolvedWorksheetData,
  LevelInfo,
  WorksheetResult,
} from '../../lib/worksheet-core';

/**
 * The worksheet: one question at a time, then a result view. Ported to the site's own shapes --
 * the `.filter` segmented button for an answer, `.panel`/`.connection`/`.pill` for the result --
 * the same way LevelExplorer re-renders a pattern-row and a name-list inline instead of importing
 * the .astro components (an island cannot import an Astro component). State lives entirely in
 * the URL hash: `rule=no&one-call=no&...`, one key per question answered, in order. That makes a
 * result shareable by URL and makes the browser's own Back button work -- each answer sets
 * `location.hash`, which pushes a new history entry the normal way.
 *
 * `data` and `levelInfo` are fully resolved server-side (site/src/lib/worksheet.ts,
 * worksheet.astro): no taxonomy or registry import ships to the client, only the plain strings
 * this component renders.
 */

interface Props {
  data: ResolvedWorksheetData;
  levelInfo: LevelInfo[];
}

const STATUS_LABEL: Record<string, string> = {
  measured: 'Measured',
  sourced: 'Sourced',
  stub: 'Outline',
  planned: 'Planned',
};

// The taxonomy titles of the five cross-cutting slugs worksheet.json's cautions ever link to
// (human-in-the-loop, safety, evals, ops, reviewing). Kept here, not fetched from content.ts, so
// the island never has to import the taxonomy just to label five known links.
const RELATED_TITLES: Record<string, string> = {
  'human-in-the-loop': 'Human approval',
  safety: 'Safety, privacy and governance',
  evals: 'Evals',
  ops: 'Operations',
  reviewing: 'Reviewing work you did not do',
};

// Kept identical to worksheet.astro's static fallback, which prints it under every cross
// question; the two renderings of the same question must say the same thing.
const CROSS_HELP =
  'Does not change the level. Answered after the level is settled, and only changes the cautions shown with the result.';

const pad = (n: number) => String(n).padStart(2, '0');

function parseHash(): AnswerPair[] {
  if (typeof window === 'undefined') return [];
  const h = window.location.hash.replace(/^#/, '');
  if (!h) return [];
  return [...new URLSearchParams(h).entries()] as AnswerPair[];
}

function buildHash(answered: AnswerPair[]): string {
  const params = new URLSearchParams();
  for (const [q, a] of answered) params.append(q, a);
  return params.toString();
}

/**
 * Re-walks the tree checking `raw` against `data`, keeping only the leading run that is a real,
 * in-order path: core questions from the root until one settles, then cross questions in their
 * fixed order. A hand-edited or stale hash degrades to whatever leading prefix still makes sense
 * rather than throwing.
 */
function sanitize(data: ResolvedWorksheetData, raw: AnswerPair[]): AnswerPair[] {
  const out: AnswerPair[] = [];
  let i = 0;
  const byId = new Map(data.core_questions.map((q) => [q.id, q]));
  let qid: string | undefined = data.first_question;
  let settled = false;
  while (qid && i < raw.length) {
    const [rq, ra] = raw[i];
    if (rq !== qid) break;
    const q = byId.get(qid);
    const a = q?.answers.find((x) => x.id === ra);
    if (!q || !a) break;
    out.push([rq, ra]);
    i++;
    if (a.action === 'settle') {
      settled = true;
      qid = undefined;
    } else {
      qid = a.next;
    }
  }
  if (!settled) return out;
  for (const cq of data.cross_questions) {
    if (i >= raw.length) break;
    const [rq, ra] = raw[i];
    if (rq !== cq.id || !cq.answers.find((x) => x.id === ra)) break;
    out.push([rq, ra]);
    i++;
  }
  return out;
}

export default function Worksheet({ data, levelInfo }: Props) {
  const [answered, setAnswered] = useState<AnswerPair[]>([]);
  // Answering replaces the question, so the button that was focused is removed from the page and
  // focus falls back to <body>: a keyboard user loses their place and a screen reader never hears
  // the next question. After an answer, focus moves to the heading that replaced it.
  const advanced = useRef(false);

  useEffect(() => {
    if (!advanced.current) return;
    advanced.current = false;
    document.querySelector<HTMLElement>('.ws-card [data-ws-focus]')?.focus();
  });

  useEffect(() => {
    function sync() {
      setAnswered(sanitize(data, parseHash()));
    }
    sync();
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const coreIds = new Set(data.core_questions.map((q) => q.id));
  const coreAnswers = answered.filter(([q]) => coreIds.has(q));
  const crossAnswers = answered.filter(([q]) => !coreIds.has(q));
  const step = currentStep(data, coreAnswers, crossAnswers);
  const total = maxQuestions(data);
  const askedSoFar = answered.length;

  function choose(qid: string, aid: string) {
    advanced.current = true;
    const next: AnswerPair[] = [...answered, [qid, aid]];
    if (typeof window !== 'undefined') window.location.hash = buildHash(next);
    setAnswered(next);
  }

  function back() {
    if (typeof window !== 'undefined') window.history.back();
  }

  function startOver() {
    if (typeof window !== 'undefined') window.location.hash = '';
    setAnswered([]);
  }

  if (step.phase === 'result') {
    const result = { ...evaluateCore(data, coreAnswers), cautions: evaluateCross(data, crossAnswers) };
    const info = levelInfo[result.level];
    return (
      <div className="ws-card">
        <ResultView result={result} info={info} onBack={back} onStartOver={startOver} />
      </div>
    );
  }

  const question = step.question;

  return (
    <div className="ws-card">
      <div className="ws-progress">
        <span>
          Question {askedSoFar + 1} of up to {total}
        </span>
        {/* The line above already says "Question 3 of up to 11"; the bar is the same fact drawn,
            so it is hidden from assistive technology rather than announced twice. */}
        <span className="ws-progress-bar" aria-hidden="true">
          <span
            className="ws-progress-fill"
            style={{ width: `${Math.min(100, (askedSoFar / total) * 100)}%` }}
          />
        </span>
      </div>
      <div className="panel ws-question">
        <h3 data-ws-focus tabIndex={-1}>{question.prompt}</h3>
        {step.phase === 'core' ? (
          step.question.help && <p className="ws-help">{step.question.help}</p>
        ) : (
          // The same line the no-JS fallback prints under every cross-cutting question
          // (worksheet.astro). Without it, a reader answering one of these four in the
          // interactive flow has no way to know it will not move the level.
          <p className="ws-help">{CROSS_HELP}</p>
        )}
        <div className="ws-answers" role="group" aria-label={question.prompt}>
          {question.answers.map((a) => (
            <button key={a.id} type="button" className="filter ws-answer" onClick={() => choose(question.id, a.id)}>
              {a.label}
            </button>
          ))}
        </div>
        <div className="ws-controls">
          <button type="button" onClick={back} disabled={askedSoFar === 0}>
            &larr; Back
          </button>
          <button type="button" onClick={startOver} disabled={askedSoFar === 0}>
            Start over
          </button>
        </div>
      </div>
    </div>
  );
}

function ResultView({
  result,
  info,
  onBack,
  onStartOver,
}: {
  result: WorksheetResult;
  info: LevelInfo;
  onBack: () => void;
  onStartOver: () => void;
}) {
  const color = info.color;
  return (
    <div>
      <div className="ws-result-hero" style={{ '--c': color } as React.CSSProperties}>
        <div className="eyebrow" style={{ '--c': color, color } as React.CSSProperties}>
          <span className="dot" />
          Level {pad(info.order)}
        </div>
        <h2 data-ws-focus tabIndex={-1}>{info.title}</h2>
        <p>{info.description}</p>
        <p>This is a candidate classification, not a ranking of solutions. Check that the complete design delivers your desired automation, output quality, and acceptable hands-on effort. Compare alternatives before choosing.</p>
        <div className="connection" style={{ '--c': color } as React.CSSProperties}>
          <strong>Who decides the next step</strong>
          {info.who}
        </div>
      </div>

      <div className="ws-controls" style={{ borderTop: 0, marginTop: 18, paddingTop: 0 }}>
        <button type="button" onClick={onBack}>
          &larr; Change an answer
        </button>
        <button type="button" onClick={onStartOver}>
          Start over
        </button>
      </div>

      <div className="subhead" style={{ marginTop: 32 }}>
        Why
        <span>{result.reasons.length} answers</span>
      </div>
      <ol className="ws-reasons">
        {result.reasons.map((r) => (
          <li key={r.questionId}>
            <b>{r.answerLabel}</b>
            {r.text}
          </li>
        ))}
      </ol>

      {info.next && (
        <div className="ws-next-up" style={{ marginTop: 22 }}>
          <strong>
            Why not level {pad(info.next.order)}, {info.next.title}?
          </strong>
          {info.next.description} It would take more to build, more to test and more ways to
          fail quietly: worth it only once level {pad(info.order)} has actually fallen short,
          not because it might. A proposal that skips several levels has to clear that same test
          at every level in between.
        </div>
      )}

      <div className="subhead" style={{ marginTop: 32 }}>
        Cautions
        <span>{result.cautions.length}</span>
      </div>
      {result.cautions.length > 0 ? (
        <div className="ws-caution-list">
          {result.cautions.map((c) => (
            <div className="ws-caution" key={c.questionId}>
              <strong>{c.questionPrompt}</strong>
              {c.text}
              {c.relatesTo.length > 0 && (
                <div className="ws-caution-links">
                  {c.relatesTo.map((slug) => (
                    <a key={slug} href={url(`/techniques/${slug}/`)}>
                      {RELATED_TITLES[slug] ?? slug}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="ws-no-cautions">
          Nothing flagged: a wrong answer here is cheap, easy to check, easy to undo, and nothing
          leaves your machine.
        </p>
      )}

      <div className="subhead" style={{ marginTop: 32 }}>
        Techniques at this level
        <span>{info.techniques.length}</span>
      </div>
      <div className="panel reading">
        {info.techniques.map((t) => (
          <div className="pattern-row" key={t.slug}>
            <h3>
              <i className="row-dot" style={{ '--c': color } as React.CSSProperties} />
              <a href={url(`/techniques/${t.slug}/`)}>{t.title}</a>
            </h3>
            <span className={`pill ${t.status}`}>{STATUS_LABEL[t.status]}</span>
            <p>{t.summary}</p>
          </div>
        ))}
      </div>

      {info.recipes.length > 0 && (
        <>
          <div className="subhead" style={{ marginTop: 32 }}>
            Recipes that top out here
            <span>{info.recipes.length}</span>
          </div>
          <div className="signal-list">
            {info.recipes.map((r) => (
              <div className="signal-row" key={r.slug}>
                <div className="signal-layer">
                  {r.levels.map((l) => (
                    <i key={l} style={{ '--c': `var(--o${l})` } as React.CSSProperties} />
                  ))}
                  <span>{r.levels.map((l) => `Level ${l}`).join(' + ')}</span>
                </div>
                <div className="signal-body">
                  <h3>
                    <a href={url(`/recipes/${r.slug}/`)}>{r.title}</a>
                  </h3>
                  <p>{r.summary}</p>
                </div>
                <div className="signal-meta">Needs level {Math.max(...r.levels)}</div>
                <a href={url(`/recipes/${r.slug}/`)} aria-label={`Open ${r.title}`}>
                  &#8599;
                </a>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="ws-result-links">
        <a href={url(`/levels/${info.order}/`)}>See the full level {pad(info.order)} page &rarr;</a>
        <a href={url('/#climb')}>See it on the curve &rarr;</a>
      </div>
    </div>
  );
}
