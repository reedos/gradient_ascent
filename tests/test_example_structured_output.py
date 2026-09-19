"""End-to-end test for the structured-output example: a valid reply is accepted on the first
try, an invalid reply triggers exactly one retry with the validation error appended, and a reply
that is still invalid after the retry is reported as such rather than accepted anyway."""
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
from examples.structured_output.__main__ import SCRIPTED  # noqa: E402
from examples.structured_output.run import LEVEL, WARRANTY_SECTIONS, run  # noqa: E402

QUESTION = "What is the DW-480's warranty?"
VALID_RECORD = {
    "model": "DW-480",
    "full_warranty_years": 2,
    "limited_years": 5,
    "limited_scope": "dishwasher motor and tub",
    "commercial_rental_days": 90,
}
SEQUENCE = [
    json.dumps(dict(VALID_RECORD, full_warranty_years="two")),
    json.dumps(VALID_RECORD),
]


class StructuredOutputExampleTests(unittest.TestCase):
    def test_a_valid_reply_is_accepted_on_the_first_try(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(VALID_RECORD))])
        tracer = Tracer(example="structured_output", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer)
        self.assertEqual(json.loads(answer.text), VALID_RECORD)
        self.assertEqual(answer.citations, WARRANTY_SECTIONS)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 1, "should not have retried")

    def test_an_invalid_reply_retries_once_and_then_succeeds(self) -> None:
        bad = dict(VALID_RECORD, full_warranty_years="two")  # wrong type
        model = StubModel([StubResponse(text=json.dumps(bad)), StubResponse(text=json.dumps(VALID_RECORD))])
        tracer = Tracer(example="structured_output", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer)
        self.assertEqual(json.loads(answer.text), VALID_RECORD)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)
        retry_prompts = [s for s in tracer.steps if s.title == "Ask again with the validation error"]
        self.assertEqual(len(retry_prompts), 1)

    def test_still_invalid_after_the_retry_is_reported_not_accepted(self) -> None:
        bad = {"model": "DW-480"}  # missing every other field, twice
        model = StubModel([StubResponse(text=json.dumps(bad)), StubResponse(text=json.dumps(bad))])
        tracer = Tracer(example="structured_output", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer)
        self.assertEqual(answer.citations, [], "an unvalidated record must not be cited as an answer")
        self.assertIn("error", json.loads(answer.text))
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2, "must not retry more than once")

    def test_invalid_json_is_caught_the_same_way_as_a_schema_mismatch(self) -> None:
        model = StubModel([StubResponse(text="not json at all"), StubResponse(text=json.dumps(VALID_RECORD))])
        tracer = Tracer(example="structured_output", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer)
        self.assertEqual(json.loads(answer.text), VALID_RECORD)

    def test_every_step_is_decided_by_code(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(VALID_RECORD))])
        tracer = Tracer(example="structured_output", level=LEVEL, model_id="stub-1")
        run(QUESTION, model, tracer)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))

    def test_the_appliance_is_read_from_the_question(self) -> None:
        model = StubModel([StubResponse(text=json.dumps(dict(VALID_RECORD, model="DR-210", limited_years=7)))])
        tracer = Tracer(example="structured_output", level=LEVEL, model_id="stub-1")
        answer = run("What is the DR-210's warranty?", model, tracer)
        self.assertEqual(json.loads(answer.text)["model"], "DR-210")

    def test_declares_its_level_and_a_run_function(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))


class ScriptedCommandTests(unittest.TestCase):
    """The sequence `python -m examples.structured_output --model stub:scripted` plays, run the
    same way the CLI runs it, plus the guard that keeps the two in step."""

    def test_the_scripted_sequence_fails_once_then_retries_into_a_valid_record(self) -> None:
        model = StubModel([StubResponse(text=t) for t in SEQUENCE])
        tracer = Tracer(example="structured_output", level=LEVEL, model_id="stub-1")
        answer = run(QUESTION, model, tracer)
        self.assertEqual(json.loads(answer.text), VALID_RECORD)
        self.assertEqual(sum(1 for s in tracer.steps if s.kind == "model"), 2)

    def test_the_command_s_sequence_is_the_one_this_test_scripts(self) -> None:
        """If these two drift apart, the command on the page stops demonstrating what this test
        says the example does."""
        self.assertEqual([r.text if hasattr(r, "text") else r for r in SCRIPTED], SEQUENCE)


if __name__ == "__main__":
    unittest.main()
