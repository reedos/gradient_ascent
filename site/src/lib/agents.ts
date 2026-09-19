// The site for a reader's own AI agent. A person describes a job, points their agent here, and the
// agent recommends the simplest way to do it and says why. Everything an agent needs for that is
// built in this module from the same data the human pages use, as three things:
//
//   the guide        what to ask, how to walk the decision, what an answer should contain, and
//                    what not to claim (/agents.md, and shown in full on /agents/ so a person can
//                    read exactly what their agent will)
//   the worksheet    the decision tree as text, because the interactive page is no use to a
//                    program (/worksheet.md; /data/worksheet.json is the same thing as data)
//   the use cases    every recipe and teardown with the level it needs and the techniques it is
//                    made from (/data/use-cases.json)
//
// Pure: data comes in as arguments, so the tests run under plain `node --test`.
//
// One principle governs the wording of the guide. A page that addresses instructions to an AI
// agent is shaped like a prompt injection, and the only honest version of that is one that (a)
// says the user's own instructions outrank it, (b) asks for nothing except a better answer to
// the user's question, and (c) is shown to the human in full. All three are true here, and the
// tests hold (a) and (c) in place.

export const GUIDE_TITLE = 'Gradient Ascent: a guide for an AI agent helping someone choose';
export const WORKSHEET_TITLE = 'Find the lowest level that does the job';
export const SHAPES_TITLE = 'What kind of job is it?';

export type Block =
  | { kind: 'h2'; text: string }
  | { kind: 'h3'; text: string }
  | { kind: 'p'; text: string }
  | { kind: 'ol'; items: string[] }
  | { kind: 'ul'; items: string[] }
  | { kind: 'code'; text: string };

export interface AgentLevel {
  order: number;
  title: string;
  who: string;
  description: string;
}

export interface AgentCoreAnswer {
  id: string;
  label: string;
  action: 'settle' | 'next';
  level?: number;
  next?: string;
  reason: string;
}

export interface AgentCoreQuestion {
  id: string;
  level_tested: number;
  prompt: string;
  help?: string;
  answers: AgentCoreAnswer[];
}

export interface AgentCrossQuestion {
  id: string;
  prompt: string;
  /** `caution` is absent or null when an answer adds no advice. */
  answers: { id: string; label: string; caution?: { text: string; relates_to?: string[] } | null }[];
}

export interface AgentWorksheet {
  first_question: string;
  core_questions: AgentCoreQuestion[];
  cross_questions: AgentCrossQuestion[];
}

/** A job shape as the guide needs it. See lib/shapes.ts and content/shapes.json. */
export interface AgentShape {
  id: string;
  title: string;
  what: string;
  signals: string[];
  usual_level: number;
  lower_when: string;
  higher_when: string;
  techniques: { slug: string; title: string; markdown: string }[];
  recipes: { slug: string; title: string; domain: string; markdown: string }[];
  teardowns: { slug: string; title: string; markdown: string }[];
  elsewhere: string[];
}

export interface UseCase {
  kind: 'recipe' | 'teardown';
  slug: string;
  title: string;
  summary: string;
  domain: string;
  /** The job shapes this use case illustrates (ids from /data/shapes.json). */
  shapes: string[];
  /** The highest level the job needs: the level to settle on before this use case fits. */
  needs_level: number | null;
  levels: number[];
  techniques: { slug: string; title: string; level: number | 'topic'; url: string; markdown: string }[];
  url: string;
  markdown: string;
}

export interface GuideInput {
  /** Absolute URL builder: abs('/agents.md') -> 'https://.../gradient_ascent/agents.md'. */
  abs: (path: string) => string;
  levelRule: string;
  levels: AgentLevel[];
  counts: { techniques: number; recipes: number; teardowns: number; names: number; milestones: number; terms: number };
  namesAsOf: string;
  allDraft: boolean;
  /** How many use cases carry each domain, from the data. The guide may only point an agent at a
   *  domain that has something in it: a cold sitting on 09/19/2026 caught the first version
   *  telling agents to prefer `engineering` recipes before a single one existed. */
  domainCounts: Record<string, number>;
  shapes: AgentShape[];
}

