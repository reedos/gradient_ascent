"""Level 5: plan a trip and hold the bookings. A loop with three read-only tools --
search_routes, search_stays and opening_hours -- and one tool that is not read only, book. How
many lookups a trip needs is not fixed in advance: a route that does not connect, or a stay with
no room left, changes what to search next, so the model's own output chooses every tool call and
the loop keeps going until it stops itself or a cap does, the same shape
`examples/agentic_rag/run.py` uses for a document search.

`book` is where that shape changes. The loop never runs it. Finding a `book` call in the model's
output stops the run right there and returns a `PendingBooking` checkpoint: the exact call, its
price in cents and its cancellation terms, nothing executed. `approve`, a second and separate
call, is the same split `examples/human_in_the_loop/run.py` uses for its own pause and resume: it
takes the checkpoint and a person's decision, and only on approval does it book anything -- and
only the call the person actually saw. `approve` recomputes a fingerprint of the call it is about
to run and refuses to execute one whose price, date or reference has moved since it was approved,
which is the whole reason a checkpoint carries a fingerprint rather than trusting its own fields.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

from examples.common.agent_loop import assistant_turn, force_final, tool_result
from examples.common.model import Message, Model, ToolCall
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 5
MAX_STEPS = 6
MAX_TOKENS = 3000

SAMPLE_INPUT = (
    "Plan a trip from Wrenfield to Aldercliff for November 14 to 17, find somewhere to stay, "
    "and book the cheapest outbound route."
)

# ---------------------------------------------------------------------------
# Invented data: two obviously invented cities, a few routes between them, two places to stay,
# and opening hours for two attractions. No real airline, hotel, city pair or booking site.
# ---------------------------------------------------------------------------

ROUTES = [
    {"id": "R1", "origin": "Wrenfield", "destination": "Aldercliff", "date": "2026-11-14",
     "depart": "08:10", "arrive": "10:55", "price_cents": 8900,
     "cancellation": "Refundable up to 24 hours before departure; no refund after that."},
    {"id": "R2", "origin": "Wrenfield", "destination": "Aldercliff", "date": "2026-11-14",
     "depart": "17:40", "arrive": "20:25", "price_cents": 6400,
     "cancellation": "Non-refundable."},
    {"id": "R3", "origin": "Aldercliff", "destination": "Wrenfield", "date": "2026-11-17",
     "depart": "09:05", "arrive": "11:50", "price_cents": 7200,
     "cancellation": "Refundable up to 24 hours before departure; no refund after that."},
]

STAYS = [
    {"id": "S1", "city": "Aldercliff", "name": "The Cormorant Inn", "price_cents": 11200,
     "cancellation": "Free cancellation until 48 hours before check-in."},
    {"id": "S2", "city": "Aldercliff", "name": "Harrow Lane Hostel", "price_cents": 4300,
     "cancellation": "Non-refundable."},
]

OPENING_HOURS = {
    "Aldercliff Museum of Tides": {"open": "09:00", "close": "17:00", "closed_days": ["Monday"]},
    "Thistle Botanical Garden": {"open": "08:00", "close": "19:00", "closed_days": []},
}

SYSTEM_PROMPT = (
    "You help plan a trip. Call search_routes(origin, destination), search_stays(city) and "
    "opening_hours(place) as many times as you need; all three are read only and their results "
    "come back right away. Call book(kind, ref) with kind 'route' or 'stay' and the id from a "
    "search result once you have decided what to reserve. Booking spends money: it does not "
    "happen when you call it, a person sees the price and the cancellation terms first. Call no "
    "tools, in your final turn, once you are ready to summarize the plan."
)

TOOLS = [
    {
        "name": "search_routes",
        "description": "Read only. Find routes between two cities.",
        "parameters": {
            "type": "object",
            "properties": {"origin": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["origin", "destination"],
        },
    },
    {
        "name": "search_stays",
        "description": "Read only. Find places to stay in a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    },
    {
        "name": "opening_hours",
        "description": "Read only. Look up the opening hours of one named place.",
        "parameters": {"type": "object", "properties": {"place": {"type": "string"}}, "required": ["place"]},
    },
    {
        "name": "book",
        "description": "Reserve a route or a stay by its id. Spends money; does not run immediately.",
        "parameters": {
            "type": "object",
            "properties": {"kind": {"type": "string", "enum": ["route", "stay"]}, "ref": {"type": "string"}},
            "required": ["kind", "ref"],
        },
    },
]

Decision = Literal["approve", "reject"]


@dataclass(frozen=True)
class BookingCall:
    """Exactly what the model proposed, with the two facts a person's decision turns on: the
    price it actually found and the cancellation terms that came with it, never a paraphrase of
    either."""

    kind: Literal["route", "stay"]
    ref: str
    price_cents: int
    cancellation: str
    detail: str


def _fingerprint(call: BookingCall) -> str:
    """A hash of every field in `call`. `approve` recomputes this from the call it is about to
    run and refuses when it no longer matches the fingerprint that was actually approved -- the
    only thing standing between "a person approved this" and "a person approved something that
    used to look like this."""
    return hashlib.sha256(json.dumps(asdict(call), sort_keys=True).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PendingBooking:
    """A paused run: everything a person needs to approve or reject is in `call`, and
    `fingerprint` is what `approve` checks that call against before anything is spent."""

    request: str
    call: BookingCall
    fingerprint: str


def _search_routes(origin: str, destination: str) -> str:
    hits = [
        r for r in ROUTES
        if r["origin"].lower() == origin.strip().lower() and r["destination"].lower() == destination.strip().lower()
    ]
    if not hits:
        return f"no routes from {origin} to {destination}"
    return "\n".join(
        f"{r['id']}: {r['origin']} -> {r['destination']}, {r['date']} {r['depart']}-{r['arrive']}, "
        f"${r['price_cents'] / 100:.2f}, {r['cancellation']}"
        for r in hits
    )


def _search_stays(city: str) -> str:
    hits = [s for s in STAYS if s["city"].lower() == city.strip().lower()]
    if not hits:
        return f"no stays in {city}"
    return "\n".join(
        f"{s['id']}: {s['name']}, ${s['price_cents'] / 100:.2f} per night, {s['cancellation']}" for s in hits
    )


def _opening_hours(place: str) -> str:
    hours = OPENING_HOURS.get(place)
    if hours is None:
        return f"{place}: not found"
    closed = ", ".join(hours["closed_days"]) or "none"
    return f"{place}: open {hours['open']}-{hours['close']}, closed {closed}"


def _booking_call(call: ToolCall) -> BookingCall:
    """Turn a `book` tool call into a `BookingCall` against the record it actually names, or
    refuse it outright. A reference the search data does not have is not a price a person could
    approve, so this raises rather than inventing one."""
    kind = str(call.arguments.get("kind", ""))
    ref = str(call.arguments.get("ref", ""))
    records = ROUTES if kind == "route" else STAYS if kind == "stay" else None
    if records is None:
        raise ValueError(f"unknown booking kind: {kind!r}")
    record = next((r for r in records if r["id"] == ref), None)
    if record is None:
        raise ValueError(f"unknown {kind}: {ref!r}")
    detail = (
        f"{record['id']}: {record['origin']} -> {record['destination']}, {record['date']} "
        f"{record['depart']}-{record['arrive']}"
        if kind == "route"
        else f"{record['id']}: {record['name']}, {record['city']}"
    )
    return BookingCall(
        kind=kind, ref=ref, price_cents=record["price_cents"], cancellation=record["cancellation"], detail=detail
    )


def _run_read_only(call: ToolCall) -> str:
    if call.name == "search_routes":
        return _search_routes(str(call.arguments.get("origin", "")), str(call.arguments.get("destination", "")))
    if call.name == "search_stays":
        return _search_stays(str(call.arguments.get("city", "")))
    if call.name == "opening_hours":
        return _opening_hours(str(call.arguments.get("place", "")))
    return f"unknown tool: {call.name}"


def run(
    request: str,
    model: Model,
    tracer: Tracer,
    *,
    max_steps: int = MAX_STEPS,
    max_tokens: int = MAX_TOKENS,
) -> Answer | PendingBooking:
    messages = [Message(role="system", content=SYSTEM_PROMPT), Message(role="user", content=request)]
    tokens_used = 0

    for _ in range(max_steps):
        completion = model.complete(messages, tools=TOOLS, max_tokens=400)
        tokens_used += completion.tokens_in + completion.tokens_out

        if not completion.tool_calls:
            tracer.record(
                kind="model", decided_by="model", title="Model stops and answers",
                detail=completion.text[:200], tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out, ms=completion.ms,
            )
            return Answer(text=completion.text)

        calls_desc = ", ".join(f"{c.name}({json.dumps(c.arguments, sort_keys=True)})" for c in completion.tool_calls)
        tracer.record(
            kind="model", decided_by="model", title="Model calls a tool",
            detail=calls_desc, tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out, ms=completion.ms,
        )
        turn, calls = assistant_turn(completion, len(messages))
        messages.append(turn)

        for call in calls:
            if call.name == "book":
                booking = _booking_call(call)
                tracer.record(
                    kind="code", decided_by="code", title="Pause for approval before booking",
                    detail=f"{booking.detail}; ${booking.price_cents / 100:.2f}; {booking.cancellation}",
                )
                return PendingBooking(request=request, call=booking, fingerprint=_fingerprint(booking))
            result_text = _run_read_only(call)
            tracer.record(kind="code", decided_by="code", title=f"Run tool: {call.name}", detail=result_text[:200])
            messages.append(tool_result(call, result_text))

        if tokens_used >= max_tokens:
            final = force_final(messages, model, tracer, reason=f"token budget reached: {tokens_used} >= {max_tokens}", max_tokens=400)
            return Answer(text=final.text)

    final = force_final(messages, model, tracer, reason=f"step cap reached: {max_steps} steps", max_tokens=400)
    return Answer(text=final.text)


def approve(pending: PendingBooking, decision: Decision, tracer: Tracer, *, note: str = "") -> Answer:
    """Execute the approved booking, and only the approved booking.

    There is no `edit` decision here, unlike `examples/human_in_the_loop/run.py`'s draft text: a
    person can approve or reject the price and terms that were actually found, but cannot edit a
    price into existence. `note` is kept for a reviewer's own record of why, and is never read
    back into what gets booked.
    """
    tracer.record(
        kind="code", decided_by="code", title="Resume from checkpoint with the reviewer's decision",
        detail=f"decision={decision}" + (f" note={note!r}" if note else ""),
    )
    if decision == "reject":
        return Answer(text="The reviewer declined this booking; nothing was booked.")

    if _fingerprint(pending.call) != pending.fingerprint:
        tracer.record(
            kind="code", decided_by="code", title="Refuse: the call no longer matches what was approved",
            detail=f"approved fingerprint {pending.fingerprint[:12]}, call now hashes to {_fingerprint(pending.call)[:12]}",
        )
        raise ValueError("the booking call has changed since it was approved; refusing to execute it")

    tracer.record(
        kind="code", decided_by="code", title="Execute the approved booking",
        detail=f"{pending.call.detail}; ${pending.call.price_cents / 100:.2f}",
    )
    text = f"Booked {pending.call.detail} for ${pending.call.price_cents / 100:.2f}. {pending.call.cancellation}"
    return Answer(text=text, citations=[pending.call.ref])
