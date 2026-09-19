// The site's navigation, defined once. The header's menus, the rail under it, the phone sheet
// and the footer's sitemap all read this, so they cannot disagree about what the site contains
// or where a page belongs. Pure: data comes in as arguments, which keeps it testable under plain
// `node --test` without the real content/taxonomy.json.
//
// The structure follows the site, not the file tree:
//   Levels       the ladder itself, eight rungs
//   Techniques   every page, how they connect, and the topics that cut across the levels
//   In practice  what to do with it: find your level, build a recipe, read a teardown
//   Reference    when things arrived, who makes what, what the words mean, how the site works

export interface NavLevel {
  order: number;
  title: string;
  short?: string;
  /** Technique slugs at this level: a technique page belongs to its level's part of the site. */
  slugs: string[];
}

export interface NavTrack {
  id: string;
  title: string;
  slugs: string[];
}

export interface NavItem {
  label: string;
  /** Site-relative path starting with "/" (the caller runs it through url()). */
  path: string;
  /** One line under the label in the menu. */
  hint?: string;
  /** Set on level items: drives the level hue. */
  level?: number;
}

export interface NavSection {
  /** A small heading inside a group's panel. */
  heading?: string;
  items: NavItem[];
}

export interface NavGroup {
  id: 'levels' | 'techniques' | 'practice' | 'reference';
  label: string;
  /** One sentence at the top of the panel saying what this part of the site is. */
  blurb: string;
  sections: NavSection[];
}

export function buildNav(levels: NavLevel[], tracks: NavTrack[]): NavGroup[] {
  const ordered = [...levels].sort((a, b) => a.order - b.order);
  return [
    {
      id: 'levels',
      label: 'Levels',
      blurb: 'Eight levels, ordered by who decides the next step. Start at the lowest one that does the job.',
      sections: [
        {
          items: ordered.map((l) => ({ label: l.title, path: `/levels/${l.order}/`, hint: l.short, level: l.order })),
        },
      ],
    },
    {
      id: 'techniques',
      label: 'Techniques',
      blurb: 'Every technique has a page: what it is, a run you can step through, when not to use it, how it fails.',
      sections: [
        {
          heading: 'Browse',
          items: [
            { label: 'All techniques', path: '/techniques/', hint: 'Every page, grouped by level' },
            { label: 'The map', path: '/map/', hint: 'How the techniques connect' },
            { label: 'Graph engineering', path: '/threads/graph-engineering/', hint: 'One idea followed across three levels' },
          ],
        },
        {
          heading: 'Topics across every level',
          items: tracks.map((t) => ({ label: t.title, path: `/techniques/${t.id}/`, hint: `${t.slugs.length + 1} pages` })),
        },
      ],
    },
    {
      id: 'practice',
      label: 'In practice',
      blurb: 'Start from the job, not the technique.',
      sections: [
        {
          items: [
            { label: 'Find your level', path: '/worksheet/', hint: 'Seven questions, one recommendation' },
            { label: 'Recipes', path: '/recipes/', hint: 'Whole jobs, built from techniques' },
            { label: 'Teardowns', path: '/teardowns/', hint: 'Products you have used, taken apart' },
            { label: 'Failure modes', path: '/failures/', hint: 'How each technique goes wrong' },
          ],
        },
      ],
    },
    {
      id: 'reference',
      label: 'Reference',
      blurb: 'The record behind the pages.',
      sections: [
        {
          items: [
            { label: 'Timeline', path: '/timeline/', hint: 'When each level reached the public' },
            { label: 'Names', path: '/names/', hint: 'Who makes what: models, products, tools' },
            { label: 'Glossary', path: '/glossary/', hint: 'The words, defined from the pages' },
            { label: 'Method', path: '/method/', hint: 'Premise, principles, how claims are checked' },
          ],
        },
      ],
    },
  ];
}

export interface NavContext {
  /** The group the current page belongs to; undefined on the home page, search and 404. */
  group?: NavGroup['id'];
  /** The level a page sits at, when it has one (a level page, or a technique page at a level). */
  level?: number;
}

/** Normalises "/x" and "/x/index.html" style paths to "/x/". */
function norm(path: string): string {
  let p = path.split('#')[0].split('?')[0];
  if (!p.startsWith('/')) p = `/${p}`;
  if (!p.endsWith('/') && !/\.[a-z0-9]+$/i.test(p)) p += '/';
  return p;
}

/**
 * Where a path sits in the site. A technique page at a level belongs to LEVELS (it is a rung's
 * content, and the rail shows the ladder); a topic page belongs to TECHNIQUES.
 */
export function navContext(path: string, levels: NavLevel[], tracks: NavTrack[]): NavContext {
  const p = norm(path);
  const level = /^\/levels\/(\d+)\//.exec(p);
  if (level) return { group: 'levels', level: Number(level[1]) };
  const tech = /^\/techniques\/([^/]+)\//.exec(p);
  if (tech) {
    const slug = tech[1];
    const at = levels.find((l) => l.slugs.includes(slug));
    if (at) return { group: 'levels', level: at.order };
    return { group: 'techniques' };
  }
  if (p === '/techniques/' || p.startsWith('/map/') || p.startsWith('/threads/')) return { group: 'techniques' };
  if (p.startsWith('/worksheet/') || p.startsWith('/recipes/') || p.startsWith('/teardowns/') || p.startsWith('/failures/')) return { group: 'practice' };
  if (p.startsWith('/timeline/') || p.startsWith('/names/') || p.startsWith('/glossary/') || p.startsWith('/method/')) return { group: 'reference' };
  // tracks is accepted so a future rule can use it; topic pages already resolve above.
  void tracks;
  return {};
}

/** The items the rail under the header shows for a context: the current group's own pages. */
export function railItems(groups: NavGroup[], ctx: NavContext): NavItem[] {
  const group = groups.find((g) => g.id === ctx.group);
  if (!group) return [];
  if (group.id === 'techniques') return group.sections[0].items;
  return group.sections.flatMap((s) => s.items);
}

/** True when `item` is the page at `path`, or (for a section index) an ancestor of it. */
export function isCurrent(item: NavItem, path: string, ctx: NavContext): boolean {
  const p = norm(path);
  const target = norm(item.path);
  if (item.level !== undefined) return ctx.level === item.level;
  if (p === target) return true;
  // "/recipes/" stays current on "/recipes/support-desk/"; "/techniques/" does not claim a
  // technique page that belongs to a level.
  if (target === '/techniques/') return false;
  return target !== '/' && p.startsWith(target);
}
