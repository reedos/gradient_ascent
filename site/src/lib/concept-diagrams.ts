// Small conceptual models of the explanations on the technique pages, not recorded runs.
// Keep the distinction visible: a sequence, a choice, concurrent work, and a feedback loop
// have different topologies. The harness has its own enclosing boundary.
export type ConceptShape = 'flow' | 'loop' | 'fork' | 'choice' | 'harness' | 'retrieval';
export interface ConceptNode { title: string; detail: string }
export interface ConceptDiagram {
  shape: ConceptShape;
  headline: string;
  takeaway: string;
  nodes: ConceptNode[];
}
type NodeCopy = [string, string];
const diagram = (shape: ConceptShape, headline: string, takeaway: string, nodes: NodeCopy[]): ConceptDiagram =>
  ({ shape, headline, takeaway, nodes: nodes.map(([title, detail]) => ({ title, detail })) });
const flow = (headline: string, takeaway: string, ...nodes: NodeCopy[]) => diagram('flow', headline, takeaway, nodes);
const loop = (headline: string, takeaway: string, ...nodes: NodeCopy[]) => diagram('loop', headline, takeaway, nodes);
const fork = (headline: string, takeaway: string, ...nodes: NodeCopy[]) => diagram('fork', headline, takeaway, nodes);
const choice = (headline: string, takeaway: string, ...nodes: NodeCopy[]) => diagram('choice', headline, takeaway, nodes);

