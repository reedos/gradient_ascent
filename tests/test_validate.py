import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate  # noqa: E402


def page(slug, **extra):
    return {"slug": slug, "title": slug.title(), "summary": f"About {slug}.", "status": "stub", **extra}


def taxonomy():
    return {
        "statuses": ["planned", "stub", "draft", "published"],
        "domains": ["general", "engineering"],
        "relation_types": {"requires": "", "upgrades_to": ""},
        "tiers": [
            {"id": "a", "order": 0, "title": "A", "short": "short a", "who": "nobody",
             "description": "desc a", "pages": [page("one")]},
            {"id": "b", "order": 1, "title": "B", "short": "short b", "who": "you",
             "description": "desc b", "pages": [page("two"), page("three")]},
        ],
        "tracks": [{"id": "evals", "pages": [page("grading")]}],
        # Rule 22 wants a thread to cross levels, and rule 20 wants a general recipe at every
        # level, so the fixture carries the smallest set that satisfies both: three thread pages
        # drawn from two tiers, and one general recipe per tier.
        "threads": [{"id": "t", "pages": ["one", "two", "three"]}],
        "recipes": [
            {"slug": "r", "domain": "general", "uses": ["two", "evals"]},
            {"slug": "r0", "domain": "general", "uses": ["one"]},
            {"slug": "r1", "domain": "general", "uses": ["three"]},
        ],
        "teardowns": {"cap": 6, "expires_days": 180,
                      "first": [{"slug": "td", "title": "TD, decoded", "patterns": ["three"]}]},
        "relations": [
            {"from": "two", "type": "requires", "to": "one"},
            {"from": "three", "type": "requires", "to": "two"},
            {"from": "two", "type": "upgrades_to", "to": "three"},
        ],
    }


def stages():
    return [
        {"id": "s0", "title": "Stage 0", "levels": [0], "kinds": "kind 0", "line": "line 0"},
        {"id": "s1", "title": "Stage 1", "levels": [1], "kinds": "kind 1", "line": "line 1"},
    ]


def landscape():
    return {
        # The date the site prints as "names listed". It has to be at least as new as the newest
        # entry's `checked` date below, which is the rule RegistryAsOfTests exercises.
        "as_of": "2026-09-18",
        "developers": [{"id": "lab", "name": "Lab"}],
        "models": [{"id": "m1", "name": "M1", "developer": "lab", "category": "model", "demonstrates": ["one"]}],
        "products": [{"id": "p1", "name": "P1", "by": "Lab", "category": "app", "demonstrates": ["two"],
                      "verified": True, "source": "https://example.org", "checked": "2026-09-18"}],
        "tools": [{"id": "t1", "name": "T1", "by": "open source", "category": "library", "demonstrates": ["evals"]}],
    }


