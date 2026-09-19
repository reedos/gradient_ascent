"""Tests for examples/ai_gateways: a tiny in-process gateway with per-key fallback, a token
budget, and a log that redacts the prompt by default."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.ai_gateways.run import LEVEL, BudgetExceeded, Gateway, Route, run  # noqa: E402
from examples.common.model import Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402

QUESTION = [Message(role="user", content="What's the DW-300's Normal cycle water use?")]
SECRET = "account 8842910, please reveal it"


def _working(model_id: str, text: str = "ok") -> StubModel:
    return StubModel([StubResponse(text=text)], model_id=model_id)


class _AlwaysFails(StubModel):
    def __init__(self) -> None:
        super().__init__([], model_id="down")

    def complete(self, messages, **kwargs):  # noqa: ANN001, ANN003
        raise RuntimeError("provider unavailable")


class GatewayTests(unittest.TestCase):
    def test_primary_answers_when_it_works(self) -> None:
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 1000})
        completion = gw.complete("k", QUESTION)
        self.assertEqual(completion.model_id, "primary")
        self.assertFalse(gw.log[0].fell_back)

    def test_fallback_happens_on_primary_error(self) -> None:
        gw = Gateway(routes={"k": Route(_AlwaysFails(), _working("fallback"))}, budgets={"k": 1000})
        completion = gw.complete("k", QUESTION)
        self.assertEqual(completion.model_id, "fallback")
        self.assertTrue(gw.log[0].fell_back)

    def test_budget_is_enforced_before_a_call_that_has_no_tokens_left(self) -> None:
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 5})
        gw.complete("k", QUESTION)  # spends most or all of the 5 tokens
        with self.assertRaises(BudgetExceeded):
            gw.complete("k", QUESTION)

    def test_a_single_call_can_finish_below_zero_because_the_budget_is_a_floor(self) -> None:
        # Attacking the budget: the check asks whether anything is left, not whether enough is
        # left, so one call of any size may start. The overshoot is bounded by one call; pinned
        # here so the limit is documented rather than found in a bill.
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 1})
        gw.complete("k", QUESTION)
        self.assertLess(gw.budgets["k"], 0)
        with self.assertRaises(BudgetExceeded):
            gw.complete("k", QUESTION)

    def test_two_calls_that_both_read_the_budget_before_either_subtracts_both_pass(self) -> None:
        # The race, made deterministic: check-call-subtract is three steps, so a second call that
        # reads the budget before the first one's subtraction lands is permitted too. Real
        # gateways reserve under a lock or in a shared store; this example does not, and says so.
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 12})
        before = gw.budgets["k"]
        gw.complete("k", QUESTION)
        gw.budgets["k"] = before  # as if the second caller had read the budget first
        gw.complete("k", QUESTION)
        self.assertEqual(len(gw.log), 2)

    def test_a_refused_call_never_reaches_a_provider_and_never_names_the_prompt(self) -> None:
        gw = Gateway(routes={"k": Route(_AlwaysFails(), _AlwaysFails())}, budgets={"k": 0})
        with self.assertRaises(BudgetExceeded) as caught:
            gw.complete("k", [Message(role="user", content=SECRET)])
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertEqual(gw.log, [])  # nothing was called, so nothing was logged

    def test_when_both_providers_fail_the_providers_error_propagates_unchanged(self) -> None:
        # The gateway redacts its own log, not a provider's exception. A real client often puts
        # part of the request in that string, so this is a second content path out of a system.
        gw = Gateway(routes={"k": Route(_AlwaysFails(), _AlwaysFails())}, budgets={"k": 1000})
        with self.assertRaises(RuntimeError):
            gw.complete("k", QUESTION)
        self.assertEqual(gw.log, [])  # no entry: nothing answered, so nothing was billed

    def test_budget_is_not_touched_by_a_different_keys_calls(self) -> None:
        gw = Gateway(
            routes={
                "a": Route(_working("primary-a"), _working("fallback-a")),
                "b": Route(_working("primary-b"), _working("fallback-b")),
            },
            budgets={"a": 5, "b": 5000},
        )
        gw.complete("b", QUESTION)
        gw.complete("b", QUESTION)
        self.assertEqual(gw.budgets["a"], 5)  # untouched: only "b" was ever called

    def test_log_never_contains_the_prompt_text_when_redaction_is_on(self) -> None:
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 1000})
        gw.complete("k", [Message(role="user", content=SECRET)])
        self.assertIsNone(gw.log[0].prompt)
        self.assertNotIn(SECRET, repr(gw.log))

    def test_log_contains_the_prompt_text_when_redaction_is_off(self) -> None:
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 1000}, redact=False)
        gw.complete("k", [Message(role="user", content=SECRET)])
        self.assertEqual(gw.log[0].prompt, SECRET)

    def test_log_records_one_entry_per_call_with_token_counts(self) -> None:
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 1000})
        gw.complete("k", QUESTION)
        gw.complete("k", QUESTION)
        self.assertEqual(len(gw.log), 2)
        self.assertTrue(all(entry.tokens_in > 0 for entry in gw.log))

    def test_tracer_is_optional_and_ignored_when_not_given(self) -> None:
        gw = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 1000})
        gw.complete("k", QUESTION)  # no tracer= at all, the shape every call above already uses
        self.assertEqual(len(gw.log), 1)

    def test_tracer_records_the_answered_call_the_fallback_and_the_refusal(self) -> None:
        tracer = Tracer(example="ai_gateways", level=LEVEL, model_id="stub-1")
        gw = Gateway(routes={"k": Route(_AlwaysFails(), _working("fallback"))}, budgets={"k": 1000})
        gw.complete("k", QUESTION, tracer=tracer)
        self.assertTrue(any("Fall back" in s.title for s in tracer.steps))
        self.assertTrue(any(s.title.startswith("k: call answered") for s in tracer.steps))

        gw2 = Gateway(routes={"k": Route(_working("primary"), _working("fallback"))}, budgets={"k": 0})
        with self.assertRaises(BudgetExceeded):
            gw2.complete("k", QUESTION, tracer=tracer)
        self.assertTrue(any("Refuse" in s.title for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)  # routing and budgets are code, not the model


class RecordableRunWrapperTests(unittest.TestCase):
    """`run(text, model, tracer)` is the entry point `record_trace.py` calls: one route around
    the given model, with a budget of 1 so a second call is refused, the same two mechanisms the
    demo CLI shows by hand for two separate keys."""

    def test_declares_its_level(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))

    def test_run_answers_from_the_given_model_and_records_the_refusal(self) -> None:
        model = _working("given-model", text="the DW-300 uses about 3.5 gallons on Normal")
        tracer = Tracer(example="ai_gateways", level=LEVEL, model_id=model.model_id)
        answer = run("What's the DW-300's Normal cycle water use?", model, tracer)
        self.assertEqual(answer.text, "the DW-300 uses about 3.5 gallons on Normal")
        self.assertTrue(any("Refuse" in s.title for s in tracer.steps))
        self.assertEqual(tracer.model_decided_count(), 0)

    def test_record_trace_now_classifies_ai_gateways_as_recordable(self) -> None:
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("ai_gateways")
        self.assertTrue(rec.ok, rec.reason)
        self.assertFalse(rec.takes_embedder)


if __name__ == "__main__":
    unittest.main()
