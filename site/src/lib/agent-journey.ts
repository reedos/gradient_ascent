export const agentJourney = [
  {
    "title": "Language models become conversational",
    "short": "Chat",
    "added": "Language models generate responses from instructions and conversation history. A chat interface makes that capability accessible through ordinary language.",
    "shift": "A person can ask follow-up questions and refine an answer through conversation. The basic interaction is still a request followed by a response.",
    "limit": "The model alone cannot look up current information or act in another system. Fluent responses can still be wrong.",
    "flow": [
      "Message + conversation",
      "Language model",
      "Response"
    ],
    "next": "A model’s training cannot contain every private document or stay current with every change."
  },
  {
    "title": "Answers gain access to external information",
    "short": "Context",
    "added": "Applications bring documents, search results, and stored information into the model’s context: the information available for its current response.",
    "shift": "Retrieval-augmented generation (RAG) connects search to generation. Answers can use information outside the model’s training and point back to sources.",
    "limit": "Retrieval does not retrain the model. Missing, stale, or misleading source material can still lead to a poor answer.",
    "flow": [
      "Search or stored information",
      "Context + model",
      "Answer with evidence"
    ],
    "next": "A single response is useful, but repeatable processes often need several transformations and checks."
  },
  {
    "title": "Model calls become parts of software workflows",
    "short": "Workflow",
    "added": "Developers connect model calls with ordinary code: fixed steps, branches, validation, and retries. Language generation becomes a component in a larger process.",
    "shift": "Software can extract information, transform it, check it, and pass it onward. Code determines which step runs next.",
    "limit": "A workflow can be scheduled and complex without being an agent. Its routing rules remain defined by software.",
    "flow": [
      "Input",
      "Code-directed model steps",
      "Checked output"
    ],
    "next": "Fixed workflows determine the actions in advance. Tool calling lets a model request an action based on the information it receives."
  },
  {
    "title": "Models can request actions through tools",
    "short": "Tools",
    "added": "Tool interfaces let a model produce a structured request to search, calculate, run code, or interact with another application. Software executes the request and returns the result.",
    "shift": "The connection becomes two-way: the system can obtain new information or change external state, rather than only produce text.",
    "limit": "The model proposes the call; software controls execution, permissions, and approvals. Tool access alone does not create an autonomous loop.",
    "flow": [
      "Model requests a tool",
      "Software executes it",
      "Result returns to model"
    ],
    "next": "A tool result can reveal another question or another action. Feeding that result back makes an ongoing decision loop possible."
  },
  {
    "title": "Tool use becomes an agent loop",
    "short": "Agent",
    "added": "The system repeatedly gives the model the current goal, context, and action results. The model chooses another action, revises its approach, or signals that it is finished.",
    "shift": "Control over the next step shifts from a fully prescribed sequence toward decisions made during the run. The surrounding software still enforces limits and executes tools.",
    "limit": "Agents can repeat mistakes or stop too early. Their reliability depends on the model, available evidence, tools, checks, and stopping rules.",
    "flow": [
      "Choose an action",
      "Execute through tools",
      "Observe → choose again"
    ],
    "next": "Agent loops can also be coordinated: work and review can be distributed across separate contexts."
  },
  {
    "title": "Agents can coordinate with other agents",
    "short": "Team · optional",
    "added": "Multiple agent loops exchange tasks and findings. A lead agent or coordination framework can divide work among specialists and combine their results.",
    "shift": "Separate contexts allow specialization, parallel investigation, and independent review. This extends the architecture beyond one agent’s working context.",
    "limit": "Coordination adds cost and new failure modes. Teams are optional; a single agent can also become always-on.",
    "flow": [
      "Coordinator",
      "Specialist agents",
      "Findings return to coordinator"
    ],
    "next": "Both single agents and teams need persistence to continue beyond an individual run."
  },
  {
    "title": "Agent systems persist across sessions",
    "short": "Always-on",
    "added": "Persistent storage, schedules, event triggers, and a continuing runtime let an agent system start or resume work without a new chat message each time.",
    "shift": "Saved state connects sessions. Events initiate work, the agent acts within its permissions, and progress is recorded for a later run.",
    "limit": "Always-on does not mean continuously thinking. Software starts runs and preserves records; approval policies, monitoring, and stop controls remain essential.",
    "flow": [
      "Schedule or event",
      "Load state → run agent",
      "Save state → wait"
    ],
    "next": ""
  }
];
