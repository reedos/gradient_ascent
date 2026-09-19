"""Level 5: skills. A small registry holds three skills, each a short description (always in
context) and a longer body (loaded only when chosen). The model reads the descriptions, decides
which skill fits the question, and calls `load_skill` to bring its body into context; your code
runs the lookup and appends the body; the model then continues with that body available and
decides whether it needs another skill or is ready to answer.

Choosing a skill, and the decision to stop, are `decided_by: "model"`; looking a skill up and
loading its body into the conversation are always `decided_by: "code"`, the same split every
level-5 example on this site makes between the model's choices and the code that carries them
out. See this page's Use it lane for how the makers document progressive disclosure and the
security point that a skill is instructions written by someone else.
"""
from __future__ import annotations

from dataclasses import dataclass

from examples.common.agent_loop import force_final, record_completion
from examples.common.model import Embedder, Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_STEPS = 3
MAX_TOKENS = 1500


@dataclass(frozen=True)
class Skill:
    name: str
    description: str  # level 1: always in context
    body: str  # level 2: loaded only when the model chooses this skill


SKILLS: dict[str, Skill] = {
    "warranty-checklist": Skill(
        name="warranty-checklist",
        description="Use when a question asks whether something is covered under warranty, or for how long.",
        body=(
            "1. State the warranty length that applies.\n"
            "2. Check whether anything about this case voids it.\n"
            "3. Say plainly whether the item is covered."
        ),
    ),
    "unit-conversion": Skill(
        name="unit-conversion",
        description="Use when a question needs a measurement converted between units, such as gallons to liters.",
        body="Multiply gallons by 3.785 for liters. Multiply inches by 2.54 for centimeters. Show both figures.",
    ),
    "citation-style": Skill(
        name="citation-style",
        description="Use when formatting how a source should be cited in an answer, independent of what it says.",
        body="Cite a source as file#section, e.g. dw300-manual#6. Never cite a section you did not use.",
    ),
}
LOAD_SKILL_TOOL = {
    "name": "load_skill",
    "description": "Load the full instructions for one skill by name.",
    "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
}


def _skill_list(registry: dict[str, Skill]) -> str:
    return "\n".join(f"- {s.name}: {s.description}" for s in registry.values())


def run(
    question: str,
    model: Model,
    embedder: Embedder | None,
    tracer: Tracer,
    *,
    registry: dict[str, Skill] = SKILLS,
    max_steps: int = MAX_STEPS,
    max_tokens: int = MAX_TOKENS,
) -> Answer:
    del embedder  # skills are loaded from the registry below, not retrieved from the corpus
    listing = _skill_list(registry)
    tracer.record(kind="code", decided_by="code", title="List skill descriptions (always in context)", detail=listing)
    system = (
        "Answer the question. These skills are available; each description says what it is for. "
        "Call load_skill with a skill's name if one of them applies before answering:\n" + listing
    )
    messages = [Message(role="system", content=system), Message(role="user", content=question)]

    loaded: list[str] = []
    tokens_used = 0
    for _ in range(max_steps):
        completion = model.complete(messages, tools=[LOAD_SKILL_TOOL], max_tokens=250)
        tokens_used += completion.tokens_in + completion.tokens_out

        if not completion.tool_calls:
            record_completion(tracer, decided_by="model", title="Model answers", completion=completion)
            return Answer(text=completion.text, citations=loaded)

        name = str(completion.tool_calls[0].arguments.get("name", ""))
        record_completion(tracer, decided_by="model", title="Model chooses a skill to load", completion=completion, detail=name)
        skill = registry.get(name)
        if skill is None:
            body = f"unknown skill: {name}"
        else:
            body = skill.body
            loaded.append(skill.name)
        tracer.record(kind="code", decided_by="code", title="Load the skill body into context", detail=body[:200])
        messages.append(Message(role="assistant", content=f"[loaded skill {name}]"))
        messages.append(Message(role="user", content=f"Skill '{name}' body:\n{body}"))

        if tokens_used >= max_tokens:
            reason = f"token budget reached: {tokens_used} >= {max_tokens}"
            final = force_final(messages, model, tracer, reason=reason, max_tokens=300)
            return Answer(text=final.text, citations=loaded)

    final = force_final(messages, model, tracer, reason=f"step cap reached: {max_steps} steps", max_tokens=300)
    return Answer(text=final.text, citations=loaded)
