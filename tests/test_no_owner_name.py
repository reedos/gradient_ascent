"""No personal identifier leaks out of `LICENSE` into the rest of the tracked tree.

A previous writer took the repository owner's name from git config and used it as an invented
person's name in example code. It reached the built public site and had to be hotfixed. The
owner's name belongs in the `Copyright` line of `LICENSE` and the explicitly requested footer
credit. Everywhere else tracked is public once the site builds and is checked for accidental use.

This does two independent things:

1. Derives the owner's name from `LICENSE` itself at test time (never hard-coded here, or the
   name would just move into a second file) and looks for it, and each of its individual name
   tokens, as a standalone word anywhere else in the tracked tree. Same for any email address this
   repository has on record in a tracked file.
2. Looks for the *shape* of a personal identifier regardless of whose it is: an email address, or
   a `C:\\Users\\<name>`, `/home/<name>` or `/Users/<name>` path -- any of which would out
   whoever's machine wrote the example, owner or not.

Usage: python -m unittest tests.test_no_owner_name -v
"""
from __future__ import annotations

import re
import subprocess
import unittest
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LICENSE_PATH = ROOT / "LICENSE"

# Detected by extension (some binary formats, e.g. a well-formed PNG, may not show a NUL in the
# first 8 KB) as well as by content, so either check catches them.
BINARY_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "ico", "woff", "woff2", "ttf", "otf",
    "pdf", "zip", "mp4", "svgz",
}

EMAIL_SHAPE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
WINDOWS_USER_PATH = re.compile(r"C:\\Users\\[^\\/:*?\"<>|\r\n]+", re.IGNORECASE)
# The slash after the alternation, rather than inside it, so this line does not spell the very
# thing it searches for: the scan reads every tracked file including this one, and the earlier
# spelling matched its own source and failed the suite on itself.
UNIX_HOME_PATH = re.compile(r"(?:/home|/Users)/[^/\s\"'<>]+")

# (path relative to ROOT, posix separators, exact matched text) pairs a reviewer has looked at and
# ruled not a personal identifier. Each one is commented with why. Nothing is allowlisted by
# pattern or by directory prefix: `.local/` was considered (the brief calls for exempting it if it
# has real hits) but it holds zero tracked files today -- `git ls-files` returns nothing under it
# -- so there is nothing to exempt.
ALLOWED_HITS: set[tuple[str, str]] = set()
# These exact addresses are authored synthetic fixtures on the reserved .test domain,
# not personal contact details. Keep the allowance file-specific; real addresses still fail.
ALLOWED_HITS |= {(path, 'alex' + '@example.test') for path in (
    'examples/practical_labs/cases.json',
    'examples/practical_labs/validation/initial/approval-gate.json',
    'examples/practical_labs/validation/schema-constrained/approval-gate.json',
)}
ALLOWED_HITS.add(('examples/practical_labs/test_labs.py', 'someone-else' + '@example.test'))


def _tracked_files() -> list[Path]:
    """Every file `git` is tracking, so untracked build output (`site/dist`) and `node_modules`
    are excluded the same way they are excluded from the published site: by never being committed."""
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def _is_binary(path: Path) -> bool:
    if path.suffix.lstrip(".").lower() in BINARY_EXTENSIONS:
        return True
    try:
        with path.open("rb") as handle:
            chunk = handle.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def _license_owner() -> str:
    """The name off the `Copyright (c) <year> <Name>` line in LICENSE, read fresh every run so
    this file never has to spell the name itself."""
    text = LICENSE_PATH.read_text(encoding="utf-8")
    match = re.search(r"(?m)^Copyright \(c\)\s+\d{4}\s+(.+?)\s*$", text)
    assert match, "LICENSE has no 'Copyright (c) <year> <Name>' line to derive needles from"
    return match.group(1).strip()


def _configured_email() -> str | None:
    """An email address configured for this repository, if one is on record in a tracked file --
    a package manifest's author/email field, a CITATION.cff email: line, or a .mailmap entry.
    Never git config, and never anything outside the repo. None of those files carry an email
    today (checked directly: no tracked file matches EMAIL_SHAPE at all), so this returns None and
    the email needles below are simply empty -- but the lookup stays generic so it picks one up
    the moment a future commit adds it, instead of needing this test edited too."""
    candidates = [
        ROOT / "package.json",
        ROOT / "site" / "package.json",
        ROOT / "CITATION.cff",
        ROOT / ".mailmap",
    ]
    for path in candidates:
        if not path.exists():
            continue
        match = EMAIL_SHAPE.search(path.read_text(encoding="utf-8", errors="ignore"))
        if match:
            return match.group(0)
    return None


def _word_needle(text: str) -> re.Pattern[str]:
    return re.compile(r"\b" + re.escape(text) + r"\b", re.IGNORECASE)


def _known_needles() -> dict[str, re.Pattern[str]]:
    """The full owner name, each of its tokens of length >= 3, and any configured email address
    (full address and local part), each as a standalone-word, case-insensitive needle. Keyed by
    the plain text so a hit can report which needle it was."""
    owner = _license_owner()
    needles = {owner: _word_needle(owner)}
    for token in owner.split():
        if len(token) >= 3:
            needles[token] = _word_needle(token)

    email = _configured_email()
    if email:
        needles[email] = _word_needle(email)
        local_part = email.split("@", 1)[0]
        if len(local_part) >= 3:
            needles[local_part] = _word_needle(local_part)
    return needles


