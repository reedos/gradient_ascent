"""Tests for the weekly status report example, one half at a time, and then the two checks.

The assembly half (level 0, no model): the window, the counts, the reconciled project names, the
name nobody recognized, and the source that is behind the report date. None of these call a model
at all.

The writing half (level 1, one call): the call happens once whatever kind of week it was, and the
prompt carries the figures and the week's note and nothing else.

Most of the file attacks the two checks, because the page is built on them. `unsupported_figures`
is attacked with a rounded figure, an invented total, an invented date, a task id, a date written
in another form, and a right figure next to the wrong project. `missing_required` is attacked
with a draft that leaves out the line somebody had to act on, with a figure too short to check,
and with two figures that share a text, which is the case the check cannot tell apart.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.weekly_status_report.run import (  # noqa: E402
    LEVEL,
    MIN_CHECKABLE,
    SAMPLE_INPUT,
    SOURCES,
    Figure,
    Source,
    compute_figures,
    missing_required,
    project_key,
    required_figures,
    run,
    short_must_say,
    unsupported_figures,
)

# A draft built only from the figures the sample week computes, including all four must-say
# figures. This is what a model that followed the system prompt would return.
CLEAN_DRAFT = """Week ending 09/18/2026

Ferndale Library is the one to look at before Monday. It has used 98.3 percent of its budgeted
hours, 59.0 of 60, and still has 3 tasks open. One of those is the accessibility review, which
was due 09/10/2026 and is still not closed. The client's budget question from Tuesday has been
waiting on us for 6 days.

Brightwater Commons closed 2 tasks this week and opened 1. The permit application was due
09/16/2026 and is the project's one overdue item; the revised site plan thread has been waiting
on us for 8 days. Hours are at 36.1 percent of the 180 budgeted.

Halloway Bridge Survey opened the draft report this week and closed nothing. Nothing on it is
overdue, and the next thing due is 10/02/2026. It has used 9.5 hours of its 60.

Across the three projects, 3 tasks closed, 3 opened, and 2 are overdue. 2 client threads have
been waiting on us for more than 3 days.

