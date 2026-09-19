// The Method page as data: the premise, the ten principles, the six method entries, what the
// registry is, and where the site stands today. Written once here so that /method/ (for a person)
// and /method.md (for a reader's own agent) are the same words and cannot drift apart. The
// rendering lives in pages/method.astro and pages/method.md.ts, the way lib/agents.ts feeds
// /agents/ and /agents.md.
//
// Pure, apart from reading the taxonomy: the level rule is quoted from content/taxonomy.json
// rather than retyped, so the glossary, /llms.txt and this page cannot disagree about it.
import type { Block } from './agents';
import { taxonomy } from './content';

export const METHOD_TITLE = 'Why this site exists and how it works';

export interface MethodSection {
  /** The heading's anchor on /method/, and the target of the on-this-page nav. */
  id: string;
  /** The short label in the on-this-page nav. */
  nav: string;
  heading: string;
  blocks: Block[];
}

/** What the registry is and is not, and what a person who wants to buy rather than build should
 *  check for themselves. Shown on /method/ and again on /names/, from this one definition. */
export function registryBlocks(abs: (path: string) => string): Block[] {
  return [
    {
      kind: 'p',
      text:
        `[The registry](${abs('/names/')}) lists models, developer tools and AI-first products, and records which technique each one demonstrates, with a primary source and the date it was checked. That is the whole of it. It is not a buyer’s guide: it carries no prices, no seat costs, no setup effort and no measure of quality, it ranks nothing, and it does not cover the ordinary business software a person already runs that has since grown an AI feature. Use it to work out what a product is doing underneath, not to choose which one to pay for.`,
    },
    {
      kind: 'p',
      text:
        'If you want to buy rather than build, four things are worth asking about any product in any category. This site cannot answer them for you, because every answer depends on the plan and is the seller’s to state, but a seller who cannot answer them has told you something.',
    },
    {
      kind: 'ul',
      items: [
        '**Which level it operates at.** Does it answer one request at a time, run a fixed workflow somebody wrote down, or decide its own next step? That is the question this site’s eight levels ask, and the answer sets both what the product can do without you and how many ways it can go wrong.',
        `**Who else holds the text.** The model’s maker is rarely the only company that receives what you type: the product in front of it keeps its own copy under its own terms. [Who else holds the text](${abs('/techniques/safety/#who-else-holds-the-text')}) says whose pages to read, in what order, and what the intermediaries usually do not say.`,
        '**Whether a person approves before anything is sent or changed.** Ask whether an approval step exists, whether it is on by default, and what it actually covers: a message sent, a record changed, a payment made.',
        '**Whether you can get the work back out.** The documents, the records and the history, exported in a format another program can read, and what happens to them when you stop paying.',
      ],
    },
  ];
}

/** Every section of /method/, in order. */
export function methodSections(abs: (path: string) => string): MethodSection[] {
  return [
    {
      id: 'premise',
      nav: 'Premise',
      heading: 'Premise',
      blocks: [
        {
          kind: 'p',
          text:
            'AI is a general-purpose technology. It is changing how work gets done in every industry: the workflows people follow, the processes companies run, how productive a person or a team can be, and how software and machines are operated, in the digital world and the physical one. People who understand the full range of techniques will make better decisions about where to use it. This site describes that range, shows how each technique works, and will measure what each one costs.',
        },
      ],
    },
    {
      id: 'principles',
      nav: 'Principles',
      heading: 'Principles',
      blocks: [
        {
          kind: 'ul',
          items: [
            '**Use the simplest approach that works.** Every page says when the technique is not needed and what to try first.',
            '**Measure before claiming.** A page may say a level helps only when a committed result file shows it. No result file exists yet, so nothing on the site reports a measured number.',
            '**Name real things.** Every technique is tied to the models, products and tools that use it. Names come from a dated registry with sources.',
            '**Show how it works.** Each technique has a diagram, a recorded run the reader can step through, and code the reader can run.',
            '**State the costs and the failures.** Each page lists the cost in tokens and time, the common failure modes, and how to test for them.',
            '**Stay current and say how current.** Every page and every name carries the date it was last checked. Anything not checked in 90 days is flagged.',
            '**One site for beginners and experts.** Each page has a version with no code and a version with code. Both describe the same technique.',
            '**Independent.** No rankings, no sponsorship, no affiliate links. Where several companies make something, the page names more than one.',
            '**Open.** MIT licensed. The taxonomy, the registry and the result files are published as data. Corrections are welcome.',
            '**Private data stays private.** Examples, traces and test documents are synthetic.',
          ],
        },
      ],
    },
    {
      id: 'method',
      nav: 'Method',
      heading: 'Method',
      blocks: [
        { kind: 'h3', text: 'How a level is defined' },
        {
          kind: 'p',
          // The rule itself comes from content/taxonomy.json, not a copy typed here: the glossary's
          // "level" entry and /llms.txt print the same string, so the three cannot drift apart.
          text:
            `${taxonomy.level_rule} Levels 1 to 3 all leave the decisions with the person or the code; ` +
            'they differ in how much has to be built around the model.',
        },
        { kind: 'h3', text: 'How a technique gets a page' },
        {
          kind: 'p',
          text:
            'It is described in primary sources from at least two independent makers or papers. It is placed at the lowest level where it applies. If it fits no level, the taxonomy gets a dated amendment.',
        },
        { kind: 'h3', text: 'How a page is written' },
        {
          kind: 'p',
          text:
            'Fixed anatomy, word budgets, sources for every factual claim, one production line: sources, draft, example and trace, eval, figure, review.',
        },
        { kind: 'h3', text: 'How results are measured' },
        {
          kind: 'p',
          text:
            'One task, run at every level, on three classes of model spanning small local to a frontier API. Result files are what the charts are built from; a number with no file cannot render.',
        },
        { kind: 'h3', text: 'How names are checked' },
        {
          kind: 'p',
          text:
            'A registry entry needs a primary source, a checked date and a verified flag before a published page can cite it. Entries unchecked for 90 days are flagged.',
        },
        { kind: 'h3', text: 'How the site changes' },
        {
          kind: 'p',
          text: 'Dated amendments to the taxonomy, a changelog per page, a review queue worked oldest first.',
        },
      ],
    },
    {
      id: 'registry',
      nav: 'What the registry is',
      heading: 'What the registry is, and is not',
      blocks: registryBlocks(abs),
    },
    {
      id: 'status',
      nav: 'Where the site is today',
      heading: 'Where the site is today',
      blocks: [
        {
          kind: 'p',
          text:
            `Every technique, topic and recipe page is a **draft**: written, sourced and reviewed, but with no recorded run and no scored result file behind it. Nothing on this site reports a measured number. Every cost-and-latency strip and every stepped trace is an illustration, labeled as one above its figures, and a page becomes **published** only once a real run and a real eval sit behind it. The [evals](${abs('/techniques/evals/')}) page describes how that measurement works and what it will record.`,
        },
      ],
    },
    {
      id: 'not',
      nav: 'What the site does not do',
      heading: 'What the site does not do',
      blocks: [
        {
          kind: 'p',
          text: 'It does not rank vendors, predict the future, or give legal, financial or safety-critical advice.',
        },
      ],
    },
  ];
}

/** The same sections flattened for the Markdown twin, each heading becoming an `h2`. */
export function methodBlocks(sections: MethodSection[]): Block[] {
  return sections.flatMap((s): Block[] => [{ kind: 'h2', text: s.heading }, ...s.blocks]);
}
