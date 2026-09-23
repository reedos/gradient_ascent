// Where the project lives, and the feedback link every page carries. One constant, so a rename
// of the repository is one edit.
export const REPO_URL = 'https://github.com/reedos/gradient_ascent';

/**
 * Whether search engines may index the site. False while every page is a draft: the site is
 * reachable by link, not yet offered to search. A robots.txt under a project path
 * (/gradient_ascent/robots.txt) is not read by crawlers, which only look at the host root, so
 * the page-level meta tag is what actually does this. Set to true to open the site to search.
 */
export const INDEXABLE = false;

/**
 * The no-account feedback form (a Google Form; responses go to the maintainer's sheet). Its
 * "Page" question takes a prefilled answer through `entry.<id>`; the id comes from the form's own
 * pre-filled link and changes only if that question is deleted and re-added.
 */
export const FEEDBACK_FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLSezLxgDBSuN4o5v6o6B9uAFvKK5BS3r4ZBnGJBZYzLgu-dllg/viewform';
const FEEDBACK_FORM_PAGE_ENTRY = 'entry.1267414112';

/** The feedback form with the page already filled in, so the reader only says what is wrong. */
export function feedbackUrl(pageUrl: string): string {
  const params = new URLSearchParams({ usp: 'pp_url', [FEEDBACK_FORM_PAGE_ENTRY]: pageUrl });
  return `${FEEDBACK_FORM_URL}?${params.toString()}`;
}

/**
 * The same report as a public GitHub issue, for readers who want to discuss it in the open. GitHub
 * issue forms take a field's `id` as a query parameter, so `page` and `title` arrive prefilled.
 * See .github/ISSUE_TEMPLATE/feedback.yml for the field ids.
 */
export function issueUrl(pageUrl: string, pageTitle: string): string {
  const short = pageTitle.split(' · ')[0].split(' — ')[0].trim();
  const params = new URLSearchParams({ template: 'feedback.yml', title: `Feedback: ${short}`, page: pageUrl });
  return `${REPO_URL}/issues/new?${params.toString()}`;
}
