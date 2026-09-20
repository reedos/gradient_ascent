export interface WalkthroughGuide {
  overview: string; assumptions: string; choices: string; recovery: string; transfer: string;
}
export interface WalkthroughCase {
  artifacts: {name:string;body:string;change:string}[];
  guide: WalkthroughGuide;
  slug: string; title: string; group: string; definition: string; audience: string;
  prompt: string; inputs: string; action: string; outcome: string; change: string;
  changedOutcome: string; question: string; correct: string; wrong: string;
  explanation: string; verify: string; approval: boolean;
  approvalDraft?: string; approvalKind?: string; approvalScope?: string;
}
export const audienceLabels: Record<string,string> = {
  everyday: 'Everyday life', engineering: 'Engineering & technical work', business: 'Business & team operations',
};
export function approvalKey(version: number, draft: string, recipients: string) {
  return JSON.stringify({version, draft, recipients});
}
export function canDeliver(key: string, approved: string | null, sent: string[]) {
  return key === approved && !sent.includes(key);
}
