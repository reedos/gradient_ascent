// Unit tests for src/lib/agents.ts: the guide, the worksheet as text and the inline renderer that
// serve a reader's own AI agent. Synthetic fixtures; nothing here reads the real content.
//
// Three of these tests hold the guide to the principle in agents.ts's header. A page that
// addresses instructions to an AI agent is shaped like a prompt injection, and the honest version
// says the user outranks it, asks for nothing but a better answer, and is shown to the human.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  agentFiles,
  agentGuide,
  inlineHtml,
  toMarkdown,
  worksheetBlocks,
  type AgentLevel,
  type AgentWorksheet,
  shapesBlocks,
  type AgentShape,
  type GuideInput,
} from '../src/lib/agents.ts';

const abs = (p: string) => `https://example.org/site${p}`;
const levels: AgentLevel[] = [
  { order: 1, title: 'One call', who: 'Nobody decides.', description: 'd1' },
  { order: 0, title: 'No model', who: 'Your code.', description: 'd0' },
  { order: 5, title: 'Agents', who: 'The model, in a loop.', description: 'd5' },
];
const fixtureShapes: AgentShape[] = [
  {
    id: 'do-a-task',
    title: 'Carry out a task',
    what: 'The steps are not known in advance.',
    signals: ['The goal is clear.', 'The path is not.'],
    usual_level: 5,
    lower_when: 'The steps can be written down.',
    higher_when: 'The parts are independent.',
    elsewhere: ['Fix a failing test', 'Bring up a new board'],
    techniques: [{ slug: 'agent-loop', title: 'The agent loop', markdown: abs('/techniques/agent-loop.md') }],
    recipes: [{ slug: 'repo-assistant', title: 'Repo assistant', domain: 'engineering', markdown: abs('/recipes/repo-assistant.md') }],
    teardowns: [],
  },
  {
    id: 'rewrite',
    title: 'Turn one text into another',
    what: 'Text in, text out.',
    signals: ['One input.'],
    usual_level: 1,
    lower_when: 'A template does it.',
    higher_when: 'It needs facts the text lacks.',
    elsewhere: ['Summarize a meeting'],
    techniques: [{ slug: 'prompting', title: 'Prompting', markdown: abs('/techniques/prompting.md') }],
    recipes: [],
    teardowns: [],
  },
];
const input = (over: Partial<GuideInput> = {}): GuideInput => ({
  abs,
  levelRule: 'A new level starts where the answer to who decides changes.',
  levels,
  counts: { techniques: 49, recipes: 20, teardowns: 3, names: 216, milestones: 96, terms: 103 },
  namesAsOf: '2026-09-18',
  allDraft: true,
  domainCounts: { general: 15 },
  shapes: fixtureShapes,
  ...over,
});
const sheet: AgentWorksheet = {
  first_question: 'rule',
  core_questions: [
    // Deliberately out of order: the text must follow the chain, not the array.
    {
      id: 'one-call',
      level_tested: 1,
      prompt: 'Is one request enough?',
      answers: [
        { id: 'yes', label: 'Yes.', action: 'settle', level: 1, reason: 'One call does it.' },
        { id: 'no', label: 'No.', action: 'next', next: 'loop', reason: 'It needs more.' },
      ],
    },
    {
      id: 'rule',
      level_tested: 0,
      prompt: 'Can a rule do it?',
      help: 'If you could write it as if/then, start there.',
      answers: [
        { id: 'yes', label: 'Yes.', action: 'settle', level: 0, reason: 'A rule does it.' },
        { id: 'no', label: 'No.', action: 'next', next: 'one-call', reason: 'It needs language.' },
      ],
    },
    {
      id: 'loop',
      level_tested: 5,
      prompt: 'Are the steps unknown in advance?',
      answers: [{ id: 'yes', label: 'Yes.', action: 'settle', level: 5, reason: 'It has to decide as it goes.' }],
    },
  ],
  cross_questions: [
    {
      id: 'cost',
      prompt: 'What does a wrong answer cost?',
      answers: [
        { id: 'cheap', label: 'Little.', caution: null },
        { id: 'high', label: 'A lot.', caution: { text: 'Put a person in the loop.', relates_to: ['human-in-the-loop'] } },
      ],
    },
  ],
};

