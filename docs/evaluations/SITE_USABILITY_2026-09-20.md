# Site usability changes and observation status

Date: 2026-09-20. This is an implementation record, not evidence of improved human performance.

## Shipped changes

- Personalized project briefs and builder requests omit unanswered fields rather than implying their facts are missing from the whole request. Blank templates retain their prompts. Literal supplied text remains intact.
- Builder downloads use `*-request.md` filenames. They explicitly ask the receiving agent to create the final artifact, including AGENTS.md or CLAUDE.md where selected.
- Navigation follows Understand, Explore, Apply, and Reference, with compact mobile disclosure groups and preserved original routes.
- The homepage retains the introduction, entry points, one comparison, and a compact explanation of the framework. Repeated catalogues and invitations are removed.
- Four recognizable examples lead the directory, with input/action/output descriptions. The full catalogue is expandable and opens for search/filter results.
- Technical sections can be expanded; direct section links reveal their containing sections. The DUT walkthrough remains visible, with its supporting implementation material expandable.

## Automated evidence

Browser checks cover desktop/mobile overflow, navigation, catalogue search and no-result behavior, exports preserving photo requirements without contradictory unknown labels, safe request filenames, and deep links into collapsed content. Build, type checks, content validation, and relevant unit tests are run before publication. These checks establish technical behavior, not comprehension or usefulness for newcomers.

## Human observation: pending

No newcomers have been observed for this revision. Do not report a completion rate, satisfaction score, or measured usability improvement.

The public session page is `/usability/`; the downloadable facilitator script and observation sheet are `/usability-session.md`. The owner has been asked whether they can invite newcomers. Do not contact participants without authorization, and do not replace human observations with simulated users.

Observe concept discovery, explanation in the participant’s own words, preparation/export of a useful request, understanding of what is and is not verified, and the next action. Record help and abandonment. Retest with fresh participants after changes.
