# Gradient Ascent — resource quality update

Prepared as an isolated prototype on September 20, 2026, based on commit `3043640`. Revised and approved for publication on September 21. The separate Labs section was removed after review; practical examples now live within Recipes.

## Assessment

The existing site has substantial breadth, useful cross-links, and an explicit distinction between authored demonstrations and measured results. Its biggest educational gaps were generic diagrams that omitted control boundaries, too much prose before practical evidence, and a weak transition from scripted examples to an executable project.

The prototype improves those foundations. It does **not** establish that this is the best or most current resource in its class. That would need broader source verification, comparison against alternatives, repeated model evaluations, and testing with actual readers.

## Complete change list

1. **Seven new architecture diagrams:** RAG, knowledge graphs, single agents, the agent harness, agentic RAG, human approval, and always-on assistants. Edges have explicit meanings; completion, refusal, feedback, and idle states appear where appropriate. Source relationships are distinguished from execution transitions.
2. **Responsive diagram rendering:** desktop SVGs use readable cards, wrapped descriptions, model highlighting, nearby legends, accessible descriptions, and optional design notes. Phone views expose every connection as labeled outgoing references between lettered cards, rather than shrinking a wide graph.
3. **Shared diagram improvements:** wrapped detail text, stronger headings, consistent framing, and expandable text versions of connections for the remaining conceptual diagrams. Their underlying generic topologies have not all been redesigned.
4. **Three new visual thread comparisons:** context/memory/checkpoints; proposal/authorization/execution; record validation/outcome evaluation/tracing.
5. **Four rewritten thread explanations:** graph engineering, what the model sees, who approves what, and checking the work. Shorter sections and compact comparison tables preserve the important distinctions.
6. **Technical corrections:** graphs do require advance design even when routing is dynamic; checkpointing is not inherent to every graph; memory selection is not exclusive to level 7; a separate reviewer does not guarantee independent errors; agents can retain per-action human gates; evaluations can grade individual runs and use code, human, or model graders.
7. **Three technique-page corrections:** agent-graph definitions no longer promise automatic checkpointing; always-on assistants do not require a dedicated computer or model call on every tick; evaluation descriptions no longer offer only exact-match or model-based grading.
8. **New eight-part design guide:** context/retrieval/memory, workflow versus agent, reasoning effort, one versus multiple agents, output structure versus correctness, tools and authority, persistence, and evaluation. Each topic includes a practical starting point, nuance, measures, and a primary-source link.
9. **Six practical examples inside existing Recipes:** a warranty evidence answer, invoice extraction, weekly status workflow, exact-proposal approval gate, bounded incident agent, and durable stock monitor. Each has a copyable chat brief with synthetic records and review criteria. Reference answers, design steps, failure cases, adaptation guidance, and implementation limits remain expandable. Examples attach to document Q&A, invoice matching, weekly status, assistant teams, incident runbooks, and nightly monitoring; their relationship to each larger recipe is stated explicitly.
10. **Six optional downloadable starter kits:** each includes the shared Python runner and tests, all editable cases, plus the selected task brief, source records, reference answer, and README. Python standard library only; no package installation. Each archive is generated from the same source data the website renders.
11. **Working runtime behavior:** lexical retrieval, citation membership checks, arithmetic validation, a two-call workflow with validated handoff, an approval simulation bound to payload/version/expiry, a six-call allowlisted agent loop, and a durable SQLite outbox with event deduplication.
12. **Own-model support:** Ollama uses native JSON schemas; a compatible Chat Completions adapter uses JSON instructions plus post-generation validation. Explicit model selection, bounded output, per-request timeout, response-size limit, and refusal to forward credentials through redirects. Provider compatibility is not universal.
13. **Boundary tests:** failures cover unsupported citations, invalid totals, invented due dates, incomplete workflow handoffs, changed/expired/stale approvals, duplicate receipts, forbidden tools, unread citations, exhausted call budgets, durable restart behavior, and failed generation. Local HTTP fixtures exercise both API adapters.
14. **Shared walkthrough readability:** removed the pretend “Send request” gate and typewriter animation. The first record is immediately readable; every stage can be selected directly. Existing alternate scenarios and approval exercises remain.
15. **Connected discovery:** search and concept-page links lead into the existing recipes. Removed the separate Labs destination, navigation item, and homepage promotion. Recipe Markdown exports include the practical material. The primary action copies a complete brief and sample inputs; Python downloads and setup are optional, collapsed details.
16. **Review and provenance:** a private prototype banner and review hub supported approval; both are removed from the public build. Retained the complete change log, reproducible smoke-test script, and downloadable records of successful and rejected local-model trials. README language now scopes the new observed runs separately from legacy scripted content.
17. **Repository integration checks:** integrated practical examples into recipe Markdown exports and registered the new runner with the evaluation harness’s explicit not-scored list. Added exact allowances for reserved-domain synthetic email fixtures. Corrected the timeline’s aggregate `as_of` date to match its already-recorded September 20 source check; no milestone assignment or date was changed.

## Final implementation validation

