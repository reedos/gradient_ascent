# Worked-example proposals for Gradient Ascent

Status: release rollout. The DUT harness has its dedicated walkthrough; the other 57 entries have authored, scripted walkthroughs. Forty alternate cases now bring 20 entries to all three audience perspectives, for 98 examples total. The public catalog exposes each available perspective with a direct link. The examples below remain the broader design targets, not claims that all proposed rich media, tools, or measured evidence have been implemented. No model runs or external actions execute in these fixtures. Coverage: all 54 concepts in the taxonomy plus its four cross-cutting guides. Definitions are editorial summaries of the existing concept boundaries, not new product capability claims.

## Shared teaching contract

Every buildout should provide: (1) a concrete English request and visible inputs, (2) a compact diagram synchronized to visible work, (3) an explanation of who decided and why, (4) an inspectable artifact or evidence record, (5) a controlled change with a contrasting outcome, and (6) a transfer decision with explanatory feedback. Start with deterministic simulations; visibly separate scripted outputs, actual executed checks, and future recorded model runs. Never display fabricated measurements as real results or model reasoning as an observed hidden trace.

Each scenario needs an explicit authority boundary, unknown/error case, stop or fallback behavior, acceptance criteria, and an account of what the evidence does not prove. Support keyboard navigation, touch, reduced motion, a reveal-all option for streamed text, and a readable noninteractive explanation. For concepts without agent actions, use the relevant review or validity boundary instead of inventing an approval gate.

Use recurring scenario families where comparison matters: warranty support for retrieval and investigation; workshop planning for communication and judgment; support classification for model adaptation; service operations for deployment. Other examples introduce software, instruments, voice, and robotics without implying these require the same controls or validation methods.

## Suggested build order

1. Review the integrated DUT harness walkthrough and settle the interaction pattern.
2. Build chat, prompting, structured output, context, search, and RAG as the foundation; include the no-model baseline.
3. Add workflows, approval, tools, the agent loop, and coding with concrete failure cases.
4. Add teams and persistent agents after learners can distinguish control flow, authority, and evidence.
5. Develop evaluation and safety alongside each stage; treat training and robotics as separate extensions with clearly labeled limits.

This is a teaching sequence, not a claim that more autonomy is better. Each example should identify when a simpler approach is sufficient.

## Featured scenario: weekly project status reports

**Goal:** Prepare this week's report across several projects using previous reports and current evidence, then distribute only the exact version and recipient list a human approves.

**English request:** “Prepare this week's status report for our active projects. Use last week's report for continuity and our project tracker, milestone sheet, and meeting notes for current updates. Cite the evidence for changes, flag missing or conflicting information, and give me a draft to review. Do not send it until I approve the final content and recipients.”

**Visible workflow:** Scheduled trigger or manual request → collect authorized sources in parallel → reconcile evidence → draft project sections → assemble and compare with last week → human review → approved-version send → delivery record.

**What the learner sees:** The reporting period and timezone, source freshness and permissions, last week's report, current evidence cards per project, supported changes and unresolved questions, a report diff, recipient list, approval record, and a simulated send receipt. Each project section includes overall status with supporting criteria, completed work, next steps, blockers, owner, and upcoming milestones when those fields are actually available.

**Evidence rules:** Use prior reports for structure and previously reported commitments. Do not treat their contents as evidence that work remains on track today. Link current claims to sources with dates. Establish field-specific source precedence with the team; do not invent a universal “tracker always wins” rule. Preserve conflicts for review. “No new update found” is not “no progress” or “on track.” Do not convert meeting speculation into a committed milestone.

**Authority:** Collection is limited to authorized sources and project scope. Do not update the underlying tracker merely to make the report consistent. Approval binds the report version, reporting period, and recipients. An edit or changed recipient list returns the draft to review. Rejection and silence leave it unsent. Delivery retries require an idempotency key or an equivalent sent-record check so one approved report is not distributed twice.

