"""Tests for content/worksheet.json, the worksheet's decision data.

Reimplements the small tree-walking evaluator from site/src/lib/worksheet.ts in plain Python, so
the data is checked independently of the TypeScript that also reads it. Covers: every referenced
level and relation actually exists in content/taxonomy.json, the rules are monotonic (continuing
past a question never lowers the eventual level), every level 0-7 is reachable, and twelve worked
cases land where a person reading the site's own level definitions would expect.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "content" / "worksheet.json", encoding="utf-8") as f:
    WORKSHEET = json.load(f)
with open(ROOT / "content" / "taxonomy.json", encoding="utf-8") as f:
    TAXONOMY = json.load(f)

CORE_BY_ID = {q["id"]: q for q in WORKSHEET["core_questions"]}
CROSS_BY_ID = {q["id"]: q for q in WORKSHEET["cross_questions"]}

UPGRADE_RELATIONS = {
    (r["from"], r["to"]) for r in TAXONOMY["relations"] if r["type"] == "upgrades_to"
}
RELATION_WHEN = {
    (r["from"], r["to"]): r.get("when", "")
    for r in TAXONOMY["relations"]
    if r["type"] == "upgrades_to"
}

TIER_ORDERS = {t["order"] for t in TAXONOMY["tiers"]}

# Every id a worksheet caution or relation might legitimately point at: tier pages, track roots,
# and track pages -- mirrors site/src/lib/content.ts's techniqueIndex.
VALID_SLUGS = set()
for tier in TAXONOMY["tiers"]:
    for page in tier["pages"]:
        VALID_SLUGS.add(page["slug"])
for track in TAXONOMY["tracks"]:
    VALID_SLUGS.add(track["id"])
    for page in track.get("pages", []):
        VALID_SLUGS.add(page["slug"])


def answer_reason(answer):
    """The reason text for one core answer: a relation's own `when` sentence when it has one,
    else its authored `reason`. Mirrors worksheet.ts's answerReason/resolveWorksheet."""
    rel = answer.get("relation")
    if rel:
        return RELATION_WHEN.get((rel["from"], rel["to"]), answer.get("reason", ""))
    return answer.get("reason", "")


def evaluate_core(answers):
    """answers: ordered list of (question_id, answer_id) pairs. Returns (level, reasons, settled).
    Mirrors worksheet.ts's evaluateCore exactly: walk from first_question, follow the given
    answers, stop at the first settle."""
    given = dict(answers)
    reasons = []
    qid = WORKSHEET["first_question"]
    level = 0
    settled = False
    while qid:
        q = CORE_BY_ID.get(qid)
        if q is None:
            break
        answer_id = given.get(qid)
        if answer_id is None:
            break
        answer = next((a for a in q["answers"] if a["id"] == answer_id), None)
        if answer is None:
            break
        reasons.append((qid, answer_id, answer_reason(answer)))
        if answer["action"] == "settle":
            level = answer.get("level", level)
            settled = True
            qid = None
        else:
            qid = answer.get("next")
    return level, reasons, settled


def evaluate_cross(answers):
    given = dict(answers)
    cautions = []
    for q in WORKSHEET["cross_questions"]:
        answer_id = given.get(q["id"])
        if answer_id is None:
            continue
        answer = next((a for a in q["answers"] if a["id"] == answer_id), None)
        if answer is None or not answer.get("caution"):
            continue
        cautions.append((q["id"], answer_id, answer["caution"]))
    return cautions


def min_reachable_level(qid, seen=frozenset()):
    """The lowest level any path starting at (or continuing through) `qid` can settle at. Used
    to check monotonicity: settling right here must never beat what continuing could reach."""
    if qid in seen:
        return 8  # cyclic data bug guard; never actually hit by this file's tree
    q = CORE_BY_ID[qid]
    levels = []
    for a in q["answers"]:
        if a["action"] == "settle":
            levels.append(a["level"])
        else:
            levels.append(min_reachable_level(a["next"], seen | {qid}))
    return min(levels)