- Static build: passed, 139 HTML pages after folding the examples into Recipes and removing the private review page.
- Astro/TypeScript: zero errors and warnings; 47 informational hints remain.
- Site tests: 264 passed (259 existing plus five prototype checks).
- New example tests: 16 passed, including local HTTP transport tests for both adapters.
- Content validator: passed; checks include 49 techniques, 34 recipes, 223 registry entries, 106 glossary terms, and 97 timeline markers.
- All six generated ZIPs were fetched through the Tailscale preview, byte-compared to the build, extracted, and run in offline replay. The test suite also passed from an extracted kit.
- Internal route tests found no broken built-page links after packaging. The practical material is included in recipe Markdown twins; the seven custom architecture descriptions are included in their technique Markdown exports.
- Browser checks at desktop and 390-pixel phone widths found no horizontal overflow on the checked RAG/agent and practical-lab layouts. Checked disclosure behavior and confirmed that heading text did not acquire glossary buttons.
- Full legacy Python suite: 1,846 tests; **eight failures and one error remain**, all also present in the baseline. The baseline had nine failures and one error. The aggregate timeline-date correction resolves one; remaining failures concern old timeline-markup expectations, two pre-existing missing Markdown twins (`chatbot-to-agent` and `usability`), and pre-existing synthetic-email fixture flags. This is not an all-green legacy suite.

The test results establish implementation behavior, not a universal model-quality or educational-effectiveness score.

## Practical implementation boundaries

| Example | What runs | What is deliberately absent |
|---|---|---|
| Warranty answer | Word-overlap retrieval, model generation, source-ID checks | Vector database, access service, document parser, automatic entailment grade |
| Invoice | Extraction, integer-cent arithmetic, selected field checks | OCR, payment, full accounting validation |
| Weekly report | Extract → validate → draft; checked table preserved | Ticket connector, delivery, automatic semantic truth judgment |
| Approval | Proposal validation, digest, version/expiry checks, duplicate local receipts | Authenticated reviewer, durable approval service, calendar action |
| Incident agent | A real model-directed loop over three synthetic read-only tools | Production access, shell, repair actions, total monetary budget |
| Durable monitor | One event per invocation, SQLite deduplication and pending outbox | Scheduler, real delivery, worker leases, external exactly-once guarantee |

The durable monitor is a scheduled model-assisted workflow illustrating a capability used by always-on agents. It is not mislabeled as a complete autonomous agent. The incident example is a real decision loop with a synthetic environment. The approval gate is a local simulation. These distinctions are visible in the recipe examples.

## What the local-model trials revealed

The installed Ollama model `muse-glimmer:30b-q4_K_M-dflash` was called with synthetic data only. Records include timestamps, available usage counts, timings, returned structured objects on later trials, and prompt/runner hashes where recorded. This is a development smoke test, not a comparative benchmark.

- Plain JSON mode sometimes returned empty or incomplete records. Required-field validation rejected them.
- Native schemas improved shape control. They did not prevent a semantically useless status table containing placeholders; source-coverage validation rejected that output.
- A more explicit extraction-stage brief produced a complete status table and a separate summary. It preserved missing owners, blockers, and a proposed date as tentative.
- Every example eventually completed its intended local-model path. This is an existence check after development, **not a 100% success-rate claim**. Earlier failures remain in the records.
- The warranty response selected the applicable policy, preserved both invalidating conditions, and excluded accidental damage. The invoice preserved the stated $550 total while computing $540 and routing the mismatch to review.
- Agent traces showed allowed read-only observations followed by a handoff. A model’s plausible incident hypothesis is still not proof of root cause.

There was no live calendar, email, payment, production action, or external delivery. The compatible API transport was tested against a local HTTP fixture, not a paid hosted provider.

## Source-check scope

The new explanations were checked against primary references including the [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [effective agents](https://www.anthropic.com/engineering/building-effective-agents), [multi-agent research](https://www.anthropic.com/engineering/multi-agent-research-system), [long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [agent evaluations](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), the [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [Ollama chat](https://docs.ollama.com/api/chat), [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking), and the [RAG paper](https://arxiv.org/abs/2005.11401).

These references support mechanisms and implementation choices. They do not certify the whole site, prove every diagram is optimal, or independently validate the site’s editorial level system.

## Remaining work before a world-class claim

- Reverify the complete named-product registry and model capability index against current primary sources. This prototype does not refresh their dates to imply that happened.
- Test multiple model families with repeated, held-out cases, including retrieval misses, conflicting sources, attacks, malformed tools, interruptions, and negative examples.
- Expand runnable coverage beyond these six examples and deepen domain-specific examples, especially hardware, multi-agent coordination, and richer retrieval.
- Replace remaining generic diagrams where concrete architecture would teach more. The new diagram language is a proposed direction for review, not a declaration that every visual is finished.
- Observe newcomers and experienced builders using the material. Measure comprehension and successful adaptation; review accessibility with assistive-technology users.
- Review legacy long recipes and examples individually. Their code remains available, but this pass has not rewritten every recipe or verified every runnable backend path.

## Review suggestions

Start with the RAG diagram, the incident companion example, the scheduling approval example, and the design-decision guide. Compare phone and desktop. The useful review questions are whether the diagrams explain control clearly, whether the examples feel directly useful, and whether the optional detail is in the right place.

The homepage map, timeline milestones, capability chart, and branding retain their existing design. Publication includes the approved diagrams, explanations, recipe examples, and design guide; it excludes the private review banner and review-only page.