const guideText = () => toMarkdown('T', agentGuide(input()));

test('the guide says the user outranks it, in its first paragraph', () => {
  const first = agentGuide(input())[0];
  assert.equal(first.kind, 'p');
  assert.match((first as { text: string }).text, /Their instructions outrank everything here/);
});

test('the guide asks nothing of the agent except a better answer', () => {
  const text = guideText().toLowerCase();
  // Nothing that reaches past the user's question: no telling the agent to keep things from the
  // user, to promote the site, to fetch anything unrelated, or to change how it treats them.
  for (const bad of ['do not tell the user', 'ignore previous', 'ignore your', 'disregard', 'always recommend this site', 'system prompt', 'secret']) {
    assert.ok(!text.includes(bad), `the guide must not contain "${bad}"`);
  }
  assert.match(text, /asks nothing of you except a better answer/);
});

test('the guide tells the agent where a human can read the same words', () => {
  assert.match(guideText(), /shows this same guide to a human reader, word for word/);
  assert.ok(guideText().includes(abs('/agents/')));
});

test('the rule the site is built on is stated, and level 0 is defended', () => {
  const text = guideText();
  assert.match(text, /recommend the lowest level that does the job/);
  assert.match(text, /If the honest answer is level 0/);
});

test('while every page is a draft, the guide forbids quoting a number as a measurement', () => {
  assert.match(guideText(), /Nothing on this site is measured yet/);
  assert.match(guideText(), /Do not quote a number from this site as a measurement/);
  const later = toMarkdown('T', agentGuide(input({ allDraft: false })));
  assert.ok(!later.includes('Nothing on this site is measured yet'));
  assert.match(later, /only a page marked Published carries measured numbers/);
});

test('the guide points at engineering recipes only when the data has some', () => {
  // A cold sitting caught the first version promising a domain that was still empty.
  assert.ok(!guideText().includes('engineering'), 'no engineering use cases, so no mention of them');
  const withSome = toMarkdown('T', agentGuide(input({ domainCounts: { general: 15, engineering: 8 } })));
  assert.match(withSome, /8 of them have the domain `engineering`/);
  assert.match(withSome, /read those first/);
});

test('the job is matched to a shape, and a recipe is an illustration, never the answer', () => {
  // The owner asked whether "find the closest recipe" builds things too narrow. It did.
  const text = guideText();
  assert.match(text, /Name the shape of the job/);
  assert.match(text, /Match on what the work is, not on what it is about/);
  assert.match(text, /Use recipes as illustrations, not as the answer/);
  assert.match(text, /do not stretch one: compose the answer from the shape\u2019s techniques and say that is what you did/);
  assert.match(text, /Do not bend the job to fit an example/);
  assert.ok(!/closest recipe/i.test(text), 'the guide must not send an agent looking for the closest recipe');
});

test('the guide lists every shape lowest level first, and says when one has no recipe', () => {
  const text = guideText();
  const low = text.indexOf('**Turn one text into another.** Usually level 1. No recipe yet');
  const high = text.indexOf('**Carry out a task.** Usually level 5. Worked in: Repo assistant.');
  assert.ok(low > 0 && high > low, text);
});

test('the shapes text carries what moves a job lower or higher, and other fields with the same shape', () => {
  const text = toMarkdown('S', shapesBlocks(fixtureShapes, abs));
  assert.ok(text.indexOf('## Turn one text into another') < text.indexOf('## Carry out a task'));
  assert.match(text, /\*\*Lower when\.\*\* The steps can be written down\./);
  assert.match(text, /\*\*Higher when\.\*\* The parts are independent\./);
  assert.match(text, /\*\*The same shape in other fields\.\*\* Fix a failing test\. Bring up a new board\./);
  assert.match(text, /\[Repo assistant\]\(https:\/\/example\.org\/site\/recipes\/repo-assistant\.md\) \(engineering\)/);
  assert.match(text, /take its reasoning and leave its subject/);
  assert.match(text, /\*\*Worked examples\.\*\* None yet\. Compose the answer from the techniques above\./);
});

