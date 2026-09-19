"""The tools the model may call, and the code that runs them.

Kept out of `examples/function_calling/run.py` and `examples/agentic_rag/run.py` so each of
those files is the technique and nothing else: the reader following level 4 or level 5 on the
page should see the control flow, not a keyword searcher.

A tool is a definition (the JSON the model is shown) plus a function (what the code runs when
the model asks for it). Running one is always the program's job, so nothing here ever records a
`decided_by: "model"` step; see `examples/common/trace.py` for why that line is where it is.

Level 4 and level 5 are given deliberately different search tools. Level 4's returns the full
text of the top sections, because it gets one call and then has to answer. Level 5's returns
titles and citations only, so the model has to decide what is worth reading and call `read` on
it: that second decision is what makes the loop a loop rather than a slower level 4.
"""
from __future__ import annotations

from evals.corpus import Section, bm25_search, lookup_part

SEARCH_K = 3

SEARCH_TOOL = {
    "name": "search",
    "description": "Keyword search over the Halvorsen document set; returns the top matching sections.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}

LOOKUP_PART_TOOL = {
    "name": "lookup_part",
    "description": "Look up one part by its HLV part number in the parts list.",
    "parameters": {"type": "object", "properties": {"part_number": {"type": "string"}}, "required": ["part_number"]},
}

SEARCH_TITLES_TOOL = {
    "name": "search",
    "description": "Keyword search over the Halvorsen document set; returns matching titles and citations, not full text.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}

READ_TOOL = {
    "name": "read",
    "description": "Get the full text of one section by its citation, e.g. dw300-manual#3.",
    "parameters": {"type": "object", "properties": {"cite": {"type": "string"}}, "required": ["cite"]},
}

# What a tool hands back: the text the model sees, and the citations the code can vouch for.
ToolResult = tuple[str, list[str]]


def search_full_text(sections: dict[str, Section], query: str, k: int = SEARCH_K) -> ToolResult:
    hits = bm25_search(sections, query, k=k)
    text = "\n\n".join(f"[{s.cite}] {s.title}\n{s.text}" for s, _ in hits)
    return (text or "no results"), [s.cite for s, _ in hits]


def search_titles(sections: dict[str, Section], query: str, k: int = SEARCH_K) -> ToolResult:
    hits = bm25_search(sections, query, k=k)
    return ("\n".join(f"{s.cite}: {s.title}" for s, _ in hits) or "no results"), []


def read_section(sections: dict[str, Section], cite: str) -> ToolResult:
    section = sections.get(cite)
    if section is None:
        return f"{cite} not found", []
    return f"[{section.cite}] {section.title}\n{section.text}", [section.cite]


def part_line(sections: dict[str, Section], part_number: str) -> ToolResult:
    """The parts list is the one document with a row-per-part shape, so a part number can be
    answered exactly rather than by search. Cites the parts-list section the row came from."""
    line = lookup_part(part_number)
    if not line:
        return f"{part_number} not found in the parts list", []
    cite = next((c for c, s in sections.items() if c.startswith("parts-list") and part_number in s.text), None)
    return line, [cite] if cite else []


def unknown_tool(name: str) -> ToolResult:
    """A model may ask for a tool that does not exist. Say so and let it try again, rather than
    raising: an agent that can recover from its own mistake is the thing being measured."""
    return f"unknown tool: {name}", []
