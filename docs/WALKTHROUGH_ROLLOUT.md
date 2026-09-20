# Local walkthrough rollout

This rollout contains 98 authored examples across 58 concepts and guides. Twenty entries offer all three perspectives; specialized entries retain a focused example. Publication authorized by the user; the former learning path has been retired.

## Coverage

- 54 concepts and four cross-cutting guides.
- Dedicated six-stage DUT harness walkthrough retained.
- 57 additional authored cases share a six-stage reader: starting evidence, design choices, action/control, result, review/recovery, and adaptation.
- Each case has a fixed English request, original/changed outcomes, a decision with explanatory feedback, and a downloadable text record.
- Weekly-report examples have an interactive simulated delivery gate: exact content, recipients, and version require approval; edits invalidate approval; repeated delivery of the same version is blocked in this page session.
- This is an in-memory teaching gate, not production authorization, durable idempotency, or a real mail integration.

## Audience coverage

Twenty entries now have everyday, engineering, and business examples. Forty alternate cases add distinct evidence, actions, changed conditions, decisions, and verification limits. The other 38 entries retain one focused case.

Expanded entries: prompt engineering, structured output, context engineering, RAG, memory, prompt chaining, workflow graphs, human approval, function calling, code execution, agent harness, guardrails, observability, briefing, reviewing, delegating, trust, single agent, multimodal, and voice agents.

## What is and is not implemented

All outputs are authored fictional fixtures. Selecting a changed condition reveals a corresponding authored result; it does not call a model. Calculations and source claims are inspectable but arbitrary user code, retrieval services, audio/image inference, training, robot motion, and external transactions do not execute. Voice, multimodal, and robot examples are text representations of observations and controls, not rich media simulators. Full evidence goals in the catalog describe later elaborations and must not be reported as already measured.

Additional perspectives are included only where they change the task and consequences meaningfully. The audience selector supports direct links through the audience query parameter. Switching perspectives remounts the walkthrough, clearing answers, outputs, and approvals; approval never carries between cases. Human-approval examples distinguish simulated external actions from report delivery. Neither executes externally.

## Implementation

- Authored fixtures: `site/src/data/concept-walkthroughs.json` and `site/src/data/walkthrough-perspectives.json`.
- Audience selection and fresh-state boundary: `site/src/components/islands/WalkthroughPerspectives.tsx`.
- Shared catalog: `site/src/lib/walkthrough-catalog.ts`.
- Shared interface: `site/src/components/islands/ConceptWalkthrough.tsx`.
- Shared wrapper and no-JavaScript explanation: `site/src/components/page/ConceptWalkthrough.astro`.
- Approval identity and delivery eligibility: `site/src/lib/walkthrough.ts`.
- Markdown parity: `site/src/lib/walkthrough-markdown.ts`.
- Catalog: `/examples/`, with text and audience filters and direct example links.
- Existing DUT walkthrough remains the engineering selection within the harness page, preserving its more detailed six-stage workflow.

## Verification

Taxonomy coverage and approval invariants have repository unit tests. Local browser verification visits all 57 new examples, traverses original/changed/decision states, checks the report gates, and checks Markdown counterparts. Representative desktop/mobile screenshots, no-JavaScript fallback, and the existing DUT workflow are checked separately. Build, type checking, site tests, and content validation must pass before publication is considered. Release checks run before the authorized publication.

## Reader overviews and depth

Every perspective now opens with an overview, its task, and what to look for. `walkthrough-guides.json` supplies concept-specific assumptions, design tradeoffs, recovery options, and transfer guidance for all 58 entries. These principles complement each audience case’s distinct evidence, actions, outcomes, and decision. They do not add universal approval requirements. The DUT overview explains its particular team policy separately from the reusable harness pattern. Markdown, non-JavaScript content, and case downloads include the expanded guidance.