/** The files an agent can fetch, in the order it should want them. One list, used by the guide,
 *  the human page and llms.txt. */
export function agentFiles(abs: (p: string) => string): { path: string; url: string; what: string }[] {
  const f = (path: string, what: string) => ({ path, url: abs(path), what });
  return [
    f('/agents.md', 'This guide: how to turn a person’s job into a recommendation.'),
    f('/worksheet.md', 'The decision tree as text: seven questions that settle the level, four that change the advice.'),
    f('/shapes.md', 'The kinds of job, by the shape of the work and not its subject: how to recognize each, where it usually settles, what moves it lower or higher, and jobs from other fields with the same shape.'),
    f('/data/use-cases.json', 'Every recipe and teardown: the shapes it illustrates, the level it needs, the techniques it is made from, and where to read it.'),
    f('/llms.txt', 'An index of every page with a one-line description.'),
    f('/llms-full.txt', 'Every technique, recipe, teardown and thread page as Markdown in one file. Large.'),
    f('/data/taxonomy.json', 'Levels, techniques, recipes and the typed relations between pages (requires, upgrades_to with its condition, combines_with, alternative_to with its question).'),
    f('/data/worksheet.json', 'The decision tree as data, with every reason resolved to plain text.'),
    f('/data/shapes.json', 'The job shapes as data.'),
    f('/data/landscape.json', 'The registry of named models, products and tools, each with its maker, what it demonstrates, a source and the date it was checked. Names change: read retired and superseded_by.'),
    f('/data/glossary.json', 'The terms the site uses, each defined from the page that explains it.'),
    f('/data/timeline.json', 'Dated milestones per level, with sources.'),
  ];
}