The time spreadsheet is current only to 09/15/2026, so hours are counted through 09/11/2026 and
this week's are not in them yet. One project name in the inbox matched nothing on our list, so 1
thread is not counted against any project here."""


def tracer() -> Tracer:
    return Tracer(example="weekly_status_report", level=LEVEL, model_id="stub-1")


def answering(draft: str) -> StubModel:
    return StubModel([StubResponse(text=draft)])


def figures_of(draft_source=SOURCES):
    return compute_figures(draft_source).figures


class TheAssemblyHalfTests(unittest.TestCase):
    """Level 0. Nothing here calls a model, which is the point: every number in the report is
    decided before anything is written."""

    def test_the_window_is_the_schedule_and_not_a_judgment(self) -> None:
        """A task closed on the day of the previous report belongs to that report, not this one.
        The window is open at the start and closed at the end, and the sample week has one task
        on each side of it."""
        assembly = compute_figures()
        brightwater = next(p for p in assembly.projects if p.project == "Brightwater Commons")
        halloway = next(p for p in assembly.projects if p.project == "Halloway Bridge Survey")
        self.assertEqual(brightwater.closed, 2)
        self.assertEqual(halloway.closed, 0)  # its one closed task closed on 09/09/2026

    def test_the_sample_week_computes_the_figures_the_page_quotes(self) -> None:
        assembly = compute_figures()
        by_project = {p.project: p for p in assembly.projects}
        self.assertEqual(sum(p.closed for p in assembly.projects), 3)
        self.assertEqual(sum(p.opened for p in assembly.projects), 3)
        self.assertEqual(sum(p.overdue for p in assembly.projects), 2)
        self.assertEqual(by_project["Ferndale Library"].hours_to_date, 59.0)
        self.assertEqual(by_project["Ferndale Library"].budget_hours, 60.0)
        self.assertAlmostEqual(by_project["Ferndale Library"].percent_of_budget, 98.3, places=1)
        self.assertEqual(len(assembly.waiting), 2)
        self.assertEqual(len(assembly.figures), 38)

    def test_a_project_name_no_list_recognizes_is_reported_and_not_guessed_at(self) -> None:
        """The inbox names a project nothing else knows. Attaching it to the nearest match would
        put a client's thread on the wrong job; dropping it would lose the thread. It is named."""
        assembly = compute_figures()
        self.assertEqual(assembly.unmatched, ("Mavis Street",))
        self.assertIsNone(project_key("Mavis Street"))
        self.assertEqual(project_key("brightwater"), "Brightwater Commons")
        self.assertEqual(project_key("BRIGHTWATER COMMONS"), "Brightwater Commons")

    def test_a_source_behind_the_report_date_is_named_rather_than_read_as_a_quiet_week(self) -> None:
        """The spreadsheet is three days behind, so this week's hours are not in it. Code says the
        date it is current to instead of reporting zero hours for the week."""
        assembly = compute_figures()
        self.assertEqual(assembly.behind, (("time spreadsheet", 3),))
        self.assertEqual(assembly.hours_through, "2026-09-11")
        labels = [f.label for f in assembly.figures]
        self.assertIn("the time spreadsheet is current only to", labels)
        current_to = next(f for f in assembly.figures if f.label == "the time spreadsheet is current only to")
        self.assertEqual(current_to.text, "09/15/2026")
        self.assertTrue(current_to.must_say)

    def test_hours_are_never_reported_as_zero_for_a_week_nobody_typed_in(self) -> None:
        """The figures hold hours to date and the date they run to. There is no this-week hours
        figure at all, because the source cannot support one."""
        labels = [f.label for f in compute_figures().figures]
        self.assertFalse([label for label in labels if "hours this week" in label])

    def test_a_quiet_week_still_produces_a_report(self) -> None:
        """A standing report that goes silent on a quiet week is indistinguishable from one that
        broke. The figures are all zeros and the report still goes out."""
        empty = tuple(Source(name=s.name, as_of=s.as_of) for s in SOURCES)
        assembly = compute_figures(empty)
        self.assertEqual(sum(p.closed for p in assembly.projects), 0)
        self.assertEqual(assembly.waiting, ())
        # Nothing is overdue and no budget is near its limit, so the only line the report still
        # has to carry is the one about the source that is behind. A quiet week and a broken
        # pull are different things and this is where the difference is kept.
        self.assertEqual(
            [f.label for f in required_figures(assembly.figures)],
            ["the time spreadsheet is current only to"],
        )


