"""Load and chunk the synthetic evaluation corpus.

The corpus lives in `evals/corpus/*.md`. Each file has numbered sections written as
`## N. Title`. A citation is written as `file#section`, for example `dw300-manual#3`. The text
before the first numbered section (the title line and the one-line description under it) is
folded into section 1, so a citation to section 1 also carries the document's revision line and
scope statement.

Used by the examples (as the thing they search, chunk and embed), by `scripts/eval_run.py`, and
by `tests/test_examples.py` to check that every question's citations and accepted answers are
grounded in the corpus text.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)
WORD_RE = re.compile(r"[a-z0-9]+")

DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


@dataclass(frozen=True)
class Section:
    """One numbered section of one corpus document."""

    doc: str
    number: int
    title: str
    text: str

    @property
    def cite(self) -> str:
        return f"{self.doc}#{self.number}"


def corpus_files(corpus_dir: Path = DEFAULT_CORPUS_DIR) -> list[Path]:
    return sorted(corpus_dir.glob("*.md"))


def parse_sections(doc: str, text: str) -> list[Section]:
    """Split one document's raw text into its numbered sections."""
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return []
    preamble = text[: matches[0].start()].strip()
    sections = []
    for i, match in enumerate(matches):
        number = int(match.group(1))
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if number == 1 and preamble:
            body = preamble + "\n\n" + body
        sections.append(Section(doc=doc, number=number, title=title, text=body))
    return sections


def load_sections(corpus_dir: Path = DEFAULT_CORPUS_DIR) -> dict[str, Section]:
    """Return every section in the corpus, keyed by its `file#section` citation."""
    out: dict[str, Section] = {}
    for path in corpus_files(corpus_dir):
        text = path.read_text(encoding="utf-8")
        for section in parse_sections(path.stem, text):
            out[section.cite] = section
    return out


def load_documents(corpus_dir: Path = DEFAULT_CORPUS_DIR) -> dict[str, str]:
    """Return the full raw text of every corpus file, keyed by its filename stem."""
    return {path.stem: path.read_text(encoding="utf-8") for path in corpus_files(corpus_dir)}


def section_text(sections: dict[str, Section], cites: list[str]) -> str:
    """Concatenate the text of the given citations, in order, for a grounding check."""
    return "\n\n".join(sections[cite].text for cite in cites)


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace, including the mid-sentence line wraps Markdown prose uses,
    into single spaces, so a phrase that wraps across a line break is still found intact."""
    return " ".join(text.split())


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def bm25_search(
    sections: dict[str, Section],
    query: str,
    k: int = 3,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[tuple[Section, float]]:
    """Rank sections against a query with BM25. No model, no embeddings: this is what level 0
    (`examples/order_zero`) runs, and what the tool-using examples call for a `search` tool."""
    docs = list(sections.values())
    tokenized = [tokenize(s.title + " " + s.text) for s in docs]
    lengths = [len(t) for t in tokenized]
    avg_len = sum(lengths) / len(lengths) if lengths else 0.0
    doc_freq: Counter[str] = Counter()
    for toks in tokenized:
        doc_freq.update(set(toks))
    n = len(docs)
    query_terms = tokenize(query)
    scored: list[tuple[Section, float]] = []
    for doc, toks, length in zip(docs, tokenized, lengths):
        term_freq = Counter(toks)
        score = 0.0
        for term in query_terms:
            freq = term_freq.get(term, 0)
            if freq == 0:
                continue
            idf = math.log((n - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5) + 1)
            denom = freq + k1 * (1 - b + b * (length / avg_len if avg_len else 1))
            score += idf * (freq * (k1 + 1)) / denom
        scored.append((doc, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:k]


def lookup_part(part_number: str, corpus_dir: Path = DEFAULT_CORPUS_DIR) -> str | None:
    """Find a part's line in `parts-list.md` by part number, e.g. `HLV-2205`. Returns the line
    text (part number, name, price, and fitment when the list states one) or None."""
    parts_path = corpus_dir / "parts-list.md"
    if not parts_path.exists():
        return None
    for line in parts_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip().lstrip("- ").strip()
        if stripped.startswith(part_number):
            return stripped.rstrip(".")
    return None
