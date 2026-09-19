"""Level 7: long-running tasks. A queue of questions is worked through across many separate
sessions, each a fresh call to `run_session` standing in for a fresh process on a fresh context
window. Nothing here waits for a person to start a session: a scheduler calling `run_session` on
a timer is the trigger, and that call is `decided_by: "code"` -- the run starts on its own.

A session never sees the previous session's transcript. It rebuilds its context from
`QueueState.notes`, a short list of one-line compactions written by earlier sessions, the way
Anthropic's own writing on long-running agents describes structured note-taking: the agent
"regularly writes notes persisted to memory outside of the context window", read back in on a
later turn. The state itself -- the queue, the notes, the finished answers, the ones a person
still needs to look at -- is checkpointed to a plain JSON file after every session, write-then-
replace, so a crash between sessions never leaves a half-written file.

What that buys, exactly, because it is easy to claim more: an interrupted session writes nothing,
so the checkpoint holds every finished answer and holds each one once. The interrupted question
goes back to the front of the queue and is asked again, so the model call itself can happen twice
-- the work is at-least-once, the record is once. That is safe here only because the sole thing a
session changes outside its own memory is the checkpoint. A session that also sent an email would
need the email to be idempotent, or a marker written before sending.


The one thing the model decides in a session is what a level-4 function call decides: which of
two actions to take. Given the sources, it either answers, or calls `flag_for_review` instead of
guessing -- the one point where this run checks in with a person rather than running unattended
straight through the queue.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from evals.corpus import DEFAULT_CORPUS_DIR, bm25_search, load_sections
from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 7
RETRIEVE_K = 3
MAX_NOTES = 6  # the oldest note drops first: this is a compaction, not a growing log
SYSTEM = (
    "You answer questions about Halvorsen appliances using only the sources given. Call "
    "answer(text, citations) if the sources support a confident answer. Call "
    "flag_for_review(reason) instead if the sources disagree with each other or say nothing "
    "useful about the question -- do not guess."
)
ANSWER_TOOL = {
    "name": "answer",
    "description": "Give the final answer to the queued question.",
    "parameters": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "citations": {"type": "array", "items": {"type": "string"}}},
        "required": ["text", "citations"],
    },
}
FLAG_TOOL = {
    "name": "flag_for_review",
    "description": "Hand this question to a person instead of guessing.",
    "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
}
TOOLS = [ANSWER_TOOL, FLAG_TOOL]


class CheckpointError(RuntimeError):
    """The checkpoint file exists but cannot be read as a `QueueState`."""


class ConcurrentSessionError(RuntimeError):
    """Another session checkpointed while this one was working."""


@dataclass
class QueueState:
    """Everything checkpointed to `state_path` between sessions. `notes`, not `answers` or
    `queue`, is what a fresh session's prompt is built from -- see `run_session`."""

    queue: list[str]
    notes: list[str] = field(default_factory=list)
    answers: dict[str, dict] = field(default_factory=dict)
    pending: dict[str, str] = field(default_factory=dict)  # question -> reason a person must resolve
    sessions_run: int = 0

    @classmethod
    def load(cls, path: Path, *, questions: list[str]) -> QueueState:
        """Read the checkpoint, or start a fresh queue if there is none yet. A file that exists
        but cannot be read is an error, never a fresh start: silently starting over would throw
        away a queue and re-answer everything already answered, which is the expensive way to
        lose work. Loud and unresumed beats quiet and wrong."""
        if not path.exists():
            return cls(queue=list(questions))
        try:
            state = cls(**json.loads(path.read_text(encoding="utf-8")))
            for name, want in (("queue", list), ("notes", list), ("answers", dict), ("pending", dict), ("sessions_run", int)):
                if not isinstance(getattr(state, name), want):
                    raise TypeError(f"{name} is {type(getattr(state, name)).__name__}, not {want.__name__}")
        except Exception as exc:
            raise CheckpointError(f"{path} is not a readable checkpoint ({exc}); repair or remove it rather than starting the queue over") from exc
        return state

    def save(self, path: Path, *, expect_sessions_run: int | None = None) -> None:
        """Write the checkpoint by replacing a temp file, so a process killed mid-write never
        leaves the next session a half-written file to load. The temp file carries this
        process's id, so two writers never share one.

        `expect_sessions_run` is the counter this session read when it started. If the file no
        longer holds it, another session checkpointed in the meantime and this one refuses
        rather than overwrite work it never saw. That is a check before a write, not a lock: it
        catches overlapping scheduled sessions, it does not make them safe. Sessions that must
        genuinely run at the same time need a lock or a database, not this.
        """
        if expect_sessions_run is not None and path.exists():
            on_disk = json.loads(path.read_text(encoding="utf-8")).get("sessions_run")
            if on_disk != expect_sessions_run:
                raise ConcurrentSessionError(
                    f"{path} moved from session {expect_sessions_run} to {on_disk} while this session was working; nothing was written"
                )
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        # newline="\n" explicitly: on Windows the default would translate every \n in the JSON to
        # \r\n, so the same queue would checkpoint to different bytes on different machines.
        tmp.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)


