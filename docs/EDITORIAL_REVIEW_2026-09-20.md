# Editorial and teaching review — 2026-09-20

## Changes delivered

1. Concept and thread pages have an explicit reading order and local section links. No sequential curriculum was reintroduced. The DUT walkthrough retains its established location and anchor.
2. Prior implementation traces are closed, optional details. Product catalogs move after practical guidance into an optional section. Use it / Build it now explains its purpose. The main guided example is the primary demonstration.
3. All 97 shared walkthrough variants have six inspectable records, with an explicit account of what changed. The separate DUT workflow retains its existing artifacts. These records are authored; they do not represent executed model calls.
4. Six primary examples have custom records: prompting (brief, competing drafts, review); RAG (source packet, claim support, missing evidence); workflows (evidence register, reconciliation, report, uncertain delivery); approval (scope, review packet, audience change); single agent (observations, changing action, qualified finding); evals (per-case judgments, aggregate, release decision, excluded case). Alternate audience cases retain their own evidence and results, using the shared record format; they are not claimed to have equally extensive custom traces.
5. Assumptions, design choices, recovery, and transfer guidance distinguish the reusable principle from local policies. Verification plans are labeled as plans, not completed checks.
6. The review removed blanket “every claim checked” statements and future promises of recorded traces. It corrected the workflow definition (persistence is optional), a booking diagnosis with missing timing evidence, and scenario inputs that did not explicitly provide facts used by the result.
7. Build, type checking, route/source validation, automated tests, and browser checks cover presentation and interactions. The human-reader protocol below remains a separate empirical check.

## Evidence review and limits

All 97 shared case input/result pairs were read for internal support and uncertainty; the existing DUT account was retained against the user's supplied requirements. All 58 overview/assumption/choice/recovery/transfer guides were checked for consistency with the concept boundaries and with the scripted nature of the site. This is an editorial review, not a measurement of model quality.

Primary references consulted for the priority concepts and important distinctions:

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) — predefined workflows versus adaptive action selection; use simpler approaches when sufficient. Its tooling examples are time-dependent, not a permanent architecture standard.
- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) — state, nodes, and transitions.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) — checkpointing is an added capability, not a defining property of every graph.
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — explicit pauses and resumption. The site's version-bound report policy is an illustrative application policy, not a claim that every framework supplies it automatically.
- [Lewis et al., Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401) — retrieval plus generation. The site's warranty passages are fictional and do not come from this paper.
- [Anthropic: Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) — task criteria and evaluation; no universal prompt guarantees.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — task, trial, grader, transcript, and actual outcome are distinct. The four-case table here contains invented judgments, not a benchmark.

This pass does not establish that every external product claim or every historical source quotation across the entire site is current. Existing product verification flags and source dates remain intact; they were not mass-updated. Software test results do not certify factual accuracy. The source/claim inventory is maintained alongside this report so unreviewed external claims are not silently represented as newly verified.

## Unfamiliar-reader protocol — ready, not yet conducted

Recruit readers who have not worked on the site, spanning everyday, engineering, and business contexts. Do not explain the page first. Run a 15–20 minute session, recording assistance and confusion rather than attributing a score to the person.

1. Ask the reader to choose one concept and explain it in their own words after the introduction and example.
2. Ask which parts of the displayed record are supplied evidence, proposed actions, and established outcomes.
3. Ask them to inspect a changed condition and explain why the result should change.
4. Give a different task from their own experience. Ask what carries over and which assumptions or controls should differ.
5. Ask them to find implementation guidance and a primary source without coaching.

Observe navigation mistakes, misread evidence, inappropriate transfer of restrictions, and whether scripted records are mistaken for live computation. Successful navigation alone is not successful learning. Revise the confusing section and repeat with a new reader; do not reuse coached responses as proof of clarity.

No sessions or comprehension scores have been fabricated. External reader testing and a complete re-verification of the product registry remain unperformed work, not implied by the automated release checks.