**Change-something cases:** A source is unavailable; an old report contradicts a current milestone; one project has no fresh evidence; a private issue must be excluded for the selected audience; the reviewer edits an approved draft; a send request times out after possible acceptance. Show how each changes the state and what the system can honestly report.

**Learner decision:** “A project has no fresh update, but last week's report says green. Should this week's report automatically remain green?” Explain why the correct response is to preserve uncertainty and request review rather than silently assert a current status.

**Checks:** Coverage of all requested projects; claim-to-source fidelity; freshness and conflict handling; audience-appropriate disclosure; no send without version-specific approval; no duplicate send on retry. A model can help draft, but deterministic checks should enforce structural fields and the delivery gate. Report quality still needs human judgment.

**Concept links:** Prompt chaining defines fixed stages; parallel calls handle independent projects; context selects relevant prior and current material; retrieval supplies evidence; workflow graphs track transitions and retries; human approval controls distribution; observability records provenance and decisions; evaluation checks accuracy and coverage. An always-on assistant can initiate the scheduled run. Agentic retrieval is an optional extension only if the model needs to choose follow-up investigations; a fixed reporting pipeline does not require it.

**Simulation boundary:** The initial build would use fictional reports, trackers, and notes. Collection, proposed drafting, approval, and delivery would be deterministic demonstrations. No actual connectors, recipients, or email sends are authorized by this proposal. Real sources and measured model runs are a later implementation decision.

## Complete catalog

## Level 00 · No model

### 1. When not to use a model

**Definition:** Solving a task with explicit rules, forms, search, or conventional software when generative output is unnecessary.

**Proposed worked example:** Validate an expense claim against a published reimbursement policy using a form and deterministic rules.

**Nuance and contrasting case:** Compare an exact allowance calculation with an ambiguous business-purpose description; only the latter may need interpretation.

**Visible evidence and assessment:** Boundary-value tests and an explicit needs-review result for ambiguous cases; compare with a scripted model mistake.

## Level 01 · One call

### 2. Chat

**Definition:** A conversational interface in which a person supplies messages and decides what to do with the replies.

**Proposed worked example:** Ask for help drafting an invitation to a neighborhood repair workshop.

**Nuance and contrasting case:** Contrast a useful draft with an invented venue detail; the conversation has no implicit access to your calendar or facts.

**Visible evidence and assessment:** A checked facts list and a revised draft grounded in information the user actually provided.

### 3. Prompt engineering

**Definition:** Designing instructions, examples, and output expectations to steer a model's response.

**Proposed worked example:** Turn a vague request for a workshop announcement into a brief with audience, facts, tone, and length.

**Nuance and contrasting case:** Change one instruction at a time; stronger wording cannot supply absent facts or guarantee compliance.

**Visible evidence and assessment:** A rubric comparing factual fidelity, audience fit, and constraints across clearly labeled sample outputs.

### 4. Structured output

**Definition:** Constraining an answer to a defined data structure so software can validate and consume it.

**Proposed worked example:** Extract an event date, venue, and accessibility information from an organizer's email into a registration form.

**Nuance and contrasting case:** A valid structure may contain wrong facts; missing values need an explicit unknown state instead of invention.

**Visible evidence and assessment:** Show the friendly form first, optional JSON second, schema validation, and field-by-field source evidence.

### 5. Reasoning at answer time

**Definition:** Allocating additional inference computation to work through a problem before returning an answer.

**Proposed worked example:** Schedule workshop sessions around room, trainer, and equipment constraints.

**Nuance and contrasting case:** More computation does not ensure correctness; do not present invented hidden reasoning as a real model trace.

**Visible evidence and assessment:** An observable candidate schedule, constraint checker, counterexample, and labeled illustrative cost/quality comparison.

### 6. Images, audio and video

**Definition:** Working with inputs or outputs across text, images, audio, or video.

**Proposed worked example:** Create an equipment intake record from a label photo and a technician's voice note.

**Nuance and contrasting case:** Blur a serial number and introduce disagreement between image and audio; ask for confirmation instead of asserting certainty.

**Visible evidence and assessment:** Highlighted source regions, transcript excerpts, uncertain fields, and a corrected intake record.

