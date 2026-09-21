// The site's navigation, defined once. The header's menus, the rail under it, the phone sheet
// and the footer's sitemap all read this, so they cannot disagree about what the site contains
// or where a page belongs. Pure: data comes in as arguments, which keeps it testable under plain
// `node --test` without the real content/taxonomy.json.
//
// Visitor-facing groups are Understand, Explore, Apply, and Reference.
// Existing internal group IDs remain stable for header styles and level colors.

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

export interface NavThread {
  id: string;
  title: string;
}

/** What the menu says under a thread's title. A thread with no line here gets the general one,
 *  so a new thread in content/taxonomy.json appears in the menu with no edit to this file. */
const THREAD_HINTS: Record<string, string> = {
  'graph-engineering': 'One idea followed across three levels',
  'who-approves-what': 'What a person still holds, level by level',
  'checking-the-work': 'Five ways to tell whether it worked',
  'what-the-model-sees': 'Context, from a prompt to a note for the next session',
};

export function buildNav(levels: NavLevel[], tracks: NavTrack[], threads: NavThread[] = []): NavGroup[] {
  return [
    { id: 'levels', label: 'Understand', blurb: 'Explore an idea. Levels organize patterns; they are not a required progression.', sections: [
      { heading: 'Browse concepts', items: [
        {label:'All concepts',path:'/techniques/',hint:'Definitions, diagrams, and examples'},
        {label:'From chatbot to agent',path:'/chatbot-to-agent/',hint:'Seven steps through the basics'},
        {label:'Concept map',path:'/map/',hint:'See how ideas connect'},
        {label:'Design decisions',path:'/design-decisions/',hint:'The distinctions that change an architecture'},
        {label:'Choose an approach',path:'/worksheet/',hint:'Explore a candidate design for your task'},
      ]},
      { heading: 'Browse by level', items: [...levels].sort((a,b)=>a.order-b.order).map(l=>({label:l.title,path:`/levels/${l.order}/`,hint:l.short,level:l.order})) },
    ]},
    { id:'techniques', label:'Explore', blurb:'Start with a recognizable task and see what goes in, what happens, and what comes out.', sections:[
      { heading:'Tasks and applications', items:[
        {label:'Worked examples',path:'/examples/',hint:'Four starting examples, then the full catalogue'},
        {label:'Recipes',path:'/recipes/',hint:'Complete tasks assembled from concepts'},
        {label:'Job shapes',path:'/shapes/',hint:'Recognize the structure of your work'},
        {label:'Product teardowns',path:'/teardowns/',hint:'How familiar products work'},
      ]},
      {heading:'Follow an idea',items:threads.map(t=>({label:t.title,path:`/threads/${t.id}/`,hint:THREAD_HINTS[t.id]??'One idea across several concepts'}))},
    ]},
    {id:'practice',label:'Apply',blurb:'Prepare a useful request for your own model. You do not need to complete every tool.',sections:[{items:[
      {label:'Create a project brief',path:'/apply/',hint:'Describe the outcome and human role you want'},
      {label:'Project tools',path:'/tools/',hint:'Prepare requests for instructions, workflows, checks, and handoffs'},
      {label:'Use the guide with your AI',path:'/agents/',hint:'Copy a prompt or share model-readable references'},
    ]}]},
    {id:'reference',label:'Reference',blurb:'Definitions, sources, limitations, and the record behind the guide.',sections:[
      {items:[
        {label:'Glossary',path:'/glossary/',hint:'Terms explained'},
        {label:'Names',path:'/names/',hint:'Models, products, and tools'},
        {label:'Timeline',path:'/timeline/',hint:'How the field developed'},
        {label:'Failure modes',path:'/failures/',hint:'What can go wrong'},
        {label:'Method',path:'/method/',hint:'How claims and levels are defined'},
        {label:'What changed',path:'/changes/',hint:'Corrections and additions'},
      ]},
      {heading:'Topics across every level',items:tracks.map(t=>({label:t.title,path:`/techniques/${t.id}/`,hint:`${t.slugs.length+1} pages`}))},
    ]},
  ];
}

export interface NavContext {
  /** The group the current page belongs to; undefined on the home page, search and 404. */
  group?: NavGroup['id'];
  /** The level a page sits at, when it has one (a level page, or a technique page at a level). */
  level?: number;
}

/** Normalizes "/x" and "/x/index.html" style paths to "/x/". */
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
  if (level) return {group:'levels',level:Number(level[1])};
  const tech = /^\/techniques\/([^/]+)\//.exec(p);
  if (tech) {
    const at=levels.find(l=>l.slugs.includes(tech[1]));
    return at ? {group:'levels',level:at.order} : {group:'levels'};
  }
  if (p === '/design-decisions/' || p === '/chatbot-to-agent/' || p === '/techniques/' || p.startsWith('/map/') || p.startsWith('/worksheet/')) return {group:'levels'};
  if (['/examples/','/recipes/','/shapes/','/teardowns/','/threads/'].some(prefix=>p.startsWith(prefix))) return {group:'techniques'};
  if (['/apply/','/tools/','/agents/'].some(prefix=>p.startsWith(prefix))) return {group:'practice'};
  if (['/glossary/','/names/','/timeline/','/failures/','/method/','/changes/'].some(prefix=>p.startsWith(prefix))) return {group:'reference'};
  void tracks;
  return {};
}

/** Compact local navigation; full catalogues remain in menus and the footer. */
export function railItems(groups: NavGroup[], ctx: NavContext): NavItem[] {
  const group=groups.find(g=>g.id===ctx.group);
  if (!group) return [];
  if (ctx.group==='levels' && ctx.level!==undefined) return group.sections[1].items;
  return group.sections[0].items;
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