def run_session(
    state_path: Path,
    model: Model,
    tracer: Tracer,
    *,
    questions: list[str],
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
) -> Answer | None:
    """One scheduled session. Returns the answer it produced, or None if it flagged the question
    for a person, or if the queue was already empty."""
    tracer.record(kind="code", decided_by="code", title="Scheduler starts a session", detail="no person asked for this run")
    state = QueueState.load(state_path, questions=questions)
    if not state.queue:
        return None
    started_from = state.sessions_run  # what the checkpoint must still say when this session writes
    state.sessions_run += 1
    question = state.queue[0]

    sections = load_sections(corpus_dir)
    sources = [s for s, score in bm25_search(sections, question, k=RETRIEVE_K) if score > 0]
    tracer.record(kind="code", decided_by="code", title="Retrieve sources for the next queued question", detail=", ".join(s.cite for s in sources) or "none")

    notes_block = "\n".join(f"- {n}" for n in state.notes) or "(no notes yet)"
    blocks = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s in sources)
    messages = [
        Message(role="system", content=SYSTEM),
        Message(role="user", content=f"Notes from earlier sessions:\n{notes_block}\n\nSources:\n\n{blocks}\n\nQuestion: {question}"),
    ]
    tracer.record(kind="code", decided_by="code", title="Rebuild context from notes, not the transcript", detail=f"{len(state.notes)} notes carried forward, no prior session's messages included")

    completion = model.complete(messages, tools=TOOLS, max_tokens=300)
    call = completion.tool_calls[0] if completion.tool_calls else None
    call_desc = f"{call.name}({json.dumps(call.arguments, sort_keys=True)})" if call else "(no tool call)"
    tracer.record(
        kind="model", decided_by="model", title="Model decides whether to answer or flag this question",
        detail=call_desc, tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
    )

    if call and call.name == "flag_for_review":
        reason = str(call.arguments.get("reason", "unspecified"))
        state.pending[question] = reason
        state.queue.pop(0)
        tracer.record(kind="code", decided_by="code", title="Hand the question to a person", detail=reason)
        result = None
    else:
        text = str(call.arguments.get("text", "")) if call else completion.text
        citations = list(call.arguments.get("citations", [])) if call else []
        state.answers[question] = {"text": text, "citations": citations}
        state.notes.append(f"{question} -> {text[:80]}")
        state.notes = state.notes[-MAX_NOTES:]
        state.queue.pop(0)
        tracer.record(kind="code", decided_by="code", title="Record the answer and compact a note", detail=text[:120])
        result = Answer(text=text, citations=citations)

    tracer.record(kind="code", decided_by="code", title="Checkpoint the queue to disk", detail=f"{len(state.queue)} left in queue, session {state.sessions_run}")
    state.save(state_path, expect_sessions_run=started_from)
    return result


def resolve(state_path: Path, question: str, note: str, tracer: Tracer) -> None:
    """A person resolves one flagged question, whenever they get to it -- not on a schedule.
    Writes the answer into the same checkpoint file a later session's notes are built from."""
    state = QueueState.load(state_path, questions=[])
    reason = state.pending.pop(question, "unspecified")
    tracer.record(kind="code", decided_by="code", title="Person resolves a flagged question", detail=f"was flagged: {reason}")
    state.answers[question] = {"text": note, "citations": []}
    state.notes.append(f"{question} -> {note[:80]}")
    state.notes = state.notes[-MAX_NOTES:]
    state.save(state_path, expect_sessions_run=state.sessions_run)


def run(question: str, model: Model, tracer: Tracer) -> Answer | None:
    """Recordable entry point for `record_trace.py`: one session against a fresh checkpoint file
    in a new temp directory, the same kind of fresh state `python -m examples.long_horizon`'s
    `main` builds when no `--state` is given (see `_fresh_state_path` in `__main__.py`)."""
    state_path = Path(tempfile.mkdtemp(prefix="long_horizon_")) / "state.json"
    return run_session(state_path, model, tracer, questions=[question])
