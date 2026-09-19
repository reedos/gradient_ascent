import { useEffect, useState } from 'react';
import { url } from '../../lib/url';
import type { NameGroup, Status } from '../../lib/content';

/**
 * "Eight levels, and what is in each": the level tabs plus the two detail panels (the level's
 * techniques, and the products/tools/models that use them). Ported from the prototype's
 * renderTabs()/selectLevel(). Tabs are real links to /levels/<n>/ (or /levels/tracks/) so the
 * page works with JavaScript off; with JS on, a click is intercepted and swaps the panels in
 * place instead of navigating. LevelStack's slab clicks drive this via the "ga:selectLevel"
 * window event.
 */

export interface LevelPage {
  slug: string;
  title: string;
  summary: string;
  status: Status;
}

export interface LevelDetail {
  order: number;
  title: string;
  who: string;
  description: string;
  pages: LevelPage[];
  /** Already grouped and labelled on the server, so the island ships only rendered strings. */
  names: NameGroup[];
}

export interface TracksDetail {
  title: string;
  who: string;
  description: string;
  pages: LevelPage[];
  names: NameGroup[];
}

interface Props {
  levels: LevelDetail[];
  tracksDetail: TracksDetail;
  initialLevel?: number | 'tracks';
}

const STATUS_LABEL: Record<Status, string> = {
  published: 'Published',
  draft: 'Draft',
  stub: 'Outline',
  planned: 'Planned',
};
const pad = (n: number) => String(n).padStart(2, '0');

export default function LevelExplorer({ levels, tracksDetail, initialLevel = 1 }: Props) {
  const [level, setLevel] = useState<number | 'tracks'>(initialLevel);

  useEffect(() => {
    function onSelect(e: Event) {
      const detail = (e as CustomEvent<{ level: number }>).detail;
      if (detail && typeof detail.level === 'number') setLevel(detail.level);
    }
    window.addEventListener('ga:selectLevel', onSelect);
    return () => window.removeEventListener('ga:selectLevel', onSelect);
  }, []);

  const current = level === 'tracks' ? tracksDetail : levels.find((l) => l.order === level);
  const pages = current?.pages ?? [];
  const title = current?.title ?? '';
  const who = current?.who ?? '';
  const description = current?.description ?? '';
  const groups = current?.names ?? [];
  const color = level === 'tracks' ? 'var(--ot)' : `var(--o${level})`;
  const eyebrowLabel = level === 'tracks' ? 'Every level' : `Level ${pad(level)}`;

  function go(next: number | 'tracks', e: React.MouseEvent<HTMLAnchorElement>) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    setLevel(next);
  }

  return (
    <>
      <div className="layer-nav" role="group" aria-label="Level">
        {levels.map((l) => (
          <a
            key={l.order}
            href={url(`/levels/${l.order}/`)}
            aria-current={level === l.order ? 'true' : undefined}
            style={{ '--c': `var(--o${l.order})` } as React.CSSProperties}
            onClick={(e) => go(l.order, e)}
          >
            <small>{pad(l.order)}</small>
            {l.title}
          </a>
        ))}
        <a
          href={url('/levels/tracks/')}
          aria-current={level === 'tracks' ? 'true' : undefined}
          style={{ '--c': 'var(--ot)' } as React.CSSProperties}
          onClick={(e) => go('tracks', e)}
        >
          <small>ALL</small>
          Every level
        </a>
      </div>
      <div className="detail-layout">
        <div className="panel level-head">
          <div className="eyebrow" style={{ '--c': color, color } as React.CSSProperties}>
            <span className="dot" />
            {eyebrowLabel}
          </div>
          <h3>{title}</h3>
          <p>{description}</p>
          <div className="connection" style={{ '--c': color } as React.CSSProperties}>
            <strong>Who decides the next step</strong>
            {who}
          </div>
          <div className="subhead">
            {level === 'tracks' ? 'Topics' : 'Techniques'}
            <span>{pages.length}</span>
          </div>
          {pages.map((p) => (
            <div className="pattern-row" key={p.slug}>
              <h4>
                <i className="row-dot" style={{ '--c': color } as React.CSSProperties} />
                <a href={url(`/techniques/${p.slug}/`)}>{p.title}</a>
              </h4>
              <span className={`pill ${p.status}`}>{STATUS_LABEL[p.status]}</span>
              <p>{p.summary}</p>
            </div>
          ))}
        </div>
        <div className="panel">
          {groups.length ? (
            groups.map((g) => (
              <div className="name-group" key={g.label}>
                <div className="subhead">
                  {g.label}
                  <span>{g.entries.length}</span>
                </div>
                <ul className="name-list">
                  {g.entries.map((n) => (
                    <li key={n.name}>
                      <b>{n.name}</b>
                      <span>
                        {n.maker} &middot; {n.category}
                        {n.formerly ? ` · formerly ${n.formerly}` : ''}
                      </span>
                      {n.retirement ? <span className="pill gone">{n.retirement}</span> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ))
          ) : (
            <p className="footnote">No names listed for this level yet.</p>
          )}
        </div>
      </div>
    </>
  );
}