class ValidateTests(unittest.TestCase):
    def errors(self, tax=None, land=None):
        return validate.validate(tax or taxonomy(), landscape() if land is None else land)[0]

    def test_valid_fixture_passes_and_reports(self):
        errors, report = validate.validate(taxonomy(), landscape())
        self.assertEqual(errors, [])
        self.assertEqual(report["levels"], 2)
        self.assertEqual(report["level_pages"], 3)
        self.assertEqual(report["track_pages"], 1)
        self.assertEqual(report["unnamed"], ["three"])

    # Rule 17: the recipes index groups by domain, so a recipe with no valid domain is a page
    # that exists and appears under no heading.
    def test_recipe_domain_must_be_declared(self):
        tax = taxonomy()
        tax["recipes"][0]["domain"] = "hardware"
        self.assertIn("recipe r has no valid domain: 'hardware'", self.errors(tax))

    def test_recipe_with_no_domain_at_all(self):
        tax = taxonomy()
        del tax["recipes"][0]["domain"]
        self.assertIn("recipe r has no valid domain: None", self.errors(tax))

    def test_every_declared_domain_is_accepted(self):
        for domain in taxonomy()["domains"]:
            tax = taxonomy()
            tax["recipes"][0]["domain"] = domain
            self.assertEqual(self.errors(tax), [], domain)

    def test_taxonomy_must_declare_domains(self):
        tax = taxonomy()
        tax["domains"] = []
        self.assertIn("taxonomy declares no domains", self.errors(tax))

    def test_report_counts_recipes_by_domain(self):
        tax = taxonomy()
        tax["recipes"].append({"slug": "e", "domain": "engineering", "uses": ["two"]})
        _, report = validate.validate(tax, landscape())
        self.assertEqual(report["recipes_by_domain"], {"general": 3, "engineering": 1})

    def test_the_real_taxonomy_gives_every_recipe_a_domain(self):
        """The rule is only worth having if the shipped file obeys it."""
        import json

        real = json.loads((ROOT / "content" / "taxonomy.json").read_text(encoding="utf-8"))
        declared = set(real["domains"])
        self.assertTrue(declared)
        for recipe in real["recipes"]:
            self.assertIn(recipe.get("domain"), declared, recipe["slug"])
        engineering = [r for r in real["recipes"] if r["domain"] == "engineering"]
        self.assertGreaterEqual(len(engineering), 11)
        # Two level-0 recipes lead the group, as a pair, and neither is the default: one is
        # production test (limits-without-a-model), one is engineering test
        # (characterize-a-design), and both say that most of the job needs no model at all.
        # Whichever of the two a reader's work looks like, the other is beside it rather than
        # above it, and the index aside says so.
        self.assertEqual(
            [r["slug"] for r in engineering[:2]],
            ["limits-without-a-model", "characterize-a-design"],
        )
        for recipe in engineering[:2]:
            self.assertEqual(recipe["uses"], ["order-zero"], recipe["slug"])

    def test_the_engineering_recipes_are_ordered_by_the_level_they_need(self):
        """The list's order is a claim the index makes in its aside, so it is checked here.

        Ordering by level is what keeps either setting from reading as the default: production
        test and engineering test interleave through the list by what each recipe needs, not by
        which audience it belongs to.
        """
        import json

        real = json.loads((ROOT / "content" / "taxonomy.json").read_text(encoding="utf-8"))
        level_of = {
            page["slug"]: tier["order"]
            for tier in real["tiers"]
            for page in tier["pages"]
        }
        levels = [
            max(level_of.get(use, 0) for use in r["uses"])
            for r in real["recipes"]
            if r["domain"] == "engineering"
        ]
        self.assertEqual(levels, sorted(levels), levels)

    def test_every_engineering_recipe_has_a_page_file(self):
        import json

        real = json.loads((ROOT / "content" / "taxonomy.json").read_text(encoding="utf-8"))
        for recipe in real["recipes"]:
            if recipe["domain"] != "engineering":
                continue
            path = ROOT / "site" / "src" / "content" / "recipes" / f"{recipe['slug']}.mdx"
            self.assertTrue(path.exists(), recipe["slug"])
            self.assertIn(f"slug: {recipe['slug']}", path.read_text(encoding="utf-8"))

    def test_duplicate_slug(self):
        tax = taxonomy()
        tax["tiers"][1]["pages"].append({"slug": "one"})
        self.assertIn("duplicate slug: one", self.errors(tax))

    def test_level_orders_must_be_sequential(self):
        tax = taxonomy()
        tax["tiers"][1]["order"] = 2
        self.assertTrue(any("level orders" in e for e in self.errors(tax)))

    def test_unknown_relation_end(self):
        tax = taxonomy()
        tax["relations"].append({"from": "two", "type": "requires", "to": "missing"})
        self.assertIn("relation references unknown id: missing", self.errors(tax))

    def test_unknown_relation_type(self):
        tax = taxonomy()
        tax["relations"].append({"from": "two", "type": "beats", "to": "one"})
        self.assertTrue(any("unknown relation type: beats" in e for e in self.errors(tax)))

    def test_recipe_thread_and_teardown_references(self):
        tax = taxonomy()
        tax["recipes"][0]["uses"].append("nope-r")
        tax["threads"][0]["pages"].append("nope-t")
        tax["teardowns"]["first"][0]["patterns"].append("nope-d")
        errors = self.errors(tax)
        for missing in ("nope-r", "nope-t", "nope-d"):
            self.assertTrue(any(missing in e for e in errors), missing)

    def test_requires_cycle(self):
        tax = taxonomy()
        tax["relations"].append({"from": "one", "type": "requires", "to": "three"})
        self.assertTrue(any(e.startswith("requires cycle") for e in self.errors(tax)))

    def test_upgrades_to_may_point_forward_without_being_a_cycle(self):
        self.assertEqual(self.errors(), [])

    def test_registry_unknown_reference(self):
        land = landscape()
        land["tools"][0]["demonstrates"] = ["missing"]
        self.assertTrue(any("demonstrates unknown id: missing" in e for e in self.errors(land=land)))

    def test_registry_entry_must_demonstrate_something(self):
        land = landscape()
        land["tools"][0]["demonstrates"] = []
        self.assertTrue(any("demonstrates nothing" in e for e in self.errors(land=land)))

    def test_model_needs_known_developer(self):
        land = landscape()
        land["models"][0]["developer"] = "ghost"
        self.assertTrue(any("unknown developer: ghost" in e for e in self.errors(land=land)))

    def test_product_needs_a_maker(self):
        land = landscape()
        del land["products"][0]["by"]
        self.assertTrue(any("has no maker" in e for e in self.errors(land=land)))

    def test_duplicate_registry_id(self):
        land = landscape()
        land["tools"].append(copy.deepcopy(land["products"][0]))
        self.assertIn("duplicate registry id: p1", self.errors(land=land))

    def test_verified_needs_source_and_date(self):
        land = landscape()
        del land["products"][0]["checked"]
        self.assertTrue(any("verified without a source" in e for e in self.errors(land=land)))

    def test_tier_missing_field_is_an_error(self):
        tax = taxonomy()
        del tax["tiers"][0]["who"]
        self.assertTrue(any("tier a has no who" in e for e in self.errors(tax)))

    def test_page_missing_summary_is_an_error(self):
        tax = taxonomy()
        del tax["tiers"][1]["pages"][0]["summary"]
        self.assertTrue(any("page two has no summary" in e for e in self.errors(tax)))

    def test_page_status_must_be_declared(self):
        tax = taxonomy()
        tax["tiers"][1]["pages"][0]["status"] = "in-progress"
        self.assertTrue(any("page two has no valid status" in e for e in self.errors(tax)))

    def test_track_page_needs_title_summary_status(self):
        tax = taxonomy()
        del tax["tracks"][0]["pages"][0]["title"]
        self.assertTrue(any("page grading has no title" in e for e in self.errors(tax)))

    # Rules added 2026-09-18 after an independent re-check of the registry found a retirement
    # with no explanation, a supersession pointing at nothing, a rename with no page saying it
    # happened, and categories that had started to read like pitches.
    def test_retired_entry_needs_a_note(self):
        land = landscape()
        land["products"][0]["retired"] = "2026-12-11"
        self.assertTrue(any("retired or superseded and has no note" in e for e in self.errors(land=land)))

    def test_superseded_entry_needs_a_note(self):
        land = landscape()
        land["products"][0]["superseded_by"] = "t1"
        self.assertTrue(any("retired or superseded and has no note" in e for e in self.errors(land=land)))

    def test_retired_entry_with_a_note_passes(self):
        land = landscape()
        land["products"][0]["retired"] = "2026-12-11"
        land["products"][0]["note"] = "Shut down on 2026-12-11; T1 replaces it."
        land["products"][0]["superseded_by"] = "t1"
        self.assertEqual(self.errors(land=land), [])

    def test_superseded_by_must_resolve(self):
        land = landscape()
        land["products"][0]["superseded_by"] = "ghost"
        land["products"][0]["note"] = "Replaced."
        self.assertTrue(any("superseded by unknown id: ghost" in e for e in self.errors(land=land)))

    def test_superseded_by_may_not_be_itself(self):
        land = landscape()
        land["products"][0]["superseded_by"] = "p1"
        land["products"][0]["note"] = "Replaced."
        self.assertTrue(any("superseded by itself" in e for e in self.errors(land=land)))

    def test_former_name_needs_a_source(self):
        land = landscape()
        land["tools"][0]["formerly"] = "T-Zero"
        self.assertTrue(any("former name with no source" in e for e in self.errors(land=land)))

    def test_category_may_not_be_title_case(self):
        land = landscape()
        land["tools"][0]["category"] = "Coding agent"
        self.assertTrue(any("category is title case" in e for e in self.errors(land=land)))

    def test_category_keeps_acronyms_and_mixed_case_names(self):
        land = landscape()
        for ok in ("model API", "LoRA and other adapters", "vector search in Postgres"):
            land["tools"][0]["category"] = ok
            self.assertEqual(self.errors(land=land), [], ok)

    def test_category_may_not_be_long(self):
        land = landscape()
        land["tools"][0]["category"] = "a library for doing many different useful things quickly"
        self.assertTrue(any("keep it to 7 or fewer" in e for e in self.errors(land=land)))

    def test_category_may_not_sell(self):
        land = landscape()
        land["tools"][0]["category"] = "leading agent framework"
        self.assertTrue(any("uses marketing wording: leading" in e for e in self.errors(land=land)))

    def test_missing_registry_is_allowed(self):
        errors, report = validate.validate(taxonomy(), None)
        self.assertEqual(errors, [])
        self.assertEqual(report["unnamed"], [])

    def test_real_content_is_valid(self):
        errors, report = validate.validate(*validate.load(ROOT / "content"))
        self.assertEqual(errors, [])
        self.assertEqual(report["levels"], 8)

    # Rule 14, added 2026-09-18 for the home-page climb chart: `stages` groups the tiers into
    # the four ways of working with a model (plus order zero), and has to stay in lockstep with
    # `tiers` or the chart quietly stops matching the taxonomy it is drawn from.
    def test_valid_stages_pass(self):
        tax = taxonomy()
        tax["stages"] = stages()
        self.assertEqual(self.errors(tax), [])

    def test_stages_are_optional(self):
        tax = taxonomy()
        self.assertNotIn("stages", tax)
        self.assertEqual(self.errors(tax), [])

    def test_stage_missing_field_is_an_error(self):
        tax = taxonomy()
        tax["stages"] = stages()
        del tax["stages"][0]["title"]
        self.assertTrue(any("stage s0 has no title" in e for e in self.errors(tax)))

    def test_stage_with_no_levels_is_an_error(self):
        tax = taxonomy()
        tax["stages"] = stages()
        tax["stages"][0]["levels"] = []
        self.assertTrue(any("stage s0 has no levels" in e for e in self.errors(tax)))

    def test_stage_levels_must_cover_every_tier(self):
        tax = taxonomy()
        st = stages()
        st[1]["levels"] = []
        tax["stages"] = st
        errors = self.errors(tax)
        self.assertTrue(any("must cover every tier exactly once in ascending order" in e for e in errors))

    def test_stage_levels_must_be_in_ascending_order(self):
        tax = taxonomy()
        st = stages()
        st[0]["levels"], st[1]["levels"] = [1], [0]
        tax["stages"] = st
        self.assertTrue(any("must cover every tier exactly once in ascending order" in e for e in self.errors(tax)))

    def test_stage_levels_may_not_repeat_a_tier(self):
        tax = taxonomy()
        st = stages()
        st[0]["levels"] = [0, 0]
        st[1]["levels"] = [1]
        tax["stages"] = st
        self.assertTrue(any("must cover every tier exactly once in ascending order" in e for e in self.errors(tax)))

    def test_real_content_stages_cover_all_eight_tiers(self):
        taxonomy_data, _ = validate.load(ROOT / "content")
        stages_data = taxonomy_data["stages"]
        self.assertEqual(len(stages_data), 5)
        covered = [level for stage in stages_data for level in stage["levels"]]
        self.assertEqual(covered, list(range(8)))


def glossary_entry(term, page="one", **extra):
    return {"term": term, "page": page, "definition": "One two three four five six seven eight nine.", **extra}


