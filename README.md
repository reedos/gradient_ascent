# Gradient Ascent

A guide to the main ways of using a language model, from one chat message to agents that run on
their own. The techniques are grouped into eight levels, ordered by how much the model decides
for itself. Each page shows how the technique works, what it costs, and when a simpler one is
enough.

**Every way to work with AI, from a question to a workforce.**

**Read it: https://reedos.github.io/gradient_ascent/**

**Status: live and in development.** Every page is a draft, and nothing in this repository has
ever called a model — see [What is and is not real yet](#what-is-and-is-not-real-yet). Found
something wrong? Every page has a feedback link, or open
[the feedback form](https://github.com/reedos/gradient_ascent/issues/new?template=feedback.yml);
see [CONTRIBUTING.md](CONTRIBUTING.md).

## Get it running

Two toolchains, no shared setup. The Python side is stdlib only: there is nothing to install, no
virtual environment, and no `requirements.txt`. Python 3.11 or newer; Node 22.12 or newer.

```
git clone <this repository> && cd gradient_ascent

python scripts/validate.py                    # the content files: 8 levels, 49 techniques, the registry
python -m unittest discover -s tests          # 770 tests, about 2 seconds

cd site && npm ci && npm run build            # the site, into site/dist/
npm run dev                                   # or serve it at localhost:4321
```

Run an example against the stub model — no network, no API key, no local model:

```
python -m examples.rag --model stub --question "What is the DW-300's Normal cycle water use?"
```

Every one of the 44 examples takes `--model stub` and prints what it did. Each has a README with
its own command; `examples/rag/README.md` is the one to read first.

## What is where

| | |
|---|---|
| `examples/<technique>/` | One runnable example per technique: `run.py` (the technique, ~50 readable lines), `__main__.py` (the command line), `README.md` (what it shows and how to run it). |
| `examples/common/` | The thin model interface (`model.py`), the trace recorder (`trace.py`), the shared tools and agent-loop plumbing. Start here to understand any example. |
| `evals/` | The synthetic document set (`corpus/`), the 60 questions (`questions.json`), and the projected token budget (`budget.json`). |
| `scripts/` | `validate.py` (content rules), `eval_run.py` (the eval runner), `record_trace.py` (records one run), `import_eci.py` (refreshes the capability snapshot; the only script that uses the network), `preview_server.py` (serves the built site under its base path). |
| `tests/` | The Python suite. Stdlib `unittest`, no network, no fixtures outside the repository. |
| `content/` | `taxonomy.json` (the levels, tracks, recipes, teardowns and typed edges between pages), `landscape.json` (the registry of named models, products and tools), `glossary.json`, `timeline.json`, `worksheet.json`, and `capability.json` (a dated snapshot of Epoch AI's Epoch Capabilities Index, CC BY 4.0, drawn on the timeline page). |
| `site/` | The Astro site: MDX pages in `src/content/`, Preact islands in `src/components/islands/`, run diagrams in `src/data/runs/`. |

## The docs

| | |
|---|---|
| [docs/WRITING-A-TECHNIQUE-PAGE.md](docs/WRITING-A-TECHNIQUE-PAGE.md) | How to write a page: anatomy, components, word budgets, sourcing, the draft-to-published line. |
| [docs/WRITING-A-TEARDOWN.md](docs/WRITING-A-TEARDOWN.md) | How to write a teardown: the sections, the frontmatter, the components allowed, the length, and the sourcing rule for a page about somebody else's product. |
| [docs/EVALS.md](docs/EVALS.md) | The eval runner: which examples the question set can score and which it cannot, how a question is graded, how to read a result file. |
| [docs/FIRST-LIVE-RUN.md](docs/FIRST-LIVE-RUN.md) | The exact sequence for the first run against a real model, and the gate a page passes to become published. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to send feedback or a correction, and what to run before a pull request. |

## The one rule worth knowing before you read any code

The whole site turns on one distinction, defined once in `examples/common/trace.py`:

> A step is `decided_by: "model"` when the model's **output**, not the program, selected which
> action happens next — choosing to call a tool, choosing which tool, choosing its arguments, or
> choosing to stop. Everything else is `decided_by: "code"`.

Calling a model is not a model decision. Levels 1, 2 and 3 call a model, sometimes several times,
but the code decided every one of those calls would happen: those steps are `kind: "model"` and
`decided_by: "code"`. So levels 0 to 3 record no model-decided steps at all, level 4 records
exactly one per run, and level 5 records one per tool call plus one for the stop.
`tests/test_examples.py` asserts it for every example.

## What is and is not real yet

Everything here was built without calling a model, local or remote. That means:

- **Real:** the examples, which run end to end against `StubModel`; the tests; the validator; the
  synthetic corpus and the 60 questions; the site and all 70 written pages.
- **Not real:** every number on the site. The cost strips are illustrative and say so above the
  numbers. Every run diagram carries `"illustrative": true`. No example has a recorded
  `trace.json`, and `evals/results/` is empty.
- **Projected, not measured:** the token figures in `evals/budget.json`, which come from
  `eval_run.py --dry` — a token counter, not a model.

A page becomes `published` when it has a recorded non-stub trace and a non-stub result file.
`docs/FIRST-LIVE-RUN.md` has the full gate.

## Contributing

Corrections are welcome: the license is MIT and the taxonomy, registry and result files are
published as data. Every page has a feedback link, and [CONTRIBUTING.md](CONTRIBUTING.md) says
what makes a correction quick to accept.

If you are changing code here, two things will bite you otherwise:

1. **Before any commit**, both of these must exit 0: `python scripts/validate.py` and
   `python -m unittest discover -s tests`.
2. **Pages pin code by line number.** Fifty-four `<CodeFile start={…} end={…}>` pins point into
   `examples/` and `scripts/`, each guarded by an `expect=` literal. Editing one of those files
   above a pinned range slides it, and the validator will tell you. See
   `docs/WRITING-A-TECHNIQUE-PAGE.md` for which files, and prefer `func=` over a range in new
   pages.

MIT licensed. See [LICENSE](LICENSE).
