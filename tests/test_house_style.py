"""House style, enforced where a reader can see it: no dash asides in the site's own prose.

The style rule is that a spaced em dash, a spaced double hyphen or a spaced en dash may not be
used to set a phrase off mid-sentence or to tack a clause onto the end of one. A comma, a colon,
two sentences or a pair of parentheses always says the same thing, and one of them reads better.

`tests/test_changes.py` has enforced this for `content/changes.json` since the change log was
written, and nothing enforced it anywhere else, so 94 of them accumulated in the older prose. This
module is the general version: every prose string in `content/*.json`, every line of MDX body copy,
and every line of an Astro page's template.

Two exemptions, both deliberate and both narrow:

  A quotation is exact.  Where the site quotes a maker's own page, a paper or a standard, the
  dash belongs to whoever wrote the sentence and may not be edited. Text inside quotation marks
  is skipped: straight double quotes and curly quotes in JSON and MDX, and curly quotes (or their
  HTML entities) in Astro, where a straight double quote is a string delimiter rather than a
  quotation mark.

  Code is not prose.  Fenced blocks, inline code spans, an Astro component's script section, its
  `<style>` and `<script>` blocks, and every kind of comment are skipped, along with the JSON keys
  that hold an address, an identifier or a date rather than a sentence.

Not covered here, on purpose: `site/src/components/`. What is left in those files is developer
comments and CSS, which no reader sees, and a check that had to understand both would be a worse
check. Component copy that a reader does see lives in the pages and content files below.

Usage: python -m unittest tests.test_house_style -v
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
MDX_DIRS = [ROOT / "site" / "src" / "content"]
ASTRO_DIR = ROOT / "site" / "src" / "pages"

NL = chr(10)
DASH_ASIDE = re.compile(r"\s(?:—|–|--)\s")

# JSON keys that hold an address, an identifier, a date or a proper name rather than a sentence.
NOT_PROSE_KEYS = {
    "accessed", "as_of", "category", "checked", "compute", "date", "domain", "first_question",
    "formerly", "href", "id", "kind", "maker", "name", "next", "path", "publisher", "quote",
    "slug", "source", "status", "superseded_by", "url", "version",
}

# Quotation spans. A quotation is exact, so whatever is inside one is not this module's business.
# Matched over the whole document rather than line by line: a quotation long enough to be worth
# quoting is usually long enough to wrap, and its second line is still inside it.
QUOTED = [
    re.compile(r'"[^"]{0,1500}"', re.DOTALL),
    re.compile(r"“[^”]{0,1500}”", re.DOTALL),
    re.compile(r"&ldquo;.{0,1500}?&rdquo;", re.DOTALL),
]
# Curly quotes only for Astro: there, a straight double quote delimits a string, and stripping
# those would exempt almost every sentence on the page.
QUOTED_ASTRO = QUOTED[1:]
CODE_SPAN = re.compile(r"`[^`\n]*`")

FENCE = re.compile(r"^\s*```")
MDX_COMMENT = re.compile(r"\{/\*.*?\*/\}", re.DOTALL)
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT = re.compile(r"(?m)^\s*//.*$")
STYLE_OR_SCRIPT = re.compile(r"<(style|script)\b.*?</\1>", re.DOTALL)

# Lines a reviewer has looked at and ruled a quotation that the stripping above cannot see, for
# example a maker's sentence reproduced without quotation marks. Empty today, and adding to it is
# a decision somebody has to write down rather than a regular expression somebody has to loosen.
EXEMPT_LINES: set[str] = set()


def _blank(match: re.Match[str]) -> str:
    """Replace a span with the newlines it held, so a reported line number still points at the
    line it came from."""
    return NL * match.group(0).count(NL)


def _strip(text: str, quoted: list[re.Pattern[str]]) -> str:
    text = CODE_SPAN.sub(" ", text)
    for pattern in quoted:
        text = pattern.sub(_blank, text)
    return text


def _json_strings(node: object, path: str = ""):
    """Every string in a JSON document, with the dotted path that reached it."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _json_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _json_strings(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def _is_prose(path: str) -> bool:
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in NOT_PROSE_KEYS:
        return False
    # A source's own title is the name of somebody else's page, reproduced as they spell it.
    if key == "title" and (".sources[" in path or path.endswith(".source.title")):
        return False
    return True


def _mdx_prose_lines(text: str) -> list[tuple[int, str]]:
    """MDX body copy, line by line, with the frontmatter, the fenced code, the comments, the
    imports, the inline code spans and the quotations blanked out. Blanked rather than deleted,
    so a line number here is a line number in the file."""
    text = MDX_COMMENT.sub(_blank, text)
    kept: list[str] = []
    in_fence = False
    in_frontmatter = False
    for n, line in enumerate(text.split(NL), start=1):
        if n == 1 and line.strip() == "---":
            in_frontmatter = True
            kept.append("")
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            kept.append("")
            continue
        if FENCE.match(line):
            in_fence = not in_fence
            kept.append("")
            continue
        kept.append("" if in_fence or line.lstrip().startswith("import ") else line)
    return list(enumerate(_strip(NL.join(kept), QUOTED).split(NL), start=1))