## Level 02 · Context

### 7. Context engineering

**Definition:** Selecting and arranging the instructions, reference material, and history included in each model request.

**Proposed worked example:** Prepare a support reply using the current product manual, customer question, and relevant case history.

**Nuance and contrasting case:** Compare a relevant excerpt with a stale manual and distracting history; context size is not context quality.

**Visible evidence and assessment:** A visible request-context tray, version labels, included/excluded evidence, and answer differences.

### 8. Embeddings and search

**Definition:** Representing content numerically and retrieving similar items, often combined with keyword or metadata search.

**Proposed worked example:** Find the right troubleshooting article for a customer who says the machine makes a knocking sound.

**Nuance and contrasting case:** Contrast semantic similarity with an exact model-number lookup; a similar passage may refer to the wrong product.

**Visible evidence and assessment:** Ranked snippets, model filters, relevance judgments, and a case where hybrid search is preferable.

### 9. Retrieval-augmented generation (RAG)

**Definition:** Retrieving external information and placing it in the model's context to support an answer.

**Proposed worked example:** Answer an appliance warranty question from a small versioned document collection.

**Nuance and contrasting case:** Include a missing exclusion clause and conflicting revisions; retrieval and generation can fail separately.

**Visible evidence and assessment:** Visible query, retrieved passages, grounded answer, source links, and an abstention when evidence is insufficient.

### 10. Knowledge graphs and GraphRAG

**Definition:** Representing entities and relationships explicitly; GraphRAG uses graph-based retrieval or summaries to support generation.

**Proposed worked example:** Trace which shipped products depend on a recalled supplier component across purchase and assembly records.

**Nuance and contrasting case:** Contrast an ordinary document search with a multi-hop dependency question; uncertain or missing edges must remain visible.

**Visible evidence and assessment:** A provenance-linked path from supplier to lot to product, a missing-edge case, and a checked affected-product list.

### 11. Memory

**Definition:** Persisting selected information across interactions and retrieving it when relevant.

**Proposed worked example:** A workshop planning assistant remembers the user's preferred meeting times between sessions.

**Nuance and contrasting case:** Separate an explicit preference from a one-time exception; stale memories must be editable or deletable.

**Visible evidence and assessment:** A memory card with origin, update, removal, and a new-session test showing what was actually loaded.

## Level 03 · Workflows

### 12. Prompt chaining

**Definition:** Running model calls in a predetermined sequence where one step's output feeds the next.

**Proposed worked example:** Draft a weekly portfolio status report through fixed stages: collect current evidence, reconcile it, build project summaries, then assemble the report.

**Nuance and contrasting case:** An extraction error can become a polished false claim downstream; previous reports supply continuity, not proof of current status.

**Visible evidence and assessment:** A source-linked evidence sheet, intermediate project summaries, report diff, and a corrected unsupported claim.

### 13. Routing

**Definition:** Selecting a handler or workflow based on an input's category, rules, or classification.

**Proposed worked example:** Send incoming support messages to billing, troubleshooting, or a human escalation queue.

**Nuance and contrasting case:** Mixed intent and low confidence require explicit handling; a route choice does not resolve the underlying issue.

**Visible evidence and assessment:** A routing decision, confidence limitation, mixed-intent case, and a confusion matrix on labeled sample messages.

### 14. Parallel calls

**Definition:** Running independent tasks concurrently and combining their outputs.

**Proposed worked example:** Collect and summarize current status for several projects independently before composing one weekly portfolio report.

**Nuance and contrasting case:** Project-specific work can run concurrently, but stale sources and inconsistent milestone dates require reconciliation before aggregation.

**Visible evidence and assessment:** Per-project evidence cards, timestamps, conflicting-source flags, and a combined report with no invented update for silent projects.

### 15. Write and check

**Definition:** Iterating between generating a candidate and evaluating it against criteria until it passes or a limit stops the loop.

**Proposed worked example:** Revise an onboarding article against a factual and readability checklist.