@lru_cache(maxsize=1)
def _scan() -> tuple[list[str], list[str]]:
    """One pass over the tracked tree. Returns (known-identifier offenders, identifier-shape
    offenders), each already formatted as 'path:line: matched text' and already filtered against
    ALLOWED_HITS."""
    needles = _known_needles()
    known_offenders: list[str] = []
    shape_offenders: list[str] = []

    for path in _tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel == "LICENSE":
            continue
        if not path.is_file() or _is_binary(path):
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")

        for n, line in enumerate(text.split("\n"), start=1):
            # The owner explicitly requested this public attribution. Exempt only that exact
            # markup in the shared footer; other identifiers and lines remain checked.
            if rel == "site/src/components/Footer.astro":
                credit = f'<p class="project-attribution"><strong>An independent project by {_license_owner()}.</strong></p>'
                line = line.replace(credit, "")
            for label, needle in needles.items():
                m = needle.search(line)
                if m and (rel, m.group(0)) not in ALLOWED_HITS:
                    known_offenders.append(f"{rel}:{n}: {m.group(0)!r} (needle: {label!r})")

            for pattern in (EMAIL_SHAPE, WINDOWS_USER_PATH, UNIX_HOME_PATH):
                m = pattern.search(line)
                if m and (rel, m.group(0)) not in ALLOWED_HITS:
                    shape_offenders.append(f"{rel}:{n}: {m.group(0)!r}")

    return known_offenders, shape_offenders


class NoOwnerNameTest(unittest.TestCase):
    """`unittest.TestCase`, not bare pytest functions: the full check runs
    `python -m unittest discover -s tests`, which collects `TestCase` methods and nothing else.
    A bare `def test_...` here would be skipped in silence, which is the failure mode this whole
    file exists to prevent."""

    def test_owner_identifiers_appear_only_in_authorized_locations(self) -> None:
        known_offenders, _ = _scan()
        self.assertEqual(
            known_offenders,
            [],
            "the LICENSE owner's name (or configured email) appears outside authorized locations:\n"
            + "\n".join(known_offenders),
        )

    def test_no_email_or_home_path_shape_anywhere_in_the_tracked_tree(self) -> None:
        _, shape_offenders = _scan()
        self.assertEqual(
            shape_offenders,
            [],
            "an email address or a C:\\Users\\<name> / /home/<name> / /Users/<name> path shape "
            "was found in the tracked tree:\n" + "\n".join(shape_offenders),
        )

    def test_the_owner_line_is_actually_parsed_so_this_check_is_not_a_no_op(self) -> None:
        # A check with an empty needle set would pass on an empty repo. Pin that LICENSE really
        # does have a name to derive, and that it is not accidentally one or two characters long
        # (which would make every needle match nearly everything, or the token filter drop it).
        owner = _license_owner()
        self.assertGreaterEqual(len(owner), 3)
        self.assertTrue(any(len(token) >= 3 for token in owner.split()))

    def test_a_planted_name_is_actually_caught(self) -> None:
        # The check above passes on a clean tree, which is also what a broken scanner returns.
        # Plant the owner's name in a line of text and confirm the needles find it, so a future
        # edit that quietly stops matching (a regex typo, a changed LICENSE line) fails here.
        owner = _license_owner()
        needles = _known_needles()
        planted = f"    author = get_author()  # {owner}"
        self.assertTrue(
            any(needle.search(planted) for needle in needles.values()),
            "the derived needles no longer match the owner's own name; the scan is a no-op",
        )

    def test_a_planted_identifier_shape_is_actually_caught(self) -> None:
        # Same reasoning as the planted name above, for the three shape patterns. The home-path
        # regex in particular is spelled carefully so it does not match its own source, and a
        # careless respelling could easily stop it matching anything at all.
        # Each sample is assembled from pieces rather than written out, for the same reason the
        # home-path regex above is: a literal sample here would be a real hit in a tracked file
        # and this file would fail its own scan.
        who = "someone"
        back = "\\"
        for line, pattern in (
            (f"contact = {who}" + "@" + "example.com", EMAIL_SHAPE),
            (f"path = C:{back}Users{back}{who}{back}notes.txt", WINDOWS_USER_PATH),
            ("path = " + "/home" + "/" + who + "/notes.txt", UNIX_HOME_PATH),
            ("path = " + "/Users" + "/" + who + "/notes.txt", UNIX_HOME_PATH),
        ):
            with self.subTest(line=line):
                self.assertTrue(pattern.search(line))

    def test_license_itself_is_exempt_and_not_silently_skipped_for_the_wrong_reason(self) -> None:
        # LICENSE is skipped by an exact relative-path match ("LICENSE"), not because it happens
        # to be binary or missing. Confirm it is tracked, present, and does contain the owner's
        # name, so the exemption in _scan is doing the skipping and not an accident.
        tracked = {p.relative_to(ROOT).as_posix() for p in _tracked_files()}
        self.assertIn("LICENSE", tracked)
        owner = _license_owner()
        self.assertTrue(_word_needle(owner).search(LICENSE_PATH.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