class GlossaryTests(unittest.TestCase):
    """Rules for content/glossary.json, added by finish-indexes: unique names (case-insensitive,
    including `aka`), every `page` a real technique or topic slug, every `see` resolving to
    another entry, and definitions between 8 and 60 words."""

    def errors(self, terms, tax=None):
        return validate.validate_glossary({"terms": terms}, tax or taxonomy())

    def test_a_valid_glossary_passes(self):
        self.assertEqual(self.errors([glossary_entry("alpha"), glossary_entry("beta", page="two")]), [])

    def test_duplicate_term_case_insensitive(self):
        errors = self.errors([glossary_entry("Alpha"), glossary_entry("alpha")])
        self.assertTrue(any("duplicates" in e for e in errors), errors)

    def test_aka_duplicates_another_term(self):
        errors = self.errors([glossary_entry("alpha"), glossary_entry("beta", aka=["Alpha"])])
        self.assertTrue(any("duplicates" in e for e in errors), errors)

    def test_aka_duplicated_within_one_entry_is_still_an_error(self):
        errors = self.errors([glossary_entry("alpha", aka=["gamma", "Gamma"])])
        self.assertTrue(any("listed twice" in e for e in errors), errors)

    def test_page_must_be_a_real_slug(self):
        errors = self.errors([glossary_entry("alpha", page="ghost")])
        self.assertTrue(any("not a real technique" in e for e in errors), errors)

    def test_page_may_be_a_track_root_or_a_track_page(self):
        self.assertEqual(self.errors([glossary_entry("alpha", page="evals")]), [])
        self.assertEqual(self.errors([glossary_entry("alpha", page="grading")]), [])

    def test_page_may_be_a_thread_id(self):
        """A term whose whole point is that one word names two techniques at once belongs on the
        thread that compares them, not on either one of the pages it is confused between."""
        self.assertEqual(self.errors([glossary_entry("alpha", page="t")]), [])

    def test_a_thread_id_that_does_not_exist_is_still_an_error(self):
        errors = self.errors([glossary_entry("alpha", page="not-a-thread")])
        self.assertTrue(any("not a real technique" in e for e in errors), errors)

    def test_a_taxonomy_with_no_threads_still_validates(self):
        tax = taxonomy()
        del tax["threads"]
        self.assertEqual(self.errors([glossary_entry("alpha")], tax=tax), [])

    def test_definition_too_short_is_an_error(self):
        errors = self.errors([{"term": "alpha", "page": "one", "definition": "Too short."}])
        self.assertTrue(any("2 words" in e for e in errors), errors)

    def test_definition_too_long_is_an_error(self):
        long_def = " ".join(["word"] * 61)
        errors = self.errors([{"term": "alpha", "page": "one", "definition": long_def}])
        self.assertTrue(any("61 words" in e for e in errors), errors)

    def test_see_resolves_to_another_term(self):
        errors = self.errors([
            glossary_entry("alpha", see=["beta"]),
            glossary_entry("beta", page="two"),
        ])
        self.assertEqual(errors, [])

    def test_see_resolves_to_an_aka(self):
        errors = self.errors([
            glossary_entry("alpha", see=["gamma"]),
            glossary_entry("beta", page="two", aka=["gamma"]),
        ])
        self.assertEqual(errors, [])

    def test_see_can_reference_a_term_defined_later_in_the_file(self):
        errors = self.errors([
            glossary_entry("alpha", see=["beta"]),
            glossary_entry("beta", page="two"),
        ])
        self.assertEqual(errors, [])

    def test_unresolved_see_is_an_error(self):
        errors = self.errors([glossary_entry("alpha", see=["ghost-term"])])
        self.assertTrue(any("resolves to nothing" in e for e in errors), errors)

    def test_real_glossary_is_valid(self):
        import json as _json

        taxonomy_data, _ = validate.load(ROOT / "content")
        glossary_data = _json.loads((ROOT / "content" / "glossary.json").read_text(encoding="utf-8"))
        errors = validate.validate_glossary(glossary_data, taxonomy_data)
        self.assertEqual(errors, [])
        # A range, not a count: the glossary grows with the pages, and a wildly different number
        # means either a page's terms were never added or something is being generated into it.
        self.assertGreaterEqual(len(glossary_data["terms"]), 60)
        self.assertLessEqual(len(glossary_data["terms"]), 140)


class ShapesTests(unittest.TestCase):
    """Rule 18: the job shapes resolve against the taxonomy and leave no recipe out."""

    def _real(self):
        import json as _json

        content = Path(__file__).resolve().parent.parent / "content"
        tax = _json.loads((content / "taxonomy.json").read_text(encoding="utf-8"))
        shapes = _json.loads((content / "shapes.json").read_text(encoding="utf-8"))
        return shapes, tax

    def test_the_real_shapes_file_is_clean(self):
        shapes, tax = self._real()
        self.assertEqual(validate.validate_shapes(shapes, tax), [])

    def test_a_recipe_outside_every_shape_is_an_error(self):
        shapes, tax = self._real()
        slug = tax["recipes"][0]["slug"]
        for shape in shapes["shapes"]:
            shape["recipes"] = [r for r in shape["recipes"] if r != slug]
        errors = validate.validate_shapes(shapes, tax)
        self.assertTrue(any(f"recipe '{slug}' illustrates no shape" in e for e in errors), errors)

    def test_unknown_references_a_bad_level_a_duplicate_and_a_thin_elsewhere(self):
        shapes, tax = self._real()
        first = shapes["shapes"][0]
        first["techniques"] = first["techniques"] + ["no-such-technique"]
        first["recipes"] = first["recipes"] + ["no-such-recipe"]
        first["teardowns"] = ["no-such-teardown"]
        first["usual_level"] = 9
        first["elsewhere"] = first["elsewhere"][:2]
        shapes["shapes"].append(copy.deepcopy(shapes["shapes"][1]))
        errors = "\n".join(validate.validate_shapes(shapes, tax))
        for needle in (
            "unknown technique 'no-such-technique'",
            "unknown recipe 'no-such-recipe'",
            "unknown teardown 'no-such-teardown'",
            "usual_level 9",
            "fewer than three jobs",
            "duplicate shape id",
        ):
            self.assertIn(needle, errors)


class GeneralCoverageTests(unittest.TestCase):
    """Rules 19 and 20, added in wave 9 with the general half of the recipe layer.

    Both say the same thing along different axes: the site is for three audiences, and a shape or
    a level whose only worked instance is an engineering one tells everybody else that this kind
    of job, or this level, is not for them. Neither failure is visible in a build.
    """

    def _real(self):
        import json as _json

        content = Path(__file__).resolve().parent.parent / "content"
        tax = _json.loads((content / "taxonomy.json").read_text(encoding="utf-8"))
        shapes = _json.loads((content / "shapes.json").read_text(encoding="utf-8"))
        return shapes, tax

    def test_every_real_shape_has_a_general_recipe(self):
        shapes, tax = self._real()
        self.assertEqual(validate.validate_shapes(shapes, tax), [])

    def test_a_shape_whose_recipes_are_all_engineering_is_an_error(self):
        shapes, tax = self._real()
        general = {r["slug"] for r in tax["recipes"] if r.get("domain") == "general"}
        shape = next(s for s in shapes["shapes"] if set(s["recipes"]) & general)
        shape["recipes"] = [s for s in shape["recipes"] if s not in general] or ["limits-without-a-model"]
        errors = validate.validate_shapes(shapes, tax)
        self.assertTrue(any(f"shape '{shape['id']}' has no general recipe" in e for e in errors), errors)

    def test_a_shape_with_no_recipe_at_all_is_not_asked_for_a_general_one(self):
        # A shape may legitimately have no worked instance yet; rule 18 already reports the other
        # direction (a recipe outside every shape). Only a shape that HAS recipes is asked.
        shapes, tax = self._real()
        shape = shapes["shapes"][0]
        moved = shape["recipes"]
        shape["recipes"] = []
        shapes["shapes"][1]["recipes"] = shapes["shapes"][1]["recipes"] + moved
        errors = validate.validate_shapes(shapes, tax)
        self.assertFalse([e for e in errors if "has no general recipe" in e], errors)

    def test_every_real_level_has_a_general_recipe(self):
        _, tax = self._real()
        errors = validate.validate(tax, None)[0]
        self.assertFalse([e for e in errors if "has no general recipe" in e], errors)

    def test_a_level_whose_recipes_are_all_engineering_is_an_error(self):
        tax = taxonomy()
        for recipe in tax["recipes"]:
            if recipe["slug"] in ("r", "r1"):  # both of the fixture's level-1 general recipes
                recipe["domain"] = "engineering"
        errors = validate.validate(tax, landscape())[0]
        self.assertTrue(any("level 1 (b) has no general recipe" in e for e in errors), errors)

    def test_a_recipe_that_uses_only_track_pages_counts_for_no_level(self):
        """`recipeLevels` in site/src/lib/content.ts ignores track pages, so this must too: a
        recipe built entirely from cross-cutting topics prints no "Needs level N" pill and cannot
        be what makes a level covered."""
        tax = taxonomy()
        tax["recipes"] = [r for r in tax["recipes"] if r["slug"] != "r0"]
        tax["recipes"].append({"slug": "rt", "domain": "general", "uses": ["evals"]})
        errors = validate.validate(tax, landscape())[0]
        self.assertTrue(any("level 0 (a) has no general recipe" in e for e in errors), errors)


