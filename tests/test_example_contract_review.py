"""End-to-end tests for the contract review example.

Three things this file exists to pin, matching the recipe's own claims:

- **One call per rule, and each call is independent.** `test_one_model_call_per_rule` counts the
  calls; `test_prompts_are_independent_per_rule` reads the prompts `_prompt_for_rule` actually
  builds and checks that a given call's prompt names only its own rule.
- **The merge check is what the page teaches, and it is attacked here directly.** A quote lifted
  from a real but *different* clause than the one cited, a clause number the agreement does not
  have, and a status outside the closed set must all be caught rather than passed through; `missing`
  must not be caught by the same check, since it legitimately cites no clause.
- **Every step is `decided_by="code"`.** No `decided_by="model"` string exists in the source at
  all, and `tracer.model_decided_count()` is 0 on a full run.
"""
from __future__ import annotations

import json
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import Completion, Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.contract_review.run import (  # noqa: E402
    AGREEMENT_CLAUSES,
    CHECKLIST,
    LEVEL,
    SAMPLE_INPUT,
    _merge_finding,
    _parse_clauses,
    _prompt_for_rule,
    resume,
    run,
)

RUN_PY = ROOT / "examples" / "contract_review" / "run.py"

# The six real findings this checklist produces against the built-in agreement. Every clause
# number and quote here is copied verbatim from AGREEMENT_CLAUSES so a drift between the two
# would show up as a failing test, not a silent mismatch.
_REPLIES: dict[str, str] = {
    "payment_terms": json.dumps({
        "rule": "payment_terms", "status": "breach", "clause": 5,
        "quote": "Client shall pay each Vendor invoice within forty-five (45) days of the invoice date.",
    }),
    "liability_cap": json.dumps({
        "rule": "liability_cap", "status": "meets", "clause": 9,
        "quote": (
            "Vendor's total liability arising under this Agreement shall not exceed the fees "
            "paid by Client in the twelve (12) months preceding the event giving rise to the claim."
        ),
    }),
    "notice_period": json.dumps({
        "rule": "notice_period", "status": "meets", "clause": 7,
        "quote": "Either party may terminate this Agreement for convenience upon sixty (60) days' prior written notice to the other party.",
    }),
    "assignment": json.dumps({
        "rule": "assignment", "status": "breach", "clause": 12,
        "quote": "Either party may assign this Agreement, in whole or in part, to any third party without the other party's consent",
    }),
    "governing_law": json.dumps({
        "rule": "governing_law", "status": "unclear", "clause": 13,
        "quote": "governed by the laws of the state in which Vendor maintains its principal place of business",
    }),
    "data_deletion": json.dumps({
        "rule": "data_deletion", "status": "missing", "clause": None, "quote": "",
    }),
}


# The same six replies, in CHECKLIST order, as examples/contract_review/__main__.py's SCRIPTED:
# the sequence a reader gets from `--model stub:scripted`, positional rather than matched by
# content, which is safe here only because every reply validates against any clause it might land
# on if two calls raced (see _RecordingStub below for why the run itself cannot use a positional
# stub).
SEQUENCE = [_REPLIES[rule.id] for rule in CHECKLIST]


class _RecordingStub:
    """A callable-based stub, not a list-based one: `ThreadPoolExecutor` calls `complete` from
    several threads at once, and a list-based `StubModel` advances a shared counter with no lock
    (see `examples/parallelization/run.py`'s own note on this). Matching on the prompt's own text
    is what makes a concurrent run deterministic without a race, and it doubles as evidence that
    each call really did carry only its own rule: a prompt naming no rule this stub recognizes
    fails loudly instead of returning whatever the counter's position would have given it."""

    def __init__(self, replies: dict[str, str]) -> None:
        self._replies = replies
        self.prompts: list[str] = []
        self._lock = threading.Lock()

    def __call__(self, messages: list[Message], tools) -> StubResponse:
        prompt = messages[-1].content
        with self._lock:
            self.prompts.append(prompt)
        for rule_id, text in self._replies.items():
            if f"Checklist rule {rule_id}:" in prompt:
                return StubResponse(text=text)
        raise AssertionError(f"no scripted reply matches this prompt: {prompt[:200]!r}")


def _scripted_model() -> tuple[StubModel, _RecordingStub]:
    recorder = _RecordingStub(_REPLIES)
    return StubModel(recorder), recorder


def tracer() -> Tracer:
    return Tracer(example="contract_review", level=LEVEL, model_id="stub-1")


class ContractReviewExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 3)
        self.assertTrue(callable(run))
        self.assertEqual(SAMPLE_INPUT, "\n".join(f"{n}. {AGREEMENT_CLAUSES[n]}" for n in sorted(AGREEMENT_CLAUSES)))

    def test_one_model_call_per_rule(self) -> None:
        model, recorder = _scripted_model()
        run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len(recorder.prompts), len(CHECKLIST))

    def test_prompts_are_independent_per_rule(self) -> None:
        """Each call's prompt names only its own rule. No other rule's id or rule text appears in
        it, which is the independence the page claims and that parallelization's own sectioning
        pattern depends on."""
        model, recorder = _scripted_model()
        run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len(recorder.prompts), len(CHECKLIST))
        for prompt in recorder.prompts:
            named = [rule.id for rule in CHECKLIST if f"Checklist rule {rule.id}:" in prompt]
            self.assertEqual(len(named), 1, f"prompt should name exactly one rule: {prompt[:120]!r}")
            this_rule = next(r for r in CHECKLIST if r.id == named[0])
            for other in CHECKLIST:
                if other.id != this_rule.id:
                    self.assertNotIn(other.text, prompt, f"{this_rule.id}'s prompt leaked {other.id}'s rule text")

    def test_prompt_builder_carries_only_its_own_rule(self) -> None:
        """The same claim, checked directly against the function that builds a prompt, with no
        model involved at all."""
        rule = CHECKLIST[0]
        prompt = _prompt_for_rule(rule, SAMPLE_INPUT)
        self.assertIn(rule.text, prompt)
        for other in CHECKLIST[1:]:
            self.assertNotIn(other.text, prompt)

    def test_full_run_produces_the_six_expected_findings(self) -> None:
        model, _ = _scripted_model()
        checkpoint = run(SAMPLE_INPUT, model, tracer())
        by_rule = {f.rule: f for f in checkpoint.findings}
        self.assertEqual(set(by_rule), {r.id for r in CHECKLIST})
        self.assertEqual(by_rule["payment_terms"].status, "breach")
        self.assertEqual(by_rule["payment_terms"].clause, 5)
        self.assertEqual(by_rule["liability_cap"].status, "meets")
        self.assertEqual(by_rule["notice_period"].status, "meets")
        self.assertEqual(by_rule["assignment"].status, "breach")
        self.assertEqual(by_rule["governing_law"].status, "unclear")
        self.assertEqual(by_rule["data_deletion"].status, "missing")
        self.assertIsNone(by_rule["data_deletion"].clause)
        for f in checkpoint.findings:
            self.assertEqual(f.checked_by, "model", f"{f.rule} should ship as drafted, not downgraded")

    def test_the_gate_sends_breach_missing_and_unclear_to_a_person(self) -> None:
        model, _ = _scripted_model()
        checkpoint = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual({f.rule for f in checkpoint.needs_review},
                          {"payment_terms", "assignment", "governing_law", "data_deletion"})
        self.assertEqual({f.rule for f in checkpoint.cleared}, {"liability_cap", "notice_period"})
        self.assertEqual(len(checkpoint.needs_review) + len(checkpoint.cleared), len(checkpoint.findings))

    def test_missing_is_reported_not_folded_into_meets_or_dropped(self) -> None:
        model, _ = _scripted_model()
        checkpoint = run(SAMPLE_INPUT, model, tracer())
        data_deletion = next(f for f in checkpoint.findings if f.rule == "data_deletion")
        self.assertEqual(data_deletion.status, "missing")
        self.assertIn(data_deletion, checkpoint.needs_review)
        self.assertNotIn(data_deletion, checkpoint.cleared)

    def test_the_token_counts_the_page_quotes(self) -> None:
        """The recipe page's cost strip quotes these two totals for the scripted run above; pin
        them so the page cannot drift from the prompts the code actually builds."""
        model, _ = _scripted_model()
        t = tracer()
        run(SAMPLE_INPUT, model, t)
        self.assertEqual(t.tokens_in_total(), 4742)
        self.assertEqual(t.tokens_out_total(), 252)