# -- Twelve worked cases: a scenario, the answer path a person would give, and the level the
# site's own level definitions say it lands on. Five are the task's own examples; seven more fill
# in every level the first five miss. --
WORKED_CASES = [
    (
        "Reconcile two spreadsheets with a fixed matching rule",
        [("rule", "yes")],
        0,
    ),
    (
        "Approve or deny a loan application using a fixed scoring rule on the applicant's numbers",
        [("rule", "yes")],
        0,
    ),
    (
        "Draft a thank-you note using details already given in the request",
        [("rule", "no"), ("one-call", "yes")],
        1,
    ),
    (
        "Answer one-off questions about a single pasted paragraph, nothing else needed",
        [("rule", "no"), ("one-call", "yes")],
        1,
    ),
    (
        "Answer questions from a policy manual",
        [("rule", "no"), ("one-call", "no"), ("context", "yes")],
        2,
    ),
    (
        "Sort support email into five fixed categories",
        [("rule", "no"), ("one-call", "no"), ("context", "no"), ("workflow", "yes")],
        3,
    ),
    (
        "Watch regulatory pages nightly and label what changed",
        [("rule", "no"), ("one-call", "no"), ("context", "no"), ("workflow", "yes")],
        3,
    ),
    (
        "Look up a customer's live order status and answer their question with it",
        [("rule", "no"), ("one-call", "no"), ("context", "no"), ("workflow", "no"), ("tools", "yes")],
        4,
    ),
    (
        "Investigate why a test suite fails and fix it",
        [
            ("rule", "no"),
            ("one-call", "no"),
            ("context", "no"),
            ("workflow", "no"),
            ("tools", "no"),
            ("agent", "yes"),
        ],
        5,
    ),
    (
        "Two independent agents research a claim separately and reconcile disagreements before publishing",
        [
            ("rule", "no"),
            ("one-call", "no"),
            ("context", "no"),
            ("workflow", "no"),
            ("tools", "no"),
            ("agent", "no"),
            ("team", "review"),
        ],
        6,
    ),
    (
        "Split a large literature review across several agents because it will not fit one agent's context",
        [
            ("rule", "no"),
            ("one-call", "no"),
            ("context", "no"),
            ("workflow", "no"),
            ("tools", "no"),
            ("agent", "no"),
            ("team", "split"),
        ],
        6,
    ),
    (
        "An always-on assistant that checks project status each morning on its own and keeps running unattended for weeks",
        [
            ("rule", "no"),
            ("one-call", "no"),
            ("context", "no"),
            ("workflow", "no"),
            ("tools", "no"),
            ("agent", "no"),
            ("team", "long"),
        ],
        7,
    ),
]


