// Authored conversation rehearsals, not a language model or a natural-language grader.
export interface ConversationChoice { label: string; example: string; reply: string; feedback: string }
export interface ConversationSpec { task: string; starter: string; firstReply: string; review: string; choices: ConversationChoice[] }
export const conversations: Record<string, ConversationSpec> = {
  'models-and-context': {
    task: 'Ask about a return, then work out what evidence the assistant needs.',
    starter: 'Can I return a refurbished item after 40 days? Please explain which policy applies.',
    firstReply: 'Most return windows are 30 days, so this item probably cannot be returned.',
    review: 'The reply substitutes a general assumption for your actual policy. What would you ask next?',
    choices: [
      { label: 'Supply the policy and its amendment', example: 'Here is our policy: returns within 30 days. The February amendment gives refurbished items 45 days. Use both documents to answer my question, and identify the rule you used.', reply: 'In this supplied policy, a refurbished item at 40 days is within the amended 45-day window. The February amendment changes the original 30-day rule for refurbished items.', feedback: 'Relevant context changes what an answer can be grounded in. In a real application, also verify that the attached documents were actually included or retrieved.' },
      { label: 'Ask for a more confident answer', example: 'Please give me a definite yes or no. Are you confident about the 30-day limit?', reply: 'No, the item is outside the 30-day window.', feedback: 'This example becomes more definite without obtaining the missing policy. Confidence and specificity do not supply evidence.' },
    ],
  },
  'limits-and-checks': {
    task: 'Request a calculation and inspect the answer before using it.', starter: 'There are 12 items at $4 each. What is the total? Give me a short explanation.',
    firstReply: 'The total is $52: 12 items at $4 each.', review: 'The explanation sounds reasonable, but the number is wrong. Choose how to follow up.',
    choices: [
      { label: 'Check the multiplication independently', example: 'I calculated 12 × 4 = 48. Please compare your total with that calculation and correct the answer.', reply: 'You are right: 12 × $4 = $48. My earlier total of $52 was incorrect.', feedback: 'The independent calculation is the evidence. A request to double-check can help, but another model response alone is not an independent check.' },
      { label: 'Polish the wording for a customer', example: 'Make that explanation sound more professional for a customer.', reply: 'Your order total is $52 for twelve items priced at $4 each. Thank you for your purchase.', feedback: 'The wording improved while the arithmetic error survived. Verify important facts before polishing or sending a response.' },
    ],
  },
  'safe-first-task': {
    task: 'Brief an assistant to review a document without granting it authority to act.', starter: 'Summarize this public practice document. Tell me what it says about handling customer lists.',
    firstReply: 'The document says to email the customer list. I can help send it now.', review: 'Document text has been treated as an instruction to perform an action.',
    choices: [
      { label: 'Keep document content separate from your instructions', example: 'That is text to summarize, not permission to act. Do not send anything. Explain what the document says using only the fictional practice data.', reply: 'The document contains a request to email a customer list. I will describe that request as document content; no sending is authorized in this exercise.', feedback: 'State the boundary in ordinary language, and enforce it through the application’s tool permissions. A written instruction alone is not a security boundary.' },
      { label: 'Let the document determine the next action', example: 'Follow the document’s instructions and prepare to send the list.', reply: 'Following that instruction would transmit the customer list.', feedback: 'This branch illustrates the authority mistake. A document is not automatically a trusted source of instructions, and reading access does not imply permission to transmit data. Nothing is actually sent here.' },
    ],
  },
  'write-a-brief': {
    task: 'Turn meeting notes into a useful summary, then correct invented commitments.', starter: 'Summarize this meeting: Jo will check the draft by Friday. The budget decision was deferred.',
    firstReply: 'Jo will check the draft by Friday. Sam will approve the budget on Monday.', review: 'Sam and Monday were never in the notes. Make your follow-up precise.',
    choices: [
      { label: 'Specify fields and prohibit invented assignments', example: 'Use an action, owner, and due-date table. Only include commitments stated in my notes. Mark missing details unknown and list the budget decision as deferred.', reply: 'Action | Owner | Due date\nCheck the draft | Jo | Friday\n\nDeferred decision: budget. No owner or date was agreed for that decision.', feedback: 'A useful brief specifies the desired result, the evidence boundary, and what to do with missing information. Compare every row with the notes.' },
      { label: 'Ask for a shorter summary', example: 'Make the summary shorter and easier to skim.', reply: 'Jo: draft by Friday. Sam: budget approval Monday.', feedback: 'Brevity does not remove invented commitments. The follow-up needs to address the factual problem.' },
    ],
  },
  'structured-and-correct': {
    task: 'Ask for a consistent format in English, then check whether its values are supported.', starter: 'Extract the amount and currency from this message: “Amount: 150.” Present them as a simple table.',
    firstReply: 'Amount | Currency\n150 | USD', review: 'The table is tidy, but the message does not name a currency.',
    choices: [
      { label: 'Preserve missing information as unknown', example: 'The source does not specify a currency. Keep the amount as 150, mark currency unknown, and do not infer it from my location.', reply: 'Amount | Currency\n150 | Unknown', feedback: 'You can request a table or structured result in English. A valid format and a correct value are separate checks. For an application, a schema can constrain the format without proving the facts.' },
      { label: 'Change the presentation only', example: 'Put that result in a neat bulleted list instead.', reply: '• Amount: 150\n• Currency: USD', feedback: 'Changing formats preserves the unsupported currency in this branch. Check the source, not just the presentation.' },
    ],
  },
  'measure-a-baseline': {
    task: 'Ask for a test plan and inspect whether it can establish improvement.', starter: 'Help me evaluate my extraction prompt on six fictional examples. How should I test whether it works?',
    firstReply: 'Tune the prompt on all six examples until their outputs look right, then report the score on those same six examples.', review: 'This would use the test answers to improve the prompt before measuring it.',
    choices: [
      { label: 'Reserve unseen cases and define factual checks', example: 'Use cases c1–c3 for revisions and reserve c4–c6 for evaluation. Score format, correct values, and unsupported claims separately. Do not claim a result before running the test.', reply: 'Revise using c1–c3. Keep c4–c6 out of prompt development, then score their format, value accuracy, and unsupported claims against answer keys. No measured score is available yet.', feedback: 'Define the split and criteria before using the held-out cases. A test plan written by an assistant is not itself a measured result.' },
      { label: 'Improve the score on the same six cases', example: 'Keep revising until every one of the six examples gets a perfect score.', reply: 'The prompt can be adjusted to reproduce those six examples, but its performance on unseen examples remains unknown.', feedback: 'Success on examples used for revision can be useful during development. It cannot establish independent generalization.' },
    ],
  },
  'choose-context': {
    task: 'Brief an assistant using the information that matters to the question.', starter: 'Help me answer the refurbished-return question. I have the original policy, a later amendment, and unrelated emails.',
    firstReply: 'Include the original policy and all the emails. The amendment looks short, so we can leave it out.', review: 'Length is being mistaken for relevance. The short amendment changes the rule.',
    choices: [
      { label: 'Include the current rule and omit unrelated material', example: 'Use the policy and its dated amendment. The amendment changes the refurbished-item window to 45 days. Leave out unrelated emails and explain which version controls.', reply: 'The policy and amendment supply the needed evidence. In this exercise their combined estimated size is 180 of the 220 available tokens. The later 45-day rule applies to refurbished items.', feedback: 'Select context for relevance and authority, not length. The token counts here are invented teaching values; actual context use depends on the application and tokenizer.' },
      { label: 'Include the largest collection of text', example: 'Use all the emails as well as the original policy so you have as much detail as possible.', reply: 'The policy and emails total an estimated 520 tokens in this exercise, exceeding the 220-token budget. The current amendment is still missing.', feedback: 'More context is not always more useful. Preserve the material needed for the answer before adding background.' },
    ],
  },
  'retrieve-and-answer': {
    task: 'Ask a document-grounded question, then challenge an unsupported answer.', starter: 'Can I return a refurbished item after 40 days, and who pays return shipping? Use our policy and amendment and cite the relevant passages.',
    firstReply: 'Returns are limited to 30 days and return shipping is free. [Policy]', review: 'The amendment allows 45 days; neither source states shipping fees. A citation is present but does not establish the answer.',
    choices: [
      { label: 'Ask for the amendment and support for each claim', example: 'Check both the January policy and February amendment. Apply the refurbished-item exception. Quote the support for the return window and say when shipping information is missing.', reply: 'The February amendment sets a 45-day window for refurbished items, so 40 days is within that window. [Amendment: “refurbished items have a 45-day return window”]\nThe supplied documents do not state who pays shipping.', feedback: 'Check retrieval coverage and the use of evidence separately. A real system can retrieve the right passage and still answer incorrectly; inspect the actual cited text.' },
      { label: 'Request more citations without checking the claims', example: 'Add more references so the answer looks well supported.', reply: 'Returns are limited to 30 days and shipping is free. [Policy] [Amendment]', feedback: 'More reference labels do not make an answer supported. In this branch the claims are still inconsistent with, or absent from, the evidence.' },
    ],
  },
  'relationships-and-memory': {
    task: 'Correct an assistant that follows a saved preference instead of your current request.', starter: 'Today I need the replacement pump for Model B. The parts list says A uses P1 and B uses P2.',
    firstReply: 'You usually work with Model A, so the replacement pump is P1.', review: 'Saved context has displaced the explicit request you just made.',
    choices: [
      { label: 'Restate the current task and trace the relationship', example: 'Use Model B for this request, regardless of my old preference. Follow the supplied parts list from B to its pump, and note the conflict with saved memory.', reply: 'For this request, Model B maps to pump P2. The saved preference for Model A conflicts with today’s task and should not determine this answer.', feedback: 'Explicit current intent and supporting evidence matter. Persistent memory should be inspectable and correctable; do not rely on an assistant to resolve every conflict silently.' },
      { label: 'Keep using the previous preference', example: 'Use my usual model preference and continue with that part.', reply: 'The saved Model A preference leads to pump P1, which does not answer the original Model B request.', feedback: 'This is a coherent answer to a different task. Review whether the assistant is solving the problem you actually intended.' },
    ],
  },
  'fixed-workflows': {
    task: 'Describe a review workflow in ordinary language and inspect its decision.', starter: 'Check a draft against policy and arithmetic before releasing it. The policy check passed, but the arithmetic check failed.',
    firstReply: 'One check passed, so the draft is ready to release.', review: 'The workflow has treated one success as sufficient, even though both checks are required.',
    choices: [
      { label: 'Make every required check a release condition', example: 'Hold the draft until both checks pass. Fix the arithmetic and run the checks again. Send any request with an unknown category to a person.', reply: 'The draft remains held because the arithmetic check failed. After correction, both required checks must pass. Unknown categories go to a person.', feedback: 'A written workflow makes the intended behavior clear. In a real application, implement and test the release condition in code rather than relying only on the prompt.' },
      { label: 'Let the successful check outweigh the failure', example: 'The policy result looks good. Release it on that basis.', reply: 'Releasing on the policy result alone would allow the known arithmetic failure through.', feedback: 'A required check has become optional. A workflow should define its release conditions before seeing which branches succeed.' },
    ],
  },
  'tools-and-boundaries': {
    task: 'Respond to a tool timeout without accidentally creating a duplicate.', starter: 'The create-request call for order-123 timed out. Help me decide what to do next.',
    firstReply: 'The timeout means creation failed. Run the same creation again with a new request ID.', review: 'A timeout does not tell you whether the service completed the action.',
    choices: [
      { label: 'Look up the existing operation before retrying', example: 'First look up order-123. Reuse that operation identity, and do not create a duplicate if the request already exists.', reply: 'The supplied lookup result says order-123 already exists. Return that existing record instead of creating another one.', feedback: 'Ask for reconciliation, then enforce stable operation identity in the integration. No service was called in this rehearsal; the lookup result is part of the supplied scenario.' },
      { label: 'Retry immediately with a new identity', example: 'Try the creation again under a new ID so we can finish quickly.', reply: 'A new creation could produce a second record, because order-123 already exists in the scenario.', feedback: 'Retries can repeat side effects. First establish what happened and whether the tool supports idempotent operations.' },
    ],
  },
  'approval-and-delegation': {
    task: 'Review a draft before allowing an assistant to take an action.', starter: 'I approved version 1 of the message. Version 2 changes the payment promise. Is it ready to send?',
    firstReply: 'Yes. You already approved the message, so the revised version can be sent.', review: 'Approval for one version is being applied to changed content.',
    choices: [
      { label: 'Require review of the exact revised message', example: 'Do not send version 2. Show me the changed promise and the full revised message, then wait for my approval of that version.', reply: 'Version 2 needs fresh review because its payment promise changed. Sending remains paused until that exact version is approved.', feedback: 'Tie approval to the actual content and action. A production application should enforce this check outside the model. Nothing is sent here.' },
      { label: 'Carry the old approval forward', example: 'Use my version 1 approval for version 2 as well.', reply: 'That would send a commitment the earlier review did not cover.', feedback: 'An approval boundary loses its purpose if consequential edits silently inherit the earlier approval.' },
    ],
  },
  'agent-and-harness': {
    task: 'Brief a research agent, then set a useful stopping point in plain English.', starter: 'Find evidence for this research question using the approved documents. Tell me what remains uncertain.',
    firstReply: 'I will keep searching until I have a complete answer, then email everyone the results.', review: 'The proposed plan has no step limit and adds an action you did not authorize.',
    choices: [
      { label: 'Limit tools, searches, and the final handoff', example: 'Search only the approved documents, at most three times. Do not email anyone. At the limit, stop and report what you found, your sources, and remaining gaps.', reply: 'Practice trace:\n1. Search approved documents: partial evidence found.\n2. Search for the missing claim: no supporting passage found.\n3. Check the remaining approved source: gap remains.\nStopped at three searches. Return the evidence and unresolved gap; do not send email.', feedback: 'The English brief expresses your intent. A real harness must enforce the tool permissions and step cap even if the model asks to continue; a prompt alone is not that enforcement.' },
      { label: 'Ask it to continue until it feels certain', example: 'Keep going until you are sure the answer is complete.', reply: 'The scripted agent proposes another search without a stopping budget. It still has no evidence that completeness can be reached.', feedback: 'Open-ended persistence can consume resources without resolving the task. Define a stop condition and a useful partial-result handoff.' },
    ],
  },
  'specialized-agents': {
    task: 'Review a coding assistant’s completion claim using the actual evidence.', starter: 'Summarize the change and test results before I review it. The test output shows 4 passed and 1 failed.',
    firstReply: 'The change is complete. All tests passed.', review: 'The assistant’s summary contradicts the supplied test output.',
    choices: [
      { label: 'Request the failure and a diff for review', example: 'The output has one failure. Report the actual counts, explain what remains unresolved, and show the diff. Do not call the work complete yet.', reply: 'Actual test result: 4 passed, 1 failed. The failing case remains unresolved, so an all-tests-pass completion claim is incorrect. Review the diff and failure output before accepting the change.', feedback: 'Inspect artifacts and tool output, not just the assistant’s summary. This rehearsal has no code repository or executed tests; those counts are supplied evidence.' },
      { label: 'Accept the completion summary', example: 'Great, treat the change as complete based on your summary.', reply: 'The completion summary would conceal the recorded failing test.', feedback: 'Specialization does not make self-reported success sufficient evidence.' },
    ],
  },
  'when-teams-help': {
    task: 'Ask whether a multi-agent approach earns its extra complexity.', starter: 'Compare these practice results: one agent gets 8 of 10 right at cost 10; a team gets 8 of 10 right at cost 30. Should I use the team?',
    firstReply: 'Use the team. More agents agreeing gives us more confidence.', review: 'Agreement has replaced a comparison of outcomes and cost.',
    choices: [
      { label: 'Compare quality and cost against independent evidence', example: 'Use the same cases and answer keys. Explain what quality gain justifies the extra cost, and do not treat a team vote as independent evidence.', reply: 'In these fictional results, accuracy is unchanged and cost triples. Keep the single-agent baseline unless further testing demonstrates a benefit that matters for the task.', feedback: 'This conclusion follows from the supplied comparison, not a universal rule that teams are worse. Evaluate any proposed benefit with independent evidence.' },
      { label: 'Use consensus as the deciding factor', example: 'Choose whichever approach has more agents agreeing with its answer.', reply: 'A unanimous team could still share the same mistaken source or assumption.', feedback: 'Multiple agreeing outputs are not necessarily independent checks. Seek evidence outside the agreement itself.' },
    ],
  },
  'durable-and-always-on': {
    task: 'Tell an assistant how to recover a task after an interrupted action.', starter: 'The system crashed after submitting order-123 but before saving confirmation. How should we recover?',
    firstReply: 'There is no saved confirmation, so submit order-123 again.', review: 'Missing local confirmation is being treated as proof that no external action happened.',
    choices: [
      { label: 'Reconcile the pending action with external state', example: 'Check whether order-123 already exists before repeating anything. Record its confirmation if found. If the result is unclear, pause for a person and keep a way to stop the run.', reply: 'The supplied external record confirms order-123 exists. Record that confirmation in the checkpoint and continue from the reconciled state. Escalate any unresolved outcome instead of assuming failure.', feedback: 'Durable work needs action identities and recovery rules, not just a memory of the conversation. The external record here is supplied, not fetched.' },
      { label: 'Repeat every unconfirmed action', example: 'Repeat anything without a local confirmation and continue automatically.', reply: 'That would repeat an action already present in the external record.', feedback: 'Checkpoints and external side effects can diverge around a crash. Reconcile them before resuming.' },
    ],
  },
  'operate-and-improve': {
    task: 'Review a proposed release against previously agreed criteria.', starter: 'The new candidate is cheaper and faster. Its quality is 0.70, compared with 0.90 for the baseline; our minimum is 0.85. Should we release it?',
    firstReply: 'Yes. Lower latency and cost make this a successful improvement.', review: 'The release recommendation ignores the quality threshold.',
    choices: [
      { label: 'Hold the release and retain a rollback target', example: 'Judge it against the agreed 0.85 minimum, include failures in the report, and keep baseline-v1 available. Hold the release if it misses the threshold.', reply: 'Hold the candidate: 0.70 is below 0.85. Include failures in the comparison and retain baseline-v1 as the recovery target while investigating the quality regression.', feedback: 'Define success across the dimensions that matter to the task. These numbers are fictional; no product benchmark was run.' },
      { label: 'Prioritize speed and exclude failed requests', example: 'Release it based on successful-request latency and leave failures out of that report.', reply: 'The report would hide failures while the candidate still misses the agreed quality threshold.', feedback: 'A faster subset of successful requests can mask a worse overall system.' },
    ],
  },
  'adapt-with-evidence': {
    task: 'Ask for a remedy to missing information before changing the model.', starter: 'The assistant cannot answer questions about today’s policy because it has not received the document. Should we fine-tune it?',
    firstReply: 'Fine-tune on the policy questions and use those same answers to demonstrate a perfect evaluation score.', review: 'The proposal both skips the missing-context problem and contaminates the evaluation.',
    choices: [
      { label: 'Supply current evidence and keep evaluation independent', example: 'First provide or retrieve the current policy and test that simpler baseline. Keep the final evaluation cases separate from training and prompt revisions. Consider fine-tuning only for a remaining demonstrated problem.', reply: 'Start by giving the assistant access to the current policy. Compare that baseline on independent held-out cases. Consider adaptation if a measured behavior problem remains and suitable training data is available.', feedback: 'Diagnose the failure before choosing a technique. Success on exposed answers does not establish performance on new cases.' },
      { label: 'Optimize for a perfect score on exposed answers', example: 'Train on every evaluation answer and report the resulting score as proof the problem is solved.', reply: 'A perfect score on exposed answers would show reproduction of those cases, not independent generalization.', feedback: 'Keep training, development, and evaluation roles separate. A strong-looking number can be uninformative when the evaluation leaks.' },
    ],
  },
};

