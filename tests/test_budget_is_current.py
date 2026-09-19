"""`evals/budget.json` states numbers that `scripts/eval_run.py --dry` computes. Recompute them.

The registry's `as_of` went stale for a day while its entries were being re-checked, and nothing
noticed, because the fact was written in one place and derivable in another. `evals/budget.json`
is the same shape of file and had the same defect: its `dry_run_total_tokens` was 3,049,363 while
the projection said 3,043,656, and its note quoted `rag` at 508 input tokens a question while the
runner projected 519. Both had been wrong since an example grew.

So this test runs the projection and compares every figure in the file against it, including the
ones written into English sentences, because those are the ones a reader actually reads. It is
the slowest test in the suite, a few seconds, because it imports and runs all eighteen scored
examples in dry mode. It calls no model: `DryRunModel` counts prompt tokens and reports each
call's requested `max_tokens`.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for path in (ROOT, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import eval_run  # noqa: E402
from examples.common.model import StubEmbedder  # noqa: E402

BUDGET_PATH = ROOT / "evals" / "budget.json"


def _projection() -> dict[str, dict]:
    """The dry-run projection, per example, exactly as `--example all --dry` prints it."""
    questions = eval_run.load_questions(ROOT / "evals" / "questions.json")
    out = {}
    for name in eval_run.EXAMPLE_NAMES:
        summary = eval_run.run_example(
            name,
            model=eval_run.DryRunModel("projection"),
            embedder=StubEmbedder(),
            grader=None,
            questions=questions,
            stub=False,
            dry=True,
        )
        out[name] = summary
    return out


def _number(text: str, pattern: str) -> int:
    """Pull one comma-formatted integer out of a sentence in the budget file."""
    match = re.search(pattern, text)
    assert match, f"the sentence no longer contains the figure this test pins: {pattern!r}"
    return int(match.group(1).replace(",", ""))


class BudgetIsCurrentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.budget = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
        cls.projected = _projection()
        cls.total = sum(s["tokens_in"] + s["tokens_out"] for s in cls.projected.values())

    def test_the_stated_whole_run_total_is_what_the_dry_run_projects(self) -> None:
        self.assertEqual(
            self.budget["dry_run_total_tokens"],
            self.total,
            "evals/budget.json dry_run_total_tokens has drifted from the projection; re-run "
            "`python scripts/eval_run.py --example all --model stub --dry` and update the file, "
            "including its as_of date",
        )

    def test_the_stated_question_count_matches_the_question_set(self) -> None:
        questions = eval_run.load_questions(ROOT / "evals" / "questions.json")
        self.assertEqual(self.budget["questions"], len(questions))

    def test_the_stated_scored_example_count_matches_the_runner(self) -> None:
        self.assertEqual(self.budget["scored_examples"], len(eval_run.EXAMPLE_NAMES))

    def test_every_scored_example_has_a_recommended_cap_and_no_stranger_does(self) -> None:
        caps = self.budget["recommended_cap_per_example_tokens"]
        self.assertEqual(
            sorted(caps),
            sorted(eval_run.EXAMPLE_NAMES),
            "a scored example has no recommended cap, or a cap names an example that is no "
            "longer scored",
        )

    def test_no_recommended_cap_sits_below_its_own_projected_ceiling(self) -> None:
        # The file's own reasoning: a cap is headroom above the ceiling, so it bites only when
        # something has gone wrong. A cap that has fallen below the projection would stop every
        # run of that example and read as a budget problem rather than as a stale file.
        caps = self.budget["recommended_cap_per_example_tokens"]
        too_low = {
            name: (cap, self.projected[name]["tokens_in"] + self.projected[name]["tokens_out"])
            for name, cap in caps.items()
            if cap < self.projected[name]["tokens_in"] + self.projected[name]["tokens_out"]
        }
        self.assertEqual(too_low, {}, "recommended caps now below the projected ceiling")

    def test_the_figures_written_into_the_notes_are_the_projected_ones(self) -> None:
        note = self.budget["context_engineering_is_the_expensive_one"]
        ce = self.projected["context_engineering"]
        rag = self.projected["rag"]
        questions = self.budget["questions"]

        self.assertEqual(_number(note, r"([\d,]+) input tokens"), ce["tokens_in"])
        self.assertEqual(
            _number(note, r"against rag's ([\d,]+)"),
            round(rag["tokens_in"] / questions),
            "the note compares context_engineering with rag per question; rag's projection moved",
        )
        self.assertEqual(
            _number(note, r"about ([\d,]+) a question"),
            round(ce["tokens_in"] / questions / 1000) * 1000,
            "the rounded per-question figure in the note no longer rounds to the projection",
        )

        routing_note = self.budget["routing_is_underprojected"]
        self.assertEqual(
            _number(routing_note, r"routing's dry number, ([\d,]+),"),
            self.projected["routing"]["tokens_in"],
            "routing's projected input figure is quoted in the note explaining why it is not a "
            "ceiling; it is the tokens_in column of the dry table, not in plus out",
        )

    def test_the_caps_add_up_to_what_the_how_they_were_set_note_claims(self) -> None:
        caps = self.budget["recommended_cap_per_example_tokens"]
        note = self.budget["how_these_were_set"]
        # Both figures are written as "about NM", so they are pinned to a tenth of a million
        # rather than exactly: the point is to catch a note that has drifted by a whole example,
        # not to force a rewrite every time a prompt gains a sentence.
        claimed_millions = float(re.search(r"about ([\d.]+)M tokens", note).group(1))
        self.assertAlmostEqual(sum(caps.values()) / 1_000_000, claimed_millions, delta=0.1)
        claimed_ceiling = float(re.search(r"above the ([\d.]+)M ceiling", note).group(1))
        self.assertAlmostEqual(self.total / 1_000_000, claimed_ceiling, delta=0.1)

    def test_the_as_of_date_is_a_real_date_and_not_in_the_future(self) -> None:
        as_of = date.fromisoformat(self.budget["as_of"])
        self.assertLessEqual(as_of, date.today(), "evals/budget.json as_of is dated in the future")


if __name__ == "__main__":
    unittest.main()
