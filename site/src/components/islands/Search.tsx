import { useEffect, useMemo, useRef, useState } from 'react';
import { url } from '../../lib/url';
import {
  search,
  groupResults,
  NAME_SECONDARY_LINK,
  type SearchDoc,
  type ScoredDoc,
  type ResultGroup,
} from '../../lib/search';

/**
 * The interactive half of /search/: one input, results grouped by kind. Reads and writes `?q=`
 * so a search is linkable and the back button works; the index itself is fetched once from
 * /search-index.json (search-index.json.ts), built at compile time from the same data every
 * other page renders from. Sits inside search.astro's ".search-js-only" wrapper, which CSS hides
 * until an inline script confirms JavaScript actually runs -- see search.astro and search.css
 * for the same progressive-enhancement pattern worksheet.astro/Worksheet.tsx use.
 */

function levelColor(level: SearchDoc['level']): string | undefined {
  if (level === undefined) return undefined;
  return level === 'tracks' ? 'var(--ot)' : `var(--o${level})`;
}

function readQuery(): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get('q') ?? '';
}

export default function Search() {
  const [query, setQuery] = useState('');
  const [docs, setDocs] = useState<SearchDoc[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setQuery(readQuery());
    inputRef.current?.focus();
    fetch(url('/search-index.json'))
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<SearchDoc[]>;
      })
      .then((data) => setDocs(data))
      .catch(() => setLoadError(true));
    const onPop = () => setQuery(readQuery());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  // Keep the URL in sync with what is typed, with replaceState (not pushState): every distinct
  // search is reachable by URL and shareable, but the back button steps out of the search
  // entirely instead of through every keystroke.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (query) params.set('q', query);
    else params.delete('q');
    const qs = params.toString();
    const next = window.location.pathname + (qs ? `?${qs}` : '');
    window.history.replaceState(null, '', next);
  }, [query]);

  const trimmed = query.trim();
  const results = useMemo(() => (docs && trimmed ? search(docs, query) : []), [docs, query, trimmed]);
  const groups: ResultGroup[] = useMemo(() => groupResults(results), [results]);

  function focusFirstResult() {
    document.querySelector<HTMLAnchorElement>('.search-result-link')?.focus();
  }

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown' && groups.length > 0) {
      e.preventDefault();
      focusFirstResult();
    }
  }

  function onResultKeyDown(e: React.KeyboardEvent<HTMLAnchorElement>) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const links = Array.from(document.querySelectorAll<HTMLAnchorElement>('.search-result-link'));
    const i = links.indexOf(e.currentTarget);
    e.preventDefault();
    if (e.key === 'ArrowDown') {
      (links[i + 1] ?? links[i])?.focus();
    } else if (i === 0) {
      inputRef.current?.focus();
    } else {
      links[i - 1]?.focus();
    }
  }

  return (
    <div className="search-page">
      <div className="search-input-row">
        <input
          ref={inputRef}
          id="search-input"
          type="search"
          className="search-input"
          placeholder="Search techniques, recipes, terms, names…"
          value={query}
          onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
          onKeyDown={onInputKeyDown}
          aria-label="Search the site"
          autoComplete="off"
        />
        {docs && <span className="search-count">{docs.length} entries indexed</span>}
      </div>

      {/* Results appear and change as the query is typed, with nothing on screen that says how
          many there are. This says it to assistive technology only (WCAG 2.1 4.1.3): it is in
          the page from the start so the first change is announced, and it is empty until there
          is something to announce. */}
      <p className="sr-only" role="status">
        {trimmed === '' || !docs ? '' : `${results.length} result${results.length === 1 ? '' : 's'} for ${trimmed}`}
      </p>

      {loadError && (
        <p className="search-status">The search index could not be loaded. Reload the page to try again.</p>
      )}

      {!loadError && trimmed === '' && (
        <div className="search-empty">
          <p>
            Type a word to search every technique, recipe, teardown, thread, level, glossary term,
            name and failure mode on the site. Not sure where to start? The{' '}
            <a href={url('/worksheet/')}>worksheet</a> finds the right level for a task in a few
            questions, and the <a href={url('/glossary/')}>glossary</a> defines every term the
            site uses.
          </p>
        </div>
      )}

      {!loadError && trimmed !== '' && docs && groups.length === 0 && (
        <div className="search-empty">
          <p>
            No results for &ldquo;{trimmed}&rdquo;. Try a different word, or browse the{' '}
            <a href={url('/glossary/')}>glossary</a> or the <a href={url('/worksheet/')}>worksheet</a>{' '}
            instead.
          </p>
        </div>
      )}

      {groups.map((g) => (
        <section className="search-group" key={g.kind}>
          <div className="subhead">
            {g.label}
            <span>{g.items.length}</span>
          </div>
          <div className="search-results">
            {g.items.map((item) => (
              <SearchResultRow key={item.id} item={item} onKeyDown={onResultKeyDown} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function SearchResultRow({
  item,
  onKeyDown,
}: {
  item: ScoredDoc;
  onKeyDown: (e: React.KeyboardEvent<HTMLAnchorElement>) => void;
}) {
  const color = levelColor(item.level);
  return (
    <div className="search-result">
      <a className="search-result-link" href={item.url} onKeyDown={onKeyDown}>
        {color && <i className="row-dot" style={{ '--c': color } as React.CSSProperties} />}
        {item.title}
      </a>
      {item.meta && <span className="search-result-meta">{item.meta}</span>}
      {item.summary && <p className="search-result-summary">{item.summary}</p>}
      {item.kind === 'name' && (
        <a className="search-result-secondary" href={url(NAME_SECONDARY_LINK.path)}>
          {NAME_SECONDARY_LINK.label} &rarr;
        </a>
      )}
    </div>
  );
}
