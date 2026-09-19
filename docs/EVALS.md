# Running the evals

The eval set is `evals/questions.json`: 60 synthetic questions over the synthetic documents in
`evals/corpus/`, 12 each in five kinds (lookup, multi-hop, numeric, unanswerable, conflicting
sources). `scripts/eval_run.py` scores one example, or all of the ones this set can measure,
against it. Every example and the runner are stdlib-only Python; no example calls a model until
you tell it to.

## Which examples the question set scores

The set asks one thing: here is a question about the documents, answer it and cite what you
used. An example is scored when it does that. Twenty-six of the forty-four examples do something
else: they are honest demonstrations of their own technique, but a score against this set would
be a number about a task they were not written for, which is worse than no number. Asking the
runner for one prints the reason and exits 2.

| Scored (`--example all` runs these) | Level |
|---|---|
| `order_zero` | 0 |
| `one_call` | 1 |
| `rag`, `context_engineering`, `knowledge_graphs` | 2 |
| `prompt_chaining`, `routing`, `parallelization`, `evaluator_optimizer`, `workflow_graphs` | 3 |
| `function_calling`, `mcp` | 4 |
| `single_agent`, `agent_harness`, `agentic_rag` | 5 |
| `orchestrator_workers`, `agent_graphs`, `debate_review` | 6 |

`agent_harness` is scored for the same reason `single_agent` is: it takes the runner's
`(question, model, embedder, tracer) -> Answer` signature and returns an answer with citations
into the corpus. What it varies is everything around the model (the tool allowlist, the context
policy, the approval hook and the caps), so running it against `single_agent` on the same
questions is how you see what a harness change costs and buys.

`mcp` and `single_agent` are scored because both do the set's own task: they answer a question
about the corpus and return the sections they used. `mcp` reaches the documents through a
stand-in MCP server's search tool rather than an inline Python function, and `single_agent`
plans first and then loops over its tools, but what comes back is an answer with citations
either way, so the same grading contract applies. Comparing `mcp` against `function_calling` on
the same questions is the cheapest way to see what the protocol layer itself costs.

The three level-6 examples are scored for the same reason, and they are the first entries on
this table that let the set measure what a second model costs. `orchestrator_workers` splits the
question, runs one `rag` worker per part and keeps every worker's citations in the combined
answer. `agent_graphs` lets a supervisor call decide whether to research again or write, and the
write node cites the sections the research node found. `debate_review` drafts an answer and then
has a reviewer with its own retrieval accept or reject it; the draft's citations are what the
graders see. All three take the runner's `(question, model, embedder, tracer) -> Answer`
signature, so the same grading contract applies without a special case.

