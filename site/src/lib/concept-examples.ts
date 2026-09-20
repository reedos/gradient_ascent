import type { NamedEntry } from './content';

// Illustrations of a task, rather than claims about a specific vendor's capabilities.
// Product identities, URLs, verification, and lifecycle status stay in the registry.
export const practiceExamples: Record<string, [string, string]> = {
  'order-zero': ['Validate a part number', 'A fixed pattern checks the format and a database lookup finds the part. No model is needed.'],
  chat: ['Rewrite a short email', 'Paste your draft, ask for a clearer version, and review the reply before sending it.'],
  'prompt-engineering': ['Write a repeatable support reply', 'Specify the audience, tone, required facts, and an example of the response you want.'],
  'structured-output': ['Extract an invoice record', 'Ask for supplier, invoice number, date, and amount in a fixed JSON schema, then validate each field.'],
  'inference-time-reasoning': ['Work through a difficult calculation', 'Give the model more reasoning effort or compare several candidate solutions before accepting an answer.'],
  multimodal: ['Read an instrument display', 'Supply a photo and ask for the displayed value and units, then check them against the image.'],
  'context-engineering': ['Prepare a design review', 'Send the current requirements and relevant schematic notes, rather than every file and every old conversation.'],
  'embeddings-search': ['Find differently worded instructions', 'Search for “water use” and retrieve passages about “consumption,” then inspect the matches.'],
  rag: ['Ask a question about a manual', 'Retrieve the warranty passages, put them in the model request, and return an answer with source references.'],
  'knowledge-graphs': ['Trace a part to its warranty', 'Follow the part’s appliance model, then that model’s warranty class, retaining the source of each relationship.'],
  memory: ['Remember a project preference', 'Save the preferred units from an earlier conversation and retrieve them when preparing the next report.'],
  'prompt-chaining': ['Turn notes into a checked report', 'One prompt extracts facts, another drafts the report, and a final step checks its claims against the notes.'],
  routing: ['Sort incoming support requests', 'Send billing questions to one handler, technical questions to another, and uncertain cases to a person.'],
  parallelization: ['Review independent document sections', 'Run a fixed set of prompts at the same time, one per section, and combine their findings.'],
  'evaluator-optimizer': ['Revise a draft against a rubric', 'A writer produces a draft and a checker flags missed requirements. Feed the feedback into a bounded revision loop.'],
  'workflow-graphs': ['Build an approval workflow', 'Connect extraction, validation, review, and completion steps with explicit success and failure paths.'],
  'human-in-the-loop': ['Approve a proposed refund', 'The system prepares the refund, pauses for a person to review it, and proceeds only after approval.'],
  'function-calling': ['Look up a part price', 'The model requests lookup_part with a part number. Your code runs the lookup and returns the result.'],
  'code-execution': ['Calculate from a test log', 'The model writes a small calculation, a constrained environment runs it, and you inspect the result and errors.'],
  mcp: ['Connect an assistant to a document store', 'An MCP server exposes search and read tools; the host application decides which calls it permits.'],
  'computer-use': ['Fill a form in a browser', 'An agent reads the page, enters values, checks the changed screen, and pauses before a consequential submission.'],
  'single-agent': ['Investigate a support question', 'An agent decides which document to read next, uses its tools, and stops when it can answer or reaches a limit.'],
  'agent-harness': ['Run a coding task within boundaries', 'The model proposes a command. The harness checks permission, runs it in a sandbox, records the result, and builds the next request.'],
  'agentic-rag': ['Resolve conflicting specifications', 'An agent finds a manual, notices a later bulletin, searches again, and reconciles the evidence in its answer.'],
  'coding-agents': ['Fix a failing test', 'An agent reads the relevant code, makes an edit, runs tests, and uses their output to decide what to change next.'],
  skills: ['Apply a team’s report-writing procedure', 'The agent selects a report skill and loads its instructions, template, and checks when that task comes up.'],
  'voice-agents': ['Handle a spoken support request', 'The agent listens, responds aloud, and yields when the caller interrupts to correct a detail.'],
  'orchestrator-workers': ['Research a question with several parts', 'A lead splits the question, assigns subtasks to workers, and checks their findings before combining them.'],
  'agent-graphs': ['Hand research over to a writer', 'A supervisor sends the task to a researcher, then chooses whether more research or a writing pass is needed.'],
  'debate-review': ['Challenge a proposed conclusion', 'One agent writes an answer while another independently checks the evidence and identifies unsupported claims.'],
  'long-horizon': ['Carry a migration across work sessions', 'Save completed steps, outstanding work, and blockers so a later session can resume from a checkpoint.'],
  'agent-teammates': ['Prepare a recurring status update', 'A scheduled run checks new work, drafts a summary, and queues anything requiring approval for a person.'],
  'organizations-swarms': ['Coordinate several specialist roles', 'Research, execution, and review agents share a task board with clear ownership and per-role limits.'],
  embodied: ['Move a gripper to a target', 'A model proposes a movement, a controller enforces safe bounds, and sensors report the actual new position.'],
  evals: ['Compare two support prompts', 'Run both on the same labeled questions, grade with the same criteria, and inspect where the results differ.'],
  'eval-frameworks': ['Repeat a regression evaluation', 'A runner loads saved cases, calls each candidate system, applies graders, and records comparable reports.'],
  adaptation: ['Improve extraction for your documents', 'Identify the failure first, then test whether better examples, a revised prompt, or model training addresses it.'],
  'fine-tuning': ['Learn a recurring response format', 'Train on reviewed input-output pairs and check the adapted model on examples excluded from training.'],
  distillation: ['Train a smaller task specialist', 'Have a larger teacher generate demonstrations, verify them, and train a smaller student on the accepted examples.'],
  'synthetic-data': ['Expand a labeled question set', 'Generate candidate questions, remove duplicates, verify answers, and keep evaluation data separate.'],
  'prompt-optimization': ['Search for clearer extraction instructions', 'Score candidate prompts on development examples, choose a winner, and evaluate it on untouched cases.'],
  safety: ['Handle an injected document instruction', 'Treat the retrieved text as data, keep tool authority separate, and record any blocked action.'],
  guardrails: ['Check a response before release', 'Detect forbidden content or missing required fields and route a flagged response to a retry or a person.'],
  'red-teaming': ['Probe a tool permission boundary', 'Try controlled adversarial requests, document any bypass, fix it, and keep the attempt as a regression case.'],
  ops: ['Operate a support assistant', 'Track failures, response time, and spend, then investigate regressions and roll back changes when needed.'],
  observability: ['Find why an answer went wrong', 'Follow the trace from the final answer back through retrieval, tool results, and model requests.'],
  'ai-gateways': ['Apply one policy across providers', 'Route requests through a shared entry point that handles credentials, budgets, logging, and permitted fallbacks.'],
  'cost-optimization': ['Reduce repeated work', 'Cache stable material or use a smaller model for easy cases, then rerun the quality checks.'],
  'local-inference': ['Run a model on a workstation', 'Choose weights and precision that fit the available memory, then measure performance on your own workload.'],
  'operator-craft': ['Use a model for a draft, own the outcome', 'Give it a clear brief, inspect the result against evidence, and decide what is ready to use.'],
  briefing: ['Specify a test-plan draft', 'Supply requirements, available equipment, limits, and what a complete test plan must contain.'],
  reviewing: ['Verify a measurement writeup', 'Compare every reported value and conclusion with the test log, calculations, and stated uncertainty.'],
  delegating: ['Delegate preparation, retain approval', 'Ask the model to draft a purchasing comparison while a person checks the evidence and makes the purchase decision.'],
  trust: ['Adjust review depth from evidence', 'Track how a model performs on a specific recurring task before deciding which parts can receive lighter review.'],
};

