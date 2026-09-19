"""The bench corpus and the bench data: the engineering half of this site's synthetic world.

`evals/corpus/` holds the Halvorsen appliance documents the 60-question eval set is measured
against. This package holds the parallel set for electronics test and measurement: the documents
an engineer works from (`corpus/`) and the production test data those documents describe
(`data/`). Everything in both is invented; `docs/THE-BENCH.md` says what, and why each number is
the number it is.

The corpus is read by exactly the same loader, in exactly the same format. `load_sections` takes
a directory, so nothing about the existing callers changes:

    from evals.bench import BENCH_CORPUS_DIR
    from evals.corpus import load_sections

    sections = load_sections(BENCH_CORPUS_DIR)
    sections["srb5030-datasheet#4"].text

`load_bench_sections()` and `load_bench_documents()` below are that, spelled shorter.
"""
from __future__ import annotations

from pathlib import Path

from evals.corpus import Section, load_documents, load_sections

#: The bench documents: datasheet, test spec, four programming manuals, calibration procedure,
#: engineering change notice, two notebooks (bring-up and characterization), bill of materials,
#: design-review rules and a failure-analysis guide. Same `## N. Title` format as `evals/corpus/`.
BENCH_CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

#: The generated CSVs. Two generators write them, with separate seeds and separate random
#: streams: `make_data.py` writes the three production files and `make_characterization.py`
#: writes the engineering-test one. `tests/test_bench_data.py` and
#: `tests/test_bench_characterization.py` prove each reproduces byte for byte.
BENCH_DATA_DIR = Path(__file__).resolve().parent / "data"

PRODUCTION_CSV = BENCH_DATA_DIR / "production-run-2026-08.csv"
SOAK_CSV = BENCH_DATA_DIR / "soak-2026-08-27.csv"
RETEST_CSV = BENCH_DATA_DIR / "retest-2026-08-31.csv"
#: Five revision C prototypes swept over line, load and temperature, with five readings a point:
#: the engineering-test data, where a row is a reading rather than a verdict.
CHARACTERIZATION_CSV = BENCH_DATA_DIR / "characterization-2026-09.csv"


def load_bench_sections() -> dict[str, Section]:
    """Every section of the bench corpus, keyed by its `file#section` citation."""
    return load_sections(BENCH_CORPUS_DIR)


def load_bench_documents() -> dict[str, str]:
    """The full raw text of every bench document, keyed by its filename stem."""
    return load_documents(BENCH_CORPUS_DIR)


__all__ = [
    "BENCH_CORPUS_DIR",
    "BENCH_DATA_DIR",
    "CHARACTERIZATION_CSV",
    "PRODUCTION_CSV",
    "RETEST_CSV",
    "SOAK_CSV",
    "load_bench_documents",
    "load_bench_sections",
]