class PagesOnDiskTests(unittest.TestCase):
    """Rules 21 and 22: a recipe or a thread in the taxonomy with no MDX file builds a real route
    that renders the "not written yet" outline, which is right for a page nobody has started and
    wrong as a thing to ship unnoticed. The reverse, a file with no entry, has no route at all.
    """

    def build(self, recipes=None, threads=None, tax=None):
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        for folder, files in (("recipes", recipes or {}), ("threads", threads or {})):
            content = tmp / "site" / "src" / "content" / folder
            content.mkdir(parents=True)
            for name, body in files.items():
                (content / name).write_text(body, encoding="utf-8")
        return validate.check_pages_on_disk(tmp, tax or taxonomy())

    @staticmethod
    def _page(key, value):
        return f"---\n{key}: {value}\nreviewed: 2026-09-19\nsources: []\n---\n\nA paragraph.\n"

    def _complete(self):
        return {
            "recipes": {f"{slug}.mdx": self._page("slug", slug) for slug in ("r", "r0", "r1")},
            "threads": {"t.mdx": self._page("id", "t")},
        }

    def test_a_full_set_of_pages_passes(self):
        self.assertEqual(self.build(**self._complete()), [])

    def test_a_recipe_with_no_page_is_an_error(self):
        files = self._complete()
        del files["recipes"]["r0.mdx"]
        errors = self.build(**files)
        self.assertTrue(any("no page at site/src/content/recipes/r0.mdx" in e for e in errors), errors)

    def test_a_page_with_no_recipe_is_an_error(self):
        files = self._complete()
        files["recipes"]["ghost.mdx"] = self._page("slug", "ghost")
        errors = self.build(**files)
        self.assertTrue(any("recipes/ghost.mdx has no matching recipe" in e for e in errors), errors)

    def test_a_frontmatter_slug_that_does_not_match_the_file_name_is_an_error(self):
        files = self._complete()
        files["recipes"]["r.mdx"] = self._page("slug", "other")
        errors = self.build(**files)
        self.assertTrue(any("frontmatter slug is 'other', not 'r'" in e for e in errors), errors)

    def test_a_thread_with_no_page_and_a_page_with_no_thread_are_both_errors(self):
        files = self._complete()
        files["threads"] = {"ghost.mdx": self._page("id", "ghost")}
        errors = "\n".join(self.build(**files))
        self.assertIn("thread t is in taxonomy.json with no page", errors)
        self.assertIn("threads/ghost.mdx has no matching thread", errors)

    def test_a_thread_frontmatter_id_must_match_the_file_name(self):
        files = self._complete()
        files["threads"]["t.mdx"] = self._page("id", "other")
        errors = self.build(**files)
        self.assertTrue(any("frontmatter id is 'other', not 't'" in e for e in errors), errors)

    def test_a_thread_must_order_at_least_three_pages_across_two_levels(self):
        short = taxonomy()
        short["threads"][0]["pages"] = ["two", "three"]
        errors = validate.validate(short, landscape())[0]
        self.assertTrue(any("thread t lists 2 page(s)" in e for e in errors), errors)

        flat = taxonomy()
        flat["tiers"][1]["pages"].append(page("four"))
        flat["threads"][0]["pages"] = ["two", "three", "four"]
        errors = validate.validate(flat, landscape())[0]
        self.assertTrue(any("thread t stays inside one level" in e for e in errors), errors)

    def test_the_real_recipes_and_threads_all_have_pages(self):
        import json as _json

        root = Path(__file__).resolve().parent.parent
        tax = _json.loads((root / "content" / "taxonomy.json").read_text(encoding="utf-8"))
        self.assertEqual(validate.check_pages_on_disk(root, tax), [])


class MdxReferenceTests(unittest.TestCase):
    """Rules 11 and 12, added 2026-09-18.

    Both failures are silent. A `<Link>` to a slug that is not a page renders as a live link to
    an empty page, and the build says only "Entry techniques -> x was not found". A `CodeFile`
    range pinned into a file the page does not own slides whenever anything above it changes,
    and the page then walks the reader through code that is not on screen -- which shipped once
    in wave 2 and again in wave 3, both times in `evals.mdx`, both times building green.
    """

    def build(self, mdx: str, *, pages=("index.astro", "method.astro"), files=None):
        """A throwaway repo root: one MDX file, some fixed page routes, some source files."""
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        pages_dir = tmp / "site" / "src" / "pages"
        pages_dir.mkdir(parents=True)
        for name in pages:
            (pages_dir / name).parent.mkdir(parents=True, exist_ok=True)
            (pages_dir / name).write_text("---\n---\n", encoding="utf-8")
        content = tmp / "site" / "src" / "content" / "techniques"
        content.mkdir(parents=True)
        (content / "page.mdx").write_text(mdx, encoding="utf-8")
        for rel, body in (files or {}).items():
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return validate.check_mdx(tmp, taxonomy())

    def test_a_link_to_a_real_page_passes(self):
        self.assertEqual(self.build('<Link href="/techniques/two/">two</Link>'), [])

    def test_a_link_to_a_level_a_recipe_and_a_fixed_page_passes(self):
        mdx = '<Link href="/levels/1/">l</Link><Link href="/recipes/r/">r</Link><Link href="/method/">m</Link>'
        self.assertEqual(self.build(mdx), [])

    def test_a_link_to_a_teardown_and_a_thread_passes(self):
        """Both routes are built from the taxonomy by a dynamic page, so neither appears in the
        scan of `site/src/pages/*.astro`. Teardowns were missing from the route set until a
        teardown first linked to another one, and reported as a broken link every time."""
        mdx = '<Link href="/teardowns/td/">t</Link><Link href="/threads/t/">th</Link>'
        self.assertEqual(self.build(mdx), [])

    def test_a_link_to_a_teardown_that_is_not_listed_is_still_an_error(self):
        errors = self.build('<Link href="/teardowns/ghost/">g</Link>')
        self.assertTrue(any("resolves to no route: '/teardowns/ghost/'" in e for e in errors), errors)

    def test_a_link_to_a_track_root_and_a_track_page_passes(self):
        mdx = '<Link href="/techniques/evals/">e</Link><Link href="/techniques/grading/">g</Link>'
        self.assertEqual(self.build(mdx), [])

    def test_a_link_with_a_fragment_resolves_by_its_route(self):
        self.assertEqual(self.build('<Link href="/method/#principles">m</Link>'), [])
        errors = self.build('<Link href="/ghost/#x">g</Link>')
        self.assertTrue(any("resolves to no route" in e for e in errors))

    def test_a_timeline_fragment_must_name_a_milestone_or_a_shift(self):
        tl = '{"milestones": [{"id": "m1"}], "shifts": [{"id": "s1"}]}'
        ok = self.build('<Link href="/timeline/#m1">a</Link><Link href="/timeline/#s1">b</Link>',
                        pages=("index.astro", "timeline.astro"), files={"content/timeline.json": tl})
        self.assertEqual(ok, [])
        errors = self.build('<Link href="/timeline/#ghost">c</Link>',
                            pages=("index.astro", "timeline.astro"), files={"content/timeline.json": tl})
        self.assertTrue(any("names no anchor on the timeline page" in e for e in errors))

    def test_a_link_to_a_slug_that_is_not_a_page_is_an_error(self):
        errors = self.build('<Link href="/techniques/ghost/">ghost</Link>')
        self.assertTrue(any("resolves to no route: '/techniques/ghost/'" in e for e in errors), errors)

    def test_a_link_to_a_level_that_does_not_exist_is_an_error(self):
        errors = self.build('<Link href="/levels/9/">nine</Link>')
        self.assertTrue(any("/levels/9/" in e for e in errors), errors)

    def test_a_link_missing_its_trailing_slash_is_an_error(self):
        errors = self.build('<Link href="/techniques/two">two</Link>')
        self.assertTrue(any("resolves to no route" in e for e in errors), errors)

    def test_an_offsite_href_on_link_is_an_error(self):
        errors = self.build('<Link href="https://example.org/">x</Link>')
        self.assertTrue(any("not a site-relative path" in e for e in errors), errors)

    def test_a_raw_markdown_link_is_an_error(self):
        errors = self.build("See [two](/techniques/two/) for more.")
        self.assertTrue(any("raw Markdown link" in e for e in errors), errors)

    def test_codefile_file_must_exist(self):
        errors = self.build('<CodeFile file="examples/ghost/run.py" func="run" />')
        self.assertTrue(any("file does not exist" in e for e in errors), errors)

    def test_codefile_func_must_be_defined(self):
        files = {"examples/x/run.py": "def run(a):\n    return a\n"}
        self.assertEqual(self.build('<CodeFile file="examples/x/run.py" func="run" />', files=files), [])
        errors = self.build('<CodeFile file="examples/x/run.py" func="walk" />', files=files)
        self.assertTrue(any("func 'walk' is not defined" in e for e in errors), errors)

    def test_codefile_cls_must_be_defined(self):
        files = {"examples/x/run.py": "class Thing:\n    pass\n"}
        self.assertEqual(self.build('<CodeFile file="examples/x/run.py" cls="Thing" />', files=files), [])
        errors = self.build('<CodeFile file="examples/x/run.py" cls="Other" />', files=files)
        self.assertTrue(any("cls 'Other' is not defined" in e for e in errors), errors)

    def test_a_pinned_range_past_the_end_of_the_file_is_an_error(self):
        files = {"examples/x/run.py": "one\ntwo\n"}
        errors = self.build('<CodeFile file="examples/x/run.py" start={1} end={90} />', files=files)
        self.assertTrue(any("is outside" in e for e in errors), errors)

    def test_a_pinned_range_that_slid_away_from_its_expect_is_an_error(self):
        files = {"examples/x/run.py": "alpha\nbeta\ngamma\n"}
        ok = '<CodeFile file="examples/x/run.py" start={2} end={3} expect="beta" />'
        self.assertEqual(self.build(ok, files=files), [])
        slid = '<CodeFile file="examples/x/run.py" start={2} end={3} expect="alpha" />'
        errors = self.build(slid, files=files)
        self.assertTrue(any("no longer contains 'alpha'" in e for e in errors), errors)

    def test_the_real_site_content_resolves(self):
        taxonomy_data, _ = validate.load(ROOT / "content")
        self.assertEqual(validate.check_mdx(ROOT, taxonomy_data), [])


