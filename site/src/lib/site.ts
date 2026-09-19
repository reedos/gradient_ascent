// Where the project lives, and the feedback link every page carries. One constant, so a rename
// of the repository is one edit.
export const REPO_URL = 'https://github.com/reedos/gradient_ascent';

/**
 * A link to the feedback form with the page already filled in. GitHub issue forms take a field's
 * `id` as a query parameter, so `page` and `title` arrive prefilled and the reader only has to
 * say what is wrong. See .github/ISSUE_TEMPLATE/feedback.yml for the field ids.
 */
export function feedbackUrl(pageUrl: string, pageTitle: string): string {
  const short = pageTitle.split(' · ')[0].split(' — ')[0].trim();
  const params = new URLSearchParams({ template: 'feedback.yml', title: `Feedback: ${short}`, page: pageUrl });
  return `${REPO_URL}/issues/new?${params.toString()}`;
}