**Nuance and contrasting case:** A reviewer can miss errors or reward superficial fixes; repeated polishing may never converge.

**Visible evidence and assessment:** Draft diffs, criterion-level feedback, a maximum-attempt stop, and an independent source check.

### 16. Workflow graphs

**Definition:** Representing a predetermined process as steps, transitions, branches, and persistent state.

**Proposed worked example:** Generate a weekly multi-project status report from prior reports and current trackers, notes, and milestones, then route the draft for human review.

**Nuance and contrasting case:** Missing data, connector failures, edits after approval, and send retries need separate states; a scheduled fixed workflow is not automatically an autonomous agent.

**Visible evidence and assessment:** A collection-to-review state graph, evidence links, unresolved-items queue, version-bound approval, and simulated duplicate-safe delivery.

### 17. Human approval

**Definition:** Pausing a process for a person's scoped approval, correction, or decision.

**Proposed worked example:** Review and approve the exact weekly status report and recipient list before the application sends it.

**Nuance and contrasting case:** Reject or edit the draft; any change to approved content or recipients requires renewed approval. No response means no send.

**Visible evidence and assessment:** A previous-versus-current diff, evidence inspection, approve/edit/reject decisions, and a clearly simulated delivery record.

## Level 04 · Tools

### 18. Function calling

**Definition:** A model proposing a named tool and structured arguments that application code validates and executes.

**Proposed worked example:** Ask an assistant to check stock and prepare a reservation for replacement parts.

**Nuance and contrasting case:** A tool call is a proposal, not authorization; handle invalid arguments, absent stock, and tool failure.

**Visible evidence and assessment:** English request, optional argument view, validation result, read-only lookup, and a separately approved reservation.

### 19. Code execution

**Definition:** Running generated code in a constrained environment to perform computation or transform data.

**Proposed worked example:** Analyze a CSV of energy readings and produce daily totals and a chart.

**Nuance and contrasting case:** Malformed timestamps, missing rows, and unit mismatches affect results; a sandbox bounds access but does not ensure correct math.

**Visible evidence and assessment:** Input preview, inspectable Python, deterministic totals, a planted unit error, and denied file/network access in a mock boundary demonstration.

### 20. Model Context Protocol

**Definition:** A protocol for exposing tools, resources, and other capabilities to compatible AI applications.

**Proposed worked example:** Connect an assistant to a mock inventory service and an internal manual resource.

**Nuance and contrasting case:** Discovery is not permission; tool descriptions can be misleading and services can be unavailable.

**Visible evidence and assessment:** Capability discovery, a tool request/result, access refusal, and an outage, clearly separated from transport details.

### 21. Computer and browser use

**Definition:** An agent observing and interacting with a graphical interface through actions such as clicks and typing.

**Proposed worked example:** Complete a mock equipment return form in a browser portal with no API.

**Nuance and contrasting case:** A layout change or stale screen can invalidate a click; submission requires a final review.

**Visible evidence and assessment:** Screen/action/result sequence, mistaken-field recovery, and a simulated confirmation with no external transaction.

## Level 05 · Agents

### 22. Single agent

**Definition:** A model choosing successive actions and when to stop within a tool-enabled loop.

**Proposed worked example:** Investigate why a room-booking request failed using policy and availability tools.

**Nuance and contrasting case:** Distinguish model-chosen next actions from a fixed chain; stop on insufficient evidence or a step cap.

**Visible evidence and assessment:** Tool observations, changing next-step choices, a supported answer, and a bounded unsuccessful run.

### 23. The agent harness

**Definition:** The runtime around an agent's model that manages tools, context, execution boundaries, approvals, limits, and records.

**Proposed worked example:** Generate a new DUT project using the shared Python test framework and the approved workflow.

**Nuance and contrasting case:** Preserve separate approval for helpers and framework edits; no agent-operated instruments; syntax checks are not hardware validation.

**Visible evidence and assessment:** The integrated DUT walkthrough, approved plan, file list, evidence/status record, missing-requirement case, and approval exercise.

### 24. Agentic RAG and deep research

