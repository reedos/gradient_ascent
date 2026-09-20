export const dutOverview = {
  overview: 'Imagine your team already has a Python test framework and several past device projects. You need a project for a new device under test (DUT), with different requirements but familiar instruments and conventions. This walkthrough follows a coding agent from reading that context to handing over generated files for a person to review and test.',
  task: 'Use reusable instructions in CLAUDE.md, the new DUT brief, framework documentation, and a suitable reference project to prepare Python tests, configuration, and Markdown documentation.',
  outcome: 'Watch the plan become a scoped implementation, see a missing requirement or proposed helper trigger a decision, and distinguish generated files from evidence that the real measurements work.',
  transfer: 'The reusable pattern is context → proposed work → execution within authority → evidence → handoff. In this team, shared-framework edits, new helpers, and instrument access require separate authorization. Another project can preauthorize routine edits or safe checks. Choose boundaries around ownership, reversibility, and consequences rather than copying every restriction.',
};