class RunDiagramGeometryTests(unittest.TestCase):
    """Rule 13, added 2026-09-18 after review3-recipes-a found three run files shipping with the
    final node sliced in half. `h` is the SVG's height and a node is drawn from y-19 to y+19, so
    setting `h` to the last node's `y` cuts it in two. It builds green and shows only in a
    screenshot, which makes it the cheapest defect on the site to introduce and the most annoying
    to find."""

    def build(self, *files):
        import json as _json
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, tmp, True)
        runs = tmp / "site" / "src" / "data" / "runs"
        runs.mkdir(parents=True)
        for name, data in files:
            (runs / name).write_text(_json.dumps(data), encoding="utf-8")
        return validate.check_runs(tmp)

    def run_file(self, nodes, h):
        return {"illustrative": True, "h": h, "title": "T", "sub": "s", "nodes": nodes,
                "edges": [], "steps": []}

    def test_a_diagram_whose_h_clears_its_lowest_node_passes(self):
        nodes = [{"id": "a", "x": 170, "y": 34, "l": "A", "k": "io"},
                 {"id": "b", "x": 170, "y": 200, "l": "B", "k": "code"}]
        self.assertEqual(self.build(("ok.json", self.run_file(nodes, 219))), [])

    def test_h_set_to_the_last_node_y_is_the_clipping_error(self):
        nodes = [{"id": "a", "x": 170, "y": 34, "l": "A", "k": "io"},
                 {"id": "last", "x": 170, "y": 200, "l": "B", "k": "code"}]
        errors = self.build(("clipped.json", self.run_file(nodes, 200)))
        self.assertTrue(any("clips node 'last'" in e for e in errors), errors)
        self.assertTrue(any("at least 219" in e for e in errors), errors)

    def test_one_unit_short_is_still_an_error(self):
        nodes = [{"id": "a", "x": 170, "y": 100, "l": "A", "k": "io"}]
        self.assertTrue(self.build(("x.json", self.run_file(nodes, 118))))
        self.assertEqual(self.build(("x.json", self.run_file(nodes, 119))), [])

    def test_the_conventional_branch_columns_pass(self):
        # 30 and 310 are the widest x values any approved run file uses.
        nodes = [{"id": "l", "x": 30, "y": 40, "l": "L", "k": "code"},
                 {"id": "r", "x": 310, "y": 40, "l": "R", "k": "code"}]
        self.assertEqual(self.build(("wide.json", self.run_file(nodes, 100))), [])

    def test_a_node_far_outside_the_canvas_is_an_error(self):
        nodes = [{"id": "a", "x": 170, "y": 40, "l": "A", "k": "io"},
                 {"id": "stray", "x": 520, "y": 40, "l": "S", "k": "code"}]
        errors = self.build(("stray.json", self.run_file(nodes, 100)))
        self.assertTrue(any("drawn units" in e for e in errors), errors)

    def test_a_run_file_with_no_nodes_or_no_h_is_an_error(self):
        self.assertTrue(self.build(("a.json", self.run_file([], 100))))
        bad = self.run_file([{"id": "a", "x": 170, "y": 40, "l": "A", "k": "io"}], 100)
        del bad["h"]
        self.assertTrue(self.build(("b.json", bad)))

    def test_every_real_run_file_fits_its_own_box(self):
        self.assertEqual(validate.check_runs(ROOT), [])