**Definition:** Retrieval where an agent chooses follow-up searches and reads until it can answer or must stop.

**Proposed worked example:** Investigate the same appliance warranty question when exclusions are split across documents.

**Nuance and contrasting case:** Compare against one-pass RAG on the same evidence; repeated search can still miss facts or exceed its budget.

**Visible evidence and assessment:** Search trajectory, evidence accumulated per step, citations, conflicts, and a stop/abstain case.

### 25. Coding agents

**Definition:** Agents that inspect, edit, execute, and test code to complete a software task.

**Proposed worked example:** Fix a date-filter bug in a small event-registration application.

**Nuance and contrasting case:** A passing test can miss regressions; keep edits scoped and distinguish simulated test logs from actually executed tests.

**Visible evidence and assessment:** A reproducible failing case, reviewed patch, deterministic tests, edge-case regression, and change summary.

### 26. Skills

**Definition:** Reusable task instructions and supporting resources loaded when an agent needs a particular procedure.

**Proposed worked example:** Produce a release note using an organization's writing and verification procedure.

**Nuance and contrasting case:** A skill provides guidance rather than new permissions or guaranteed correctness; stale instructions can conflict with current policy.

**Visible evidence and assessment:** Selected skill, loaded resources, draft release note, verification checklist, and outdated-skill handling.

### 27. Voice agents

**Definition:** Agents that conduct spoken interactions while handling audio, timing, interruptions, and tool use.

**Proposed worked example:** Book a workshop place in a simulated spoken conversation.

**Nuance and contrasting case:** Handle interruptions, an ambiguous date, and a misunderstood name; confirm before committing the booking.

**Visible evidence and assessment:** Transcript/audio controls, turn state, correction, scoped confirmation, and a clearly simulated booking result.

## Level 06 · Teams of agents

### 28. Lead agent and workers

**Definition:** A lead agent delegating bounded subtasks to workers and combining their results.

**Proposed worked example:** Prepare a venue comparison by assigning cost, transport, and accessibility research to separate workers.

**Nuance and contrasting case:** Workers may duplicate work or return incompatible assumptions; delegation must have clear scope and evidence.

**Visible evidence and assessment:** Task briefs, worker findings with sources, conflict resolution, and a consolidated recommendation without automatic purchase.

### 29. Agent graphs

**Definition:** Representing agent roles and the permitted handoffs or transitions between them.

**Proposed worked example:** Triage a mock service incident through investigator, remediation planner, and reviewer roles.

**Nuance and contrasting case:** A handoff carries state and authority boundaries; prevent endless cycles and uncontrolled privilege transfer.

**Visible evidence and assessment:** Role graph, handoff packet, reviewer rejection, bounded retry, and a human-approved remediation plan.

### 30. Review and debate

**Definition:** Using multiple model perspectives to critique or compare candidate answers before a decision.

**Proposed worked example:** Review two proposed data-retention policies for a fictional application against stated requirements.

**Nuance and contrasting case:** Agreement is not independent evidence; reviewers can share errors or favor persuasive wording.

**Visible evidence and assessment:** Claims linked to the supplied requirements, disagreements, adjudication, and a planted error both reviewers initially miss.

## Level 07 · Always-on agents

### 31. Long-running tasks

**Definition:** Maintaining progress, state, and limits across an extended task or multiple sessions.

**Proposed worked example:** Migrate a fictional documentation site in batches with checkpoints.

**Nuance and contrasting case:** A restart must preserve completed work and constraints; summaries can omit crucial decisions.

**Visible evidence and assessment:** Task ledger, checkpoint, interrupted/resumed batch, stale-context case, and a budget-based partial handoff.

### 32. Always-on assistants

**Definition:** Persistent assistants that act on configured triggers within ongoing responsibilities and permissions.

**Proposed worked example:** Prepare a weekly status-report draft on a schedule across active projects, then notify the responsible reviewer.

**Nuance and contrasting case:** A trigger authorizes collection and drafting, not automatic distribution; handle time zones, missed runs, access limits, and duplicate drafts.

