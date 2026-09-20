"""Level 3: workflow graphs. A tiny dict-based graph runner: nodes are plain functions that take
the shared state and return an updated state, edges are plain functions that read that state and
return the id of the next node (or None to stop), and the runner writes a checkpoint after every
node. This is the same draft/check/revise loop as write-and-check, plus one branch a single loop
cannot express as cleanly: if retrieval finds nothing, the graph goes straight to a dead end
instead of drafting from zero sources.

`state`'s durable fields are all plain values — strings, an int, a list of citation strings —
never a Section object or anything else that is not already JSON. A node may also set a
leading-underscore field (`_completion`, holding token counts and timing for the trace) that the
runner reads and strips before recording the checkpoint below; only the underscore-free fields
are what "checkpoint after every node" means in practice. `json.dumps` on that subset never
fails, so writing it to a database between nodes, and resuming a crashed run from the last one
written, is not a redesign, just a `json.dump`/`json.load` at the point the checkpoint step
already marks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from evals.corpus import DEFAULT_CORPUS_DIR, Section, bm25_search, load_sections
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer
from examples.common.types import cited_sources

LEVEL = 3
RETRIEVE_K = 4
MAX_REVISIONS = 2
PASS_TOKEN = "ALL CITATIONS SUPPORTED"
DRAFT_SYSTEM = (
    "You answer questions about Halvorsen appliances using only the numbered sources below. End "
    "your answer with a line starting 'Sources:' listing the citations, like 'dw300-manual#3', "
    "that you used."
)
CHECK_SYSTEM = (
    "You check a draft answer against the source passages it was given. List every citation the "
    "draft claims that does NOT actually appear among the sources below, one per line, as "
    f"'MISSING: <citation>'. If every citation the draft claims is one of the sources, reply with "
    f"exactly '{PASS_TOKEN}' and nothing else."
)
REVISE_SYSTEM = (
    "Revise your previous answer to fix the citation problems named below. Use only the sources "
    "given. Keep the same 'Sources:' line format."
)
State = dict


def _sources_block(cites: list[str], sections: dict[str, Section]) -> str:
    return "\n\n".join(f"[{c}] {sections[c].title}\n{sections[c].text}" for c in cites)


def _node_retrieve(state: State, sections: dict[str, Section], model: Model) -> State:
    hits = [s for s, score in bm25_search(sections, state["question"], k=RETRIEVE_K) if score > 0]
    state["source_cites"] = [s.cite for s in hits]
    return state


def _node_no_match(state: State, sections: dict[str, Section], model: Model) -> State:
    del sections, model
    state["draft_text"] = "None of the retrieved sections cover this question."
    return state


def _node_draft(state: State, sections: dict[str, Section], model: Model) -> State:
    prompt = f"Sources:\n\n{_sources_block(state['source_cites'], sections)}\n\nQuestion: {state['question']}"
    completion = model.complete([Message(role="system", content=DRAFT_SYSTEM), Message(role="user", content=prompt)], max_tokens=400)
    state["draft_text"] = completion.text
    state["_completion"] = completion
    return state


def _node_check(state: State, sections: dict[str, Section], model: Model) -> State:
    prompt = f"Sources:\n\n{_sources_block(state['source_cites'], sections)}\n\nDraft answer:\n{state['draft_text']}"
    completion = model.complete([Message(role="system", content=CHECK_SYSTEM), Message(role="user", content=prompt)], max_tokens=200)
    verdict = completion.text.strip()
    state["verdict"] = "ok" if PASS_TOKEN in verdict.upper() else verdict
    state["_completion"] = completion
    return state


def _node_revise(state: State, sections: dict[str, Section], model: Model) -> State:
    state["revisions"] += 1
    prompt = (
        f"Sources:\n\n{_sources_block(state['source_cites'], sections)}\n\nQuestion: {state['question']}\n\n"
        f"Previous answer:\n{state['draft_text']}\n\nProblems to fix:\n{state['verdict']}"
    )
    completion = model.complete([Message(role="system", content=REVISE_SYSTEM), Message(role="user", content=prompt)], max_tokens=400)
    state["draft_text"] = completion.text
    state["_completion"] = completion
    return state


NODES: dict[str, Callable[[State, dict, Model], State]] = {
    "retrieve": _node_retrieve,
    "no_match": _node_no_match,
    "draft": _node_draft,
    "check": _node_check,
    "revise": _node_revise,
}


def _edge_from_retrieve(state: State) -> str | None:
    return "draft" if state["source_cites"] else "no_match"


def _edge_from_check(state: State) -> str | None:
    if state["verdict"] == "ok" or state["revisions"] >= MAX_REVISIONS:
        return None
    return "revise"


EDGES: dict[str, Callable[[State], str | None]] = {
    "retrieve": _edge_from_retrieve,
    "no_match": lambda state: None,
    "draft": lambda state: "check",
    "check": _edge_from_check,
    "revise": lambda state: "check",
}


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
) -> Answer:
    del embedder  # retrieval here is keyword search, not a vector index
    sections = load_sections(corpus_dir)
    state: State = {"question": question, "source_cites": [], "draft_text": "", "verdict": None, "revisions": 0}

    node_id: str | None = "retrieve"
    while node_id is not None:
        state = NODES[node_id](state, sections, model)
        completion = state.pop("_completion", None)
        if completion is not None:
            tracer.record(
                kind="model", decided_by="code", title=f"Node: {node_id}", detail=completion.text[:200],
                tokens_in=completion.tokens_in, tokens_out=completion.tokens_out, ms=completion.ms,
            )
        else:
            tracer.record(kind="code", decided_by="code", title=f"Node: {node_id}", detail=", ".join(state["source_cites"]) or "none")
        next_id = EDGES[node_id](state)
        tracer.record(
            kind="code", decided_by="code", title=f"Checkpoint after '{node_id}'",
            detail=f"revisions={state['revisions']} verdict={state.get('verdict')!r} -> next: {next_id or 'stop'}",
        )
        node_id = next_id

    citations = cited_sources(state["draft_text"])
    return Answer(text=state["draft_text"], citations=citations, retrieved_sources=state["source_cites"])