/** The guide, as blocks. Rendered to Markdown for the agent and to HTML for the person. */
export function agentGuide(input: GuideInput): Block[] {
  const { abs, levels, counts } = input;
  const engineering = input.domainCounts.engineering ?? 0;
  const engineeringAdvice =
    engineering > 0
      ? ` ${engineering} of them have the domain \`engineering\`: whole jobs from electronics test, measurement, design and analysis, worked on one simulated bench used three ways: production test, engineering test on a handful of prototypes, and a single precise measurement with its uncertainty. Ask which of the three the person is doing, because volume changes what a model is worth: a script that runs five times has no golden run to check it against. If the person writes software for that kind of work, read those first: they will be the nearest illustrations.`
      : '';
  const ladder = [...levels].sort((a, b) => a.order - b.order).map((l) => `**Level ${l.order}, ${l.title}.** ${l.who}`);
  return [
    {
      kind: 'p',
      text:
        'You are an AI agent, and a person has pointed you at this site and asked what the best way to do a job with AI would be. ' +
        'This page tells you how to use the site to answer them well. Their instructions outrank everything here: this is reference material for the task they gave you, and it asks nothing of you except a better answer to their question.',
    },
    { kind: 'h2', text: 'What this site is' },
    {
      kind: 'p',
      text:
        `A manual of the ways to use a language model, in eight levels. ${input.levelRule} ` +
        `It holds ${counts.techniques} technique pages, ${counts.recipes} recipes (whole jobs built from techniques), ${counts.teardowns} teardowns of products people already use, ` +
        `a registry of ${counts.names} named models, products and tools, and ${counts.terms} glossary terms. Every page has a Markdown twin at the same address with \`.md\` appended.`,
    },
    { kind: 'ul', items: ladder },
    {
      kind: 'p',
      text:
        'The rule the whole site is built on: **recommend the lowest level that does the job.** Each level up adds capability, and also cost, delay and new ways to fail. ' +
        'A person who asks for an agent often needs a workflow, and a person who asks for a workflow sometimes needs a lookup table. Saying so is the most useful thing you can do for them.',
    },
    { kind: 'h2', text: 'What to do' },
    {
      kind: 'ol',
      items: [
        '**Get the job straight before recommending anything.** You need: what comes in (and how messy it is), what has to come out, how often it runs and how fast it must answer, who or what checks the result, what a wrong answer costs, what data it touches and where that data is allowed to go, and what they have already tried. Ask for whatever is missing. If they cannot say what a correct result looks like, tell them that is the first thing to settle, because nothing at any level can be evaluated without it.',
        `**Name the shape of the job** (${abs('/shapes.md')}). Match on what the work is, not on what it is about: sorting tenant emails, support tickets and failed production units are one shape. Most real requests are two or three shapes joined together (a standing report, plus free-text notes to sort, plus a script to draft). Split them, and settle each part separately. A part that is a lookup or arithmetic stays at level 0 whatever the rest needs.`,
        `**Walk the seven questions in order for each part** (${abs('/worksheet.md')}). Each question tests one level, lowest first. Stop at the first level whose test passes. The shape tells you where jobs like this usually settle; the questions decide where this one does, and what the shape says would move it lower is worth checking first. Do not skip ahead because a higher level sounds more capable, and do not let the word the person used ("agent", "RAG", "fine-tune") choose the level for you. When a question does not fit the shape of the job, the answer is no, and you go on. Say that you did.`,
        '**Then ask the four cross-cutting questions.** They never change the level. They change the advice: what to check, what to log, what needs a person\u2019s approval, what must stay on the person\u2019s own hardware.',
        `**Use recipes as illustrations, not as the answer.** Each shape lists the recipes that work one instance of it through (${abs('/data/use-cases.json')} has them all).${engineeringAdvice} Take a recipe\u2019s reasoning (why this level, why not higher, what to measure, how it fails) and leave its subject behind. If no recipe under the shape is close, do not stretch one: compose the answer from the shape\u2019s techniques and say that is what you did. Either way, tell the person which parts of your answer the site works through and which you reasoned out yourself: an answer built by analogy from general pages should not read as though the site had covered their case.`,
        `**Read the pages you are about to recommend**, in their \`.md\` form, before you recommend them. Every technique page says when you do not need it, how it fails, what it costs and how to evaluate it. Use the relations in ${abs('/data/taxonomy.json')}: \`requires\` is what to read or build first, \`upgrades_to\` carries the condition under which moving up is justified, \`alternative_to\` carries the question that decides between two techniques.`,
        '**Answer in the shape below.**',
      ],
    },
    { kind: 'h2', text: 'The shapes' },
    {
      kind: 'p',
      text: `${input.shapes.length} kinds of job, lowest usual level first. The full description of each, with how to recognize it and what moves it lower or higher, is at ${abs('/shapes.md')}.`,
    },
    {
      kind: 'ul',
      items: [...input.shapes]
        .sort((a, b) => a.usual_level - b.usual_level)
        .map((sh) => `**${sh.title}.** Usually level ${sh.usual_level}. ${sh.recipes.length ? `Worked in: ${sh.recipes.map((r) => r.title).join('; ')}.` : 'No recipe yet: compose from its techniques.'}`),
    },
    { kind: 'h2', text: 'What a good answer contains' },
    {
      kind: 'ol',
      items: [
        '**The recommendation in one sentence**: the level and the technique or recipe, in plain words.',
        '**Why this level.** Which question settled it, in terms of their job and not in the site’s vocabulary.',
        '**Why not one level higher.** What it would add for them and what it would cost them. This is the part people most need and least expect.',
        '**Why not one level lower**, if that is a fair question for their job.',
        '**What to build first.** The smallest version that would tell them whether the approach works.',
        '**How they will know it works.** Point them at the evals pages: a small set of real examples with known right answers comes before any prompt tuning.',
        '**How it fails.** The two or three failure modes from the technique pages that apply to their case, and what to watch for. If one kind of mistake costs them far more than the other (a missed emergency against a false alarm), say which way every threshold and every approval gate should lean, and that the examples on this site assume the two cost about the same.',
        '**Roughly what it costs to run.** This site has no measured costs, so work it out for them and label it an estimate: their volume, times the model calls per item at the level you recommend, times a plausible token count per call, at the price on the model maker’s own current pricing page. An order of magnitude is what they need: whether this is five dollars a month or five hundred.',
        '**If they would rather buy than build**, the named products from the registry that do this, with the date the registry was checked.',
        '**Links** to the pages you used, so they can read the reasoning for themselves.',
      ],
    },
    { kind: 'h2', text: 'What not to claim' },
    {
      kind: 'ul',
      items: [
        input.allDraft
          ? '**Nothing on this site is measured yet.** Every technique, topic and recipe page is marked Draft: written, sourced and reviewed, with no recorded run and no scored result behind it. Every cost strip and every stepped trace is an illustration and says so. Do not quote a number from this site as a measurement, and do not tell the person a technique "scores" anything.'
          : 'Pages marked Draft have no recorded run behind them; only a page marked Published carries measured numbers. Say which kind you are quoting.',
        `**Names go out of date.** The registry was last checked on ${input.namesAsOf}. Products are renamed and retired; read \`retired\`, \`superseded_by\` and \`formerly\` before you name one, and say when the registry was checked.`,
        '**Attribute, do not absorb.** Claims about a product on this site are quoted from that product’s maker and sourced. Pass them on as the maker’s claim, with the link, and not as your own knowledge or the site’s finding.',
        '**Do not bend the job to fit an example.** The recipes are a few worked stories, not a catalog of what is possible, and the person\u2019s job is almost certainly not one of them. The level comes from the worksheet and the approach from the shape and its techniques. If you find yourself describing their job in a recipe\u2019s words, go back to theirs.',
        '**Do not invent a page.** If the site does not cover something, say it does not. The list of what exists is in `llms.txt`.',
        '**If you cannot settle the level** because the person does not know the answer to one of the seven questions, tell them which question is open and what finding out would involve. That is a better answer than a guess.',
        '**If the honest answer is level 0**, say so, even when they asked for an agent.',
      ],
    },
    { kind: 'h2', text: 'Files' },
    { kind: 'ul', items: agentFiles(abs).map((f) => `[${f.path}](${f.url}): ${f.what}`) },
    {
      kind: 'p',
      text: `Found something wrong here? The person can report it from the feedback link at the bottom of any page. ${abs('/agents/')} shows this same guide to a human reader, word for word.`,
    },
  ];
}