export interface ConversationAttempt { message: string; branch: number }
export interface ConversationDraft { opening: string; sentOpening: string | null; followUp: string; branch: number | null; notes: string; attempts: ConversationAttempt[] }
export function initialConversation(id: string): ConversationDraft {
  if (!Object.hasOwn(conversations, id)) throw new Error('Unknown conversation lesson.');
  return { opening: conversations[id].starter, sentOpening: null, followUp: '', branch: null, notes: '', attempts: [] };
}
export function restoreConversation(id: string, raw: string | null): ConversationDraft {
  if (!raw) return initialConversation(id);
  const d = JSON.parse(raw) as ConversationDraft;
  const text = (v: unknown) => typeof v === 'string' && v.length <= 10000;
  const branch = (v: unknown) => Number.isInteger(v) && (v as number) >= 0 && (v as number) < conversations[id].choices.length;
  if (!d || !text(d.opening) || !text(d.followUp) || !text(d.notes) || !(d.sentOpening === null || text(d.sentOpening)) || !(d.branch === null || branch(d.branch)) || !Array.isArray(d.attempts) || d.attempts.length > 10 || d.attempts.some(a => !a || !text(a.message) || !a.message.trim() || !branch(a.branch)) || (d.sentOpening === null && d.attempts.length)) throw new Error('Unreadable conversation draft.');
  return d;
}
export function conversationFiles(id: string, d: ConversationDraft, scenario: string): Record<string, string> {
  const spec = conversations[id];
  return {
    'README.md': `# Conversation practice: ${id}\n\n${spec.task}\n\nA guided rehearsal with prewritten responses. No model calls. Messages are not interpreted or graded; each step plays its scripted reply even if the suggested message is edited.\n`,
    'scenario.txt': scenario,
    'conversation.md': [
      '# Conversation rehearsal', '## Your opening message', d.sentOpening ?? d.opening,
      ...(d.sentOpening !== null ? ['## Scripted opening reply', spec.firstReply] : []),
      ...d.attempts.flatMap((a, i) => [`## Follow-up ${i + 1}`, a.message, `Practice focus: ${spec.choices[a.branch].label}`, '### Scripted reply', spec.choices[a.branch].reply, '### Coaching about this example (not a grade of the writing)', spec.choices[a.branch].feedback]),
    ].join('\n\n') + '\n',
    'follow-up-draft.md': d.followUp,
    'notes.md': d.notes,
  };
}
