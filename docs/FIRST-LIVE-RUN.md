# The first live run

Nothing in this repository has ever called a model. Every example, every test and every number
in `evals/budget.json` was produced against a stub or a token counter. A technique page goes from
Draft to Published only when it has a recorded trace from a real run and a result file that is
not marked `stub`: see *Draft to Published* at the end of this file.

Read `docs/EVALS.md` first for what `scripts/eval_run.py` does. This file is the sequence to run
it in, one page at a time, plus `scripts/record_trace.py`, which records the trace a page's
Build-it lane plays back.

Both scripts take `--model stub`, `ollama:<tag>` or `claude:<id>`. Neither takes
`stub:scripted`, the spec that plays an example's own written-down replies from the command line
(`docs/RUNNING-AN-EXAMPLE.md`): that is a fixture for a demonstration, and a score or a recorded
trace taken from one would be a measurement of a string somebody typed. The refusal is in
`build_model`, so it is an error rather than a silent stub run.

Every command below runs from the repository root with `C:\Program Files\Python314\python.exe`,
written as `python` for short.

## Before you start

- **Run when the machine is otherwise idle.** Stop anything scheduled that talks to your local
  model server before you start, and do not start a run and then walk away while something else
  on the machine wakes up on a timer; it will make this run slower and, because the runner
  records wall time into the result file, wrong in a way nothing downstream can detect.
- **One example at a time.** Do not pass `--example all` to `eval_run.py` against your local
  model on the first day. It runs every example in sequence, but you want to read each result
  before paying (in time, locally, or in dollars, against the metered API) for the next.
- **Set the context size explicitly.** `OllamaModel` always sends `num_ctx`, defaulting to 8192
  (`DEFAULT_NUM_CTX` in `examples/common/model.py`). Left to your local model's own default, a
  long prompt is silently truncated from the front, the model never sees the sources, and the
  chart would read that as the technique failing. If you raise it, say so in your run notes: a
  result file records the model id, not the context size.
- **Nothing here pulls a model for you.** `OllamaModel` never pulls, on purpose. A missing tag is
  an HTTP 404 with your local server's own message; pull it yourself, deliberately, so you know
  which tag you measured.