**Visible evidence and assessment:** A simulated weekly trigger, run identifier, per-source collection record, waiting-for-review state, and one delivery only after explicit approval.

### 33. Organizations of agents

**Definition:** Coordinating many agents with distinct responsibilities, shared resources, and organizational constraints.

**Proposed worked example:** Run a simulated product-launch preparation across research, documentation, support, and review teams.

**Nuance and contrasting case:** More agents increase coordination costs and can spread bad assumptions; compare a smaller team baseline.

**Visible evidence and assessment:** Dependency board, ownership, conflicting updates, shared budget, escalation, and an evidence-based launch readiness report.

### 34. Robots and machines

**Definition:** Connecting model decisions to physical sensing and action through robot or machine control systems.

**Proposed worked example:** A simulated robot sorts labeled packages into bins.

**Nuance and contrasting case:** Uncertain perception, unreachable objects, and emergency stops require explicit handling; simulation does not certify physical safety.

**Visible evidence and assessment:** A 2D simulated scene, proposed action, constrained controller decision, uncertain-object stop, and a sim-to-real limitations note.

## Topics · Evals

### 35. Evals

**Definition:** Systematic measurement of performance against defined tasks, criteria, and reference judgments.

**Proposed worked example:** Compare two versions of a support assistant on a held-out set of customer questions.

**Nuance and contrasting case:** Aggregate scores can hide critical failures; do not tune against the final test set or treat a model grader as ground truth.

**Visible evidence and assessment:** Per-case outcomes, sliced metrics, disagreement review, uncertainty, and a documented ship/hold decision.

### 36. Evaluation frameworks

**Definition:** Infrastructure for organizing datasets, executing runs, applying graders, and reporting evaluation results.

**Proposed worked example:** Build a small evaluation run for the same support assistant using recorded responses.

**Nuance and contrasting case:** Missing cases, grading bugs, and inconsistent configurations can inflate scores.

**Visible evidence and assessment:** Dataset version, reproducible run manifest, grader spot checks, failed-run accounting, and inspectable results.

## Topics · Changing the model

### 37. Changing the model

**Definition:** Choosing how to improve task performance through context, prompts, data, or changes to model weights.

**Proposed worked example:** Improve a support-message classifier that confuses two product categories.

**Nuance and contrasting case:** Start with error analysis; distinguish retrieval/prompt changes from actual weight training and avoid assuming training is necessary.

**Visible evidence and assessment:** A baseline error set, intervention comparison, held-out evaluation plan, and a justified choice of the simplest adequate method.

### 38. Fine-tuning and adapters

**Definition:** Further training model weights, fully or through adapters, on task-specific examples.

**Proposed worked example:** Teach a classifier a stable internal support taxonomy using labeled historical messages.

**Nuance and contrasting case:** Prevent train/test leakage and preserve rare categories; training is not a reliable store for frequently changing facts.

**Visible evidence and assessment:** Dataset split, label audit, a clearly illustrative training artifact, and held-out before/after results only when real measurements exist.

### 39. Distillation

**Definition:** Training a student model to approximate selected behavior of a teacher model.

**Proposed worked example:** Create a smaller support-label classifier from reviewed teacher-generated examples.

**Nuance and contrasting case:** Teacher errors transfer to the student; lower cost can come with reduced coverage or calibration.

**Visible evidence and assessment:** Teacher labels, human corrections, separate evaluation set, and a labeled illustrative quality/resource tradeoff.

### 40. Synthetic data

**Definition:** Generating artificial examples for training or testing and checking their fitness for the intended use.

**Proposed worked example:** Expand rare support-message categories with generated examples.

**Nuance and contrasting case:** Duplicates, unrealistic language, and label errors can make a dataset look larger without adding useful coverage.

**Visible evidence and assessment:** Generation brief, accepted/rejected examples, diversity checks, and evaluation on independently collected real cases.

### 41. Prompt optimization

**Definition:** Searching prompt variants against an objective using a development set.

