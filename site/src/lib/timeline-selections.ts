// Editorial labels and explanations for the selected timeline milestones.
// `short` replaces the title on the chart when the title is too long for a lane; `subtitle` adds a
// second line under it; `datePrefix` qualifies the marked date in the note; `evidence` adds a
// line to the note for a date that rests on something other than the milestone's own source.
export interface Selection {
  id?: string;
  title: string;
  short?: string;
  subtitle?: string;
  event: string;
  note: string;
  datePrefix?: string;
  evidence?: { label: string; text: string; url: string };
}

export const selections: Record<number, Selection> = {
  1: { title: 'ChatGPT', event: 'Research preview released', note: 'A recognizable public example of prompting a language model. Earlier products existed; this is a selected milestone, not the invention of prompting.' },
  2: { title: 'Perplexity', event: 'Search-and-answer product launched', evidence: { label: 'Early behavior', text: 'Founder interview describing the first Perplexity Ask', url: 'https://www.cognitiverevolution.ai/in-search-of-truth-w-aravind-srinivas-of-perplexity-ai/' }, note: 'The early Perplexity Ask combined retrieved search results with a generated answer and citations. That is the specific Level 2 pattern illustrated here, not a classification of every later Perplexity feature. Cofounder Aravind Srinivas dates the launch to December 7, 2022 in a retrospective interview; this is founder testimony, not a contemporaneous launch announcement.' },
  3: { id: 'zapier-openai-2022', title: 'OpenAI steps in Zapier', short: 'Zapier + OpenAI', datePrefix: 'Available by', event: 'Archived availability evidence', note: 'A model call inside a workflow whose steps are set in advance. December 9 is an archived-page capture, not a confirmed launch date. Microsoft 365 Copilot remains a related workplace-AI milestone, rather than the defining workflow example.' },
  4: { title: 'ChatGPT plugins', event: 'Limited alpha announced · waitlist', note: 'A visible example of a model choosing a tool. This dates the limited rollout, not broad availability or the first implementation of tool use.' },
  5: { title: 'Operator', event: 'Browser-use agent preview · US Pro', note: 'The agent observes a browser, acts, and decides what to do next. This is a browser-use milestone; agents and autonomous loops existed earlier.' },
  6: { id: 'anthropic-multiagent-research-2025', title: 'Claude Research', subtitle: 'Subagents documented', event: 'Multi-agent architecture documented', note: 'Anthropic explicitly describes a lead agent delegating to parallel subagents on June 13. Research launched on April 15, but that announcement does not establish whether the same architecture was in use then. June is the documentation date, not an asserted deployment date.' },
  7: { title: 'Grok Bot', event: 'Paid beta released', note: 'An example of agents that keep working beyond an interactive session. The product also describes a team of agents: one product can illustrate more than one level.' },
};

// Chart wording for model shifts whose timeline.json title and summary are written for the full
// shifts section, not for the compact chart.
export const shiftLabels: Record<string, { label: string; summary: string }> = {
  'system-one-models': {
    label: 'Typed decision models (Jev)',
    summary: 'TypeSafe introduced Jev in early access on September 15, 2026: a model that returns typed decisions with probabilities rather than generated text. “System One” is TypeSafe’s name for its proposed model category.',
  },
};