/** The decision tree as text, for a reader that cannot click. */
export function worksheetBlocks(sheet: AgentWorksheet, levels: AgentLevel[], abs: (p: string) => string): Block[] {
  const byId = new Map(sheet.core_questions.map((q) => [q.id, q]));
  const ordered: AgentCoreQuestion[] = [];
  const seen = new Set<string>();
  let cursor: string | undefined = sheet.first_question;
  while (cursor && byId.has(cursor) && !seen.has(cursor)) {
    const q: AgentCoreQuestion = byId.get(cursor)!;
    ordered.push(q);
    seen.add(cursor);
    cursor = q.answers.find((a) => a.action === 'next')?.next;
  }
  for (const q of sheet.core_questions) if (!seen.has(q.id)) ordered.push(q);

  const levelTitle = (n: number | undefined) => {
    const l = levels.find((x) => x.order === n);
    return l ? `level ${l.order}, ${l.title}` : `level ${n}`;
  };

  const blocks: Block[] = [
    {
      kind: 'p',
      text:
        `The worksheet at ${abs('/worksheet/')}, as text. Seven questions, asked in order, each testing one level from the lowest up. Stop at the first answer that says "settle": that is the lowest level that does the job. ` +
        'Then ask all four cross-cutting questions. They do not change the level, they add cautions. A question that does not fit the shape of the job (the documents question, for a job that sorts messages and acts on them) is answered no.',
    },
    { kind: 'h2', text: 'The seven questions that settle the level' },
  ];
  ordered.forEach((q, i) => {
    blocks.push({ kind: 'h3', text: `${i + 1}. ${q.prompt}` });
    if (q.help) blocks.push({ kind: 'p', text: q.help });
    blocks.push({
      kind: 'ul',
      items: q.answers.map((a) =>
        a.action === 'settle'
          ? `**${a.label}** Settle on ${levelTitle(a.level)} (${abs(`/levels/${a.level}/`)}). ${a.reason}`
          : `**${a.label}** Go on to the next question. ${a.reason}`,
      ),
    });
  });
  blocks.push({ kind: 'h2', text: 'The four questions that change the advice' });
  sheet.cross_questions.forEach((q, i) => {
    blocks.push({ kind: 'h3', text: `${i + 1}. ${q.prompt}` });
    blocks.push({
      kind: 'ul',
      items: q.answers.map((a) => {
        if (!a.caution) return `**${a.label}** No extra caution.`;
        const pages = (a.caution.relates_to ?? []).map((s) => abs(`/techniques/${s}.md`)).join(', ');
        return `**${a.label}** ${a.caution.text}${pages ? ` Read: ${pages}` : ''}`;
      }),
    });
  });
  return blocks;
}