// These explain the concrete harness examples highlighted by the page's own sources.
const harnessNotes: Record<string, string> = {
  'deep-agents': 'A ready-made harness with context management, file tools, subagents, and human approval built on LangChain and LangGraph.',
  'strands-agents': 'An agent SDK with a model-driven loop, tool execution, sessions, execution limits, hooks, and tracing.',
  'langgraph': 'A lower-level runtime for building a custom harness with persisted state, durable execution, and human checkpoints.',
  'google-adk': 'A framework for building agents with tools, session state, and multi-agent coordination.',
  'pydantic-ai': 'A typed Python agent framework: define tools and validated outputs, then build the surrounding application policies.',
  'ms-agent-framework': 'Microsoft’s framework for building agents and coordinating multi-agent workflows in Python and .NET.',
  'crewai': 'A framework for coordinating agents, tasks, and flows. It supplies orchestration pieces for a custom agent system.',
  'claude-code': 'A complete coding-agent product that packages the model with a tool loop, repository context, and permission controls.',
  'claude-agent-sdk': 'Provides Claude Code’s agent loop, tools, and context management as a library, with permissions and hooks.',
  'openai-agents-sdk': 'Building blocks for an agent runtime: the run loop, tools, handoffs, sessions, guardrails, and tracing.',
  codex: 'A coding-agent product whose surrounding harness controls tool execution, sandbox boundaries, and approval checks.',
};

// Editorial order puts familiar entry points first; every verified match is still returned.
const featured: Record<string, string[]> = {
  'agent-harness': ['claude-agent-sdk', 'openai-agents-sdk', 'deep-agents', 'strands-agents', 'claude-code', 'codex', 'langgraph', 'google-adk', 'ms-agent-framework', 'crewai', 'pydantic-ai'],
  chat: ['chatgpt', 'claude-app', 'gemini-app', 'microsoft-copilot', 'grok', 'deepseek-chat'],
  'coding-agents': ['claude-code', 'codex', 'github-copilot', 'cursor', 'gemini-cli', 'cline', 'aider', 'devin', 'replit-agent'],
  rag: ['llamaindex', 'langchain', 'haystack', 'gemini-notebook', 'perplexity', 'glean'],
  'embeddings-search': ['pgvector', 'pinecone', 'qdrant', 'weaviate', 'chroma', 'milvus', 'faiss'],
  'single-agent': ['claude-agent-sdk', 'openai-agents-sdk', 'google-adk', 'pydantic-ai', 'strands-agents', 'vercel-ai-sdk'],
  'agent-graphs': ['langgraph', 'openai-agents-sdk', 'google-adk', 'ms-agent-framework', 'crewai'],
  'workflow-graphs': ['langgraph', 'n8n', 'dify', 'flowise', 'langflow'],
  'local-inference': ['ollama', 'lm-studio', 'llama-cpp', 'vllm', 'sglang', 'mlx'],
  evals: ['promptfoo', 'braintrust', 'langsmith', 'deepeval', 'ragas', 'phoenix'],
  observability: ['langsmith', 'langfuse', 'phoenix', 'helicone', 'opentelemetry'],
};

export function concreteNames(slug: string, entries: NamedEntry[]) {
  const eligible = entries.filter((n) => n.verified && !n.retirement);
  const priority = featured[slug] ?? [];
  const sorted = [...eligible].sort((a, b) => {
    const rank = (id: string) => priority.includes(id) ? priority.indexOf(id) : priority.length;
    return rank(a.id) - rank(b.id);
  });
  return sorted.map((n) => ({ ...n, explanation: slug === 'agent-harness' ? harnessNotes[n.id] : undefined }));
}
