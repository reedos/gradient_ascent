// Typed access to content/timeline.json, the dated milestones behind /timeline/ and the home
// page's timeline strip. Deliberately self-contained: it imports ONLY content/timeline.json (with
// an explicit `type: json` attribute, required for this file to run standalone under plain Node
// -- see site/tests/timeline.test.ts, which runs via `node --test` with no bundler and no
// attribute-less JSON loader). It does not import lib/content.ts, so a milestone's `technique`
// and `registry_id` are resolved to a page/name by the Astro components that render this data
// (Timeline.astro, TimelineStrip.astro), which already run inside Astro's Vite pipeline where
// content.ts's own JSON imports work.
//
// NO date, id or count from content/timeline.json is hard-coded here: every function reads the
// file's actual shape at call time, including which of "described" / "buildable" / "available"
// (or some future key) a given level entry carries. `timeline-review` owns the data and may
// change it under this file at any time; re-import (a fresh build) picks up whatever is there.
import timelineData from '../../../content/timeline.json' with { type: 'json' };

export type Precision = 'day' | 'month' | 'year';
export type MilestoneKind = 'research' | 'model' | 'product' | 'tool' | 'standard';
export type MarkShape = 'circle' | 'square' | 'triangle';

export interface Source {
  title: string;
  url: string;
  publisher: string;
  /** The Internet Archive capture of `url` that was actually read, where the maker's own page
   *  will not open from here (several OpenAI hosts return 403). The capture is the maker's own
   *  page as it stood on that day, so a milestone verified this way is still verified against a
   *  primary source -- see docs/TIMELINE-METHOD.md. Always accompanied by `url`. */
  archive_url?: string;
}

/** How available a product was on the date its milestone marks: generally available, a preview,
 *  behind a waitlist, or included with a paid plan. Optional, and only meaningful for products. */
export type Availability = 'general' | 'preview' | 'waitlist' | 'paid plans';

export interface Milestone {
  /** A few words for tight places (the home strip's in-row label). Falls back to `title`. */
  short?: string;
  /** On a launch that was not open on its launch day (a waitlist, a preview, an unveiling): the
   *  day an ordinary customer could actually get in, in the maker's own dated words. */
  opened?: { date: string; precision: Precision; text: string; milestone?: string };
  id: string;
  date: string;
  precision: Precision;
  level: number;
  kind: MilestoneKind;
  title: string;
  maker: string;
  what: string;
  technique?: string;
  registry_id?: string;
  source: Source;
  checked: string;
  verified: boolean;
  availability?: Availability;
  note?: string;
}

/** One milestone the data considered for one of a level's marked dates, with the reason it was
 *  or was not chosen. A candidate may sit at another level -- that is often exactly why it was
 *  rejected -- so nothing here assumes `id` resolves within the same level. */
export interface LevelCandidate {
  mark: string;
  id: string;
  chosen?: boolean;
  why: string;
}

export interface Measure {
  id: string;
  quote: string;
  what_it_measures: string;
  scope: string;
  source: Source;
  date: string;
  checked: string;
}

export interface Criteria {
  described: string;
  available: string;
  [key: string]: string;
}

/**
 * One entry from timeline.json's `levels` array: a level number plus whichever marked-date keys
 * (described, buildable, available, ... ) the data defines for it, each either a milestone id or
 * null, plus an optional note explaining a missing key (level 0 has no maker to announce
 * "available" in the ordinary sense). Kept as a loose record -- not a fixed
 * `{described, available}` shape -- so an added, renamed or removed key needs no change here.
 */
export interface LevelMarkEntry {
  level: number;
  note?: string;
  candidates?: LevelCandidate[];
  [key: string]: string | number | null | undefined | LevelCandidate[];
}

/** A change in the models themselves that cuts across the levels (reasoning models, System One
 *  models). Not a level: who decides the next step does not change. Anchored to one milestone for
 *  its date and source. */
