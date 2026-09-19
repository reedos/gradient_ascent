# Writing an engineering recipe

The engineering recipes are the pages for readers who write code for electronics test
automation, test data analysis, electronics design and the software around all three. They are
recipes like any other: a whole job, composed from techniques, with the reasoning for every
choice. What is different is the audience. An engineer will check your arithmetic, and one wrong
unit ends the page's credibility on the spot.

Read `docs/THE-BENCH.md` first. It describes the world every engineering recipe runs on and
holds the answer key to the data. Read `docs/WRITING-A-TECHNIQUE-PAGE.md` for the house rules on
prose, links, sources and MDX, which apply here unchanged.

## The two claims every one of these pages carries

**Most of test automation is level 0.** A limit check is a comparison. A yield is a count. A Cpk
is a mean, a standard deviation and a subtraction. A control chart is those plotted against time.
Finding a bad lot or a bad fixture is a `GROUP BY`. A sequencer is a loop. A test engineer's week
is mostly this, and the honest version of this site says so before it offers a model.

`limits-without-a-model` is the page that teaches it, it leads the engineering list, and every
recipe above it names the part of the job that actually needed a model. If your page could have
been level 0 and you wrote it at level 4, an engineer will notice before your second paragraph.

**The pass or fail decision never involves a model.** Not as a check, not as a tie-breaker, not
as a summarizer of a borderline reading. A wrong pass ships a bad unit. A model that is right 99
times in 100 adds a one percent defect rate to a line that measures defects in parts per million.
Say this plainly on any page where a reader could imagine putting a model in that path.

## What an engineering recipe page contains

In this order. Sections may be renamed to suit the page; none may be dropped.

### 1. The job, in an engineer's words

Not "document question answering over a technical corpus." Something closer to: a board fails a
limit on one fixture and passes on another, and you have 400 units to get through today. Name the
artifacts the reader actually has, by the names they actually have: a datasheet, a test spec, an
ECN, a production log, a programming manual.

### 2. The lowest level that does it, and why not higher

Say which level and why, in terms of the job. Then say what the next level up would add and what
it would cost: more calls, more latency, more ways to be wrong, another thing to evaluate. This
is the part readers least expect and most need.

Where a part of the job is level 0, split it out and say so, even on a page that is otherwise
about level 4. A page that admits half its job is a `GROUP BY` is more trusted for the half that
is not.

### 3. The run on the bench, stepped

A concrete walkthrough on `docs/THE-BENCH.md`'s bench, step by step, with the actual commands and
the actual numbers. Use `<Run>` where a recorded run exists. Where it does not, say so: the site
has no measured results, and an illustrated run is labeled as one.

Name the instrument each command goes to. The two vendors on this bench have different SCPI
dialects, and a page that shows `INP ON` going to a TRN-2400 is showing a command that returns
`-224,"Illegal parameter value"`.

### 4. The code, embedded

Embed real code from the example package with `<CodeFile file="examples/bench_<name>/run.py"
func="run" />`. `scripts/validate.py` rule 12 checks that the file exists and defines the function
you named, so an embedded block cannot drift from the code. Never paste code into the MDX by
hand.

### 5. What it costs

Model calls per item, tokens per call, and what that is per unit and per day at a production
volume the reader would recognize. This site has no measured costs: work the estimate through in
the open and label it an estimate. For a level-0 recipe the honest cost line is that it costs
nothing per unit, which is worth writing down next to a page that costs a call per unit.

### 6. How it fails on a real bench, specifically

Not "the model may hallucinate." Specifically, and from this bench:

- An answer read off the datasheet that an ECN superseded, for the board revision in the fixture.
- A command drafted from the wrong vendor's manual, which the instrument rejects silently and
  reports only when `SYST:ERR?` is asked.
- A reading taken before the settle delay, which is a number and not a measurement.
- A ripple figure taken with the bandwidth limit off, which is roughly double and still a real
  reading of something else.
- A meter on too small a range, which returns an overload value with an empty error queue.
- A retest export merged on a column named for volts and filled with millivolts.
- A cause assigned from an operator note that was typed on the wrong row.

Pick the ones that apply to your recipe and say what catches each.

### 7. How to evaluate it

What a right answer looks like, and how many examples with known right answers a reader should
collect before tuning anything. For a classifier, the confusion that matters and which direction
the cost is asymmetric in. For a drafting recipe, whether the drafted script ran clean on the
simulated instrument, which is a pass or fail and not a judgment.

### 8. How to adapt it to the reader's own instruments

The bench is simulated. Say so, and say what the port looks like: every instrument here is one
`send(command: str) -> str` method, which is the shape PyVISA's `write` and `query` pair
covers, so the code that composes and checks commands does not change and the transport does.
State that as a pointer for the reader to follow, not as a tested fact: nothing in this repo has
been run against real hardware, and no page may imply it has.

Also say what does not port: the DUT model, the specific command set, and every number in
`docs/THE-BENCH.md`. The reader's instrument has its own manual and their board has its own
datasheet, and the whole lesson of the drafting recipe is that those are the documents to check
against.