export const conceptDiagrams: Record<string, ConceptDiagram> = {
  'order-zero': flow('A known rule can be the whole solution.', 'Start here when a rule, lookup, or form already covers the task.',
    ['Input', 'A fact or a request'], ['Rule or lookup', 'Ordinary code applies it'], ['Result', 'No model call needed']),
  chat: flow('One message in. One reply out.', 'You supply the request and decide what to do with the reply.',
    ['Your message', 'Question and context'], ['Model', 'Generates a response'], ['Your next move', 'Use, edit, or ask again']),
  'prompt-engineering': flow('Make the request easier to get right.', 'Clear instructions shape the response without changing the model itself.',
    ['Write the brief', 'Goal, context, examples'], ['Model', 'Works from your request'], ['Check the response', 'Against your instructions']),
  'structured-output': flow('Give the answer a shape your code can read.', 'A fixed format is useful only when you also validate the returned values.',
    ['Text + schema', 'What to extract and how'], ['Model', 'Returns a structured record'], ['Validate', 'Accept or request a retry']),
  'inference-time-reasoning': flow('Spend more work on the answer before returning it.', 'Extra reasoning happens while answering; it does not train a new model.',
    ['Hard question', 'A task worth extra effort'], ['Reason or compare', 'More work at answer time'], ['Final answer', 'Still needs checking']),
  multimodal: flow('The context can be more than words.', 'Images, sound, and text can inform the same task; supported formats vary by model.',
    ['Text, image, audio', 'Inputs the model supports'], ['Model', 'Works across those inputs'], ['Response', 'Text or supported media']),
  'context-engineering': flow('Choose what the model can see this time.', 'The model works from the context you actually send, not everything your system knows.',
    ['Available material', 'Instructions, files, history'], ['Assemble context', 'Select, order, fit, cache'], ['Model request', 'Only the chosen material']),
  'embeddings-search': flow('Find nearby meanings in a shared space.', 'Similarity finds candidates; it does not prove that a passage answers the question.',
    ['Query + passages', 'Encode as vectors'], ['Similarity search', 'Find nearby vectors'], ['Ranked passages', 'Read the best matches']),
  rag: diagram('retrieval', 'Find the evidence before asking for an answer.', 'The question selects evidence from your documents. The model receives that evidence with the question and writes a cited answer.',
    [['Your question', 'What needs answering?'], ['Document collection', 'Your searchable source material'], ['Retrieve passages', 'Select relevant evidence'], ['Model', 'Question + selected passages'], ['Cited answer', 'Check claims against sources']]),
  'knowledge-graphs': flow('Follow relationships to connect facts.', 'Explicit relationships let a question follow several linked facts.',
    ['Part', 'Fits a particular model'], ['Appliance model', 'Has a warranty class'], ['Warranty class', 'Trace back to the sources']),
  memory: flow('Carry selected information into a later conversation.', 'Memory is a store you maintain and retrieve from, not unlimited context.',
    ['Conversation now', 'Choose what to remember'], ['Memory store', 'Save, update, or forget'], ['Conversation later', 'Retrieve relevant memories']),
  'prompt-chaining': flow('Hand each step’s output to the next.', 'The code fixes the steps and their order before the first model call.',
    ['Rewrite the question', 'First prompt'], ['Draft from sources', 'Second prompt'], ['Check the draft', 'Pass along a checked result']),
  routing: choice('Pick a path for this input.', 'A classifier supplies a label; code maps that label to a known handler.',
    ['Classify the input', 'Which handler fits?'], ['Lookup', 'Answer a factual question'], ['Calculation', 'Use a fixed numeric rule'], ['Ask a person', 'Handle uncertain cases']),
  parallelization: fork('Work on independent pieces at the same time.', 'Code starts the branches and combines their results; one branch does not direct another.',
    ['Split the work', 'A fixed set of branches'], ['Prompt A', 'One independent piece'], ['Prompt B', 'Another independent piece'], ['Prompt C', 'Another independent piece'], ['Combine', 'Collect the useful results']),
  'evaluator-optimizer': loop('Write, check, and revise.', 'A failed check feeds a revision. A passing check or a fixed cap ends the loop.',
    ['Task + criteria', 'Define what good means'], ['Draft', 'Write a candidate answer'], ['Evaluate', 'Check against the criteria'], ['Feedback', 'Revise if it did not pass']),
  'workflow-graphs': choice('Make the next step an explicit connection.', 'The program owns the graph and the conditions that select its paths.',
    ['Check the draft', 'Evaluate a condition'], ['Revise', 'Follow the failure edge'], ['Finish', 'Follow the passing edge'], ['Escalate', 'Follow the exception edge']),
  'human-in-the-loop': choice('Stop at a decision that needs a person.', 'The proposed action waits until a person approves, changes, or refuses it.',
    ['Human checkpoint', 'Review a proposed action'], ['Approve', 'Let the action proceed'], ['Correct', 'Change it before proceeding'], ['Reject', 'Do not run the action']),
  'function-calling': flow('The model requests a tool. Code runs it.', 'A tool call is a structured request for an action, not the action itself.',
    ['Model request', 'Tool name + arguments'], ['Your code', 'Validate and run the tool'], ['Tool result', 'Return data for the answer']),
  'code-execution': flow('Turn a generated program into a checked result.', 'The execution environment needs its own limits; generated code is not automatically safe.',
    ['Model writes code', 'A program for the task'], ['Sandbox runs it', 'Bounded execution'], ['Result + errors', 'Inspect the actual output']),
  mcp: flow('Give tools and data a common connection.', 'MCP describes the connection; the host still owns permissions and execution policy.',
    ['AI application', 'Host and MCP client'], ['MCP connection', 'Discover and call tools'], ['MCP server', 'Exposes tools and data']),
  'computer-use': loop('Read the screen, act, then look again.', 'The next screen is the feedback. Actions need bounds and consequential steps may need approval.',
    ['Task', 'A goal in an application'], ['Observe + choose', 'Model reads the screen'], ['UI action', 'Click, type, or scroll'], ['New screen', 'Check what changed']),
  'single-agent': loop('Let the model choose the next action.', 'The model can request another action or finish; code enforces the limits.',
    ['Goal', 'What needs to get done'], ['Model', 'Choose an action or finish'], ['Run a tool', 'Code executes the request'], ['Observe result', 'Feed it into the next turn']),
  'agent-harness': diagram('harness', 'The model proposes. The harness controls the run.',
    'Change the tools, permissions, or context policy and the same model can behave very differently.',
    [['Context', 'Instructions + selected history'], ['Model', 'Propose an action or finish'], ['Permissions', 'Allow, ask, or refuse'], ['Tools + sandbox', 'Execute within boundaries'], ['Results', 'Feed back into the next turn']]),
  'agentic-rag': loop('Let the agent decide what to search next.', 'Unlike a fixed retrieval pass, the next search depends on what the agent has already found.',
    ['Research question', 'What needs evidence?'], ['Agent', 'Search, read, or answer'], ['Search + read', 'Retrieve selected sources'], ['Evidence', 'Inform the next decision']),
  'coding-agents': loop('Edit code, run it, and learn from the result.', 'Tests and tool output feed the next edit; passing tests still need review.',
    ['Coding task', 'Goal and repository context'], ['Agent', 'Choose the next change'], ['Edit + run tests', 'Tools work on the code'], ['Diff + test output', 'Review and iterate']),
  skills: flow('Load the instructions when the task needs them.', 'A skill supplies reusable instructions and resources; the agent still has to do the work.',
    ['Task + skill list', 'Read short descriptions'], ['Select a skill', 'Load the relevant guidance'], ['Agent uses it', 'Follow it with available tools']),
  'voice-agents': loop('Listen and respond without losing the turn.', 'Conversation timing and interruption handling surround the model’s response.',
    ['Spoken input', 'A person starts a turn'], ['Agent', 'Understand and respond'], ['Speak', 'Deliver the response'], ['Listen again', 'New turn or interruption']),
  'orchestrator-workers': fork('A lead delegates pieces and combines the answers.', 'The lead chooses the subtasks; workers return their findings to it.',
    ['Lead agent', 'Decide how to split the task'], ['Worker A', 'Investigate one subtask'], ['Worker B', 'Investigate another'], ['Worker C', 'Investigate another'], ['Lead combines', 'Check and synthesize findings']),
  'agent-graphs': choice('Pass work between agents along allowed paths.', 'The handoff can be model-selected, but code still limits which destinations exist.',
    ['Supervisor', 'Choose the next agent'], ['Research agent', 'Find more evidence'], ['Writing agent', 'Produce the answer'], ['Review agent', 'Check the work']),
  'debate-review': loop('Give another agent a chance to find the mistake.', 'A reviewer needs evidence and clear criteria; agreement alone is not proof.',
    ['Question + sources', 'Material for the author'], ['Author', 'Draft an answer'], ['Reviewer', 'Check with its own evidence'], ['Critique', 'Challenge or accept']),
  'long-horizon': loop('Save progress so the work can continue later.', 'A checkpoint carries state between sessions; caps and review still apply.',
    ['Long task', 'Break it into milestones'], ['Work session', 'Advance the current step'], ['Checkpoint', 'Save progress and blockers'], ['Resume', 'Load state for the next session']),
  'agent-teammates': loop('A trigger starts the next piece of work.', 'Working unattended requires explicit authority, limits, and a path back to a person.',
    ['Schedule or event', 'Work arrives without a chat'], ['Agent teammate', 'Assess what needs doing'], ['Policy + action', 'Run, queue, or refuse'], ['Report + state', 'Carry progress to the next run']),
  'organizations-swarms': fork('Coordinate roles around a shared goal.', 'More agents add coordination work: ownership, shared state, budgets, and review.',
    ['Shared goal', 'Allocate roles and budgets'], ['Research role', 'Own a bounded task'], ['Execution role', 'Own a bounded task'], ['Review role', 'Own a bounded task'], ['Shared state', 'Track handoffs and progress']),
  embodied: loop('Close the loop through the physical world.', 'A safety controller bounds physical actions; the next sensor reading checks their effect.',
    ['Physical goal', 'A task in the real world'], ['Perceive + plan', 'Interpret sensor readings'], ['Bounded actuation', 'Move within safety limits'], ['Sensors', 'Observe the changed world']),
  evals: flow('Compare a change on the same test cases.', 'A score is meaningful only when the cases and grading match the job you care about.',
    ['Fixed test set', 'Inputs and expected behavior'], ['Run + grade', 'Apply the same criteria'], ['Compare versions', 'Inspect wins and failures']),
  'eval-frameworks': flow('Automate the evaluation, keep the judgment visible.', 'The framework runs the machinery; you remain responsible for the test and grader quality.',
    ['Cases + graders', 'Define the experiment'], ['Evaluation runner', 'Execute and record results'], ['Report + review', 'Inspect scores and examples']),
  adaptation: choice('Choose what you want to change.', 'Changing weights, training examples, and prompts are different interventions.',
    ['Observed weakness', 'Find what needs improvement'], ['Model weights', 'Fine-tune or distill'], ['Training data', 'Generate and verify examples'], ['Prompt', 'Search for better instructions']),
  'fine-tuning': flow('Learn from examples by changing model parameters.', 'Training changes weights or adapters; it is different from adding context to one request.',
    ['Training examples', 'Inputs with desired outputs'], ['Training update', 'Weights or small adapters'], ['Adapted model', 'Evaluate on held-out tasks']),
  distillation: flow('Teach a smaller model from a larger model’s work.', 'The student must be evaluated on the task, not just on agreement with the teacher.',
    ['Teacher model', 'Generate demonstrations'], ['Check the examples', 'Filter the training material'], ['Student model', 'Train and evaluate']),
  'synthetic-data': flow('Generate examples, then earn the right to use them.', 'Generated data can contain errors and duplicates; verification is part of the technique.',
    ['Seed + generator', 'Produce candidate examples'], ['Verify + deduplicate', 'Reject errors and repeats'], ['Accepted dataset', 'Use with clean test splits']),
  'prompt-optimization': loop('Search for a better prompt against a defined test.', 'Keep a held-out set separate from the examples used to choose the prompt.',
    ['Task + dev cases', 'Define the scoring target'], ['Candidate prompt', 'Try a new instruction'], ['Evaluate', 'Score on development cases'], ['Select + revise', 'Use results for the next trial']),
  safety: flow('Put boundaries around the whole system.', 'Untrusted inputs, tool permissions, and released outputs need different controls.',
    ['Untrusted material', 'Separate data from instructions'], ['Bounded execution', 'Permissions and data rules'], ['Release + audit', 'Review outputs and actions']),
  guardrails: flow('Check the input and the proposed output.', 'A check can block a known failure without making the whole system safe.',
    ['Input check', 'Reject or flag risky requests'], ['Model + tools', 'Operate within permissions'], ['Output check', 'Release, block, or escalate']),
  'red-teaming': loop('Try to break the system, then test the repair.', 'Keep the discovered attack as a regression case instead of treating a patch as proof.',
    ['Threat scenario', 'A failure worth testing'], ['Adversarial attempt', 'Probe the system’s boundary'], ['Observe failure', 'Record what actually happened'], ['Fix + regression', 'Retest the changed system']),
  ops: loop('Run the system and respond to what it does.', 'Operational decisions need measured quality, cost, latency, and reliability.',
    ['Deploy a version', 'A defined configuration'], ['Serve requests', 'Run the actual workload'], ['Measure', 'Quality, latency, cost, errors'], ['Adjust', 'Tune, roll back, or repair']),
  observability: flow('Leave a trail from the answer back to its steps.', 'A trace helps locate a failure; it does not by itself grade answer quality.',
    ['Run', 'Requests, tools, and decisions'], ['Trace + metrics', 'Record steps and timings'], ['Investigate', 'Find where behavior changed']),
  'ai-gateways': choice('Put one controlled entry point before providers.', 'Routing and fallback follow your policy; limits and logs live at the shared entry point.',
    ['Gateway', 'Keys, routing, budgets, logs'], ['Provider A', 'Primary route'], ['Provider B', 'Alternate or fallback'], ['Local model', 'A route for suitable tasks']),
  'cost-optimization': choice('Spend less where the task allows it.', 'Check quality after each change; cheaper requests are not useful if they fail the task.',
    ['Measured workload', 'Find where the cost comes from'], ['Reuse work', 'Cache or batch requests'], ['Use less context', 'Keep the relevant material'], ['Smaller model', 'Use it where quality holds']),
  'local-inference': flow('Run the model on hardware you control.', 'Model size, precision, and context compete for memory on the same machine.',
    ['Model weights', 'Choose size and precision'], ['Your hardware', 'Runtime, memory, compute'], ['Local response', 'Measure speed and quality']),
  'operator-craft': flow('Brief well, inspect the work, own the decision.', 'The quality of working with a model depends on what you ask and what you verify.',
    ['Brief', 'Goal, context, constraints'], ['Model does work', 'Within the scope you gave'], ['Review + decide', 'Check before relying on it']),
  briefing: flow('Make success and the boundaries explicit.', 'Give the model enough information to work without inventing the missing requirements.',
    ['Goal + context', 'What and why'], ['Boundaries', 'Constraints and examples'], ['Acceptance check', 'What counts as done']),
  reviewing: flow('Trace claims back to something you can check.', 'Review the evidence and the result, not just how convincing the prose sounds.',
    ['Proposed work', 'An answer, edit, or action'], ['Independent checks', 'Sources, tests, constraints'], ['Your decision', 'Accept, correct, or reject']),
  delegating: choice('Decide which work can leave your hands.', 'Scope and review should match the consequence of a mistake.',
    ['Task + consequences', 'What could go wrong?'], ['Keep it', 'Judgment stays with you'], ['Delegate a draft', 'You review before use'], ['Delegate execution', 'Bound authority and check it']),
  trust: loop('Calibrate reliance from observed results.', 'Trust should be specific to a task and revised when evidence changes.',
    ['A bounded task', 'Set the stakes and checks'], ['Model does work', 'Within that scope'], ['Verify results', 'Record successes and misses'], ['Adjust reliance', 'Change scope or review depth']),
};