export interface Shift {
  id: string;
  title: string;
  milestone: string;
  /** Draw it as a vertical rule on the compact strip. */
  strip?: boolean;
  technique?: string;
  /** Other milestone ids the body draws on, linked under it. */
  also?: string[];
  summary: string;
  body: string[];
  /** What the thing is for, each tied to the technique page where that use lives. */
  applications_intro?: string;
  applications?: { title: string; text: string; technique?: string }[];
  limits?: string;
}

export interface TimelineData {
  shifts?: Shift[];
  version: number;
  as_of: string;
  criteria: Criteria;
  levels: LevelMarkEntry[];
  milestones: Milestone[];
  measures: Measure[];
}

export const timeline = timelineData as unknown as TimelineData;
export const milestones: Milestone[] = timeline.milestones;
export const measures: Measure[] = timeline.measures;
export const shifts: Shift[] = timeline.shifts ?? [];
export const criteria: Criteria = timeline.criteria;
export const asOf: string = timeline.as_of;

const milestoneById = new Map<string, Milestone>(milestones.map((m) => [m.id, m]));

export function milestone(id: string): Milestone | undefined {
  return milestoneById.get(id);
}

// -- Marked-date keys: order and labels, data-driven --------------------------------------------

/**
 * The order a level's marked dates render in, when more than one is present. Any key not listed
 * here (a future addition beyond these three) sorts after them, alphabetically -- the page still
 * renders it, just without a hand-tuned position or label.
 */
const MARK_KEY_ORDER = ['described', 'buildable', 'available'];
const MARK_KEY_LABEL: Record<string, string> = {
  described: 'Described',
  buildable: 'Buildable',
  available: 'Reached the public',
};
// Keys on a `levels[]` entry that are not marked dates. `candidates` is the audit trail behind
// the marks (what else was considered, and why it was not chosen), not a mark of its own.
const RESERVED_LEVEL_KEYS = new Set(['level', 'note', 'candidates']);

export function markLabel(key: string): string {
  return MARK_KEY_LABEL[key] ?? key.charAt(0).toUpperCase() + key.slice(1);
}

/**
 * The marked-date keys actually present on one `levels[]` entry (non-null values only), in
 * MARK_KEY_ORDER order first, then any extra key alphabetically. Handles a missing key (an entry
 * with only `available`) and an extra one (a third key beyond described/buildable/available)
 * alike: it reads whatever is there.
 */
function byMarkKeyOrder(a: string, b: string): number {
  const ia = MARK_KEY_ORDER.indexOf(a);
  const ib = MARK_KEY_ORDER.indexOf(b);
  if (ia !== -1 && ib !== -1) return ia - ib;
  if (ia !== -1) return -1;
  if (ib !== -1) return 1;
  return a.localeCompare(b);
}

export function markKeys(entry: LevelMarkEntry): string[] {
  const keys = Object.keys(entry).filter((k) => !RESERVED_LEVEL_KEYS.has(k) && entry[k] != null);
  return keys.sort(byMarkKeyOrder);
}

/** Every distinct marked-date key actually used across a set of levels (default: the real data),
 *  in the same described/buildable/available-first order as `markKeys`. Lets a page describe
 *  "the marked dates" without assuming there are exactly two of them. */
export function usedMarkKeys(series: LevelSeries[] = levelSeries()): string[] {
  const keys = new Set<string>();
  for (const s of series) for (const m of s.marks) keys.add(m.key);
  return [...keys].sort(byMarkKeyOrder);
}

// -- Dates: parsing by precision, and formatting at exactly that precision ----------------------

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const CUMULATIVE_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

/**
 * A date at its stated precision, placed on a continuous year axis: a year-precision date sits at
 * the middle of its year, a month-precision date at the middle of its month, and a day-precision
 * date at its exact calendar day (as a fraction of its year). This is placement geometry ONLY --
 * see `formatDate` for what a reader actually sees, which never shows more precision than the
 * data records.
 */