| Not scored here | Why, and what to measure instead |
|---|---|
| `embeddings_search` | Ranks the corpus against a query and compares embedding search with keyword search. No model call, no answer. Measure retrieval: how often the section holding the answer lands in the top k. |
| `memory` | Answers from facts written in earlier conversations. These 60 questions are independent, so the store would be empty every time. Measure the store: recall of a fact written earlier, and that a forgotten fact stays gone. |
| `prompt_engineering` | Sends one fixed passage two ways, bare and structured, to compare prompt styles. It never reads the corpus. Measure format adherence, one prompt against the other, on a set of inputs. |
| `structured_output` | Extracts a warranty record into a five-field schema. Its output is a record, not an answer. Measure schema validity, field accuracy, and how often the retry is needed. |
| `inference_time_reasoning` | Samples one arithmetic question n times and returns the majority answer. No documents, no citations. Measure accuracy at n=1 against n=5, and how often the samples agree. |
| `human_in_the_loop` | Stops and hands back a checkpoint whenever a draft trips a threshold, so many questions end with no answer. Measure the gate: which drafts it pauses, and whether an approved or edited answer is right after resume. |
| `multimodal` | Sends a picture and words in one request. This set is text over text, with no image or audio input. Measure field accuracy against known labels, and how often an unreadable input is reported rather than guessed at. |
| `code_execution` | Answers by writing one arithmetic expression for a sandbox to evaluate. That fits the 12 numeric questions and none of the other four kinds, which it declines by construction. Measure accuracy on the numeric questions, and how often an expression written to escape the whitelist is refused rather than evaluated. |
| `computer_use` | Picks one action on a synthetic screen. No documents, no answer, no citations. Measure whether the chosen action advances the task, the refusal rate on actions outside the allowlist, and how often an irreversible action stops for confirmation. |
| `safety` | Runs one customer-service scenario where a retrieved note carries an injected instruction. What it demonstrates is a refusal, not a cited answer. Measure the share of injected requests correctly refused against the share of legitimate ones correctly permitted. |
| `coding_agents` | Edits a Python function held in memory until fixed test cases pass. It reads no documents and cites only the function's name. Measure the share of tasks that reach passing tests, the attempts it took, and whether an accepted edit broke behavior the shown tests do not cover. |
| `skills` | Chooses among three skill descriptions held in memory and loads one body into context. The choice is the technique. Measure selection accuracy against a labeled set of tasks, and the tokens spent against loading every skill body every time. |
| `voice_agents` | Simulates the control flow of one spoken turn. No document, no citation, no audio. Measure turn-taking on its own set: how quickly an interruption yields the floor, time to the first chunk, and recovery after a false interrupt. |
| `adaptation` | Builds and checks a supervised fine-tuning file out of the question set itself. It answers nothing. Measure that the output is well-formed chat JSONL, that the train/validation split is a clean partition, and that the leak check catches a near-duplicate question straddling it. |
| `distillation` | A teacher answers the exact-graded questions from its own knowledge, with no retrieval and no citations, and what comes out is a training file, not an answer. Measure the capture: the filter's pass rate against `grade_exact`, and, on a sample, whether the kept answers are actually right by a person's reading. |
| `synthetic_data` | Generates new questions rather than answering existing ones, so the grading contract has nothing to check its output against. Measure yield per seed, the split between duplicates and failed verification among the rejects, and, downstream, the ordinary score of whatever was trained or tested on the output. |
| `prompt_optimization` | Searches over candidate system prompts using these questions themselves as its development and held-out splits, so a score against the same 60 would be a score against its own training data. Measure the winner on the held-out split it was never compared on, and that no held-out question is asked during selection. |
| `ops` | Reads recorded trace files and a price table and reports cost and latency per question and per level. No model call, no answer. Measure its report against a hand-computed cost for a known trace and price table, and that a model id with no price reports no dollar figure rather than zero. |
| `observability` | Reads a recorded trace and renames its fields into OpenTelemetry-named span attributes. No model call, no answer. Measure that `capture_content=False` output never contains a step's `detail` text, and that the emitted attribute names still match the current names in the specification the page cites. |
| `ai_gateways` | Routes, falls back and enforces a token budget over two stub providers. Nothing is answered and nothing is cited. Measure the fallback rate, that a call refused for budget is never billed anyway, and that the log holds no prompt text while redaction is on. |
| `local_inference` | Estimates a model's memory footprint from parameter count, bits per weight, context length and concurrency. No model call, no answer. Measure the estimate against a real runtime's own reported memory use at the same model and context length, treating the gap as the activation and framework overhead it says up front it leaves out. |
| `reviewing` | Takes an answer somebody else drafted and checks whether each cited section contains a figure the answer states. It asks the corpus nothing of its own and returns a report, not an answer. Measure how often it flags a citation that genuinely does not support the claim, against how often it flags one that does. |
| `long_horizon` | Works a queue across many separate sessions, and a session may flag a question for a person instead of answering it. Measure across sessions: the share of the queue that finishes, the citation hit rate on unflagged answers, and that a crash between sessions never loses or repeats a finished answer. |
| `agent_teammates` | Wakes on a schedule and sorts proposed actions into run-unattended, queue-for-approval and refuse. No question, no citation. Measure the policy on a labeled set of actions: how many are sorted correctly, how many forbidden actions reach an executor (must be none), and how long one waits for approval. |
| `organizations_swarms` | Assigns tasks on a shared board to three roles under a per-role budget; what a role then does with a task is out of scope. Measure the coordination: rounds that exceed the budget or claim a task twice (must be none), and how evenly work lands across roles against what the coordinator asked for. |
| `embodied` | Proposes one move for a simulated gripper and clamps or refuses it against fixed bounds, a speed cap and forbidden zones. No corpus, no answer. Measure the envelope: whether any move that should have been clamped or refused reaches the actuator log (must be none), and the refusal rate on legitimate in-bounds moves. |

`tests/test_eval_run.py` checks that every directory under `examples/` appears in exactly one of
the two lists, so a new example cannot be added and left silently unscored.

## Dry run: project the cost before spending anything

```
python scripts/eval_run.py --example all --model ollama:llama3.1 --dry
```

