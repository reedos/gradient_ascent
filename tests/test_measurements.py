"""The gate a page passes to be `measured` (docs/FIRST-LIVE-RUN.md, "Draft to Published"), as code.

A page is `measured` in content/taxonomy.json exactly when content/measurements.json lists it, and
every entry there points at a result file and a recorded trace that are real, whole and readable.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = json.loads((ROOT / "content" / "taxonomy.json").read_text(encoding="utf-8"))
MEASUREMENTS = json.loads((ROOT / "content" / "measurements.json").read_text(encoding="utf-8"))


def _pages(node, out):
    """Every dict in the taxonomy with a slug and a status, wherever it sits."""
    if isinstance(node, dict):
        if isinstance(node.get("slug"), str) and isinstance(node.get("status"), str):
            out[node["slug"]] = node
        for value in node.values():
            _pages(value, out)
    elif isinstance(node, list):
        for value in node:
            _pages(value, out)
    return out


PAGES = _pages(TAXONOMY, {})


def _safe_name(model_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", model_id)


class MeasuredPagesTests(unittest.TestCase):
    def test_a_page_is_measured_exactly_when_it_has_a_measurement(self) -> None:
        measured = {slug for slug, page in PAGES.items() if page["status"] == "measured"}
        listed = {entry["page"] for entry in MEASUREMENTS["results"]}
        self.assertEqual(measured, listed, "taxonomy status and content/measurements.json disagree")

    def test_every_model_is_described_with_a_class_the_site_measures_and_a_source(self) -> None:
        for model_id, model in MEASUREMENTS["models"].items():
            self.assertIn(model["class"], MEASUREMENTS["classes"], model_id)
            self.assertTrue(model["source"]["url"].startswith("https://"), model_id)
            for field in ("name", "maker", "how_run"):
                self.assertTrue(model.get(field), f"{model_id} has no {field}")


class MeasurementEntryTests(unittest.TestCase):
    def test_every_entry_points_at_a_whole_readable_result(self) -> None:
        for entry in MEASUREMENTS["results"]:
            where = f"{entry['page']} on {entry['model']}"
            self.assertIn(entry["model"], MEASUREMENTS["models"], where)
            self.assertIn(entry["grader"], MEASUREMENTS["models"], f"{where}: grader is not described")
            path = ROOT / "evals" / "results" / entry["example"] / f"{_safe_name(entry['model'])}.json"
            self.assertTrue(path.is_file(), f"{where}: no result file at {path.relative_to(ROOT)}")
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(result["model_id"], entry["model"], where)
            self.assertFalse(result["stub"], f"{where}: stub run")
            self.assertFalse(result["partial"], f"{where}: partial run")
            self.assertFalse(result.get("interrupted"), f"{where}: interrupted run")
            self.assertEqual(result["questions_run"], result["questions_total"], f"{where}: not every question ran")
            self.assertEqual(result["ungraded"], 0, f"{where}: ungraded answers")
            self.assertEqual(result.get("empty_completions"), 0, f"{where}: empty replies, or not counted")
            self.assertGreaterEqual(
                entry["grader_sample_checked"], result["run_date"][:10],
                f"{where}: the grader's verdicts were checked before this run happened",
            )

    def test_every_entry_has_a_recorded_trace_whose_steps_fit_the_level(self) -> None:
        for entry in MEASUREMENTS["results"]:
            where = f"{entry['page']} on {entry['model']}"
            path = ROOT / "examples" / entry["example"] / "trace.json"
            self.assertTrue(path.is_file(), f"{where}: no recorded trace")
            trace = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(trace["stub"], f"{where}: the trace is a stub run")
            self.assertFalse(trace["illustrative"], f"{where}: the trace is marked illustrative")
            self.assertEqual(trace["model_id"], entry["model"], f"{where}: the trace is from another model")
            level = PAGES[entry["page"]].get("level", trace["level"])
            self.assertEqual(trace["level"], level, where)
            decided = [s["decided_by"] for s in trace["steps"]]
            if trace["level"] <= 3:
                # Levels 0-3: code chooses every step (examples/common/trace.py).
                self.assertEqual(set(decided), {"code"}, f"{where}: a model chose a step at level {trace['level']}")
            else:
                # Levels 4 and up exist because the model chooses what happens next.
                self.assertIn("model", decided, f"{where}: no model-decided step at level {trace['level']}")

    def test_a_loop_result_says_how_many_questions_a_cap_ended(self) -> None:
        """A loop the code's budget cut off is scored like one the model finished. The count has
        to be on the result so the page can say how often the budget, not the model, stopped it."""
        for entry in MEASUREMENTS["results"]:
            trace = json.loads((ROOT / "examples" / entry["example"] / "trace.json").read_text(encoding="utf-8"))
            if trace["level"] < 4:
                continue
            path = ROOT / "evals" / "results" / entry["example"] / f"{_safe_name(entry['model'])}.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("forced_finals", result, f"{entry['page']}: result predates forced_finals; re-run it")


if __name__ == "__main__":
    unittest.main()