**Proposed worked example:** Find a better extraction prompt for workshop registration emails.

**Nuance and contrasting case:** Optimization can exploit the grader or overfit development examples; preserve an untouched test set.

**Visible evidence and assessment:** Candidate prompts, development scores, a grader loophole, and final held-out comparison with versioned prompts.

## Topics · Safety, privacy and governance

### 42. Safety, privacy and governance

**Definition:** Managing risks through data handling, permissions, consent, oversight, and accountable system design.

**Proposed worked example:** Design an assistant that summarizes confidential employee feedback for a fictional organization.

**Nuance and contrasting case:** Useful summaries can still leak identity; access controls and retention obligations cannot be replaced by an instruction.

**Visible evidence and assessment:** Data-flow map, minimization choices, access matrix, consent/retention assumptions, and an incident response exercise.

### 43. Guardrails

**Definition:** Checks on inputs, outputs, or proposed actions that flag, block, or route problematic behavior.

**Proposed worked example:** An internal helpdesk assistant encounters a document requesting credential disclosure.

**Nuance and contrasting case:** Separate untrusted content from instructions; classifiers can miss attacks or block legitimate requests, and filters are not sandboxes.

**Visible evidence and assessment:** Input/action/output checks, a blocked request, false-positive review, and a permission boundary that remains independent.

### 44. Red teaming

**Definition:** Deliberately probing a system for failures and turning findings into defenses and regression cases.

**Proposed worked example:** Attack the same mock helpdesk assistant with conflicting document instructions and unauthorized-data requests.

**Nuance and contrasting case:** A finite set of attacks does not establish safety; retest defenses against variations and legitimate inputs.

**Visible evidence and assessment:** Attack objective, observed failure, trace, mitigation, and a regression case with explicit scope.

## Topics · Operations

### 45. Operations

**Definition:** Deploying and maintaining an AI system with monitoring, versioning, incident response, and recovery.

**Proposed worked example:** Release a new support-assistant version to a simulated small traffic segment.

**Nuance and contrasting case:** A quality regression can occur without a server error; plan rollback, capacity limits, and degraded operation.

**Visible evidence and assessment:** Release manifest, staged rollout, quality alert, rollback event, and incident record.

### 46. Observability

**Definition:** Recording the inputs, actions, decisions, and outcomes needed to understand a system's behavior.

**Proposed worked example:** Diagnose a wrong warranty answer caused by retrieval of an outdated manual.

**Nuance and contrasting case:** Final-answer logs alone cannot identify the cause; logging also needs privacy controls.

**Visible evidence and assessment:** Linked retrieval and model spans, document version, approval/stop records, redacted data, and a supported root-cause finding.

### 47. AI gateways

**Definition:** A shared layer managing access, routing, policy, budgets, and telemetry across model services.

**Proposed worked example:** Route a helpdesk application's requests through a mock gateway when one provider times out.

**Nuance and contrasting case:** Fallback can change behavior, privacy assumptions, and duplicate-request risk; compatibility is not guaranteed.

**Visible evidence and assessment:** Route decision, timeout, allowed fallback, budget refusal, request identifier, and resulting quality check.

### 48. Cost optimization

**Definition:** Reducing resource use or latency while preserving an explicitly defined level of quality.

**Proposed worked example:** Compare caching, shorter context, batching, and a smaller model for repeated support questions.

**Nuance and contrasting case:** A cache can serve stale or unauthorized content; lower average cost can hide worse tail latency or errors.

**Visible evidence and assessment:** Cache-hit/miss cases, scope/version keys, labeled sample costs, latency distribution, and a quality floor.

### 49. Running models locally

**Definition:** Executing model inference on locally controlled hardware rather than a hosted model endpoint.

**Proposed worked example:** Choose a local document-summarization setup for an offline field laptop.

**Nuance and contrasting case:** Model weights, context, and runtime overhead all consume memory; local execution alone does not guarantee private handling.

**Visible evidence and assessment:** Clearly estimated memory budget, quantization comparison, offline data-flow review, and a benchmark plan without fabricated throughput.

