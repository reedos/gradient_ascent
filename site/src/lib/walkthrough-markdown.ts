import { examplesFor } from './walkthrough-catalog';
import { audienceLabels } from './walkthrough';
export function walkthroughMarkdown(slug:string):string {
  return examplesFor(slug).map(e=>`\n## Guided worked example · ${audienceLabels[e.audience]}\n\nFictional scripted fixture, not a measured run. No model or external actions execute.\n\n**Request:** ${e.prompt}\n\n**Starting evidence:** ${e.inputs}\n\n**Action and control:** ${e.action}\n\n**Sample result:** ${e.outcome}\n\n**Change something — ${e.change}:** ${e.changedOutcome}\n\n**Decision:** ${e.question}\n\n**Answer:** ${e.correct}\n\n**Why:** ${e.explanation}\n\n**Review criteria:** ${e.verify}\n`).join('\n');
}