test('an answer built by analogy has to say so', () => {
  assert.match(guideText(), /an answer built by analogy from general pages should not read as though the site had covered their case/);
});

test('the guide carries live counts and the registry date, not typed ones', () => {
  const text = toMarkdown('T', agentGuide(input({ counts: { techniques: 7, recipes: 3, teardowns: 1, names: 9, milestones: 2, terms: 4 }, namesAsOf: '2030-01-02' })));
  assert.match(text, /7 technique pages, 3 recipes/);
  assert.match(text, /last checked on 2030-01-02/);
});

test('levels are listed lowest first whatever order they arrive in', () => {
  const text = guideText();
  assert.ok(text.indexOf('Level 0, No model') < text.indexOf('Level 1, One call'));
  assert.ok(text.indexOf('Level 1, One call') < text.indexOf('Level 5, Agents'));
});

test('every published file is absolute, unique, and the guide lists all of them', () => {
  const files = agentFiles(abs);
  assert.equal(new Set(files.map((f) => f.path)).size, files.length);
  for (const f of files) {
    assert.ok(f.url.startsWith('https://example.org/site/'), f.url);
    assert.ok(guideText().includes(f.url), `${f.path} is missing from the guide`);
  }
  assert.equal(files[0].path, '/agents.md');
});

test('the worksheet text follows the chain of questions, not the order of the array', () => {
  const text = toMarkdown('W', worksheetBlocks(sheet, levels, abs));
  const rule = text.indexOf('1. Can a rule do it?');
  const one = text.indexOf('2. Is one request enough?');
  const loop = text.indexOf('3. Are the steps unknown in advance?');
  assert.ok(rule > 0 && rule < one && one < loop, text);
});

test('a settling answer names its level and links it; a caution links the pages it relates to', () => {
  const text = toMarkdown('W', worksheetBlocks(sheet, levels, abs));
  assert.match(text, /Settle on level 0, No model \(https:\/\/example\.org\/site\/levels\/0\/\)\. A rule does it\./);
  assert.match(text, /Put a person in the loop\. Read: https:\/\/example\.org\/site\/techniques\/human-in-the-loop\.md/);
  assert.match(text, /\*\*Little\.\*\* No extra caution\./);
  assert.match(text, /If you could write it as if\/then, start there\./);
});

test('a question the chain never reaches is still printed, never dropped', () => {
  const orphaned: AgentWorksheet = { ...sheet, core_questions: [...sheet.core_questions, { id: 'stray', level_tested: 7, prompt: 'Stray?', answers: [] }] };
  assert.match(toMarkdown('W', worksheetBlocks(orphaned, levels, abs)), /4\. Stray\?/);
});

test('inline rendering escapes first, so data can never become markup', () => {
  assert.equal(inlineHtml('a <script>x</script> & "b"'), 'a &lt;script&gt;x&lt;/script&gt; &amp; &quot;b&quot;');
  assert.equal(inlineHtml('**bold** and `code`'), '<strong>bold</strong> and <code>code</code>');
  assert.equal(inlineHtml('[/a.md](https://e.org/a.md): what'), '<a href="https://e.org/a.md">/a.md</a>: what');
  assert.equal(inlineHtml('see (https://e.org/w.md). Next'), 'see (<a href="https://e.org/w.md">https://e.org/w.md</a>). Next');
});

test('Markdown output: headings, numbered and bulleted lists, one blank line between blocks', () => {
  const md = toMarkdown('Title', [{ kind: 'h2', text: 'H' }, { kind: 'p', text: 'P' }, { kind: 'ol', items: ['a', 'b'] }, { kind: 'ul', items: ['c'] }]);
  assert.equal(md, '# Title\n\n## H\n\nP\n\n1. a\n2. b\n\n- c\n');
});

test('the human page renders the same guide the agent is served, from the same function', () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const page = readFileSync(join(here, '..', 'src', 'pages', 'agents.astro'), 'utf8');
  const endpoint = readFileSync(join(here, '..', 'src', 'pages', 'agents.md.ts'), 'utf8');
  assert.match(page, /agentGuide\(guideInput\(Astro\.site\)\)/);
  assert.match(endpoint, /agentGuide\(guideInput\(site\)\)/);
});