`--dry` never calls a model, and never writes a result file. It runs every example through a
token-counting stand-in and prints the tokens in and out it projects per example, so you can
size a dollar budget before a metered run.

The projection is a ceiling, not a guess. Input tokens are counted for real, with `count_tokens`
over the prompt the example actually builds. Output tokens are reported as the `max_tokens` the
example asked for on every call, which is the most a provider can bill for output, since every
call is capped. Whenever tools are offered the stand-in calls one, every time, so a tool-using
example runs all the way to its own step cap or token cap instead of stopping after one round
trip. A real run should come in under the projection; if one does not, the projection is wrong
and is the bug.

One limit, worth knowing before you set a budget from a number. The ceiling holds for an example
whose control flow does not read the model's text. Where it does (`routing` classifies the
question and sends it down one of three branches), the stand-in's placeholder text is not a label
the example recognizes, so the projection follows the fallback branch, which is the cheapest one.
Project a branching example from the branch you expect to be busiest instead: run `--dry` on a
`--kind` subset that takes that branch, or read the branch's own token counts off the trace.

## Set a budget

```
python scripts/eval_run.py --example rag --model claude:claude-sonnet-5 --budget-tokens 100000
```

`--budget-tokens` is a hard cap on tokens in plus out for one example's run. The runner adds one
question's tokens, then compares against the cap, so it can overshoot by at most a single
question before it stops. It writes a partial result: `"partial": true` and `"questions_run"`
less than `"questions_total"`. Re-run with a higher budget, or on a `--kind` subset, to fill in
the rest; cached responses from the first run are reused (see below), so you only pay for what is
still missing.

`evals/budget.json` holds the dry-run ceiling per example as of 2026-09-18, a recommended cap for
each, and a whole-run cap. **Nothing reads it automatically**: it is a record of what the
projection said and where the projection is not to be trusted, and you pass the number yourself.
Two entries are not the dry number: `routing`, for the branching reason above, and
`context_engineering`, which puts the whole document set in every prompt by design and is the one
example that costs about 14,000 input tokens a question against `rag`'s 508.

## A live local run

```
python scripts/eval_run.py --example rag --model ollama:llama3.1 --budget-tokens 100000
```

One example at a time, not `--example all`, at least until you have read a result. No
`--allow-stub`: that flag exists only for `--model stub`, and a real backend never needs it.

The local server must already be running at `127.0.0.1:11434` with the tag pulled; `OllamaModel`
never pulls one for you, on purpose, so a missing tag is an HTTP 404 with the server's own
message rather than a surprise download. `num_ctx` is always sent and defaults to
`DEFAULT_NUM_CTX` in `examples/common/model.py`: left to the server's own default, a long prompt
is silently truncated from the front and the chart reads the truncation as the technique failing.

Every response is cached by `(model_id, sha256 of the prompt payload)` under `.local/eval-cache/`
(gitignored), so re-running after a small prompt change only calls the model for what actually
changed.

**If this is the first live run this repository has ever done, follow `docs/FIRST-LIVE-RUN.md`
instead of this section.** It gives the order (one example and one question kind first, then a
grader, then all 60 questions, then a recorded trace) and says what to look at between the
steps. This page describes the runner; that one describes the sitting.

## A metered run

Same command with `--model claude:<id>`, reading the key from `.local/api-keys.json` (also
gitignored). Run `--dry` first, always. Rubric-graded questions (multi-hop, unanswerable,
conflicting) need a grader model, passed as `--grader <spec>`; it defaults to `--model` if you
leave it out. 10% of the grader's verdicts are written to
`evals/results/<example>/<model-id>.review.json` for you to check by hand against its stated
rubric.

## How a question is graded

Each question carries its own grading contract. Every pattern below is a regex, matched
case-insensitively against the answer text.

| Field | Meaning |
|---|---|
| `accept` | alternatives; at least one must match |
| `require` | conjuncts; every one must match |
| `reject` | any match fails the answer outright |
| `abstain` | `unanswerable` only: the answer must match one of these to count as declining |

`exact` grading is `accept` and `require` and not `reject`. `require` is what keeps a right
number inside a wrong statement from scoring: `M01` accepts `HLV-2205` but also requires
`$52.00`, so naming the part without its price does not pass.