## A model that drafts code which could command real equipment

Any recipe where a model's output could reach an instrument carries this, explicitly, in its own
words:

1. **The model drafts.** It proposes commands or a script. It does not send anything.
2. **Code checks every command against the documented command set** for that instrument, from
   that instrument's manual. `examples/common/bench.py` is the reference implementation: a
   command the manual does not document returns the documented error and lands in the error
   queue.
3. **The script runs on the simulated instrument first**, and its errors come back for another
   pass before a person sees it.
4. **A person bench-checks it** before it touches real hardware, with the board's own current
   limit set low and somebody watching.

For an agent holding instrument tools, the split is in `examples/common/bench.py` as
`READ_ONLY_HEADERS` and `is_read_only()`, and in `docs/THE-BENCH.md`:

| Class | What it is | Who may run it |
| --- | --- | --- |
| Read only | `*IDN?`, `SYST:ERR?`, every measurement and status query | the agent, unattended |
| Sets state | voltage, current limit, mode, range, coupling, `*RST` | code, after `SafetyEnvelope` |
| Energizes a board | `OUTP ON` on the supply, `INP 1` on the load | code, plus a person's `Approval` naming the set point |

`SafetyEnvelope` holds the limits for the board in the fixture, not the limits of the instrument.
Say why on the page: the supply can do 40 V and 10 A, and the board is rated for 32 V and 3 A,
and the envelope is about the board.

## Statistical process control, and the order the recipes come in

`limits-without-a-model` covers limits, first-pass yield, Cpk, control charts, and the same
measurements grouped by lot, by fixture, by day and by shift. All six stories in
`evals/bench/data/` are findable that way, and a page that teaches this should find at least two
of them in front of the reader.

Include the negative result. Grouping the bench data by day and by shift finds nothing, and being
able to say that is worth as much as finding the fixture. A yield number grouped by lot barely
moves for the bad-capacitor lot, while the ripple mean and Cpk for that lot move enormously:
that is the argument for charting measurements rather than counting failures, and it is in the
data.

`test-data-by-conversation` starts from the other end, and must say so in its first paragraph:
the dashboard is built, the charts are up, and the question being asked is not one of them. That
is the honest order. A page that opens by offering a model for work a `GROUP BY` already does is
the thing this site exists to argue against.

## The example package

One directory per recipe, `examples/bench_<name>/`, laid out like every other example here.

    examples/bench_<name>/
      __init__.py
      run.py          the recipe, with a `run` function
      __main__.py     `python -m examples.bench_<name> --question "..."`
      README.md       what it does, how to run it, what it does not do
    tests/test_example_bench_<name>.py

Rules, all of them already true of the existing examples:

- **`run(text, model, tracer)`**, in that positional order, or
  `run(text, model, embedder, tracer)` where an embedder is needed. Every keyword-only parameter
  carries a default. `scripts/record_trace.py` reads the signature with `inspect` and can record
  any example that follows it; one that does not cannot be recorded without changing the example.
  The first parameter may be named anything that suits the recipe (`question`, `symptom`,
  `requirements`).
- **`StubModel` only.** No test calls a real model, no test touches a network, and nothing in
  this repo calls Ollama or an API. The stub is deterministic and the tests are the contract.
- **The bench is imported, not reimplemented.** `from examples.common.bench import Bench,
  GuardedSupply, ...`. A recipe that models the board itself will drift from the datasheet, and
  the datasheet tests will not catch it.
- **The data is read, not regenerated.** `from evals.bench import PRODUCTION_CSV`. Never call
  `make_data.generate()` into `evals/bench/data/` from an example or a test.
- **Standard library only**, as everywhere else in `examples/`.
- **Trace steps are honest about `decided_by`.** The rule is in `examples/common/trace.py` and
  has no exceptions: a step is `decided_by: "model"` only when the model's output selected which
  action happens next. Calling a model is not a model decision. On a level-0 recipe every step is
  `code`, which is the whole point of that page.

## Engineering correctness, the bar

- Every limit, tolerance, unit and formula is checked, and if the page teaches a formula, a test
  computes it. `tests/test_bench.py` is the pattern: the datasheet's numbers are recomputed from
  the model, so the two cannot drift.
- Units are stated everywhere, on every axis, in every table column, in every log column. Ripple
  in millivolts peak to peak. Efficiency as output power over input power, with both currents
  given so a reader can check it. Regulation as a percentage of the nominal output, with the
  range it was taken over.
- Cpk is the standard formula. One-sided against an upper limit it is `(USL - mean) / (3 * sigma)`.
  Say which form you used and against which limit.
- Round numbers, physically ordinary. If a figure needs three decimal places to be interesting,
  it is probably wrong.
- Real standards and real physics may be named and used correctly: SCPI, IEEE 488.2, Ohm's law,
  buck converter ripple, X7R bias derating. No real company, product, part number or standard
  designation may be used as if it were ours.
- Every name in the bench is invented and was checked to be invented. If you need a new one,
  search it first and record the check in `docs/THE-BENCH.md` alongside the others.
