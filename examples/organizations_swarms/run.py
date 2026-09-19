"""Level 7: organizations of agents. Three roles share one task board; a coordinator model
decides which open task goes to which role — `decided_by: "model"` — and a fixed, code-side
budget caps how many tasks each role may be assigned per run, no matter what the coordinator
asks for. `Board.tasks` is the one shared state all three roles and the coordinator read and
write; claiming a task is atomic in code, so the same task can never end up assigned twice even
if the coordinator's own output proposes it twice in one call.

What each role would actually do with an assigned task — search, draft, check — is out of scope
here on purpose: a role agent uses whatever pattern in this manual fits its own job (a single
agent, a fixed workflow). This example isolates only the part specific to an organization of
agents: the shared board, and the coordinator's assignment under a budget it does not control.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from examples.common.model import Message, Model
from examples.common.trace import Tracer

LEVEL = 7
ROLES = ("researcher", "writer", "reviewer")
BUDGET_PER_ROLE = 2  # a role cannot be assigned more than this many tasks in one run, no matter what the coordinator proposes

Status = Literal["open", "claimed", "done"]

ASSIGN_TOOL = {
    "name": "assign",
    "description": "Assign one open task to one role.",
    "parameters": {
        "type": "object",
        "properties": {"task_id": {"type": "string"}, "role": {"type": "string", "enum": list(ROLES)}},
        "required": ["task_id", "role"],
    },
}
SYSTEM = (
    "You coordinate three roles -- researcher, writer, reviewer -- over a shared task board. "
    "Call assign(task_id, role) once for each open task you want to hand out this round. A role "
    "over its budget for this round cannot take more work; say so in text instead of calling "
    "assign for it."
)


@dataclass
class Task:
    id: str
    description: str
    status: Status = "open"
    assigned_to: str | None = None


@dataclass
class Board:
    """The one piece of state every role and the coordinator share. It outlives a round: the
    tasks and their claims persist, which is what makes the organization standing rather than
    assembled for one job. `assigned_count` does not -- see `coordinate`."""

    tasks: list[Task]
    assigned_count: dict[str, int] = field(default_factory=lambda: {r: 0 for r in ROLES})

    def get(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)


def _digest(board: Board) -> str:
    open_tasks = "\n".join(f"- {t.id}: {t.description}" for t in board.tasks if t.status == "open") or "(none open)"
    budgets = ", ".join(f"{r}: {BUDGET_PER_ROLE - board.assigned_count[r]} left" for r in ROLES)
    return f"Open tasks:\n{open_tasks}\n\nBudget remaining this round: {budgets}"


def coordinate(board: Board, model: Model, tracer: Tracer) -> list[dict]:
    """One coordination round. Returns the assignments actually made — which can be fewer than
    the coordinator asked for, since every proposed assignment is checked against the board and
    the budget before it counts.

    The budget is per round and refills here, at the start of each one. Claims are not: a task
    claimed in an earlier round is still claimed, because the board persists and the counters do
    not. Both facts have to be tested, and testing the second one needs a round that still has
    an open task to offer -- otherwise the round returns before the model is ever called and the
    test passes without checking anything.
    """
    board.assigned_count = {r: 0 for r in ROLES}  # the budget is per round, so it starts full
    if not any(t.status == "open" for t in board.tasks):
        return []

    messages = [Message(role="system", content=SYSTEM), Message(role="user", content=_digest(board))]
    completion = model.complete(messages, tools=[ASSIGN_TOOL], max_tokens=200)
    proposed = list(completion.tool_calls)
    desc = ", ".join(f"assign({c.arguments.get('task_id')}, {c.arguments.get('role')})" for c in proposed) or "no assignments proposed"
    tracer.record(
        kind="model", decided_by="model", title="Coordinator assigns open tasks to roles",
        detail=desc, tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )

    made: list[dict] = []
    for call in proposed:
        task_id = str(call.arguments.get("task_id", ""))
        role = str(call.arguments.get("role", ""))
        task = board.get(task_id)
        if task is None or task.status != "open":
            tracer.record(kind="code", decided_by="code", title="Refuse: task is not open", detail=f"{task_id} (already claimed, or does not exist)")
            continue
        if role not in ROLES:
            tracer.record(kind="code", decided_by="code", title="Refuse: no such role", detail=f"{role} for {task_id} (roles are fixed in code, not named by the coordinator)")
            continue
        if board.assigned_count[role] >= BUDGET_PER_ROLE:
            tracer.record(kind="code", decided_by="code", title="Refuse: role is over budget", detail=f"{role} for {task_id}")
            continue
        task.status = "claimed"
        task.assigned_to = role
        board.assigned_count[role] += 1
        tracer.record(kind="code", decided_by="code", title="Claim the task for the role", detail=f"{task_id} -> {role}")
        made.append({"task": task_id, "role": role})
    return made


# Shared by `python -m examples.organizations_swarms` and by `run` below, so a coordination
# round always has more than one thing to assign.
SAMPLE_TASKS = [
    Task(id="T1", description="Look up the DW-300's warranty terms"),
    Task(id="T2", description="Draft a summary of what changed in the latest service bulletin"),
    Task(id="T3", description="Check that the drafted summary cites the sections it uses"),
]


def run(question: str, model: Model, tracer: Tracer) -> list[dict]:
    """Recordable entry point for `record_trace.py`: one coordination round over the three fixed
    sample tasks plus one open task built from `question`, the same board
    `python -m examples.organizations_swarms`'s `main` builds by hand."""
    board = Board(tasks=[*SAMPLE_TASKS, Task(id="T4", description=question)])
    return coordinate(board, model, tracer)