`unanswerable` questions are gated in code before any grader sees them. The answer fails if it
matches a `reject` pattern (it invented a color, a phone number, a weight) or if it matches no
`abstain` pattern (it never said the documents do not answer). The shared `abstain_patterns`
list at the top of `evals/questions.json` is inherited by every unanswerable question that does
not override it. This is the site's hallucination measurement, so it is code, not a judgment
call: a grader is never asked whether an invented answer was acceptable.

`rubric` grading asks the grader model for one word. `PASS` and `FAIL` are the only readable
replies; anything else is **ungraded**, never correct. Ungraded questions are counted in
`ungraded` and left out of the score denominator, so a grader that drifts into prose shows up as
a visible gap rather than as a run of zeros. Running without a grader leaves every rubric
question ungraded for the same reason.

Citations are compared as normalized `file#section`: case, a `.md` suffix, a directory prefix
and `section 3` / `§3` spellings all normalize to the same citation, so two models that cite the
same section score the same.

## Reading a result file

`evals/results/<example>/<model-id>.json` has `score_overall` (over graded questions only),
`ungraded`, `score_by_kind` (n, ungraded and score per kind), `citation_coverage` (the mean
share of `must_cite` sections an answer cited) and `citation_hit_rate` (the share of questions
where every `must_cite` section was cited), `tokens_in`/`tokens_out`, `wall_time_s`,
`tool_calls`, `model_decided_steps` (the count of trace steps the model, not the code, decided),
plus `run_date`, `commit`, and whether the run was `partial`. Keys are written sorted, so two
runs of the same code differ only in the fields that are genuinely per-run.

`--review-seed` (default 0) picks the 10% of rubric verdicts written to the `.review.json` file.
The same seed always draws the same sample; a second reviewer can take an independent sample
with a different seed without re-running anything.

## What `decided_by` means

Every trace step carries `decided_by`, and the site charts how many steps the model decided
against the level. One definition, no exceptions:

> A step is `decided_by: "model"` when the model's output, not the program,
> selected which action happens next: choosing to call a tool, choosing which
> tool, choosing its arguments, or choosing to stop. Everything else is
> `decided_by: "code"`.

Three things follow, each easy to get wrong:

- **Calling a model is not a model decision.** Levels 1, 2 and 3 call a model, sometimes twice,
  but the code decided each call would happen. Those steps are `kind: "model"` and
  `decided_by: "code"`. The two fields answer different questions.
- **Returning a tool result to the model is always `code`**, as is forcing a final answer when a
  cap is reached, and parsing or filtering whatever came back.
- **Declining to call a tool is a model decision.** At level 4 the program offers a choice
  between calling a tool and answering directly, and the model's output selects one. It is the
  same decision as the stop at level 5 and is counted the same way. The alternative would let a
  model that ignores every tool look, in the trace, exactly like a level-3 workflow, which is
  the one thing this measurement exists to tell apart.

So: levels 0 to 3 record no model-decided steps; level 4 records exactly one per run; level 5
records one per tool call plus one for the stop, unless a cap cut the run short, in which case
the forced answer is a `code` step. `tests/test_examples.py` asserts all of it.

## The stub rule

A run with `--model stub` is not a real reading of anything: it exists so the pipeline, the
scoring logic, and CI can be exercised with no model and no network call. `eval_run.py` refuses
to write a result file for a stub run unless you pass `--allow-stub`, and any file it does write
that way is marked `"stub": true`. **A chart may only be built from a result file where `"stub"`
is false.** The same rule and the same flag apply to `scripts/record_trace.py`, which records one
example run for one question to `examples/<name>/trace.json`.

## What is missing right now

No example has a recorded `trace.json` or a non-stub result file yet: this repository was built
without calling any model, local or remote, so there is nothing genuine to record. Every page on
the site is `draft`. The first live run, local or metered, is the owner's to start, and
`docs/FIRST-LIVE-RUN.md` is the order to do it in, including the seven conditions a page must
meet before its status changes to `published`.

Two known gaps in the tooling, neither blocking:

- `scripts/record_trace.py` no longer keeps a list of examples: it discovers every directory under
  `examples/` and records the ones whose `run` follows the convention `(text, model, tracer)` or
  `(text, model, embedder, tracer)`, with every keyword-only parameter defaulted. Run
  `python scripts/record_trace.py --list` for the live list and, for each example it cannot
  record, the exact reason. The rest need a small change to the example itself, usually a default
  for a keyword-only argument.
- `--example all` on a local model runs eighteen examples back to back with no pause to read a
  result. It works, and `context_engineering` at the end of it will take a long time. Prefer one
  at a time until the numbers are familiar.
