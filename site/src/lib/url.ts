/**
 * Every internal link and asset URL goes through this helper so the GitHub Pages base path
 * (`/gradient_ascent/`) is prefixed exactly once, in dev and in the built site alike.
 *
 * Pass a site-relative path starting with "/" (e.g. "/levels/2/" or "/favicon.svg").
 */
export function url(path: string): string {
  const base = import.meta.env.BASE_URL; // e.g. "/gradient_ascent/"
  const b = base.endsWith('/') ? base.slice(0, -1) : base;
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${b}${p}`;
}