class TheWritingHalfTests(unittest.TestCase):
    """Level 1. One call, whatever kind of week it was."""

    def test_one_model_call_and_no_more(self) -> None:
        model = answering(CLEAN_DRAFT)
        run(SAMPLE_INPUT, model, tracer())
        with self.assertRaises(IndexError):
            model.complete([])

    def test_a_quiet_week_costs_the_same_one_call(self) -> None:
        empty = tuple(Source(name=s.name, as_of=s.as_of) for s in SOURCES)
        model = answering("Nothing closed and nothing opened this week.")
        report = run("", model, tracer(), sources=empty)
        self.assertEqual(report.unsupported, ())
        with self.assertRaises(IndexError):
            model.complete([])

    def test_every_step_is_decided_by_code(self) -> None:
        t = tracer()
        run(SAMPLE_INPUT, answering(CLEAN_DRAFT), t)
        self.assertEqual(t.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" for s in t.steps), [s.title for s in t.steps])
        self.assertEqual(sum(1 for s in t.steps if s.kind == "model"), 1)

    def test_the_prompt_carries_the_figures_and_the_note_and_not_the_raw_records(self) -> None:
        captured: list[str] = []

        def responder(messages, tools):
            captured.append("\n".join(str(m.content) for m in messages))
            return StubResponse(text=CLEAN_DRAFT)

        run("Lead with the library.", StubModel(responder), tracer())
        prompt = captured[0]
        self.assertIn("Ferndale Library: percent of budgeted hours used: 98.3", prompt)
        self.assertIn("Lead with the library.", prompt)
        self.assertNotIn("Shelving sign-off", prompt)  # an inbox subject nothing computed from

    def test_the_weeks_note_never_contributes_a_figure(self) -> None:
        """A note with a number in it is guidance, not data. It is not added to the figures, so a
        draft that quotes it is caught."""
        report = run("We are 14 days from the review.", answering(CLEAN_DRAFT + " Also 14 days."), tracer())
        self.assertIn("14", report.unsupported)


class UnsupportedFiguresTests(unittest.TestCase):
    """The first check: every number in the draft has to be one code produced."""

    def setUp(self) -> None:
        self.figures = figures_of()

    def test_a_clean_draft_has_nothing_unsupported(self) -> None:
        self.assertEqual(unsupported_figures(CLEAN_DRAFT, self.figures), ())

    def test_a_figure_rounded_to_something_tidier_is_named(self) -> None:
        draft = CLEAN_DRAFT.replace("98.3 percent", "98 percent")
        self.assertIn("98", unsupported_figures(draft, self.figures))

    def test_a_figure_written_with_an_extra_digit_is_named(self) -> None:
        """The comparison is on text, not on value, so 98.30 is a different figure from 98.3.
        That is strict on purpose: the model was asked to copy, and a number it reformatted is a
        number it retyped."""
        self.assertEqual(unsupported_figures("98.30 percent of the budget", self.figures), ("98.30",))

    def test_a_total_the_model_added_up_itself_is_named(self) -> None:
        """59.0 and 65.0 are both figures; 124.0 is the sum of them and is not."""
        draft = "The two projects have used 124.0 hours between them."
        self.assertEqual(unsupported_figures(draft, self.figures), ("124.0",))

    def test_an_invented_date_is_named_whole_and_a_real_one_is_not_split(self) -> None:
        self.assertEqual(unsupported_figures("due 10/31/2026", self.figures), ("10/31/2026",))
        self.assertEqual(unsupported_figures("due 09/16/2026", self.figures), ())

    def test_a_real_date_written_another_way_is_rejected(self) -> None:
        """9/10/2026 is the same day as 09/10/2026 and is not the same string. The check is a
        string comparison, so this is a rejection, and the fix is to redraft rather than to
        loosen the check."""
        self.assertEqual(unsupported_figures("due 9/10/2026", self.figures), ("9/10/2026",))

    def test_a_task_id_is_not_read_as_three_figures(self) -> None:
        self.assertEqual(unsupported_figures("BW-104 and IN-45 are both open", self.figures), ())

    def test_a_digit_stuck_to_a_word_with_no_hyphen_is_still_scanned(self) -> None:
        """Only hyphenated identifiers are blanked, so a number a model runs into a word is
        caught rather than hidden. This is narrower than blanking every alphanumeric token, and
        the narrower rule is the one worth having."""
        self.assertEqual(unsupported_figures("the FY26 budget", self.figures), ("26",))

    def test_a_right_figure_next_to_the_wrong_project_passes(self) -> None:
        """The limit of the check, proved rather than described: 98.3 is a real figure and
        Brightwater Commons is a real project, and the sentence is false. Nothing in code catches
        this, which is why a person reads the report."""
        draft = "Brightwater Commons has used 98.3 percent of its budgeted hours."
        self.assertEqual(unsupported_figures(draft, self.figures), ())

    def test_every_unsupported_token_is_reported_in_reading_order_with_repeats(self) -> None:
        draft = "We logged 77.0 hours, then another 77.0, and closed 3."
        self.assertEqual(unsupported_figures(draft, self.figures), ("77.0", "77.0"))


class MissingRequiredTests(unittest.TestCase):
    """The second check, and the one a standing report needs: a draft can be entirely truthful
    and still leave out the only line anybody had to act on."""

    def setUp(self) -> None:
        self.figures = figures_of()

    def test_a_clean_draft_leaves_nothing_must_say_out(self) -> None:
        self.assertEqual(missing_required(CLEAN_DRAFT, self.figures), ())

    def test_the_sample_week_marks_four_checkable_figures_must_say(self) -> None:
        required = required_figures(self.figures)
        self.assertEqual(
            [f.text for f in required],
            ["09/16/2026", "09/10/2026", "98.3", "09/15/2026"],
        )

    def test_a_draft_that_drops_the_budget_line_is_named(self) -> None:
        draft = CLEAN_DRAFT.replace("It has used 98.3 percent of its budgeted\nhours, 59.0 of 60, and", "It")
        missing = missing_required(draft, self.figures)
        self.assertEqual([f.text for f in missing], ["98.3"])
        self.assertIn("percent of budgeted hours used", missing[0].label)

    def test_a_draft_that_drops_the_stale_source_line_is_named(self) -> None:
        draft = CLEAN_DRAFT.replace("current only to 09/15/2026", "up to date")
        self.assertEqual([f.text for f in missing_required(draft, self.figures)], ["09/15/2026"])

    def test_no_figure_shorter_than_the_minimum_is_ever_required(self) -> None:
        """A check that a draft mentions "2" is not a check. Code refuses to claim one rather
        than running a test that passes by coincidence."""
        for figure in required_figures(self.figures):
            self.assertGreaterEqual(len(figure.text), MIN_CHECKABLE)
        short = short_must_say(self.figures)
        self.assertEqual(sorted({f.text for f in short}), ["1", "2"])
        self.assertTrue(any("overdue" in f.label for f in short))

    def test_a_short_must_say_figure_reaches_the_person_instead(self) -> None:
        report = run(SAMPLE_INPUT, answering(CLEAN_DRAFT), tracer())
        self.assertTrue(report.ok)
        self.assertEqual([f.text for f in report.confirm_by_eye], ["1", "1", "2", "2"])

    def test_two_figures_that_share_a_text_cannot_be_told_apart(self) -> None:
        """The case this check cannot see. Both figures are 09/11/2026, so a draft that mentions
        the date for one reason satisfies the requirement for the other. The page names this, and
        compute_figures avoids it in the sample week by requiring a date no other figure carries."""
        figures = (
            Figure("previous report", "09/11/2026"),
            Figure("the permit expired", "09/11/2026", must_say=True),
        )
        self.assertEqual(missing_required("Since 09/11/2026 the team has been on site.", figures), ())

    def test_a_report_that_fails_either_check_is_handed_back_whole(self) -> None:
        """Neither check repairs, retries or discards a draft. It goes to a person with the
        failures named, which is the only thing a level-1 recipe may do with one."""
        draft = CLEAN_DRAFT.replace("98.3 percent", "99 percent")
        report = run(SAMPLE_INPUT, answering(draft), tracer())
        self.assertFalse(report.ok)
        self.assertIn("99", report.unsupported)
        self.assertEqual([f.text for f in report.missing], ["98.3"])
        self.assertEqual(report.text, draft)


class PageFiguresTests(unittest.TestCase):
    """Numbers the recipe page and its run diagram quote, pinned here."""

    def test_the_run_costs_one_call_at_the_token_counts_the_page_states(self) -> None:
        t = tracer()
        run(SAMPLE_INPUT, answering(CLEAN_DRAFT), t)
        self.assertEqual(t.tokens_in_total(), 812)
        self.assertEqual(t.tokens_out_total(), 285)

    def test_the_example_declares_level_one(self) -> None:
        self.assertEqual(LEVEL, 1)
        self.assertTrue(callable(run))

    def test_the_command_plays_the_same_draft_these_tests_are_written_against(self) -> None:
        """One call, so one reply. If the demo command's sequence and this file's draft drift
        apart, the command demonstrates a run these tests never checked."""
        from examples.weekly_status_report.__main__ import SCRIPTED

        self.assertEqual(SCRIPTED, [CLEAN_DRAFT])


if __name__ == "__main__":
    unittest.main()
