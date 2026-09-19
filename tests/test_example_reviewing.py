"""Tests for examples/reviewing: one review surface, a presence check over an answer's figures
and the citations it names. No model is involved.

The first class is an attack suite on `figures_in`, because the example teaches a check and a
check that is wrong in the quiet direction -- reporting clean -- is worse than none. Each case is
one way a figure gets written in a real document: separators, currency marks, units, percentages,
ranges, negatives, dates, and identifiers that look like figures but claim nothing.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.corpus import Section, load_sections  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.common.types import Answer  # noqa: E402
from examples.reviewing.run import LEVEL, figures_in, run  # noqa: E402

SECTIONS = load_sections()

# A tiny synthetic corpus for the cases the appliance corpus does not happen to contain.
SCRATCH = {
    "spec#1": Section(doc="spec", number=1, title="Speeds", text="The pump runs at 1152 rpm and draws 15A."),
    "spec#2": Section(doc="spec", number=2, title="Price", text="The price is $1200 per unit, up 5 percent."),
    "spec#3": Section(doc="spec", number=3, title="Life", text="Rated for 18 to 24 months at -20°C."),
    "spec#4": Section(doc="spec", number=4, title="Revision", text="Superseded on 2026-09-18 by HLV-2205."),
}


class FiguresInTests(unittest.TestCase):
    def test_a_thousands_separator_is_the_same_figure_as_none(self) -> None:
        self.assertEqual(figures_in("It costs $1,200."), figures_in("It costs 1200 dollars."))

    def test_a_currency_mark_and_trailing_zeros_do_not_change_the_figure(self) -> None:
        self.assertEqual(figures_in("$52.00"), figures_in("52"))

    def test_a_unit_written_against_the_digits_is_kept_out_of_the_figure(self) -> None:
        self.assertEqual(figures_in("A 120V circuit at 120°F drawing 15A."), ["120", "15"])

    def test_a_percentage_is_one_figure_however_it_is_written(self) -> None:
        self.assertEqual(figures_in("80%"), ["80%"])
        self.assertEqual(figures_in("80 %"), ["80%"])
        self.assertEqual(figures_in("80 percent"), ["80%"])
        self.assertEqual(figures_in("80 percent"), ["80%"])

    def test_a_percentage_is_not_the_same_figure_as_the_bare_number(self) -> None:
        self.assertNotEqual(figures_in("Fill to 80%."), figures_in("Wait 80 minutes."))

    def test_a_range_states_both_of_its_ends(self) -> None:
        self.assertEqual(figures_in("Rated for 18-24 months."), ["18", "24"])
        self.assertEqual(figures_in("Rated for 18–24 months."), ["18", "24"])

    def test_a_negative_figure_keeps_its_sign(self) -> None:
        self.assertEqual(figures_in("Store above -20°C."), ["-20"])
        self.assertEqual(figures_in("Store above −20°C."), ["-20"])
        self.assertNotEqual(figures_in("-20"), figures_in("20"))

    def test_an_iso_date_is_one_figure_not_three(self) -> None:
        self.assertEqual(figures_in("Revised 2026-09-18."), ["2026-09-18"])

    def test_a_prose_date_is_a_known_limit(self) -> None:
        # Pinned, not endorsed: a date written in prose reads as its separate numbers, so it does
        # not match the same date written 2026-09-18. The page says so; a reviewer still checks
        # dates by eye.
        self.assertEqual(figures_in("Revised September 18, 2026."), ["18", "2026"])

    def test_identifiers_state_no_figure(self) -> None:
        self.assertEqual(figures_in("The HLV-2205 fits the DW-300 and the DW300."), [])
        self.assertEqual(figures_in("See dw300-manual#3 and parts-list#2."), [])

    def test_a_version_number_does_not_leak_its_decimal_part(self) -> None:
        # v2.1 is an identifier; an earlier checker pulled a bare "1" out of it and then asked
        # every cited section to contain the number 1.
        self.assertEqual(figures_in("Firmware v2.1 ships today."), [])
        # Known limit, pinned: a trailing letter reads as a unit (52dBA, 15A), so an identifier
        # that starts with digits and ends in a letter is read as a figure.
        self.assertEqual(figures_in("Revision 3.4b applies."), ["3.4"])

    def test_punctuation_around_a_figure_is_not_part_of_it(self) -> None:
        self.assertEqual(figures_in('It costs $52.00, "the (52) list price".'), ["52"])

    def test_a_purely_qualitative_sentence_states_no_figure(self) -> None:
        self.assertEqual(figures_in("The drain pump is the standard replacement part."), [])


class PresenceCheckTests(unittest.TestCase):
    def check(self, text: str, citations: list[str], sections: dict[str, Section] | None = None):
        tracer = Tracer(example="reviewing", level=LEVEL, model_id="no-model-called")
        return run(Answer(text=text, citations=citations), sections or SECTIONS, tracer)

    def test_a_citation_that_carries_the_claimed_figure_is_clean(self) -> None:
        report = self.check("The HLV-2205 drain pump costs $52.00. Sources: parts-list#2", ["parts-list#2"])
        self.assertTrue(report.clean, report.flags)
        self.assertEqual(report.figures_claimed, ["52"])

    def test_a_citation_that_carries_none_of_the_figures_is_flagged(self) -> None:
        report = self.check(
            "The HLV-2205 drain pump costs $52.00. Sources: parts-list#2, dw300-manual#3",
            ["parts-list#2", "dw300-manual#3"],
        )
        self.assertFalse(report.clean)
        self.assertIn(("dw300-manual#3", "section carries none of the answer's figures"),
                      [(f.subject, f.reason) for f in report.flags])

    def test_a_figure_inside_a_larger_number_is_not_a_match(self) -> None:
        # The bug a substring search has: "52" appears inside "1152 rpm", so the citation would
        # have been reported as supporting a price it says nothing about.
        report = self.check("The pump costs $52.", ["spec#1"], SCRATCH)
        self.assertFalse(report.clean)

    def test_a_separator_difference_is_not_a_mismatch(self) -> None:
        report = self.check("The unit costs $1,200.", ["spec#2"], SCRATCH)
        self.assertTrue(report.clean, report.flags)

    def test_both_ends_of_a_range_are_checked(self) -> None:
        report = self.check("Rated for 18-24 months.", ["spec#3"], SCRATCH)
        self.assertTrue(report.clean, report.flags)
        report = self.check("Rated for 18-36 months.", ["spec#3"], SCRATCH)
        self.assertEqual([f.subject for f in report.flags], ["36"])

    def test_a_negative_figure_is_checked_as_a_negative(self) -> None:
        self.assertTrue(self.check("Store above -20°C.", ["spec#3"], SCRATCH).clean)
        self.assertFalse(self.check("Store above 20°C.", ["spec#3"], SCRATCH).clean)

    def test_a_figure_carried_by_no_cited_section_is_flagged_on_its_own(self) -> None:
        report = self.check("It costs $52.00 and weighs 9 kg. Sources: parts-list#2", ["parts-list#2"])
        self.assertEqual([(f.subject, f.reason) for f in report.flags],
                         [("9", "figure appears in no cited section")])

    def test_figures_with_no_citation_at_all_are_flagged(self) -> None:
        report = self.check("It costs $52.00.", [])
        self.assertEqual([f.subject for f in report.flags], ["52"])

    def test_a_citation_outside_the_corpus_is_flagged_as_missing(self) -> None:
        report = self.check("It costs $52.00.", ["not-a-real-doc#9"])
        self.assertIn("does not exist", report.flags[0].reason)

    def test_an_answer_with_no_figures_flags_nothing(self) -> None:
        report = self.check("The drain pump is the standard replacement part.", ["parts-list#2"])
        self.assertTrue(report.clean)
        self.assertEqual(report.figures_claimed, [])

    def test_a_matching_number_with_the_wrong_unit_is_a_known_limit(self) -> None:
        # Pinned, not endorsed: units are dropped, so 15 gallons "matches" a section that says
        # 15A. The page states this limit; it is what the human reviewer is still there for.
        self.assertTrue(self.check("It holds 15 gallons.", ["spec#1"], SCRATCH).clean)

    def test_every_step_is_decided_by_code(self) -> None:
        tracer = Tracer(example="reviewing", level=LEVEL, model_id="no-model-called")
        run(Answer(text="It costs $52.00.", citations=["parts-list#2"]), SECTIONS, tracer)
        self.assertEqual(tracer.model_decided_count(), 0)
        self.assertTrue(all(s.decided_by == "code" for s in tracer.steps))

    def test_declares_its_level_and_a_run_function(self) -> None:
        import examples.reviewing.run as module

        self.assertTrue(callable(module.run))
        self.assertEqual(module.LEVEL, 2)

    def test_record_trace_still_finds_reviewing_unrecordable(self) -> None:
        # `run(answer, sections, tracer)` checks a drafted Answer against the corpus; it calls no
        # model and has no single `<text>` question to fill in from --question. This same `run`
        # is what reviewing.mdx's `<CodeFile func="run" />` shows -- reshaping it to
        # (text, model, tracer), or adding a second function under that name, would either break
        # the page's walkthrough or collide with the name. Left unrecordable on purpose; see
        # .local/page-requests/wave6-examples.md.
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        import record_trace

        rec = record_trace.classify("reviewing")
        self.assertFalse(rec.ok)
        self.assertIn("answer", rec.reason)


if __name__ == "__main__":
    unittest.main()