class RunMatchesExampleTests(unittest.TestCase):
    """Rule 14, added 2026-09-18 at the repo audit's request. Nothing checked a run diagram
    against the example it illustrates, and the trace rule is the site's central claim.

    What is NOT checked here, deliberately: equality of counts. The first draft of this rule
    counted `decided_by="model"` sites in the example's source and demanded the run file play
    that many steps; it failed on eight of the repository's own pages, every one a false alarm.
    A loop fires one site many times (agentic_rag plays four steps from two sites) and a branch
    fires one of two (function_calling plays one from two), so a static site count is neither an
    upper nor a lower bound on a recorded trace. Comparing real counts needs a recorded trace per
    run file, which is what `published` status is for."""

    MODEL_STEP = {"id": "e1", "f": "a", "t": "b", "by": "model"}
    CODE_STEP = {"id": "e1", "f": "a", "t": "b", "by": "code"}

    def build(self, run, example_source=None, slug="two", tax=None):
        import json as _json
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        runs = tmp / "site" / "src" / "data" / "runs"
        runs.mkdir(parents=True)
        (runs / f"{slug}.json").write_text(_json.dumps(run), encoding="utf-8")
        if example_source is not None:
            ex = tmp / "examples" / slug.replace("-", "_")
            ex.mkdir(parents=True)
            (ex / "run.py").write_text(example_source, encoding="utf-8")
        return validate.check_run_model_steps(tmp, tax or taxonomy())

    def run_file(self, edge, **extra):
        return {
            "illustrative": True,
            "h": 200,
            "title": "T",
            "sub": "s",
            "nodes": [{"id": "a", "x": 170, "y": 40, "l": "A", "k": "io"},
                      {"id": "b", "x": 170, "y": 120, "l": "B", "k": "code"}],
            "edges": [edge],
            "steps": [{"e": "e1", "h": "h", "d": "d", "m": "m"}],
            **extra,
        }

    def test_a_code_only_diagram_with_a_code_only_example_passes(self):
        src = 'tracer.record(kind="code", decided_by="code", title="t")\n'
        self.assertEqual(self.build(self.run_file(self.CODE_STEP), src), [])

    def test_a_level_1_page_may_not_play_a_model_decided_step(self):
        # "two" is at order 1 in the fixture taxonomy: the person or the code decides every step.
        errors = self.build(self.run_file(self.MODEL_STEP), None, slug="two")
        self.assertTrue(any("level 1" in e and "model-decided step" in e for e in errors), errors)

    def test_a_level_1_example_may_not_record_a_model_decision(self):
        src = 'tracer.record(kind="model", decided_by="model", title="t")\n'
        errors = self.build(self.run_file(self.CODE_STEP), src, slug="two")
        self.assertTrue(any('decided_by="model" site' in e for e in errors), errors)

    def test_a_diagram_that_claims_the_model_decided_but_the_code_never_does_is_an_error(self):
        # A level-4 page, so the level rule is not what catches it: presence must match.
        tax = taxonomy()
        tax["tiers"].append({"id": "c", "order": 4, "title": "C", "short": "s", "who": "model",
                             "description": "d", "pages": [page("four")]})
        src = 'tracer.record(kind="code", decided_by="code", title="t")\n'
        errors = self.build(self.run_file(self.MODEL_STEP), src, slug="four", tax=tax)
        self.assertTrue(any("never records one" in e for e in errors), errors)

    def test_an_example_that_records_a_model_decision_the_diagram_hides_is_an_error(self):
        tax = taxonomy()
        tax["tiers"].append({"id": "c", "order": 4, "title": "C", "short": "s", "who": "model",
                             "description": "d", "pages": [page("four")]})
        src = 'tracer.record(kind="model", decided_by="model", title="t")\n'
        errors = self.build(self.run_file(self.CODE_STEP), src, slug="four", tax=tax)
        self.assertTrue(any("plays no model-decided step" in e for e in errors), errors)

    def test_both_quote_styles_count_as_a_model_site(self):
        tax = taxonomy()
        tax["tiers"].append({"id": "c", "order": 4, "title": "C", "short": "s", "who": "model",
                             "description": "d", "pages": [page("four")]})
        for src in ('decided_by="model"\n', "decided_by='model'\n", 'decided_by = "model"\n'):
            self.assertEqual(self.build(self.run_file(self.MODEL_STEP), src, slug="four", tax=tax), [], src)

    def test_an_empty_trace_note_is_an_error(self):
        src = 'decided_by="code"\n'
        errors = self.build(self.run_file(self.CODE_STEP, trace_note="  "), src)
        self.assertTrue(any("non-empty string" in e for e in errors), errors)

    def test_a_run_file_with_no_example_of_its_own_is_skipped(self):
        tax = taxonomy()
        tax["tiers"].append({"id": "c", "order": 4, "title": "C", "short": "s", "who": "model",
                             "description": "d", "pages": [page("four")]})
        self.assertEqual(self.build(self.run_file(self.MODEL_STEP), None, slug="four", tax=tax), [])

    def test_a_recipe_run_file_is_skipped(self):
        # A recipe diagram is assembled from several examples; there is no one run.py to match.
        self.assertEqual(self.build(self.run_file(self.MODEL_STEP), None, slug="recipe-x"), [])

    def test_every_real_run_file_agrees_with_its_example(self):
        import json as _json

        tax = _json.loads((ROOT / "content" / "taxonomy.json").read_text(encoding="utf-8"))
        self.assertEqual(validate.check_run_model_steps(ROOT, tax), [])

    def test_the_two_run_files_that_draw_one_call_as_two_edges_say_so(self):
        import json as _json

        for name in ("orchestrator-workers", "organizations-swarms"):
            data = _json.loads((ROOT / "site" / "src" / "data" / "runs" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertIn("trace_note", data, name)
            self.assertIn("one model output selected both transitions", data["trace_note"], name)


def milestone(mid, level=0, date="2020-01-01", precision="day", technique=None, registry_id=None,
              verified=False, source=None, **extra):
    m = {
        "id": mid, "date": date, "precision": precision, "level": level, "kind": "research",
        "title": mid, "maker": "Someone", "what": "It did a thing.", "checked": "2026-09-18",
        "verified": verified,
    }
    if technique is not None:
        m["technique"] = technique
    if registry_id is not None:
        m["registry_id"] = registry_id
    if source is not None:
        m["source"] = source
    m.update(extra)
    return m


def timeline_fixture():
    # Levels 0 and 1 are the only tiers the shared `taxonomy()` fixture defines; "two" is its
    # order-1 page.
    return {
        "version": 1,
        "as_of": "2026-09-18",
        "criteria": {"described": "d", "buildable": "b", "available": "a"},
        "levels": [
            {"level": 0, "described": "m0", "buildable": "m0", "available": "m0"},
            {"level": 1, "described": "m1", "buildable": "m1", "available": "m1"},
        ],
        "milestones": [
            milestone("m0", level=0, source={"title": "T", "url": "https://example.org", "publisher": "P"}),
            milestone("m1", level=1, technique="two",
                      source={"title": "T", "url": "https://example.org", "publisher": "P"}),
        ],
        "measures": [],
    }


class TimelineTests(unittest.TestCase):
    """Rules for content/timeline.json, added by timeline-research: unique milestone ids, a real
    level, a date that matches its precision and is not after `as_of`, `technique`/`registry_id`
    references that resolve, `verified: true` backed by a source and a checked date, `levels`
    entries that point at a real milestone of that level (or are null with a note), and every
    `measures` entry carrying a quote, a scope and a source.

    Extended by timeline-review: each level marks three dates, not two. `buildable` (the first
    open framework or API a developer could build the level with) sits between `described` and
    `available` (the first product an ordinary customer could use without building it), and
    `criteria` must define all three, because calling a developer framework a consumer product
    was the defect this split was made to fix."""

    def errors(self, tl=None, tax=None, land=None):
        return validate.validate_timeline(
            tl or timeline_fixture(), tax or taxonomy(), landscape() if land is None else land
        )

    def test_valid_fixture_passes(self):
        self.assertEqual(self.errors(), [])

    def test_duplicate_milestone_id(self):
        tl = timeline_fixture()
        tl["milestones"].append(milestone("m0", level=1))
        self.assertTrue(any("duplicate milestone id: m0" in e for e in self.errors(tl)))

    def test_milestone_level_must_be_a_real_tier(self):
        tl = timeline_fixture()
        tl["milestones"][0]["level"] = 9
        self.assertTrue(any("no valid level: 9" in e for e in self.errors(tl)))

    def test_date_must_match_day_precision(self):
        tl = timeline_fixture()
        tl["milestones"][0]["date"] = "2020-01"
        self.assertTrue(any("does not match precision 'day'" in e for e in self.errors(tl)))

    def test_month_precision_accepts_year_month(self):
        tl = timeline_fixture()
        tl["milestones"][0]["date"] = "2020-01"
        tl["milestones"][0]["precision"] = "month"
        self.assertEqual(self.errors(tl), [])

    def test_year_precision_accepts_bare_year(self):
        tl = timeline_fixture()
        tl["milestones"][0]["date"] = "2020"
        tl["milestones"][0]["precision"] = "year"
        self.assertEqual(self.errors(tl), [])

    def test_invalid_precision_is_an_error(self):
        tl = timeline_fixture()
        tl["milestones"][0]["precision"] = "week"
        self.assertTrue(any("no valid precision" in e for e in self.errors(tl)))

    def test_date_after_as_of_is_an_error(self):
        tl = timeline_fixture()
        tl["milestones"][0]["date"] = "2026-09-19"
        self.assertTrue(any("is after as_of" in e for e in self.errors(tl)))

    def test_date_equal_to_as_of_passes(self):
        tl = timeline_fixture()
        tl["milestones"][0]["date"] = "2026-09-18"
        self.assertEqual(self.errors(tl), [])

    def test_month_precision_date_after_as_of_month_is_an_error(self):
        tl = timeline_fixture()
        tl["milestones"][0]["date"] = "2026-10"
        tl["milestones"][0]["precision"] = "month"
        self.assertTrue(any("is after as_of" in e for e in self.errors(tl)))

    def test_technique_must_resolve(self):
        tl = timeline_fixture()
        tl["milestones"][0]["technique"] = "ghost"
        self.assertTrue(any("technique resolves to nothing: 'ghost'" in e for e in self.errors(tl)))

    def test_registry_id_must_resolve(self):
        tl = timeline_fixture()
        tl["milestones"][0]["registry_id"] = "ghost"
        self.assertTrue(any("registry_id resolves to nothing: 'ghost'" in e for e in self.errors(tl)))

    def test_verified_requires_source_and_checked(self):
        tl = timeline_fixture()
        tl["milestones"][0]["verified"] = True
        del tl["milestones"][0]["source"]
        self.assertTrue(any("verified without a source" in e for e in self.errors(tl)))

    def test_verified_with_source_and_checked_passes(self):
        tl = timeline_fixture()
        tl["milestones"][0]["verified"] = True
        self.assertEqual(self.errors(tl), [])

    def test_level_described_must_point_at_a_milestone_of_that_level(self):
        tl = timeline_fixture()
        tl["levels"][0]["described"] = "m1"  # m1 is level 1, not 0
        self.assertTrue(any("points at a milestone that is not at this level" in e for e in self.errors(tl)))

    def test_level_with_null_described_needs_a_note(self):
        tl = timeline_fixture()
        tl["levels"][0]["described"] = None
        self.assertTrue(any("has no described milestone and no note" in e for e in self.errors(tl)))

    def test_level_with_null_described_and_a_note_passes(self):
        tl = timeline_fixture()
        tl["levels"][0]["described"] = None
        tl["levels"][0]["note"] = "Predates verifiable sources."
        self.assertEqual(self.errors(tl), [])

    def test_level_buildable_must_point_at_a_milestone_of_that_level(self):
        tl = timeline_fixture()
        tl["levels"][0]["buildable"] = "m1"  # m1 is level 1, not 0
        self.assertTrue(
            any("buildable points at a milestone that is not at this level" in e
                for e in self.errors(tl))
        )

    def test_level_with_null_buildable_needs_a_note(self):
        tl = timeline_fixture()
        tl["levels"][0]["buildable"] = None
        self.assertTrue(any("has no buildable milestone and no note" in e for e in self.errors(tl)))

    def test_level_with_null_buildable_and_a_note_passes(self):
        tl = timeline_fixture()
        tl["levels"][0]["buildable"] = None
        tl["levels"][0]["note"] = "No open framework of its own could be dated here."
        self.assertEqual(self.errors(tl), [])

    def test_level_missing_buildable_entirely_needs_a_note(self):
        # An entry written before the three-date split omits the key rather than nulling it;
        # that must fail the same way, or a level silently loses a marked date.
        tl = timeline_fixture()
        del tl["levels"][1]["buildable"]
        self.assertTrue(any("has no buildable milestone and no note" in e for e in self.errors(tl)))

    def test_criteria_must_define_all_three_marked_dates(self):
        tl = timeline_fixture()
        del tl["criteria"]["buildable"]
        self.assertTrue(any("criteria has no buildable definition" in e for e in self.errors(tl)))

    def test_criteria_must_define_described_and_available_too(self):
        tl = timeline_fixture()
        tl["criteria"] = {}
        errors = self.errors(tl)
        for key in ("described", "buildable", "available"):
            self.assertTrue(any(f"criteria has no {key} definition" in e for e in errors))

    # -- archive captures, availability and the candidate list ---------------------------------

    def test_archive_url_is_accepted_on_a_verified_milestone(self):
        # A maker's page that will not open from here is read through the Internet Archive's
        # capture OF THAT PAGE; the capture read is recorded alongside the original url.
        tl = timeline_fixture()
        tl["milestones"][0]["verified"] = True
        tl["milestones"][0]["source"]["archive_url"] = (
            "https://web.archive.org/web/20230401220923id_/https://example.org"
        )
        self.assertEqual(self.errors(tl), [])

    def test_verified_through_an_archive_capture_must_name_the_original_page(self):
        tl = timeline_fixture()
        tl["milestones"][0]["verified"] = True
        tl["milestones"][0]["source"] = {
            "title": "T",
            "archive_url": "https://web.archive.org/web/20230401220923id_/https://example.org",
            "publisher": "P",
        }
        errors = self.errors(tl)
        self.assertTrue(
            any("archive capture without naming the original page" in e for e in errors)
            or any("verified without a source url" in e for e in errors),
            errors,
        )

    def test_availability_vocabulary_is_checked(self):
        tl = timeline_fixture()
        tl["milestones"][0]["availability"] = "sort of out"
        self.assertTrue(any("unknown availability" in e for e in self.errors(tl)))

    def test_every_availability_value_is_accepted(self):
        for value in ("general", "preview", "waitlist", "paid plans"):
            tl = timeline_fixture()
            tl["milestones"][0]["availability"] = value
            self.assertEqual(self.errors(tl), [], value)

    def test_candidates_are_accepted(self):
        tl = timeline_fixture()
        tl["levels"][0]["candidates"] = [
            {"mark": "available", "id": "m0", "chosen": True, "why": "The one marked."},
            {"mark": "available", "id": "m1", "chosen": False, "why": "A level-1 product."},
        ]
        self.assertEqual(self.errors(tl), [])

    def test_candidate_must_resolve_to_a_milestone(self):
        tl = timeline_fixture()
        tl["levels"][0]["candidates"] = [{"mark": "available", "id": "ghost", "why": "x"}]
        self.assertTrue(any("candidate resolves to no milestone: 'ghost'" in e for e in self.errors(tl)))

    def test_candidate_needs_a_reason(self):
        tl = timeline_fixture()
        tl["levels"][0]["candidates"] = [{"mark": "available", "id": "m0", "chosen": True}]
        self.assertTrue(any("candidate 'm0' has no reason" in e for e in self.errors(tl)))

    def test_candidate_mark_must_be_a_marked_date_key(self):
        tl = timeline_fixture()
        tl["levels"][0]["candidates"] = [{"mark": "shipped", "id": "m0", "why": "x"}]
        self.assertTrue(any("has no valid mark: 'shipped'" in e for e in self.errors(tl)))

    def test_a_chosen_candidate_must_be_the_one_the_level_marks(self):
        tl = timeline_fixture()
        tl["levels"][1]["candidates"] = [
            {"mark": "available", "id": "m1", "chosen": False, "why": "Not chosen, apparently."},
            {"mark": "described", "id": "m1", "chosen": True, "why": "fine"},
        ]
        tl["levels"][1]["available"] = "m1"
        # `available` marks m1 but no candidate claims to be the chosen one: that is allowed.
        self.assertEqual(self.errors(tl), [])
        tl["levels"][1]["candidates"][0] = {
            "mark": "available", "id": "m0", "chosen": True, "why": "Claims to be the mark."
        }
        self.assertTrue(
            any("is marked chosen for available but the level marks 'm1'" in e
                for e in self.errors(tl))
        )

    def test_measure_needs_quote_scope_and_source(self):
        tl = timeline_fixture()
        tl["measures"].append({"id": "x"})
        errors = self.errors(tl)
        self.assertTrue(any("measure x has no quote" in e for e in errors))
        self.assertTrue(any("measure x has no scope" in e for e in errors))
        self.assertTrue(any("measure x has no source url" in e for e in errors))

    def test_measure_with_everything_passes(self):
        tl = timeline_fixture()
        tl["measures"].append({"id": "x", "quote": "q", "scope": "s",
                                "source": {"title": "T", "url": "https://example.org"}})
        self.assertEqual(self.errors(tl), [])

    def test_shift_needs_fields_and_a_real_milestone(self):
        tl = timeline_fixture()
        tl["shifts"] = [{"id": "s", "milestone": "ghost", "also": ["ghost2"], "technique": "nope"}]
        errors = self.errors(tl)
        self.assertTrue(any("shift s has no title" in e for e in errors))
        self.assertTrue(any("shift s has no summary" in e for e in errors))
        self.assertTrue(any("shift s has no body" in e for e in errors))
        self.assertTrue(any("shift s points at no milestone: 'ghost'" in e for e in errors))
        self.assertTrue(any("shift s points at no milestone: 'ghost2'" in e for e in errors))
        self.assertTrue(any("shift s technique resolves to nothing" in e for e in errors))

    def test_shift_application_needs_text_and_a_real_technique(self):
        tl = timeline_fixture()
        tl["shifts"] = [{"id": "s", "title": "T", "summary": "S", "body": ["B"],
                         "milestone": tl["milestones"][0]["id"],
                         "applications": [{"title": "A", "technique": "nope"}]}]
        errors = self.errors(tl)
        self.assertTrue(any("application with no title or text" in e for e in errors))
        self.assertTrue(any("application technique resolves to nothing" in e for e in errors))

    def test_shift_with_everything_passes(self):
        tl = timeline_fixture()
        tl["shifts"] = [{"id": "s", "title": "T", "summary": "S", "body": ["B"],
                         "milestone": tl["milestones"][0]["id"]}]
        self.assertEqual(self.errors(tl), [])

    def test_missing_landscape_still_checks_technique(self):
        tl = timeline_fixture()
        tl["milestones"][0]["technique"] = "ghost"
        errors = validate.validate_timeline(tl, taxonomy(), None)
        self.assertTrue(any("technique resolves to nothing" in e for e in errors))

    def test_missing_landscape_means_no_registry_id_can_resolve(self):
        tl = timeline_fixture()
        tl["milestones"][0]["registry_id"] = "whatever"
        errors = validate.validate_timeline(tl, taxonomy(), None)
        self.assertTrue(any("registry_id resolves to nothing" in e for e in errors))

    def test_real_timeline_is_valid(self):
        import json as _json

        timeline_path = ROOT / "content" / "timeline.json"
        taxonomy_data, landscape_data = validate.load(ROOT / "content")
        timeline_data = _json.loads(timeline_path.read_text(encoding="utf-8"))
        errors = validate.validate_timeline(timeline_data, taxonomy_data, landscape_data)
        self.assertEqual(errors, [])


TEARDOWN_MDX = """---
slug: {slug}
products: [p1]
reviewed: 2026-09-18
sources:
  - title: A maker's own page
    url: https://example.org/product
    accessed: 2026-09-18
---

A paragraph.
"""


class TeardownTests(unittest.TestCase):
    """Rule 15, added in wave 6 with the teardown layer itself.

    Three of these failures are silent. A teardown listed in the taxonomy with no MDX file still
    builds a route -- an empty outline page under a real title. A file with no taxonomy entry has
    no route at all and simply never appears, with nothing saying so. A teardown page with no
    sources is a page of claims about somebody else's product citing nothing, which is exactly
    what the project plan's rules forbid and what no other check would catch, since `sources` is optional
    on a recipe and a thread.
    """

    def build(self, files, tax=None, land=None):
        """A throwaway repo root holding site/src/content/teardowns/<name>.mdx for each file."""
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        content = tmp / "site" / "src" / "content" / "teardowns"
        content.mkdir(parents=True)
        for name, body in files.items():
            (content / name).write_text(body, encoding="utf-8")
        return validate.check_teardowns(tmp, tax or taxonomy(), landscape() if land is None else land)

    def test_a_teardown_with_its_page_passes(self):
        self.assertEqual(self.build({"td.mdx": TEARDOWN_MDX.format(slug="td")}), [])

    def test_a_teardown_in_the_taxonomy_with_no_page_is_an_error(self):
        errors = self.build({})
        self.assertTrue(any("no page at site/src/content/teardowns/td.mdx" in e for e in errors), errors)

    def test_a_page_with_no_teardown_in_the_taxonomy_is_an_error(self):
        files = {"td.mdx": TEARDOWN_MDX.format(slug="td"), "ghost.mdx": TEARDOWN_MDX.format(slug="ghost")}
        errors = self.build(files)
        self.assertTrue(any("ghost.mdx has no matching teardown" in e for e in errors), errors)

    def test_frontmatter_slug_must_match_the_file_name(self):
        errors = self.build({"td.mdx": TEARDOWN_MDX.format(slug="other")})
        self.assertTrue(any("frontmatter slug is 'other'" in e for e in errors), errors)

    def test_a_teardown_page_with_sources_passes_and_one_without_them_does_not(self):
        self.assertEqual(self.build({"td.mdx": TEARDOWN_MDX.format(slug="td")}), [])
        empty = TEARDOWN_MDX.format(slug="td").replace(
            "sources:\n  - title: A maker's own page\n    url: https://example.org/product\n    accessed: 2026-09-18\n",
            "sources: []\n",
        )
        errors = self.build({"td.mdx": empty})
        self.assertTrue(any("has no sources" in e for e in errors), errors)

    def test_a_teardown_page_needs_a_reviewed_date(self):
        errors = self.build({"td.mdx": TEARDOWN_MDX.format(slug="td").replace("reviewed: 2026-09-18\n", "")})
        self.assertTrue(any("has no reviewed date" in e for e in errors), errors)

    def test_products_must_be_registry_ids(self):
        errors = self.build({"td.mdx": TEARDOWN_MDX.format(slug="td").replace("[p1]", "[nope]")})
        self.assertTrue(any("product 'nope' is not an id" in e for e in errors), errors)
        errors = self.build({"td.mdx": TEARDOWN_MDX.format(slug="td").replace("products: [p1]", "products: []")})
        self.assertTrue(any("names no products" in e for e in errors), errors)

    def test_every_pattern_slug_must_resolve(self):
        # The passing half: the fixture's teardown decodes "three", a real page.
        self.assertEqual(validate.validate(taxonomy(), landscape())[0], [])
        tax = taxonomy()
        tax["teardowns"]["first"][0]["patterns"] = ["not-a-page"]
        errors = validate.validate(tax, landscape())[0]
        self.assertTrue(any("teardown td lists unknown id: not-a-page" in e for e in errors), errors)

    def test_a_teardown_that_decodes_nothing_is_an_error(self):
        tax = taxonomy()
        tax["teardowns"]["first"][0]["patterns"] = []
        errors = self.build({"td.mdx": TEARDOWN_MDX.format(slug="td")}, tax=tax)
        self.assertTrue(any("decodes no techniques" in e for e in errors), errors)

    def test_more_teardowns_than_the_cap_is_an_error(self):
        tax = taxonomy()
        tax["teardowns"]["cap"] = 1
        tax["teardowns"]["first"].append({"slug": "td2", "title": "T2", "patterns": ["two"]})
        files = {"td.mdx": TEARDOWN_MDX.format(slug="td"), "td2.mdx": TEARDOWN_MDX.format(slug="td2")}
        errors = self.build(files, tax=tax)
        self.assertTrue(any("but the cap is 1" in e for e in errors), errors)
        tax["teardowns"]["cap"] = 6
        self.assertEqual(self.build(files, tax=tax), [])

    def test_a_missing_teardowns_directory_is_only_an_error_when_teardowns_are_listed(self):
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        errors = validate.check_teardowns(tmp, taxonomy(), landscape())
        self.assertTrue(any("does not exist" in e for e in errors), errors)
        tax = taxonomy()
        tax["teardowns"] = {"cap": 6, "expires_days": 180, "first": []}
        self.assertEqual(validate.check_teardowns(tmp, tax, landscape()), [])

    def test_the_real_teardowns_are_valid(self):
        taxonomy_data, landscape_data = validate.load(ROOT / "content")
        self.assertEqual(validate.check_teardowns(ROOT, taxonomy_data, landscape_data), [])


class RegistryAsOfTests(unittest.TestCase):
    """The registry's `as_of` is what the site prints as "names listed 09/18/2026" on the home
    page, in the footer, on every level page and in the agent guide's "say when the registry was
    checked" line. It is written by hand and every one of those lines reads it, so a pass that
    re-checks a few entries and forgets it makes the whole site understate its own freshness with
    nothing looking wrong. That is what happened on 09/19/2026: seventeen entries were re-checked
    and `as_of` stayed on the 18th."""

    def errors(self, land):
        return validate.validate(taxonomy(), land)[0]

    def _as_of_errors(self, land):
        return [e for e in self.errors(land) if e.startswith("registry: as_of")]

    def test_an_as_of_newer_than_every_checked_date_passes(self):
        land = landscape()
        land["as_of"] = "2026-09-20"
        self.assertEqual(self._as_of_errors(land), [])

    def test_an_as_of_equal_to_the_newest_checked_date_passes(self):
        land = landscape()
        land["as_of"] = "2026-09-18"
        self.assertEqual(self._as_of_errors(land), [])

    def test_an_entry_checked_after_as_of_is_an_error(self):
        land = landscape()
        land["products"][0]["checked"] = "2026-09-19"
        errs = self._as_of_errors(land)
        self.assertTrue(errs, "an entry checked after as_of should be reported")
        self.assertIn("2026-09-19", errs[0])

    def test_the_newest_checked_date_is_the_one_reported_not_the_first_found(self):
        land = landscape()
        land["products"][0]["checked"] = "2026-09-19"
        land["tools"][0].update(
            {"verified": True, "source": "https://example.org", "checked": "2026-09-25"}
        )
        errs = self._as_of_errors(land)
        self.assertTrue(errs)
        self.assertIn("2026-09-25", errs[0])

    def test_a_missing_or_malformed_as_of_is_an_error(self):
        for value in ("", "2026-09", "09/18/2026", "yesterday"):
            land = landscape()
            land["as_of"] = value
            with self.subTest(as_of=value):
                self.assertTrue(
                    self._as_of_errors(land), f"as_of {value!r} should not be accepted"
                )

    def test_an_entry_with_no_checked_date_does_not_break_the_rule(self):
        """A seed carries no `checked` at all. It is not evidence about freshness either way."""
        land = landscape()
        land["tools"][0].pop("checked", None)
        self.assertEqual(self._as_of_errors(land), [])


class UnverifiedEntryTests(unittest.TestCase):
    """Rule 16, added in wave 6 at the registry agent's request. the project plan's Named things has said
    since the registry was designed that a seed is `verified: false` "until confirmed against the
    primary source, which must happen before the first page citing them is published", and nothing
    enforced it. Every page is a draft today, so the rule is quiet; it exists to bite on the day a
    page is promoted, which is the day nobody will be re-reading the registry."""

    def errors(self, tax=None, land=None):
        return validate.validate(tax or taxonomy(), landscape() if land is None else land)[0]

    def published(self, tax, slug):
        for tier in tax["tiers"]:
            for page in tier["pages"]:
                if page["slug"] == slug:
                    page["status"] = "published"
        return tax

    def test_an_unverified_entry_named_by_a_published_page_is_an_error(self):
        tax = self.published(taxonomy(), "one")
        land = landscape()
        land["models"][0]["verified"] = False  # m1 demonstrates "one"
        errors = self.errors(tax, land)
        self.assertTrue(any("m1 is not verified but is named by published page one" in e for e in errors), errors)

    def test_a_verified_entry_named_by_a_published_page_passes(self):
        tax = self.published(taxonomy(), "one")
        land = landscape()
        land["models"][0].update(verified=True, source="https://example.org", checked="2026-09-18")
        self.assertEqual(self.errors(tax, land), [])

    def test_an_unverified_entry_named_only_by_drafts_and_stubs_passes(self):
        land = landscape()
        land["models"][0]["verified"] = False
        self.assertEqual(self.errors(land=land), [])

    def test_a_teardown_may_not_decode_an_unverified_product(self):
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        content = tmp / "site" / "src" / "content" / "teardowns"
        content.mkdir(parents=True)
        (content / "td.mdx").write_text(TEARDOWN_MDX.format(slug="td"), encoding="utf-8")
        land = landscape()
        land["products"][0]["verified"] = True  # p1, the teardown's product: passes
        self.assertEqual(validate.check_teardowns(tmp, taxonomy(), land), [])
        land["products"][0]["verified"] = False
        errors = validate.check_teardowns(tmp, taxonomy(), land)
        self.assertTrue(any("is not verified against its maker's own page" in e for e in errors), errors)

    def test_the_real_content_passes_rule_16(self):
        taxonomy_data, landscape_data = validate.load(ROOT / "content")
        errors = validate.validate(taxonomy_data, landscape_data)[0]
        self.assertEqual([e for e in errors if "is not verified" in e], [])


class FrontmatterParserTests(unittest.TestCase):
    """The small YAML subset check_teardowns reads. Everything else about a frontmatter block is
    type-checked by site/src/content.config.ts at build time; this only has to be right about how
    many items a list has and what a scalar says."""

    def test_scalars_inline_lists_and_item_blocks(self):
        front = validate.parse_frontmatter(
            "---\nslug: x\nproducts: [a, b]\nsources:\n  - title: One\n    url: https://example.org\n  - title: Two\n    url: https://example.org/2\n---\nbody\n"
        )
        self.assertEqual(front["slug"], "x")
        self.assertEqual(front["products"], ["a", "b"])
        self.assertEqual(len(front["sources"]), 2)

    def test_an_empty_list_and_a_missing_block(self):
        self.assertEqual(validate.parse_frontmatter("---\nsources: []\n---\n")["sources"], [])
        self.assertEqual(validate.parse_frontmatter("no frontmatter here\n"), {})


if __name__ == "__main__":
    unittest.main()
