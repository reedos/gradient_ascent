"""Track: AI gateways. A tiny in-process gateway over two stub "providers" per key: it tries the
primary, falls back to the secondary on error, refuses a call once the key's token budget is
spent, and writes one log line per call.

Both providers are `Model`s (`examples.common.model.Model`) -- here two `StubModel`s, standing in
for what a real gateway would route to (an Ollama tag, a Claude model id). The gateway's own code
never has to know which one actually answered; that is the point of routing behind one interface.
A real gateway would also check keys, rate limits and policy before forwarding a request; this
example keeps to the three mechanisms the page walks through, so each stays readable.

Three limits, stated because a page that teaches a control should say where it stops:

- The budget is a floor, not a cap. A key with anything left may start a call of any size, so a
  single call can finish below zero; what the check refuses is the NEXT call. Sizing a cap to the
  request needs the request's token count before it is sent, which this example does not have.
- Nothing here is safe against concurrency. Check, call, then subtract is three steps, so two
  calls racing each other can both read the same remaining budget and both pass. A real gateway
  reserves against the budget under a lock or in a shared store; this one runs in one thread.
- Fallback retries the request, which is only sound if the request is idempotent. A primary that
  fails after doing the work is indistinguishable here from one that never received it, so a
  gateway configured to fall back on anything that raises can make a non-idempotent call twice.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from examples.common.model import Completion, Message, Model, StubModel, StubResponse, content_text
from examples.common.trace import Tracer
from examples.common.types import Answer

LEVEL = 1  # ai_gateways is a track technique, not a rung on the ladder; see content/taxonomy.json


class BudgetExceeded(RuntimeError):
    """Raised when a key has no tokens left, before any provider is called, so a caller never
    pays for a request it was already out of budget for. Its message names the key and nothing
    else: an exception is a string that travels, and the prompt must not travel with it."""


@dataclass(frozen=True)
class Route:
    primary: Model
    fallback: Model


@dataclass(frozen=True)
class LogEntry:
    key: str
    model_id: str
    tokens_in: int
    tokens_out: int
    fell_back: bool
    prompt: str | None  # None whenever the gateway's redact flag is on


@dataclass
class Gateway:
    routes: dict[str, Route]
    budgets: dict[str, int]  # key -> tokens remaining
    redact: bool = True
    log: list[LogEntry] = field(default_factory=list)

    def complete(self, key: str, messages: list[Message], *, tracer: Tracer | None = None, **kwargs) -> Completion:
        """Route one call for `key`, falling back to the secondary provider on any error.

        Raises `BudgetExceeded` before calling anything if the key is spent. If the fallback
        fails too, that provider's exception propagates unchanged; see the module docstring.

        `tracer` is optional and unused by the demo CLI: when given, it records the refusal, the
        fallback (if one happened) and the call that answered as `code` steps -- routing and
        budget enforcement are fixed rules the gateway applies, never a choice a model made, so
        nothing here is ever `decided_by: "model"`.
        """
        if self.budgets.get(key, 0) <= 0:
            if tracer is not None:
                tracer.record(kind="code", decided_by="code", title=f"Refuse: {key} has no budget left", detail=key)
            raise BudgetExceeded(f"key {key!r} has no budget left")
        route = self.routes[key]
        fell_back = False
        try:
            completion = route.primary.complete(messages, **kwargs)
        except Exception:  # noqa: BLE001 - any provider failure triggers fallback, on purpose
            if tracer is not None:
                tracer.record(kind="code", decided_by="code", title=f"Fall back: {key}'s primary failed", detail=key)
            completion = route.fallback.complete(messages, **kwargs)
            fell_back = True
        self.budgets[key] -= completion.tokens_in + completion.tokens_out
        prompt = None if self.redact else "\n".join(content_text(m.content) for m in messages)
        self.log.append(
            LogEntry(
                key=key,
                model_id=completion.model_id,
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                fell_back=fell_back,
                prompt=prompt,
            )
        )
        if tracer is not None:
            tracer.record(
                kind="model",
                decided_by="code",
                title=f"{key}: call answered" + (" via fallback" if fell_back else ""),
                detail=completion.text[:200],
                tokens_in=completion.tokens_in,
                tokens_out=completion.tokens_out,
                ms=completion.ms,
            )
        return completion


def run(question: str, model: Model, tracer: Tracer) -> Answer:
    """Recordable entry point for `record_trace.py`. Routes one call for `question` through a
    single-key gateway whose primary is the given `model` and whose fallback is an unused stub
    (Route requires both; nothing calls the fallback unless the primary raises), with a budget
    small enough that a second call is refused outright -- the same two mechanisms `python -m
    examples.ai_gateways --demo` shows by hand for two separate keys. `tracer` is threaded
    through `Gateway.complete` so the answered call and the refusal are both recorded."""
    fallback = StubModel([StubResponse(text="[gateway fallback] unused")], model_id="fallback-demo")
    gateway = Gateway(routes={"demo": Route(primary=model, fallback=fallback)}, budgets={"demo": 1})
    messages = [Message(role="user", content=question)]
    completion = gateway.complete("demo", messages, tracer=tracer, max_tokens=200)
    try:
        gateway.complete("demo", messages, tracer=tracer, max_tokens=200)
    except BudgetExceeded:
        pass
    return Answer(text=completion.text, citations=[])
