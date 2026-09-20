# Site usefulness and navigation audit — September 20, 2026

## Scope and evidence

Review of local navigation, homepage, brief builder, search generation, model guide, and Markdown routes. This is an expert review plus implementation checks, not a measured usability study or broad certification of factual accuracy. The user supplied one external-model planning test; it improved after brief changes but does not establish consistency across models.

## Findings and changes

| Priority | Finding | Response |
|---|---|---|
| High | Header prioritizes “Find your level” while the primary task is applying concepts to a user's work. | Desktop and mobile CTA now “Start your project,” linked to the brief builder. Worksheet stays available as a secondary exploratory aid. |
| High | Brief builder absent from site search. | Index the project brief, tools hub, and each artifact builder. |
| High | Visitors face a large taxonomy without a clear starting decision. | Add three early homepage entries: understand a concept, see an example, apply to your work. No requirement to finish the taxonomy first. |
| High | New practical tools need a discoverable home and model-readable entry point. | Tools hub, “Tools & examples” navigation, six builders, Markdown twins, and tools.md directory linked from agents.md and llms.txt. |
| Medium | Old lowest-level phrasing survives in some navigation and guide copy. | Correct active entry points to describe desired outcomes and human effort. Taxonomy levels remain descriptions of autonomy, not a quality ranking. |
| Medium | Visitors may confuse generated text with enforced permissions or a finished system. | Builders label output as drafts, preserve unknowns, require verification, and distinguish instructions from execution controls. |
| Medium | After copying a brief there is little indication of the next step. | Link to appropriate optional builders and explain how to hand drafts and examples to the user's model. |

## Honest assessment

The site offers practical value as a concept reference plus a way to prepare a better conversation with a user's own model. It is not a proven recommender, a hosted agent platform, or a guarantee of working implementations. Readers can start with examples or a brief before mastering the taxonomy. The tools are especially useful when someone knows their task but needs to express working rules, workflow boundaries, or success criteria.

A browsing-capable agent can fetch agents.md, llms.txt, tools.md, and individual concept/template Markdown routes. Direct links and downloads provide a fallback. Fetch availability and model compliance vary; never imply every model automatically discovers the site or reads all references.

## Remaining issues and next validation

- Search-engine indexing remains intentionally disabled through INDEXABLE=false. This limits organic discovery; changing publication/indexing policy requires an explicit decision.
- The header still exposes both Levels and Techniques. That is useful for reference browsing but may overlap for newcomers. Test before a larger information-architecture rewrite.
- Ask unfamiliar readers to locate a concept, inspect one example, choose the correct builder, export a draft, and identify the next step. Record confusion and time, not just whether links work.
- Repeat brief/template trials with different models and tasks. Evaluate hidden manual labor, unsupported assumptions, accurate use of references, and whether the user can act on the resulting plan.
- Product documentation and generated implementation advice still require ongoing review. Structural tests do not establish factual completeness or artistic/engineering correctness.