export function decimalYear(date: string, precision: Precision): number {
  const [yStr, mStr, dStr] = date.split('-');
  const year = Number(yStr);
  if (precision === 'year') return year + 0.5;
  const month = Number(mStr);
  if (precision === 'month') return year + (month - 1 + 0.5) / 12;
  const day = Number(dStr);
  const leapAdjust = isLeapYear(year) && month > 2 ? 1 : 0;
  const dayOfYear = CUMULATIVE_DAYS[month - 1] + leapAdjust + day; // 1-based
  const daysInYear = isLeapYear(year) ? 366 : 365;
  return year + (dayOfYear - 0.5) / daysInYear;
}

/**
 * How a date prints, at exactly the precision it was recorded at: "2023" for year precision,
 * "Feb 2023" for month precision, "Feb 7, 2023" for day precision. Never invents a day or a month
 * that is not in the data.
 */
export function formatDate(date: string, precision: Precision): string {
  const [yStr, mStr, dStr] = date.split('-');
  if (precision === 'year') return yStr;
  const month = MONTH_NAMES[Number(mStr) - 1];
  if (precision === 'month') return `${month} ${yStr}`;
  return `${month} ${Number(dStr)}, ${yStr}`;
}

/**
 * The calendar gap, in whole months, between two dated points -- the site's OWN arithmetic over
 * the milestone dates, always (never a figure the data itself states). Positive when b is after
 * a. Every caller/renderer of this value must say it is the site's own arithmetic.
 */
export function monthsBetween(dateA: string, precA: Precision, dateB: string, precB: Precision): number {
  return Math.round((decimalYear(dateB, precB) - decimalYear(dateA, precA)) * 12);
}

export function yearOf(date: string): number {
  return Number(date.slice(0, 4));
}

// -- Per-level series: milestones, and resolved marked dates -------------------------------------

export interface ResolvedMark {
  key: string;
  label: string;
  milestone: Milestone;
}

/** A `candidates` entry with its milestone attached (undefined if the id resolves to nothing --
 *  scripts/validate.py separately refuses that) and the mark's display label. */
export interface ResolvedCandidate extends LevelCandidate {
  label: string;
  milestone?: Milestone;
}

export interface LevelSeries {
  level: number;
  entry: LevelMarkEntry;
  /** Every milestone at this level, oldest first. */
  milestones: Milestone[];
  /** The level's marked dates that resolved to a real milestone, in mark-key order. */
  marks: ResolvedMark[];
  /** Everything the data says it considered for those marks, in the order the data lists them. */
  candidates: ResolvedCandidate[];
  note?: string;
}

/** All levels named in timeline.json's `levels` array, sorted low to high, each with its
 *  milestones and resolved marks. Nothing here assumes there are eight of them. Takes the
 *  milestone list and level entries as optional parameters -- defaulting to the real data -- so
 *  the unit tests can exercise the placement logic against small synthetic fixtures instead of
 *  the real, evolving content/timeline.json. */
export function levelSeries(ms: Milestone[] = milestones, levelEntries: LevelMarkEntry[] = timeline.levels): LevelSeries[] {
  const byLevel = new Map<number, Milestone[]>();
  for (const m of ms) {
    if (!byLevel.has(m.level)) byLevel.set(m.level, []);
    byLevel.get(m.level)!.push(m);
  }
  for (const list of byLevel.values()) {
    list.sort((a, b) => decimalYear(a.date, a.precision) - decimalYear(b.date, b.precision));
  }
  const byId = new Map<string, Milestone>(ms.map((m) => [m.id, m]));

  return levelEntries
    .slice()
    .sort((a, b) => a.level - b.level)
    .map((entry) => {
      const levelMilestones = byLevel.get(entry.level) ?? [];
      const marks: ResolvedMark[] = markKeys(entry)
        .map((key): ResolvedMark | undefined => {
          const id = entry[key] as string;
          const found = byId.get(id);
          return found ? { key, label: markLabel(key), milestone: found } : undefined;
        })
        .filter((x): x is ResolvedMark => Boolean(x));
      const candidates: ResolvedCandidate[] = (entry.candidates ?? []).map((c) => ({
        ...c,
        label: markLabel(c.mark),
        milestone: byId.get(c.id),
      }));
      return { level: entry.level, entry, milestones: levelMilestones, marks, candidates, note: entry.note };
    });
}

