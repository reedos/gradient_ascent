"""Level 1: structured output. Extract one warranty record from the corpus into a fixed schema,
validate the model's JSON reply against it, and retry once with the validation error appended if
it fails. The code always asks for the same schema and retries at most once regardless of what
comes back, so every step is `decided_by: "code"`, the same as chat and prompt engineering.
"""
from __future__ import annotations

import json
import re

from evals.corpus import DEFAULT_CORPUS_DIR, load_sections
from examples.common.model import Message, Model
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1
MAX_RETRIES = 1
APPLIANCE_RE = re.compile(r"DW-300|DW-480|DR-210|DR-520")
WARRANTY_SECTIONS = ["warranty-policy#1", "warranty-policy#2", "warranty-policy#3"]
REQUIRED_FIELDS = ("model", "full_warranty_years", "limited_years", "limited_scope", "commercial_rental_days")
SCHEMA = {
    "type": "object",
    "properties": {
        "model": {"type": "string"},
        "full_warranty_years": {"type": "integer"},
        "limited_years": {"type": "integer"},
        "limited_scope": {"type": "string"},
        "commercial_rental_days": {"type": "integer"},
    },
    "required": list(REQUIRED_FIELDS),
    "additionalProperties": False,
}
SYSTEM_PROMPT = (
    "Extract a warranty record from the passage as JSON matching this schema, with no other "
    f"text and no markdown fences: {json.dumps(SCHEMA)}"
)


def _validate(record: object, appliance: str) -> list[str]:
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    problems = [f"missing field: {f}" for f in REQUIRED_FIELDS if f not in record]
    problems.extend(f"unexpected field: {f}" for f in record if f not in REQUIRED_FIELDS)
    if problems:
        return problems
    if record["model"] != appliance:
        problems.append(f"model should be {appliance!r}, got {record['model']!r}")
    for field in ("full_warranty_years", "limited_years", "commercial_rental_days"):
        if type(record[field]) is not int:
            problems.append(f"{field} must be an integer")
    if not isinstance(record["limited_scope"], str) or not record["limited_scope"]:
        problems.append("limited_scope must be a non-empty string")
    return problems


def run(question: str, model: Model, tracer: Tracer, *, corpus_dir=DEFAULT_CORPUS_DIR) -> Answer:
    match = APPLIANCE_RE.search(question)
    appliance = match.group(0) if match else "DW-300"
    sections = load_sections(corpus_dir)
    passage = "\n\n".join(sections[cite].text for cite in WARRANTY_SECTIONS)
    tracer.record(kind="code", decided_by="code", title="Find which appliance the question asks about", detail=appliance)
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=f"{passage}\n\nAppliance: {appliance}"),
    ]
    record: object = {}
    for attempt in range(MAX_RETRIES + 1):
        completion = model.complete(messages, schema=SCHEMA, max_tokens=200)
        tracer.record(
            kind="model",
            decided_by="code",
            title="Ask the model for JSON" if attempt == 0 else "Ask again with the validation error",
            detail=completion.text[:200],
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            ms=completion.ms,
        )
        try:
            record, problems = json.loads(completion.text), None
            problems = _validate(record, appliance)
        except json.JSONDecodeError as exc:
            record, problems = {}, [f"invalid JSON: {exc}"]
        tracer.record(kind="code", decided_by="code", title="Validate against the schema", detail="; ".join(problems) or "valid")
        if not problems:
            return Answer(text=json.dumps(record, sort_keys=True), citations=WARRANTY_SECTIONS)
        if attempt < MAX_RETRIES:
            messages.append(Message(role="user", content=f"That did not validate: {'; '.join(problems)}. Reply again with corrected JSON only."))
    return Answer(text=json.dumps({"error": "did not validate after retry", "last": record}), citations=[])