def _astro_template_lines(text: str) -> list[tuple[int, str]]:
    """The template half of an Astro page: everything after the component script, with comments,
    styles, client scripts and quotations blanked out."""
    lines = text.split(NL)
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    body = NL.join(lines[start:])
    for pattern in (STYLE_OR_SCRIPT, MDX_COMMENT, BLOCK_COMMENT):
        body = pattern.sub(_blank, body)
    body = LINE_COMMENT.sub("", body)
    return [(start + i + 1, line) for i, line in enumerate(_strip(body, QUOTED_ASTRO).split(NL))]


class ContentJsonTests(unittest.TestCase):
    def test_no_dash_asides_in_any_prose_field(self) -> None:
        offenders: list[str] = []
        files = sorted(CONTENT.glob("*.json"))
        self.assertGreaterEqual(len(files), 8, "sanity: content/ holds the site's data files")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            for where, value in _json_strings(data):
                if not _is_prose(where):
                    continue
                if DASH_ASIDE.search(_strip(value, QUOTED)):
                    offenders.append(f"{path.name}{where}")
        self.assertEqual(offenders, [], f"dash asides in content JSON prose: {offenders[:20]}")


class MdxTests(unittest.TestCase):
    def test_no_dash_asides_in_mdx_body_copy(self) -> None:
        offenders: list[str] = []
        files = sorted(p for d in MDX_DIRS for p in d.rglob("*.mdx"))
        self.assertGreater(len(files), 50, "sanity: the site has a lot of MDX pages")
        for path in files:
            for n, line in _mdx_prose_lines(path.read_text(encoding="utf-8")):
                if line.strip() in EXEMPT_LINES:
                    continue
                if DASH_ASIDE.search(line):
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}:{n}: {line.strip()[:90]}")
        self.assertEqual(offenders, [], "dash asides in MDX copy:" + NL + NL.join(offenders[:20]))


class AstroPageTests(unittest.TestCase):
    def test_no_dash_asides_in_astro_page_copy(self) -> None:
        offenders: list[str] = []
        files = sorted(ASTRO_DIR.rglob("*.astro"))
        self.assertGreater(len(files), 10, "sanity: the site has a lot of Astro pages")
        for path in files:
            for n, line in _astro_template_lines(path.read_text(encoding="utf-8")):
                if line.strip() in EXEMPT_LINES:
                    continue
                if DASH_ASIDE.search(line):
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}:{n}: {line.strip()[:90]}")
        self.assertEqual(offenders, [], "dash asides in Astro page copy:" + NL + NL.join(offenders[:20]))


class TheCheckItselfTests(unittest.TestCase):
    """A style check that cannot fail is worth nothing, so the pieces are tested directly."""

    def test_it_catches_each_of_the_three_dashes(self) -> None:
        for dash in ("—", "–", "--"):
            self.assertRegex(f"a sentence {dash} and its aside", DASH_ASIDE)

    def test_it_leaves_a_hyphen_and_a_command_flag_alone(self) -> None:
        self.assertIsNone(DASH_ASIDE.search("a mid-sentence hyphenated-word"))
        self.assertIsNone(DASH_ASIDE.search("run it with --allow-stub set"))

    def test_a_dash_inside_a_quotation_is_not_an_offense(self) -> None:
        line = 'The paper says "a chain of thought -- a series of steps -- improves it".'
        self.assertIsNone(DASH_ASIDE.search(_strip(line, QUOTED)))

    def test_a_dash_outside_the_quotation_still_is(self) -> None:
        line = 'The paper says "a chain of thought improves it" — which is the whole claim.'
        self.assertIsNotNone(DASH_ASIDE.search(_strip(line, QUOTED)))

    def test_a_quotation_that_wraps_is_still_one_quotation(self) -> None:
        doc = NL.join(['Google says Extensions "find things you use', 'every day -- like Gmail -- even when".'])
        self.assertIsNone(DASH_ASIDE.search(_strip(doc, QUOTED)))

    def test_a_dash_inside_a_code_span_is_not_an_offense(self) -> None:
        self.assertIsNone(DASH_ASIDE.search(_strip("run `eval_run.py -- x` first", QUOTED)))

    def test_mdx_frontmatter_and_fences_are_not_read(self) -> None:
        doc = NL.join(["---", "slug: x — y", "---", "", "real copy", "", "```", "code — here", "```", "", "more copy"])
        lines = [line for _, line in _mdx_prose_lines(doc)]
        self.assertIn("real copy", lines)
        self.assertEqual([line for line in lines if DASH_ASIDE.search(line)], [])

    def test_mdx_line_numbers_survive_the_blanking(self) -> None:
        doc = NL.join(["---", "slug: x", "---", "", "first", "second — aside"])
        offenders = [n for n, line in _mdx_prose_lines(doc) if DASH_ASIDE.search(line)]
        self.assertEqual(offenders, [6])

    def test_astro_script_section_and_comments_are_not_read(self) -> None:
        doc = NL.join(["---", "const a = 1; // a comment — here", "---", "<p>copy</p>", "{/* note — here */}"])
        kept = " ".join(line for _, line in _astro_template_lines(doc))
        self.assertIn("copy", kept)
        self.assertNotIn("a comment", kept)
        self.assertNotIn("note", kept)
        self.assertIsNone(DASH_ASIDE.search(kept))


if __name__ == "__main__":
    unittest.main()