class WorksheetDataTests(unittest.TestCase):
    def test_first_question_exists(self):
        self.assertIn(WORKSHEET["first_question"], CORE_BY_ID)

    def test_every_next_pointer_is_a_real_core_question(self):
        for q in WORKSHEET["core_questions"]:
            for a in q["answers"]:
                if a["action"] == "next":
                    self.assertIn(
                        a.get("next"), CORE_BY_ID, f"{q['id']}/{a['id']} points at unknown question {a.get('next')}"
                    )

    def test_every_settle_level_is_a_real_tier(self):
        for q in WORKSHEET["core_questions"]:
            for a in q["answers"]:
                if a["action"] == "settle":
                    self.assertIn(a.get("level"), TIER_ORDERS, f"{q['id']}/{a['id']}: level {a.get('level')}")

    def test_every_answer_action_is_known(self):
        for q in WORKSHEET["core_questions"]:
            for a in q["answers"]:
                self.assertIn(a["action"], ("settle", "next"))

    def test_every_relation_reference_resolves_in_taxonomy(self):
        for q in WORKSHEET["core_questions"]:
            for a in q["answers"]:
                rel = a.get("relation")
                if rel is None:
                    continue
                pair = (rel["from"], rel["to"])
                self.assertIn(
                    pair,
                    UPGRADE_RELATIONS,
                    f"{q['id']}/{a['id']}: no upgrades_to relation from {rel['from']} to {rel['to']} in taxonomy.json",
                )

    def test_every_answer_resolves_to_non_empty_reason_text(self):
        for q in WORKSHEET["core_questions"]:
            for a in q["answers"]:
                self.assertTrue(answer_reason(a).strip(), f"{q['id']}/{a['id']} has no reason text")

    def test_cross_caution_links_point_at_real_taxonomy_ids(self):
        for q in WORKSHEET["cross_questions"]:
            for a in q["answers"]:
                caution = a.get("caution")
                if not caution:
                    continue
                for slug in caution.get("relates_to", []):
                    self.assertIn(slug, VALID_SLUGS, f"{q['id']}/{a['id']} relates_to unknown id: {slug}")

    def test_required_cross_cutting_links_are_present_somewhere(self):
        # the project plan's brief for the result view names these five by id; make sure the data actually
        # uses all five rather than only some of them.
        required = {"human-in-the-loop", "safety", "evals", "ops", "reviewing"}
        used = set()
        for q in WORKSHEET["cross_questions"]:
            for a in q["answers"]:
                caution = a.get("caution")
                if caution:
                    used.update(caution.get("relates_to", []))
        self.assertEqual(required - used, set())

    def test_monotonic_continuing_never_lowers_the_level(self):
        for q in WORKSHEET["core_questions"]:
            for a in q["answers"]:
                if a["action"] == "settle":
                    reachable_elsewhere = [
                        min_reachable_level(other["next"])
                        for other in q["answers"]
                        if other["action"] == "next"
                    ]
                    for other_level in reachable_elsewhere:
                        self.assertLessEqual(
                            a["level"],
                            other_level,
                            f"{q['id']}/{a['id']} settles at {a['level']}, which beats what continuing reaches ({other_level})",
                        )

    def test_every_level_0_to_7_is_reachable(self):
        reachable = set()

        def walk(qid, seen):
            if qid in seen:
                return
            q = CORE_BY_ID[qid]
            for a in q["answers"]:
                if a["action"] == "settle":
                    reachable.add(a["level"])
                else:
                    walk(a["next"], seen | {qid})

        walk(WORKSHEET["first_question"], set())
        self.assertEqual(reachable, set(range(8)))

    def test_cross_questions_all_have_at_least_one_no_caution_option(self):
        # Every cross-cutting question needs a "nothing to flag" answer, or a careful task always
        # gets flagged as risky.
        for q in WORKSHEET["cross_questions"]:
            self.assertTrue(
                any(a.get("caution") is None for a in q["answers"]),
                f"{q['id']} has no answer that leaves the level un-cautioned",
            )

    def test_worked_cases(self):
        self.assertEqual(len(WORKED_CASES), 12)
        for description, path, expected_level in WORKED_CASES:
            level, reasons, settled = evaluate_core(path)
            self.assertTrue(settled, f"{description!r}: did not settle with path {path}")
            self.assertEqual(level, expected_level, f"{description!r}: expected level {expected_level}, got {level}")
            self.assertEqual(len(reasons), len(path))

    def test_worked_cases_cover_every_level(self):
        levels = {expected for _, _, expected in WORKED_CASES}
        self.assertEqual(levels, set(range(8)))

    def test_incomplete_answers_do_not_settle(self):
        level, reasons, settled = evaluate_core([("rule", "no"), ("one-call", "no")])
        self.assertFalse(settled)

    def test_cross_evaluation_only_returns_cautions_for_answered_questions(self):
        cautions = evaluate_cross([("cost", "high")])
        self.assertEqual(len(cautions), 1)
        self.assertEqual(cautions[0][0], "cost")

    def test_cross_no_caution_answer_yields_nothing(self):
        cautions = evaluate_cross([("cost", "cheap"), ("checkable", "easy"), ("reversible", "yes"), ("data", "no")])
        self.assertEqual(cautions, [])


if __name__ == "__main__":
    unittest.main()