/** `levelSeries()`, highest level first -- the order the wide chart's lanes render in (level 7 at
 *  the top). */
export function levelSeriesTopDown(): LevelSeries[] {
  return levelSeries().slice().sort((a, b) => b.level - a.level);
}

/** One mark's position on the continuous year axis -- used to sort a lane's marks by when they
 *  actually happened, since a mark's KEY order (described, then buildable, then available) is a
 *  presentation convention, not a promise about date order. The data is explicit that it is not:
 *  level 2's `buildable` (a library) predates its `described` (a paper), and level 4's `buildable`
 *  comes after its `available` -- the product shipped before an open framework for it existed. */
function markYear(mk: ResolvedMark): number {
  return decimalYear(mk.milestone.date, mk.milestone.precision);
}

/** The earliest and latest of a lane's resolved marks, BY ACTUAL DATE, not by key order --
 *  undefined if the lane has no resolved marks. When there is exactly one mark, earliest and
 *  latest are the same mark (a zero-width span). Every renderer that draws "from the first mark
 *  to the last" (the wide chart's connector, the compact strip's span) must use this rather than
 *  `marks[0]`/`marks[marks.length - 1]`, which are in key order. */
export function markExtent(marks: ResolvedMark[]): { earliest: ResolvedMark; latest: ResolvedMark } | undefined {
  if (marks.length === 0) return undefined;
  let earliest = marks[0];
  let latest = marks[0];
  for (const mk of marks) {
    if (markYear(mk) < markYear(earliest)) earliest = mk;
    if (markYear(mk) > markYear(latest)) latest = mk;
  }
  return { earliest, latest };
}

// -- "How fast": interval arithmetic, always labelled as the site's own -------------------------

export interface NamedInterval {
  /** Whole months between the two dates -- always non-negative; see `reversed`. */
  months: number;
  /** True when the second-named date actually comes BEFORE the first (e.g. a level's `buildable`
   *  framework arrived after its `available` product did). A renderer must say so in words --
   *  "the product came first" -- rather than print a negative number. */
  reversed: boolean;
}

export interface LevelIntervals {
  level: number;
  /** The level's resolved marks, in key order (described, buildable, available, ...), for
   *  rendering every marked date -- including which of the three canonical keys is missing. */
  marks: ResolvedMark[];
  /** The audit trail for this level's marks, carried through so the page can show why each
   *  marked date won and what it beat. */
  candidates: ResolvedCandidate[];
  describedToAvailable: NamedInterval | null;
  buildableToAvailable: NamedInterval | null;
  note?: string;
}

function namedInterval(from: ResolvedMark | undefined, to: ResolvedMark | undefined): NamedInterval | null {
  if (!from || !to) return null;
  const months = monthsBetween(from.milestone.date, from.milestone.precision, to.milestone.date, to.milestone.precision);
  return { months: Math.abs(months), reversed: months < 0 };
}

/**
 * Per level: the two named calendar gaps the page reports -- described to available, and (only
 * where both resolve) buildable to available -- each the site's own arithmetic over the dates in
 * `content/timeline.json`. Null when either side of a gap has no resolved mark (rendered as "no
 * single date", never silently omitted). Takes a precomputed series (default: the real data) so
 * tests can pass a synthetic one.
 */
export function levelIntervals(series: LevelSeries[] = levelSeries()): LevelIntervals[] {
  return series.map((s) => {
    const byKey = new Map(s.marks.map((m) => [m.key, m]));
    return {
      level: s.level,
      marks: s.marks,
      candidates: s.candidates,
      describedToAvailable: namedInterval(byKey.get('described'), byKey.get('available')),
      buildableToAvailable: namedInterval(byKey.get('buildable'), byKey.get('available')),
      note: s.note,
    };
  });
}

export interface ConsecutiveLevelGap {
  fromLevel: number;
  toLevel: number;
  /** Null when either level has no resolved `available` mark (level 0 today) -- the site does not
   *  substitute a different key to fill the gap, since "between consecutive levels' available
   *  dates" is specifically about the customer-facing arrival date. Never negative; see
   *  `reversed`. */
  interval: NamedInterval | null;
  fromAvailable?: ResolvedMark;
  toAvailable?: ResolvedMark;
}

