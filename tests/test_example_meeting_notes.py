"""End-to-end tests for the meeting-notes example: a valid reply is accepted on the first try, an
invalid reply triggers exactly one retry, and the grounding check (every decision's quote must be
a real substring of the transcript) is attacked directly: a decision with a quote nowhere in the
transcript, an owner nobody named, a due date nobody stated, and a decision the deferred-item test
shows the check cannot actually catch.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.meeting_notes.run import (  # noqa: E402
    LEVEL,
    SAMPLE_INPUT,
    TRANSCRIPT,
    _normalize_ws,
    run,
)

RUN_PY = ROOT / "examples" / "meeting_notes" / "run.py"

VALID_RECORD = {
    "attendees": ["Priya Okafor", "Marcus Chen", "Deshawn Fitts", "Yuki Tanaka"],
    "decisions": [
        {
            "decision": "Ship the three-step signup flow on Friday.",
            "owner": "Marcus",
            "due_date": "Friday",
            "quote": "We're shipping the three-step signup flow on Friday.",
        },
        {
            "decision": "The FAQ for the new signup flow goes to whoever is on support rotation next week.",
            "owner": "whoever's on support rotation next week",
            "due_date": "",
            "quote": "the FAQ goes to whoever's on support rotation next week.",
        },
    ],
    "open_questions": [
        "Whether the new usage-based pricing applies to the team, or whether they are grandfathered into the old tier.",
    ],
}


# The reply the recipe page and its run diagram walk through: the two real decisions plus one the
# model invented, whose quote is nowhere in the transcript. The page quotes this run's token
# counts, so they are pinned here rather than left as a number nobody can reproduce.
PAGE_RUN_RECORD = {
    **VALID_RECORD,
    "decisions": VALID_RECORD["decisions"] + [
        {
            "decision": "Cut the marketing budget by half.",
            "owner": "Deshawn",
            "due_date": "",
            "quote": "We agreed to cut the marketing budget by half.",
        },
    ],
}


def tracer() -> Tracer:
    return Tracer(example="meeting_notes", level=LEVEL, model_id="stub-1")


class MeetingNotesExampleTests(unittest.TestCase):
    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))
        self.assertEqual(SAMPLE_INPUT, TRANSCRIPT)

    def test_a_valid_reply_is_accepted_on_the_first_try(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(VALID_RECORD))])
        notes = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(list(notes.attendees), VALID_RECORD["attendees"])
        self.assertEqual(len(notes.decisions), 2)
        self.assertEqual(notes.dropped, ())
        self.assertEqual(len(notes.open_questions), 1)

    def test_the_deferred_discount_is_not_reported_as_a_decision(self) -> None:
        """The pricing discount is raised and explicitly put off to a later meeting. A good
        extractor leaves it out of decisions entirely; this checks the sample's own scripted
        reply (a stand-in for a model that followed the instruction) does not mention it."""
        model = StubModel([StubResponse(text=json.dumps(VALID_RECORD))])
        notes = run(SAMPLE_INPUT, model, tracer())
        joined = " ".join(d.decision for d in notes.decisions).lower()
        self.assertNotIn("discount", joined)
        self.assertNotIn("20 percent", joined)

    def test_an_invalid_reply_retries_once_and_then_succeeds(self) -> None:
        model = StubModel([StubResponse(text="not json at all"), StubResponse(text=json.dumps(VALID_RECORD))])
        trace = tracer()
        notes = run(SAMPLE_INPUT, model, trace)
        self.assertEqual(len(notes.decisions), 2)
        self.assertEqual(sum(1 for s in trace.steps if s.kind == "model"), 2)
        retry_steps = [s for s in trace.steps if s.title == "Ask again with the validation error"]
        self.assertEqual(len(retry_steps), 1)
        self.assertTrue(all(s.decided_by == "code" for s in retry_steps))

    def test_still_invalid_after_the_retry_is_reported_not_accepted(self) -> None:
        bad = {"attendees": ["Priya Okafor"]}  # missing decisions and open_questions, twice
        model = StubModel([StubResponse(text=json.dumps(bad)), StubResponse(text=json.dumps(bad))])
        trace = tracer()
        notes = run(SAMPLE_INPUT, model, trace)
        self.assertEqual(notes.decisions, ())
        self.assertNotEqual(notes.error, "")
        self.assertEqual(sum(1 for s in trace.steps if s.kind == "model"), 2, "must not retry more than once")

    def test_a_decision_whose_quote_is_nowhere_in_the_transcript_is_dropped_and_reported(self) -> None:
        record = json.loads(json.dumps(VALID_RECORD))
        record["decisions"].append(
            {
                "decision": "Cut the marketing budget by half.",
                "owner": "Priya",
                "due_date": "",
                "quote": "We are cutting the marketing budget by half starting next quarter.",
            }
        )
        model = StubModel([StubResponse(text=json.dumps(record))])
        notes = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len(notes.decisions), 2, "the ungrounded decision must not be kept")
        self.assertEqual(len(notes.dropped), 1)
        self.assertEqual(notes.dropped[0].decision, "Cut the marketing budget by half.")
        self.assertIn("Cut the marketing budget by half.", notes.text, "a dropped decision is reported, not silenced")

    def test_a_quote_that_only_matches_after_whitespace_is_normalized_is_kept(self) -> None:
        record = json.loads(json.dumps(VALID_RECORD))
        record["decisions"][0]["quote"] = "We're shipping the   three-step\nsignup flow on Friday."
        model = StubModel([StubResponse(text=json.dumps(record))])
        notes = run(SAMPLE_INPUT, model, tracer())
        self.assertEqual(len(notes.decisions), 2)
        self.assertEqual(len(notes.dropped), 0)

    def test_an_owner_never_named_comes_back_as_unassigned_not_a_guess(self) -> None:
        record = json.loads(json.dumps(VALID_RECORD))
        record["decisions"].append(
            {
                "decision": "Move the weekly sync to Wednesdays.",
                "owner": "unassigned",
                "due_date": "",
                "quote": "Deshawn: I'll check the schedule and let them know.",
            }
        )
        model = StubModel([StubResponse(text=json.dumps(record))])
        notes = run(SAMPLE_INPUT, model, tracer())
        by_text = {d.decision: d for d in notes.decisions}
        self.assertEqual(by_text["Move the weekly sync to Wednesdays."].owner, "unassigned")

    def test_a_due_date_not_stated_stays_empty(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(VALID_RECORD))])
        notes = run(SAMPLE_INPUT, model, tracer())
        faq = next(d for d in notes.decisions if "FAQ" in d.decision)
        self.assertEqual(faq.due_date, "")
        self.assertNotEqual(faq.owner, "")
        self.assertNotIn("Marcus", faq.owner, "the FAQ owner is a role, not the person named for the other decision")

    def test_the_quote_check_cannot_tell_a_real_decision_from_an_accurately_quoted_deferral(self) -> None:
        """What the grounding check proves is that the words appear in the transcript, not that
        the room actually agreed on them. Here the model claims the discount was decided and
        backs it with a real, verbatim sentence from the part of the meeting where Yuki argued
        for waiting a week, exactly the deferred item `test_the_deferred_discount_is_not_reported`
        checks a well-behaved reply leaves out. The substring check has nothing to say about
        whether a quote supports the decision it is attached to, so this decision is kept. That
        is the limit of what code can catch here; the page says so, and this is why a person who
        was in the room reads every run before it goes anywhere."""
        record = json.loads(json.dumps(VALID_RECORD))
        record["decisions"].append(
            {
                "decision": "Raise the annual discount to 20 percent.",
                "owner": "Deshawn",
                "due_date": "",
                "quote": "I'd want another week of modeling before we commit to a number.",
            }
        )
        self.assertIn(_normalize_ws(record["decisions"][-1]["quote"]), _normalize_ws(TRANSCRIPT))
        model = StubModel([StubResponse(text=json.dumps(record))])
        notes = run(SAMPLE_INPUT, model, tracer())
        wrong = next(d for d in notes.decisions if "discount" in d.decision.lower())
        self.assertEqual(wrong.decision, "Raise the annual discount to 20 percent.")

    def test_the_run_the_page_quotes_keeps_two_decisions_at_the_token_counts_it_states(self) -> None:
        """site/src/content/recipes/meeting-notes.mdx and its run diagram both state 712 tokens
        in and 194 out for this reply, with two decisions kept and one dropped. A number on a
        page that no test reproduces is a number that drifts the next time the prompt changes."""
        model = StubModel([StubResponse(text=json.dumps(PAGE_RUN_RECORD))])
        trace = tracer()
        notes = run(TRANSCRIPT, model, trace)
        self.assertEqual((len(notes.decisions), len(notes.dropped)), (2, 1))
        self.assertEqual(trace.tokens_in_total(), 712)
        self.assertEqual(trace.tokens_out_total(), 194)

    def test_every_step_is_decided_by_code_and_no_model_decision_is_recorded(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(VALID_RECORD))])
        trace = tracer()
        run(SAMPLE_INPUT, model, trace)
        self.assertTrue(trace.steps)
        self.assertTrue(all(s.decided_by == "code" for s in trace.steps))
        self.assertEqual(trace.model_decided_count(), 0)

    def test_the_source_records_no_model_decision_anywhere(self) -> None:
        # scripts/validate.py reads examples for this string; the example must not carry one.
        self.assertNotIn('decided_by="model"', RUN_PY.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