export interface PlacedNode extends ConceptNode { x: number; y: number; width: number; height: number }
export interface ConceptEdge { from: number; to: number; feedback?: boolean }
export function conceptEdges(shape: ConceptShape, count: number): ConceptEdge[] {
  if (shape === 'retrieval') return [{ from: 0, to: 2 }, { from: 1, to: 2 }, { from: 2, to: 3 }, { from: 3, to: 4 }];
  if (shape === 'harness') return [{ from: 0, to: 1 }, { from: 1, to: 2 }, { from: 2, to: 3 }, { from: 3, to: 4 }, { from: 4, to: 0, feedback: true }];
  if (shape === 'loop') return [{ from: 0, to: 1 }, { from: 1, to: 2 }, { from: 2, to: 3 }, { from: 3, to: 1, feedback: true }];
  if (shape === 'choice') return [1, 2, 3].map((to) => ({ from: 0, to }));
  if (shape === 'fork') return [1, 2, 3].flatMap((middle) => [{ from: 0, to: middle }, { from: middle, to: 4 }]);
  return Array.from({ length: count - 1 }, (_, i) => ({ from: i, to: i + 1 }));
}

export function conceptLayout(d: ConceptDiagram, mobile = false) {
  const width = mobile ? 340 : 960;
  const nodeWidth = mobile ? 254 : 228;
  const nodeHeight = 76;
  let points: [number, number][];
  if (mobile) {
    points = d.nodes.map((_, i) => [54, 44 + i * 110]);
  } else if (d.shape === 'retrieval') {
    points = [[28, 42], [28, 218], [366, 124], [704, 124], [704, 300]];
  } else if (d.shape === 'harness') {
    points = [[28, 100], [360, 100], [696, 42], [696, 218], [360, 270]];
  } else if (d.shape === 'loop') {
    points = [[28, 124], [360, 124], [696, 42], [696, 218]];
  } else if (d.shape === 'fork') {
    points = [[28, 142], [366, 26], [366, 142], [366, 258], [704, 142]];
  } else if (d.shape === 'choice') {
    points = [[120, 142], [612, 26], [612, 142], [612, 258]];
  } else {
    points = d.nodes.map((_, i) => [28 + i * 338, 80]);
  }
  const height = mobile ? 44 + d.nodes.length * 110 : d.shape === 'flow' ? 230 : d.shape === 'retrieval' ? 410 : d.shape === 'harness' ? 404 : 368;
  return { width, height, nodes: d.nodes.map((n, i): PlacedNode => ({ ...n, x: points[i][0], y: points[i][1], width: nodeWidth, height: nodeHeight })) };
}

