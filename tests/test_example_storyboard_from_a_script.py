"""Tests for examples/storyboard_from_a_script: the level-3 scene-then-shot chain.

Three things are pinned here, matching the recipe's own claim.

- **The full chain runs in a fixed order and every step is the code's decision.** Scenes, then
  shots, then a coverage check, whatever either model call says; `tracer.model_decided_count()`
  stays zero.
- **The coverage check is arithmetic a test can attack directly.** A shot range that falls outside
  the script is dropped and reported rather than silently counted; a shot range that falls outside
  its own scene is reported without being invented into being correct; a script line no shot
  touches is reported by number, including the pure-voiceover line that has no visual of its own
  to be found next to.
- **The duration sums and the JSON retry path are the code's, recomputed here independently of
  whatever `run.py` happens to print.**
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.common.model import Message, StubModel, StubResponse  # noqa: E402
from examples.common.trace import Tracer  # noqa: E402
from examples.storyboard_from_a_script.run import (  # noqa: E402
    LEVEL,
    OVER_BUDGET_FACTOR,
    SAMPLE_INPUT,
    SCRIPT_LINES,
    WORDS_PER_MINUTE,
    CoverageReport,
    Scene,
    Shot,
    check_coverage,
    estimate_read_seconds,
    parse_script,
    run,
)

RUN_PY = ROOT / "examples" / "storyboard_from_a_script" / "run.py"

# The script has 25 lines. Scenes split it with no gap and no overlap: 1-13, 14-15, 16-21, 22-25.
SCENES = [
    {"scene": 1, "heading": "INT. HOME OFFICE - DUSK", "first_line": 1, "last_line": 13},
    {"scene": 2, "heading": "INT. HOME OFFICE - CONTINUOUS", "first_line": 14, "last_line": 15},
    {"scene": 3, "heading": "INT. BEDROOM - NIGHT", "first_line": 16, "last_line": 21},
    {"scene": 4, "heading": "TAG - PRODUCT CARD", "first_line": 22, "last_line": 25},
]

# 20 shots. Scene 2 needs two shots for line 14 (the lamp folding and Mara zipping the box happen
# in the same beat), and the second of those two also carries line 15, the voiceover line with no
# visual of its own -- covered by pairing it with the shot playing while it is read, not dropped.
SHOTS = [
    {"scene": 1, "shot": 1, "size": "wide", "on_screen": "the cluttered desk at dusk, overhead bulb flickering", "seconds": 3.0, "first_line": 1, "last_line": 1},
    {"scene": 1, "shot": 2, "size": "medium", "on_screen": "a hand pulling the shipping box from a mailer", "seconds": 2.5, "first_line": 2, "last_line": 2},
    {"scene": 1, "shot": 3, "size": "close-up", "on_screen": "the box lid lifting to reveal the lamp", "seconds": 2.5, "first_line": 3, "last_line": 3},
    {"scene": 1, "shot": 4, "size": "medium", "on_screen": "Mara addressing camera about skipping the manual", "seconds": 3.0, "first_line": 4, "last_line": 4},
    {"scene": 1, "shot": 5, "size": "wide", "on_screen": "Mara setting the insert aside and standing the lamp upright", "seconds": 2.0, "first_line": 5, "last_line": 5},
    {"scene": 1, "shot": 6, "size": "close-up", "on_screen": "the lamp head tilting up, light warming then shifting to daylight white", "seconds": 3.0, "first_line": 6, "last_line": 7},
    {"scene": 1, "shot": 7, "size": "close-up", "on_screen": "the base ring glowing blue under her finger", "seconds": 2.0, "first_line": 8, "last_line": 8},
    {"scene": 1, "shot": 8, "size": "close-up", "on_screen": "the ring tapped twice, light dimming, tapped again to full", "seconds": 3.0, "first_line": 9, "last_line": 10},
    {"scene": 1, "shot": 9, "size": "wide", "on_screen": "the desk organized now, lamp centered over the notebook", "seconds": 2.5, "first_line": 11, "last_line": 11},
    {"scene": 1, "shot": 10, "size": "medium", "on_screen": "Mara opening her laptop and typing under steady light", "seconds": 3.0, "first_line": 12, "last_line": 13},
    {"scene": 2, "shot": 1, "size": "insert", "on_screen": "the lamp's arm folding flat against its base", "seconds": 1.5, "first_line": 14, "last_line": 14},
    {"scene": 2, "shot": 2, "size": "medium", "on_screen": "Mara zipping the shipping box shut and setting it by the door", "seconds": 2.0, "first_line": 14, "last_line": 15},
    {"scene": 3, "shot": 1, "size": "wide", "on_screen": "the nightstand: folded lamp beside water and a paperback", "seconds": 2.5, "first_line": 16, "last_line": 16},
    {"scene": 3, "shot": 2, "size": "medium", "on_screen": "Mara at the nightstand, saying she travels with hers", "seconds": 2.5, "first_line": 17, "last_line": 17},
    {"scene": 3, "shot": 3, "size": "close-up", "on_screen": "the woven fabric cord coiled neatly beside the base", "seconds": 2.5, "first_line": 18, "last_line": 19},
    {"scene": 3, "shot": 4, "size": "medium", "on_screen": "Mara unfolding the lamp and switching it to warm light", "seconds": 2.5, "first_line": 20, "last_line": 20},
    {"scene": 3, "shot": 5, "size": "close-up", "on_screen": "Mara, quieter, saying that's the whole lamp", "seconds": 2.5, "first_line": 21, "last_line": 21},
    {"scene": 4, "shot": 1, "size": "close-up", "on_screen": "slow push-in on the lit lamp as the room dims", "seconds": 3.0, "first_line": 22, "last_line": 22},
    {"scene": 4, "shot": 2, "size": "wide", "on_screen": "final card with the product name, the glow visible behind it", "seconds": 2.5, "first_line": 23, "last_line": 24},
    {"scene": 4, "shot": 3, "size": "wide", "on_screen": "the glow fading to black behind the card, closing voiceover", "seconds": 2.5, "first_line": 24, "last_line": 25},
]

SCENES_RESPONSE = json.dumps({"scenes": SCENES})
SHOTS_RESPONSE = json.dumps({"shots": SHOTS})


def tracer(model_id: str = "stub-1") -> Tracer:
    return Tracer(example="storyboard_from_a_script", level=LEVEL, model_id=model_id)


def scenes_tuple() -> tuple[Scene, ...]:
    return tuple(Scene(s["scene"], s["heading"], s["first_line"], s["last_line"]) for s in SCENES)


def shots_tuple() -> tuple[Shot, ...]:
    return tuple(Shot(s["scene"], s["shot"], s["size"], s["on_screen"], float(s["seconds"]), s["first_line"], s["last_line"]) for s in SHOTS)


class FullChainTests(unittest.TestCase):
    def test_the_full_chain_covers_every_line_with_no_drops_or_escapes(self) -> None:
        model = StubModel([StubResponse(text=SCENES_RESPONSE), StubResponse(text=SHOTS_RESPONSE)])
        trace = tracer()
        report = run(SAMPLE_INPUT, model, trace)
        self.assertEqual(len(report.scenes), 4)
        self.assertEqual(len(report.shots), 20)
        self.assertEqual(report.uncovered_lines, ())
        self.assertEqual(report.dropped_shots, ())
        self.assertEqual(report.scene_escapes, ())

    def test_the_steps_run_in_a_fixed_order_and_every_one_is_the_codes_decision(self) -> None:
        model = StubModel([StubResponse(text=SCENES_RESPONSE), StubResponse(text=SHOTS_RESPONSE)])
        trace = tracer()
        run(SAMPLE_INPUT, model, trace)
        titles = [s.title for s in trace.steps]
        self.assertEqual(
            titles,
            [
                "Read the numbered script",
                "Split into scenes",
                "Validate the scene JSON",
                "Parse the scene list",
                "Propose shots for all scenes",
                "Validate the shot JSON",
                "Parse the shot list",
                "Check coverage against the script",
            ],
        )
        self.assertTrue(all(s.decided_by == "code" for s in trace.steps))
        self.assertEqual(trace.model_decided_count(), 0)
        self.assertEqual(sum(1 for s in trace.steps if s.kind == "model"), 2, "one scenes call, one shots call")

    def test_the_source_records_no_model_decision_anywhere(self) -> None:
        # scripts/validate.py reads examples for this string; the example must not carry one.
        self.assertNotIn('decided_by="model"', RUN_PY.read_text(encoding="utf-8"))


class RetryTests(unittest.TestCase):
    def test_invalid_json_from_the_scenes_call_is_retried_once_and_then_succeeds(self) -> None:
        model = StubModel([
            StubResponse(text="not json at all"),
            StubResponse(text=SCENES_RESPONSE),
            StubResponse(text=SHOTS_RESPONSE),
        ])
        trace = tracer()
        report = run(SAMPLE_INPUT, model, trace)
        self.assertEqual(len(report.scenes), 4)
        model_steps = [s for s in trace.steps if s.kind == "model"]
        self.assertEqual(len(model_steps), 3, "scenes attempt 1, scenes retry, shots attempt 1")
        self.assertIn("retry with the validation error", model_steps[1].title)
        self.assertEqual(trace.model_decided_count(), 0)

    def test_a_scenes_call_that_never_validates_leaves_the_run_empty_but_does_not_crash(self) -> None:
        model = StubModel([
            StubResponse(text="still not json"),
            StubResponse(text="{\"scenes\": [{\"scene\": 1}]}"),  # missing required fields
            StubResponse(text=SHOTS_RESPONSE),
        ])
        trace = tracer()
        report = run(SAMPLE_INPUT, model, trace)
        self.assertEqual(report.scenes, ())
        # With no scenes, every shot in the (still-valid) shot response escapes its scene, and
        # nothing is uncovered because the shots still land inside the script's own line numbers.
        self.assertEqual(len(report.scene_escapes), 20)
        self.assertEqual(report.uncovered_lines, ())


class CoverageAttackTests(unittest.TestCase):
    """Each test here tries to get something past the coverage check that the page says the check
    catches, and asserts it does not get through."""

    def test_a_shot_range_outside_the_script_is_dropped_and_reported_not_counted(self) -> None:
        scenes = scenes_tuple()
        shots = shots_tuple() + (
            Shot(scene=4, number=9, size="wide", on_screen="an ending that never happens", seconds=99.0, first_line=26, last_line=27),
        )
        report = check_coverage(scenes, shots, parse_script(SAMPLE_INPUT))
        self.assertEqual(len(report.dropped_shots), 1)
        self.assertIn("outside the script", report.dropped_shots[0])
        self.assertEqual(len(report.shots), 20, "the out-of-script shot must not join the accepted list")
        self.assertNotIn(99.0, report.seconds_by_scene.values())

    def test_the_voiceover_line_with_no_visual_of_its_own_is_reported_uncovered_if_dropped(self) -> None:
        scenes = scenes_tuple()
        # Same as the canonical shot list, but scene 2's second shot stops at line 14 instead of
        # 15: line 15 (the pure voiceover line) is then covered by nothing.
        shots = tuple(s for s in shots_tuple() if not (s.scene == 2 and s.number == 2))
        shots += (Shot(scene=2, number=2, size="medium", on_screen="Mara zipping the box shut", seconds=2.0, first_line=14, last_line=14),)
        report = check_coverage(scenes, shots, parse_script(SAMPLE_INPUT))
        self.assertEqual(report.uncovered_lines, (15,))

    def test_a_shot_inside_the_script_but_outside_its_own_scene_is_reported(self) -> None:
        scenes = scenes_tuple()
        # Scene 1 runs lines 1-13; this shot reaches into scene 2's line 14.
        shots = shots_tuple() + (
            Shot(scene=1, number=11, size="wide", on_screen="a shot that bleeds into the next scene", seconds=2.0, first_line=12, last_line=14),
        )
        report = check_coverage(scenes, shots, parse_script(SAMPLE_INPUT))
        self.assertEqual(len(report.scene_escapes), 1)
        self.assertIn("scene 1 shot 11", report.scene_escapes[0])
        self.assertIn(shots[-1], report.shots, "an escaping shot is reported, not silently dropped")

    def test_a_shot_naming_a_scene_number_the_scene_list_does_not_have_is_reported(self) -> None:
        scenes = scenes_tuple()
        shots = (Shot(scene=9, number=1, size="wide", on_screen="orphaned shot", seconds=2.0, first_line=1, last_line=1),)
        report = check_coverage(scenes, shots, parse_script(SAMPLE_INPUT))
        self.assertEqual(len(report.scene_escapes), 1)
        self.assertIn("does not have", report.scene_escapes[0])


class DurationTests(unittest.TestCase):
    def test_seconds_sum_per_scene_and_in_total_match_an_independent_recomputation(self) -> None:
        scenes = scenes_tuple()
        shots = shots_tuple()
        report = check_coverage(scenes, shots, parse_script(SAMPLE_INPUT))
        expected_by_scene: dict[int, float] = {}
        for s in SHOTS:
            expected_by_scene[s["scene"]] = expected_by_scene.get(s["scene"], 0.0) + s["seconds"]
        self.assertEqual(report.seconds_by_scene, expected_by_scene)
        self.assertAlmostEqual(report.total_seconds, sum(s["seconds"] for s in SHOTS), places=6)
        self.assertAlmostEqual(report.total_seconds, 50.5, places=6)

    def test_the_estimated_read_time_matches_a_words_over_pace_recomputation(self) -> None:
        script_lines = parse_script(SAMPLE_INPUT)
        expected_words = sum(len(text.split()) for text in SCRIPT_LINES)
        expected_seconds = (expected_words / WORDS_PER_MINUTE) * 60.0
        self.assertAlmostEqual(estimate_read_seconds(script_lines), expected_seconds, places=6)

    def test_a_shot_list_that_runs_to_three_times_the_read_time_is_flagged_not_corrected(self) -> None:
        scenes = (Scene(1, "ONE SHOT, FOREVER", 1, 1),)
        script_lines = {1: "A single short line."}
        read_seconds = estimate_read_seconds(script_lines)
        huge_shot = Shot(scene=1, number=1, size="wide", on_screen="the same frame, held", seconds=read_seconds * (OVER_BUDGET_FACTOR + 1), first_line=1, last_line=1)
        report = check_coverage(scenes, (huge_shot,), script_lines)
        self.assertTrue(report.over_budget)
        self.assertEqual(report.total_seconds, huge_shot.seconds, "the code reports the number, it does not shorten it")

    def test_a_shot_list_well_under_the_read_time_is_not_flagged(self) -> None:
        report = check_coverage(scenes_tuple(), shots_tuple(), parse_script(SAMPLE_INPUT))
        self.assertFalse(report.over_budget)


class ParseScriptTests(unittest.TestCase):
    def test_every_numbered_line_round_trips_through_sample_input(self) -> None:
        parsed = parse_script(SAMPLE_INPUT)
        self.assertEqual(len(parsed), len(SCRIPT_LINES))
        self.assertEqual(parsed[1], SCRIPT_LINES[0])
        self.assertEqual(parsed[25], SCRIPT_LINES[24])

    def test_a_line_that_does_not_match_the_numbered_format_is_skipped_not_guessed_at(self) -> None:
        parsed = parse_script("1. First line.\nsomething unnumbered\n2. Second line.")
        self.assertEqual(parsed, {1: "First line.", 2: "Second line."})


class PageNumbersTests(unittest.TestCase):
    """Every figure site/src/content/recipes/storyboard-from-a-script.mdx quotes, reproduced from
    the same scripted run. A number on a page that no test recomputes drifts the first time a
    prompt or a duration changes, and nothing fails."""

    def test_the_run_the_page_walks_through_produces_the_numbers_it_states(self) -> None:
        model = StubModel([StubResponse(text=SCENES_RESPONSE), StubResponse(text=SHOTS_RESPONSE)])
        trace = tracer()
        report = run(SAMPLE_INPUT, model, trace)
        calls = [(s.tokens_in, s.tokens_out) for s in trace.steps if s.kind == "model"]
        self.assertEqual(calls, [(565, 89), (664, 816)])
        self.assertEqual((trace.tokens_in_total(), trace.tokens_out_total()), (1229, 905))
        self.assertEqual((len(report.scenes), len(report.shots)), (4, 20))
        self.assertEqual((report.total_seconds, report.estimated_read_seconds), (50.5, 137.6))
        self.assertFalse(report.over_budget)


class ReportTextTests(unittest.TestCase):
    def test_report_text_is_readable_and_names_the_uncovered_line(self) -> None:
        scenes = scenes_tuple()
        shots = tuple(s for s in shots_tuple() if not (s.scene == 2 and s.number == 2))
        report = check_coverage(scenes, shots, parse_script(SAMPLE_INPUT))
        self.assertIn("uncovered lines: 15", report.text)


if __name__ == "__main__":
    unittest.main()