/**
 * The gap, in months, between one level's `available` milestone and the next level's `available`
 * milestone specifically -- not "whichever mark sorts last", because `buildable` can fall on
 * either side of `available` (see markExtent's comment), which would make a generic "last mark"
 * comparison mix different kinds of date across level pairs. The gap can itself run backwards --
 * content/timeline.json has level 4 (Tools) generally available before level 3 (Workflows) is --
 * so `interval.reversed` says so rather than this returning a negative number. Takes a
 * precomputed series (default: the real data) so tests can pass a synthetic one.
 */
export function consecutiveLevelGaps(series: LevelSeries[] = levelSeries()): ConsecutiveLevelGap[] {
  const gaps: ConsecutiveLevelGap[] = [];
  for (let i = 0; i < series.length - 1; i++) {
    const a = series[i];
    const b = series[i + 1];
    const aMark = a.marks.find((m) => m.key === 'available');
    const bMark = b.marks.find((m) => m.key === 'available');
    gaps.push({ fromLevel: a.level, toLevel: b.level, interval: namedInterval(aMark, bMark), fromAvailable: aMark, toAvailable: bMark });
  }
  return gaps;
}

// -- The home strip's headline figure -------------------------------------------------------------

const NUMBER_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];

function numberWord(n: number): string {
  return NUMBER_WORDS[n] ?? String(n);
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export interface ClimbHeadline {
  /** How many levels this span covers: every level with a resolved `available` mark -- the
   *  customer-facing arrival date. A level with no such date (level 0 today: rules, search and
   *  forms predate any single maker's announcement) cannot contribute an "arrived by" date, so it
   *  is excluded from the count and the span, not backfilled with a different key. */
  count: number;
  startLevel: number;
  endLevel: number;
  startMark: ResolvedMark;
  endMark: ResolvedMark;
  months: number;
  years: number;
}

/**
 * The span from the lowest qualifying level's `available` mark to the highest qualifying level's
 * `available` mark -- product to product. The editor's calls (2026-09-18): the date a level "arrived" is
 * a product's date, not a paper's, and the product is the widely known one that brought the level
 * to the public (ChatGPT, not the text game that did the same thing three years earlier), marked
 * at its launch. Computed
 * fresh from whatever levelSeries() returns -- null only if fewer than two levels have a resolved
 * `available`. Nothing about which levels qualify, or how many there are, is hard-coded: a level
 * qualifies by having an `available` mark, and the count is however many do. Takes a precomputed
 * series (default: the real data) so tests can pass a synthetic one.
 */
export function climbHeadline(series: LevelSeries[] = levelSeries()): ClimbHeadline | null {
  const qualifying = series.filter((s) => s.marks.some((m) => m.key === 'available'));
  if (qualifying.length < 2) return null;
  const first = qualifying[0];
  const last = qualifying[qualifying.length - 1];
  const startMark = first.marks.find((m) => m.key === 'available')!;
  const endMark = last.marks.find((m) => m.key === 'available')!;
  const months = monthsBetween(startMark.milestone.date, startMark.milestone.precision, endMark.milestone.date, endMark.milestone.precision);
  return {
    count: qualifying.length,
    startLevel: first.level,
    endLevel: last.level,
    startMark,
    endMark,
    months,
    years: months / 12,
  };
}

/** A heading the data supports, e.g. "Seven levels in under four years" -- built from the computed
 *  figure, never a fixed template with a guessed count. */
export function climbHeadlineText(h: ClimbHeadline): string {
  const levelWord = h.count === 1 ? 'level' : 'levels';
  let span: string;
  if (h.years < 1) span = 'in under a year';
  else if (h.years < 10) span = `in under ${numberWord(Math.floor(h.years) + 1)} years`;
  else span = `in about ${Math.round(h.years)} years`;
  return `${capitalize(numberWord(h.count))} ${levelWord} ${span}`;
}

// -- Kinds: shape and label, at most three shapes -------------------------------------------------

const SHAPE_BY_KIND: Record<MilestoneKind, MarkShape> = {
  research: 'circle',
  model: 'square',
  product: 'square',
  tool: 'triangle',
  standard: 'triangle',
};

export function shapeForKind(kind: MilestoneKind): MarkShape {
  return SHAPE_BY_KIND[kind] ?? 'circle';
}

export const KIND_LABEL: Record<MilestoneKind, string> = {
  research: 'Research',
  model: 'Model',
  product: 'Product',
  tool: 'Tool',
  standard: 'Standard',
};

/** Why a milestone is not verified, for the accessible focus text -- the data's own note when it
 *  has one, a plain fallback otherwise. Never invents a reason the data does not give. */
export function verificationNote(m: Milestone): string | undefined {
  if (m.verified) return undefined;
  return m.note ?? 'Not verified against a primary source this site could open today.';
}

// -- Axes: the main ("2017 to today", pre-2017 compressed) and recent ("2022 to today") views ----

export interface MainAxis {
  kind: 'main';
  /** The decimal-year position of the earliest milestone dated in 2017 -- where the main axis
   *  starts being drawn to scale. */
  startYear: number;
  endYear: number;
  /** Fraction of the chart's width given to the compressed "before 2017" stub. */
  stubWidth: number;
  /** Milestones dated before 2017, oldest first -- shown in the stub, not to scale. */
  stubMilestones: Milestone[];
  /** Whole years from the first to the last, for gridlines/labels. */
  yearTicks: number[];
  /** Maps a real decimalYear >= startYear to a fraction in [stubWidth, 1]. */
  toFraction: (year: number) => number;
  /** Position, in [0, stubWidth], for the i-th (0-based) milestone in `stubMilestones`. */
  stubFraction: (index: number) => number;
}

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

/**
 * The main chart's axis: to scale from the first 2017 milestone to `asOfDate`, with every
 * milestone dated before 2017 (level 0's early history) compressed into a fixed-width stub at the
 * left rather than squeezed by true elapsed time -- 2017 minus 1966 would otherwise flatten
 * everything after 2017 into a sliver.
 */
export function buildMainAxis(ms: Milestone[] = milestones, asOfDate: string = asOf, stubWidth = 0.08): MainAxis {
  const asOfYear = decimalYear(asOfDate, 'day');
  const in2017 = ms.filter((m) => yearOf(m.date) === 2017);
  const fallbackStart = ms.reduce((min, m) => Math.min(min, decimalYear(m.date, m.precision)), Infinity);
  const startYear = in2017.length ? Math.min(...in2017.map((m) => decimalYear(m.date, m.precision))) : fallbackStart;

  const stubMilestones = ms
    .filter((m) => yearOf(m.date) < 2017)
    .slice()
    .sort((a, b) => decimalYear(a.date, a.precision) - decimalYear(b.date, b.precision));

  const yearTicks: number[] = [];
  const firstTick = Math.floor(startYear);
  for (let y = firstTick; y <= Math.floor(asOfYear); y++) yearTicks.push(y);

  function toFraction(year: number): number {
    if (asOfYear === startYear) return stubWidth;
    const t = (year - startYear) / (asOfYear - startYear);
    return stubWidth + (1 - stubWidth) * clamp01(t);
  }

  function stubFraction(index: number): number {
    if (stubMilestones.length === 0) return 0;
    // Spread evenly across the inner band of the stub, leaving a small margin on both sides so a
    // stub dot never sits flush against the left edge or the "to scale from here" boundary.
    const margin = stubWidth * 0.12;
    const usable = stubWidth - margin * 2;
    if (stubMilestones.length === 1) return margin + usable / 2;
    return margin + (usable * index) / (stubMilestones.length - 1);
  }

  return { kind: 'main', startYear, endYear: asOfYear, stubWidth, stubMilestones, yearTicks, toFraction, stubFraction };
}

export interface RecentAxis {
  kind: 'recent';
  startYear: number;
  endYear: number;
  yearTicks: number[];
  toFraction: (year: number) => number;
}

export const RECENT_START_YEAR = 2022;

/** The alternate, uncompressed axis for the dense recent stretch: January of `startYear` to
 *  `asOfDate`, straight-line scale, no stub. */
export function buildRecentAxis(asOfDate: string = asOf, startYear: number = RECENT_START_YEAR): RecentAxis {
  const start = startYear;
  const end = decimalYear(asOfDate, 'day');
  const yearTicks: number[] = [];
  for (let y = startYear; y <= Math.floor(end); y++) yearTicks.push(y);
  function toFraction(year: number): number {
    if (end === start) return 0;
    return clamp01((year - start) / (end - start));
  }
  return { kind: 'recent', startYear: start, endYear: end, yearTicks, toFraction };
}

// -- Label de-collision for the wide chart ---------------------------------------------------------

export interface LabelPoint {
  id: string;
  fraction: number;
}

/**
 * Which milestones on one lane get a printed text label on the wide chart, given each one's
 * fractional x position (0..1) on whichever axis is active. Every marked milestone (its id is in
 * `markedIds`) is always labelled -- it carries the site's own interval arithmetic and has to be
 * identifiable without a hover. Beyond that, up to `maxExtra` more are added, in the order given,
 * each only if it sits at least `minGap` away (as a fraction of the axis) from every label chosen
 * so far -- the de-collision the dense 2023-2026 stretch needs. Every point not selected is still
 * a real, focusable dot; it is reachable by keyboard and read out in the full list below the
 * chart, just not labelled inline.
 */
export function selectLabeledMilestones(
  points: LabelPoint[],
  markedIds: Set<string>,
  opts: { minGap?: number; maxExtra?: number } = {},
): Set<string> {
  const minGap = opts.minGap ?? 0.05;
  const maxExtra = opts.maxExtra ?? 2;
  const chosenFractions: number[] = [];
  const result = new Set<string>();

  for (const p of points) {
    if (markedIds.has(p.id)) {
      result.add(p.id);
      chosenFractions.push(p.fraction);
    }
  }

  const farEnough = (f: number) => chosenFractions.every((c) => Math.abs(c - f) >= minGap);
  let extras = 0;
  for (const p of points) {
    if (extras >= maxExtra) break;
    if (result.has(p.id)) continue;
    if (farEnough(p.fraction)) {
      result.add(p.id);
      chosenFractions.push(p.fraction);
      extras++;
    }
  }
  return result;
}

export type LabelSide = 'above' | 'below';

/**
 * Which side of the lane each LABELLED point's text prints on, alternating in x order over the
 * labelled points ONLY. This matters because most dots on a lane carry no visible label at all
 * (see selectLabeledMilestones): alternating by raw list position (every other dot, labelled or
 * not) would not keep adjacent VISIBLE labels apart, since an unlabelled dot can sit between two
 * labelled ones without affecting which side either prints on. Alternating over the labelled
 * subset specifically guarantees two neighbouring visible labels are never both "below" (or both
 * "above") the lane, which is what actually prevents their text overlapping.
 */
export function assignLabelSides(points: LabelPoint[], labeled: Set<string>): Map<string, LabelSide> {
  const sides = new Map<string, LabelSide>();
  points
    .filter((p) => labeled.has(p.id))
    .slice()
    .sort((a, b) => a.fraction - b.fraction)
    .forEach((p, i) => sides.set(p.id, i % 2 === 0 ? 'below' : 'above'));
  return sides;
}

// -- The full list, grouped by year ----------------------------------------------------------------

export interface YearGroup {
  year: number;
  items: Milestone[];
}

/** Every milestone grouped by calendar year, newest year first, newest date first within a year. */
export function milestonesByYearDesc(ms: Milestone[] = milestones): YearGroup[] {
  const byYear = new Map<number, Milestone[]>();
  for (const m of ms) {
    const y = yearOf(m.date);
    if (!byYear.has(y)) byYear.set(y, []);
    byYear.get(y)!.push(m);
  }
  return [...byYear.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([year, items]) => ({
      year,
      items: items.slice().sort((a, b) => decimalYear(b.date, b.precision) - decimalYear(a.date, a.precision)),
    }));
}