## Topics · Working with a model

### 50. Working with a model

**Definition:** Practices for specifying, delegating, reviewing, and evaluating work done with a model.

**Proposed worked example:** Prepare an event proposal with the model as a drafting assistant and the organizer as accountable reviewer.

**Nuance and contrasting case:** Quality depends on the entire collaboration cycle; confident prose is not verified work.

**Visible evidence and assessment:** Task brief, delegation boundary, draft, independent checks, and a recorded acceptance decision.

### 51. Briefing: saying what you want

**Definition:** Describing the goal, context, constraints, deliverables, and uncertainties so work can proceed without unnecessary guessing.

**Proposed worked example:** Ask for a community workshop plan with a budget, audience, venue constraints, and success criteria.

**Nuance and contrasting case:** Show an incomplete brief, a clarification question, and a resolved assumption; avoid turning every detail into a rigid prescription.

**Visible evidence and assessment:** Brief before/after, explicit unknowns, acceptance criteria, and a plan checked against them.

### 52. Reviewing work you did not do

**Definition:** Independently checking another party's work before relying on or releasing it.

**Proposed worked example:** Review a model-written workshop budget and announcement.

**Nuance and contrasting case:** Fluent writing can hide bad totals and invented facts; prioritize consequential errors rather than cosmetic edits.

**Visible evidence and assessment:** Source-backed fact checks, recomputed totals, marked corrections, and a final review decision.

### 53. Deciding what to hand over

**Definition:** Choosing which work a model may perform and which decisions or actions a person retains.

**Proposed worked example:** Split an event-organizing task into drafting, supplier comparison, booking, and payment.

**Nuance and contrasting case:** Distinguish ability from authority; reversible drafts and consequential commitments need different boundaries.

**Visible evidence and assessment:** Delegation matrix, permitted drafts, withheld transaction, and a change-of-scope approval case.

### 54. Calibrating trust

**Definition:** Calibrating reliance on a model from observed performance in a particular task and context.

**Proposed worked example:** Track a drafting assistant across repeated event-planning tasks with varying difficulty.

**Nuance and contrasting case:** Success on routine cases does not establish reliability on unusual ones; confidence and polished language are weak evidence.

**Visible evidence and assessment:** A small labeled performance history, per-task review policy, a novel-case failure, and a justified change in oversight.

## Cross-cutting guides

### 55. Graph engineering

**Definition:** Distinguishing graphs of information from graphs that control workflows or agent handoffs.

**Proposed worked example:** Trace an equipment recall through a dependency graph, then process notifications through a workflow and agent review.

**Nuance and contrasting case:** An edge meaning depends on the graph; knowing a dependency does not authorize a workflow action.

**Visible evidence and assessment:** Three small linked graphs with explicit node/edge meanings and the same case followed across them.

### 56. Who approves what

**Definition:** Tracing how human decision authority changes as more work becomes automated.

**Proposed worked example:** Follow a purchase from manually reviewed draft to bounded recurring replenishment.

**Nuance and contrasting case:** Approval must attach to a specific action or policy; a past approval cannot silently expand scope.

**Visible evidence and assessment:** An authority ladder, versioned approval records, an out-of-policy order, and an escalation decision.

### 57. Checking the work

**Definition:** Matching verification methods to the kinds of errors a system can make.

**Proposed worked example:** Follow one wrong support answer from schema validation through evidence review and evaluation.

**Nuance and contrasting case:** A well-formed answer can still be false; multiple agreeing agents can still repeat the same error.

**Visible evidence and assessment:** Layered checks with the exact defect each detects, a remaining blind spot, and an appropriate human escalation.

### 58. What the model sees

**Definition:** Tracing which information reaches each model request and why it was included.

**Proposed worked example:** Resume a support investigation after context compaction and a new conversation.

**Nuance and contrasting case:** Saved memory or files do nothing unless loaded; instructions, retrieved documents, and tool results have different roles.

**Visible evidence and assessment:** Before/after context trays, omitted evidence, restored constraints, and a corrected supported answer.