class MergeCheckAttackTests(unittest.TestCase):
    """Attacking the recipe's own check: replies constructed to look plausible while failing to
    actually back the finding they claim."""

    def setUp(self) -> None:
        self.clauses = _parse_clauses(SAMPLE_INPUT)
        self.rule = next(r for r in CHECKLIST if r.id == "assignment")

    def _completion(self, text: str) -> Completion:
        return Completion(text=text, tool_calls=[], tokens_in=10, tokens_out=10, ms=1.0, model_id="stub-1")

    def test_a_quote_from_a_different_real_clause_is_downgraded(self) -> None:
        """The quote is real -- it is clause 7's own sentence -- but the finding cites clause 12.
        A check that only asked "does this quote appear anywhere in the agreement" would pass
        this; the check has to ask "does it appear in the clause actually cited"."""
        reply = json.dumps({
            "rule": "assignment", "status": "breach", "clause": 12,
            "quote": "Either party may terminate this Agreement for convenience upon sixty (60) days' prior written notice to the other party.",
        })
        finding = _merge_finding(self.rule, self._completion(reply), self.clauses)
        self.assertEqual(finding.status, "unclear")
        self.assertEqual(finding.checked_by, "code")
        self.assertIn("does not appear in clause 12", finding.note)

    def test_a_clause_number_the_agreement_does_not_have_is_downgraded(self) -> None:
        reply = json.dumps({"rule": "assignment", "status": "breach", "clause": 99, "quote": "anything"})
        finding = _merge_finding(self.rule, self._completion(reply), self.clauses)
        self.assertEqual(finding.status, "unclear")
        self.assertEqual(finding.checked_by, "code")
        self.assertIn("99", finding.note)
        self.assertIn("does not have", finding.note)

    def test_a_status_outside_the_closed_set_is_rejected_not_passed_through(self) -> None:
        reply = json.dumps({"rule": "assignment", "status": "mostly_fine", "clause": 12, "quote": "Either party"})
        finding = _merge_finding(self.rule, self._completion(reply), self.clauses)
        self.assertNotEqual(finding.status, "mostly_fine")
        self.assertEqual(finding.status, "unclear")
        self.assertEqual(finding.checked_by, "code")
        self.assertIn("mostly_fine", finding.note)

    def test_missing_is_not_downgraded_for_having_no_clause(self) -> None:
        reply = json.dumps({"rule": "data_deletion", "status": "missing", "clause": None, "quote": ""})
        rule = next(r for r in CHECKLIST if r.id == "data_deletion")
        finding = _merge_finding(rule, self._completion(reply), self.clauses)
        self.assertEqual(finding.status, "missing")
        self.assertEqual(finding.checked_by, "model")
        self.assertEqual(finding.note, "")

    def test_malformed_json_is_downgraded_and_does_not_crash(self) -> None:
        finding = _merge_finding(self.rule, self._completion("not json at all"), self.clauses)
        self.assertEqual(finding.status, "unclear")
        self.assertIn("not valid JSON", finding.note)

    def test_a_quote_that_really_is_in_the_cited_clause_ships_as_drafted(self) -> None:
        reply = json.dumps({
            "rule": "assignment", "status": "breach", "clause": 12,
            "quote": "without the other party's consent",
        })
        finding = _merge_finding(self.rule, self._completion(reply), self.clauses)
        self.assertEqual(finding.status, "breach")
        self.assertEqual(finding.checked_by, "model")
        self.assertEqual(finding.note, "")


class ResumeTests(unittest.TestCase):
    def test_resume_records_the_reviewers_decision(self) -> None:
        model, _ = _scripted_model()
        t = tracer()
        checkpoint = run(SAMPLE_INPUT, model, t)
        record = resume(checkpoint, "acknowledged", t, note="Legal will redline clauses 5 and 12.")
        self.assertEqual(record.reviewer_decision, "acknowledged")
        self.assertEqual(record.note, "Legal will redline clauses 5 and 12.")
        self.assertEqual(record.findings, checkpoint.findings)
        self.assertTrue(any("Resume" in s.title for s in t.steps))


class DecidedByTests(unittest.TestCase):
    def test_every_step_is_decided_by_code(self) -> None:
        model, _ = _scripted_model()
        t = tracer()
        run(SAMPLE_INPUT, model, t)
        self.assertTrue(t.steps)
        self.assertEqual(t.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" for s in t.steps))
        self.assertEqual(sum(1 for s in t.steps if s.kind == "model"), len(CHECKLIST))

    def test_the_source_records_no_model_decision_anywhere(self) -> None:
        # scripts/validate.py reads examples for this string; the example must not carry one.
        self.assertNotIn('decided_by="model"', RUN_PY.read_text(encoding="utf-8"))


class ScriptedCommandTests(unittest.TestCase):
    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        from examples.contract_review.__main__ import SCRIPTED

        self.assertEqual(SCRIPTED, SEQUENCE)


class ClauseParsingTests(unittest.TestCase):
    def test_every_clause_in_the_constant_parses_back_out(self) -> None:
        clauses = _parse_clauses(SAMPLE_INPUT)
        self.assertEqual(set(clauses), set(AGREEMENT_CLAUSES))
        for n, text in AGREEMENT_CLAUSES.items():
            self.assertEqual(clauses[n], text)

    def test_an_empty_request_falls_back_to_the_built_in_agreement(self) -> None:
        model, _ = _scripted_model()
        checkpoint = run("", model, tracer())
        self.assertEqual(checkpoint.agreement, SAMPLE_INPUT)


if __name__ == "__main__":
    unittest.main()