- **`context_engineering` is the one to run last on a local model.** It puts the whole document
  set in every prompt by design (about 14,000 input tokens a question against `rag`'s 519), which
  is the difference between minutes and an hour on a local model.

## Order

1. One example, one question kind, no grader (`eval_run.py`).
2. Add a grader, on a question kind that needs one (`eval_run.py`).
3. One example, all 60 questions (`eval_run.py`).
4. Record the trace the page will actually show (`record_trace.py`).
5. The rest of the local run, one example at a time.
6. Only after that: the metered run, only for pages you intend to publish.

## Step 1: the smallest real thing

`rag` is the right first example: level 2, one model call per question, no branches. `lookup` is
the right first kind: 12 questions, all `exact`-graded, so no grader model is involved.

```
python scripts/eval_run.py --example rag --model ollama:<your-tag> --kind lookup --budget-tokens 40000
```

Writes: `evals/results/rag/ollama_<your-tag>.json`.

Check, in this order:

1. `"stub": false`: if true, you ran the stub; nothing about a stub run may reach a page.
2. `"partial": false`: if true, the token cap cut it short; raise `--budget-tokens` and re-run.
   The cache means you only pay for what the first run did not reach.
3. `"ungraded": 0`: every `lookup` question is `exact`-graded, so anything ungraded means a
   question is mis-tagged in `evals/questions.json`, not that the model did badly.
4. `"model_decided_steps": 0`: `rag` is level 2. Nonzero means either the example changed or the
   rule in `examples/common/trace.py` broke; stop and find out which before reading further.
5. `"citation_coverage"`: the share of `must_cite` sections the answers actually cited. Low here
   with a decent `score_overall` means the model found the right answer from the wrong passage.
6. `"score_overall"`: read it last. It is the least informative number until you trust the five
   above it.

Do not publish anything off this run. One example, one kind, one model is a smoke test.

## Step 2: add a grader

`multi_hop` questions are `rubric`-graded: a second model reads each answer against a checklist.

```
python scripts/eval_run.py --example rag --model ollama:<your-tag> --grader ollama:<your-tag> --kind multi_hop --budget-tokens 60000
```

Writes: the result file above, plus `evals/results/rag/ollama_<your-tag>.review.json`, a
deterministic 10% sample of the grader's verdicts.

Read the sample and decide, yourself, whether you agree before you look at `verdict`. One
disagreement in a small sample is noise; two in a row means the grader is not trustworthy and no
rubric score from this run means anything. If it is not trustworthy, stop here: a rubric score
from an unchecked grader is worse than no score, because it looks like a measurement.

## Step 3: one example, all 60 questions

```
python scripts/eval_run.py --example rag --model ollama:<your-tag> --grader ollama:<your-tag> --budget-tokens 100000
```

Check the same six things, plus `score_by_kind.unanswerable`: it is gated in code before any
grader sees it, so a low score there is a hallucination rate, not a grader's opinion.

## Step 4: record the trace

A score is a number; a trace is what a reader steps through on the page. Record it separately,
for one question whose answer you have already read.

**Check first whether the example can be recorded at all**, and what model shape it expects:

```
python scripts/record_trace.py --list
```

This prints every example under `examples/` and, for the ones it cannot record, why: an entry
point that is not named `run`, or a required argument `--question` cannot fill in.
`.local/page-requests/wave6-traces.md` has the exact change each of those would need; most pages
do not need it. The last line of `--list` is the count of recordable examples out of the number
discovered, which is read off the directory on every run rather than written down anywhere.

An example that takes something narrower than a question as its first argument (a serial number
that has to exist in the production log, a date, a document section) names a working one as
`SAMPLE_INPUT` in its `run.py`, and `--question` may be left out for it. `--list` does not say
which those are; `examples/<name>/README.md` prints the command.

**Then project the call before making it**, the same discipline as `eval_run.py --dry`:

```
python scripts/record_trace.py --example rag --question "How long is the warranty on the DW-480, and what voids it?" --model ollama:<your-tag> --dry-run
```

This prints the model id, the projected input and output tokens, and where the trace would be
written. It calls no model. Then record it for real:

```
python scripts/record_trace.py --example rag --question "How long is the warranty on the DW-480, and what voids it?" --model ollama:<your-tag>
```

Writes: `examples/rag/trace.json`.

Open it and check `"stub": false`, that `commit` is the commit you ran at, and that every step's
`decided_by` matches the rule in `examples/common/trace.py`: for `rag`, every step is `"code"`.

Some examples need an `embedder` as well as a model; today's embedder support covers `stub` and
`ollama:<tag>` only, so record those against your local model even when the chat answers come
from the metered API. `--list` and `--dry-run` both tell you which shape an example expects.

## Step 5: the rest of the local run

Work up the levels, reading each result before starting the next: `order_zero` (free, no model),
`one_call`, `rag`, `knowledge_graphs`, `prompt_chaining`, `routing`, `parallelization`,
`evaluator_optimizer`, `workflow_graphs`, `function_calling`, `mcp`, `single_agent`,
`agentic_rag`, `orchestrator_workers`, `agent_graphs`, `debate_review`, and `context_engineering`
last. Per-example token caps are in `evals/budget.json`; `routing` and `context_engineering` are
not what the dry run projects, and the file says why.

At level 4 and above, check `model_decided_steps` against what the level allows: exactly one per
question at level 4, one per tool call plus one for the stop at level 5. A number outside that is
either a real bug in the example or a real bug in the site's central claim, and both matter more
than the score.

Record a trace (Step 4) for each page before it publishes, in whatever order you write pages.

## Step 6: the metered run

Only after the local run is clean, and only for the pages you actually intend to publish.

1. Put the key in `.local/api-keys.json` as `{"anthropic": "sk-..."}`. That path is gitignored;
   `ClaudeModel` reads it from nowhere else.
2. **Check the projected cost first**, against the real model id:

   ```
   python scripts/eval_run.py --example all --model claude:<id> --dry
   ```

   No key is needed for this: `--dry` never builds a real backend. Compare the numbers with
   `evals/budget.json`; if they have moved since the file's own date, an example changed and the
   budget is stale.
3. Multiply the token figures by the maker's published price on the day you run. No price is
   written in this repository on purpose; see the `dollars` note in `evals/budget.json`.
4. Run one example, with a cap, and read the result before the next:

   ```
   python scripts/eval_run.py --example rag --model claude:<id> --grader claude:<id> --budget-tokens 100000
   ```
5. Record its trace the same way as Step 4, with `--model claude:<id>` in place of `ollama:...`
   (subject to the embedder note above).
6. Only synthetic documents ever leave the machine. `evals/corpus/` is invented; check nothing
   else has been added to it before a metered run.

## Stopping

Ctrl+C is safe at any point. `eval_run.py` caches every response by `(model id, prompt hash)`
under `.local/eval-cache/`, so a stopped run pays again only for the question in flight, not for
anything already answered. Resume with the same command. `record_trace.py` writes `trace.json`
only once a run finishes, so an interrupted recording leaves no partial file and does not disturb
whatever trace was already there. Nothing else needs shutting down: neither script starts a
background process.

## Draft to Published

A page may be published when every one of these is true. There is no partial version of it.

1. **A recorded trace** at `examples/<name>/trace.json`, `"stub": false` and `"illustrative":
   false`, from a model id the page names.
2. **A result file** at `evals/results/<name>/<model-id>.json`, `"stub": false` and `"partial":
   false`.
3. **The trace's `decided_by` pattern matches the level** the page claims, per
   `examples/common/trace.py`.
4. **Every number the page states comes from that result file**, and names the model class it
   holds for: "level N beats level M" with no class attached is not publishable (the project plan,
   Measurement design, Claim rule).
5. **The grader sample for that run was hand-checked**, if any of its questions were
   rubric-graded.
6. **Every registry entry the page cites is `verified: true`**, with a source and a checked date.
7. **The page's `status` in `content/taxonomy.json` changes to `published` in the same commit**
   as the trace and the result file, so the three cannot drift apart.

Until then, the run diagrams on the site carry `"illustrative": true`, which is what the site
uses to refuse to present them as measurements. Do not remove that flag from a file that is still
hand-drawn.