/** The job shapes as text. */
export function shapesBlocks(shapes: AgentShape[], abs: (p: string) => string): Block[] {
  const blocks: Block[] = [
    {
      kind: 'p',
      text:
        'The kinds of job people bring to a language model, described by the shape of the work and not by its subject. Match a job on what the work is. ' +
        'Most real requests are two or three of these joined together; split them and settle each part on its own. ' +
        `"Usually level N" is where the worksheet (${abs('/worksheet.md')}) most often settles for that shape. It is an expectation to test, never a verdict.`,
    },
  ];
  for (const sh of [...shapes].sort((a, b) => a.usual_level - b.usual_level)) {
    blocks.push({ kind: 'h2', text: sh.title });
    blocks.push({ kind: 'p', text: `${sh.what} **Usually level ${sh.usual_level}.**` });
    blocks.push({ kind: 'p', text: `**How to recognize it.** ${sh.signals.join(' ')}` });
    blocks.push({ kind: 'p', text: `**Lower when.** ${sh.lower_when}` });
    blocks.push({ kind: 'p', text: `**Higher when.** ${sh.higher_when}` });
    blocks.push({ kind: 'p', text: `**The same shape in other fields.** ${sh.elsewhere.join('. ')}.` });
    blocks.push({ kind: 'p', text: `**Techniques.** ${sh.techniques.map((t) => `[${t.title}](${t.markdown})`).join(', ')}.` });
    const worked = [
      ...sh.recipes.map((r) => `[${r.title}](${r.markdown})${r.domain !== 'general' ? ` (${r.domain})` : ''}`),
      ...sh.teardowns.map((t) => `[${t.title}](${t.markdown}) (teardown)`),
    ];
    blocks.push({
      kind: 'p',
      text: worked.length
        ? `**Worked examples.** ${worked.join(', ')}. Each is one instance of the shape: take its reasoning and leave its subject.`
        : '**Worked examples.** None yet. Compose the answer from the techniques above.',
    });
  }
  return blocks;
}

// ---------------------------------------------------------------- rendering

/** Blocks to Markdown. */
export function toMarkdown(title: string, blocks: Block[]): string {
  const out: string[] = [`# ${title}`, ''];
  for (const b of blocks) {
    if (b.kind === 'h2') out.push(`## ${b.text}`, '');
    else if (b.kind === 'h3') out.push(`### ${b.text}`, '');
    else if (b.kind === 'p') out.push(b.text, '');
    else if (b.kind === 'code') out.push('```', b.text, '```', '');
    else if (b.kind === 'ol') out.push(...b.items.map((it, i) => `${i + 1}. ${it}`), '');
    else out.push(...b.items.map((it) => `- ${it}`), '');
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd() + '\n';
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** The small inline subset the guide uses: **bold**, `code`, [text](url) and bare URLs. The text
 *  is escaped first, so nothing in the data can become markup. */
export function inlineHtml(text: string): string {
  let s = escapeHtml(text);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2">$1</a>');
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+[^\s<).,;:])/g, '$1<a href="$2">$2</a>');
  return s;
}
