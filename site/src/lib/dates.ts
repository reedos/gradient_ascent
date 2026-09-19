// How the site prints a date it stores as ISO. House style is American: month first.
//   "2026-09-18" -> "09/18/2026"   "2026-09" -> "09/2026"   "2026" -> "2026"
// Anything that is not an ISO date comes back unchanged, so a field that already holds prose
// ("September 2026") is left alone. Data files keep ISO; only what a reader sees changes.
export function usDate(iso: string | undefined | null): string {
  if (!iso) return '';
  const m = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$/.exec(iso.trim());
  if (!m) return iso;
  const [, y, mo, d] = m;
  if (mo && d) return `${mo}/${d}/${y}`;
  if (mo) return `${mo}/${y}`;
  return y;
}