export function conceptPath(a: PlacedNode, b: PlacedNode, mobile: boolean, feedback = false, branch?: 'split' | 'join'): string {
  if (mobile) {
    if (branch === 'join') return `M ${a.x + a.width} ${a.y + 38} H 326 V ${b.y + 38} H ${b.x + b.width + 4}`;
    if (branch === 'split') return `M ${a.x} ${a.y + 38} H 30 V ${b.y + 38} H ${b.x - 4}`;
    if (feedback || b.y - a.y > 115) {
      const lane = feedback ? 16 : 30;
      return `M ${a.x} ${a.y + 38} H ${lane} V ${b.y + 38} H ${b.x - 4}`;
    }
    return `M ${a.x + a.width / 2} ${a.y + a.height} V ${b.y - 5}`;
  }
  if (a.x === b.x) return `M ${a.x + a.width / 2} ${a.y + a.height} V ${b.y - 5}`;
  if (b.x > a.x) {
    const x1 = a.x + a.width, x2 = b.x - 5, y1 = a.y + 38, y2 = b.y + 38;
    return `M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`;
  }
  if (!feedback) {
    const x1 = a.x, x2 = b.x + b.width + 5, y1 = a.y + 38, y2 = b.y + 38;
    return `M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`;
  }
  // Return paths enter below the main flow, so they cannot obscure the outgoing arrow.
  const x1 = a.x, y1 = a.y + 38, x2 = b.x + b.width / 2, y2 = b.y + b.height + 5;
  return `M ${x1} ${y1} C ${x2} ${y1}, ${x2} ${y1}, ${x2} ${y2}`;
}
