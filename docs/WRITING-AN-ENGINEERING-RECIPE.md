# Writing an engineering recipe

The engineering recipes are the pages for readers who write code for electronics test
automation, test data analysis, electronics design and the software around all three. They are
recipes like any other: a whole job, composed from techniques, with the reasoning for every
choice. What is different is the audience. An engineer will check your arithmetic, and one wrong
unit ends the page's credibility on the spot.

Read `docs/THE-BENCH.md` first. It describes the world every engineering recipe runs on and
holds the answer key to the data. Read `docs/WRITING-A-TECHNIQUE-PAGE.md` for the house rules on
prose, links, sources and MDX, which apply here unchanged.

## Three settings, one bench

The same board and the same four instruments serve three different jobs, and your page is for one
of them. Say which, in the first paragraph, in the reader's own words.

1. **Production test.** Many units, a fixed sequence, a pass or a fail against limits, and
   statistical process control over the result. The economics are per unit and per day.
2. **Engineering test.** Bring-up, characterization, design verification. A handful of boards,
   sweeps over line, load and temperature, margins rather than verdicts, a script that runs five
   times, a lab notebook, a report at the end. The economics are one person's time.
3. **Precise measurement.** One number that has to be right and has to say how right it is: the
   instrument's accuracy specification, the range, the calibration interval, settling,
   repeatability, and a guardband on the limit. The economics are the half hour it takes to write
   the budget down.

None of the three is the default. A page that opens with 400 units to get through today is a
production page and should say so; the engineer validating five prototypes is reading a different
page, and the person making one careful measurement a third. Where a claim is true of only one
setting, name the setting in the sentence.

Two things are worth knowing about the boundary between them.

**Volume changes the economics, not the levels.** In production a model-drafted script is
amortized over thousands of units and checked against a golden run, so the drafting is cheap per
unit and the checking is routine. At low volume the script runs five times, there is no golden run
to check against, and the person's afternoon is the whole cost. Drafting help is worth more there,
and checking matters more there, because there is no second unit to catch the mistake.

**Level 0 is still most of it.** A sweep is a loop. A margin is a subtraction. An uncertainty
budget is a root sum of squares. A guardband is another subtraction. Nothing in that list needs a
model, in any of the three settings.

## The two claims every one of these pages carries

**Most of this work is level 0.** A limit check is a comparison. A yield is a count. A Cpk is a
mean, a standard deviation and a subtraction. A control chart is those plotted against time. A
sweep over line, load and temperature is a nested loop. A margin to a specification is a
subtraction. An uncertainty budget is a root sum of squares over four named numbers, and a
guardbanded limit is the specification limit minus one of them. Finding a bad lot, a bad fixture
or a block of readings taken on the wrong meter range is a `GROUP BY`. An engineer's week is
mostly this, and the honest version of this site says so before it offers a model.

Two pages teach it, one per data set: `limits-without-a-model` on the production log and
`characterize-a-design` on the characterization data. They lead the engineering list together,
and every recipe above them names the part of the job that actually needed a model. If your page
could have been level 0 and you wrote it at level 4, an engineer will notice before your second
paragraph.

**A model never produces a reported measurement, an uncertainty, a margin or a verdict.** This is
the general form, and the pass or fail rule is the production-test case of it. Not as a check, not
as a tie-breaker, not as a summarizer of a borderline reading, and not as the thing that assembles
a budget or rounds a margin.

The reason is different in each setting and the rule is the same in all three. In production a
wrong pass ships a bad unit, and a model that is right 99 times in 100 adds a one percent defect
rate to a line that measures defects in parts per million. In engineering test a margin is what a
design decision is made on, and a margin nobody can reproduce is worse than no margin. In precise
measurement the uncertainty is the measurement: a number a model assembled looks exactly like a
number a budget produced, and only one of them is true.

Numbers come from code. A model may read a manual, triage free text, draft a script that code then
checks, or write the prose around numbers code has already computed and placed. Say this plainly
on any page where a reader could imagine putting a model in that path.

## What an engineering recipe page contains

In this order. Sections may be renamed to suit the page; none may be dropped.

### 1. The job, in an engineer's words

Not "document question answering over a technical corpus." Something closer to one of these,
whichever setting your page is for:

- A board fails a limit on one fixture and passes on another, and you have 400 units to get
  through today.
- Five prototypes came back from the board house, the design review is Thursday, and nobody knows
  what the output does at 9 V in and 3 A out at 70 degC.
- The number going in the report is 0.299 percent against a 0.300 percent limit, and somebody is
  going to ask how good the measurement is.

Name the artifacts the reader actually has, by the names they actually have: a datasheet, a test
spec, an ECN, a production log, a characterization sweep, a lab notebook, a programming manual, a
calibration record.

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

Model calls per item, tokens per call, and what that is in the unit the reader's setting actually
counts in. This site has no measured costs: work the estimate through in the open and label it an
estimate. For a level-0 recipe the honest cost line is that it costs nothing per unit, which is
worth writing down next to a page that costs a call per unit.

The unit differs by setting, and using the wrong one makes the page read as though it was written
for somebody else:

- **Production test:** per unit and per day. A tenth of a cent a unit is 4 dollars a day at 4000
  units, and the comparison that matters is against the cost of a test step's seconds.
- **Engineering test:** per run and per session, because the script runs five times. Ten cents a
  run is not a number worth discussing; the comparison that matters is against the half hour the
  drafting saved, and against the hour lost if the draft is wrong and nobody checks it.
- **Precise measurement:** per measurement, of which there may be one. The model's cost is
  rounding error against the instrument's calibration, and the cost that matters is the cost of
  being wrong: a re-measurement, a re-spin, or a wrong number in a report somebody signs.

Say which of these your page is counting in, and do not amortize over a volume your reader does
not have. A cost section that divides by 4000 units is telling a design verification engineer
that this page was not written for them.

### 6. How it fails on a real bench, specifically

Not "the model may hallucinate." Specifically, and from this bench. The first group happens in
any of the three settings:

- An answer read off the datasheet that an ECN superseded, for the board revision on the bench.
- A command drafted from the wrong vendor's manual, which the instrument rejects silently and
  reports only when `SYST:ERR?` is asked.
- A reading taken before the settle delay, which is a number and not a measurement.
- A ripple figure taken with the bandwidth limit off, which is roughly double and still a real
  reading of something else.
- A meter on too small a range, which returns an overload value with an empty error queue.

In production test:

- A retest export merged on a column named for volts and filled with millivolts.
- A cause assigned from an operator note that was typed on the wrong row.
- A fixture offset that moves one step's mean and cancels in the two steps that are differences.

In engineering test:

- A sweep point recorded at a condition it was not taken at, which the output voltage will not
  show and the input current will.
- A corner that was never visited, so the margin nobody measured is the one that matters.
- A block of readings that scatter for a reason that is not the board: a range left set, a
  thermocouple on the rack instead of the case, a chamber that had not settled.
- A conclusion drawn from one board, which is a sample of one.

In precise measurement:

- A reading taken on a range ten times too large, which is not an error and is worth a quarter as
  much: on this meter 824.7 uV against 224.8 uV for the same 4.9930 V.
- The accuracy row for the wrong calibration interval: 79.9 uV is the 24 hour figure, and the
  meter was calibrated eleven months ago.
- A temperature coefficient left out because the ambient was inside the band for the instrument
  and not for the board, or applied to the ambient instead of to the degrees outside the band.
- An uncertainty quoted without its coverage factor, which is ambiguous by a factor of two.
- A systematic offset counted twice, or counted in a difference where it cancels.
- A margin declared a pass when it is smaller than the expanded uncertainty, where the honest
  answer is that the measurement does not say.

Pick the ones that apply to your recipe and say what catches each.

### 7. How to evaluate it

What a right answer looks like, and how many examples with known right answers a reader should
collect before tuning anything. For a classifier, the confusion that matters and which direction
the cost is asymmetric in. For a drafting recipe, whether the drafted script ran clean on the
simulated instrument, which is a pass or fail and not a judgment. For an extraction recipe, the
row-by-row comparison against the document it was extracted from, done by a person, and the two
mistakes worth counting separately: a value transcribed wrong, and a right value taken from the
wrong row of the table.

At low volume there is no golden run to score against and there may be five examples in total.
Say so rather than prescribing a set size the reader cannot reach, and say what a person checking
by hand should look at first. For a drafting or writing recipe, the check that costs nothing is a
mechanical one: every figure in the output appears in the computed results, character for
character, or the output does not ship.

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

## The two level-0 pages, and the order the recipes come in

The engineering list is ordered by level, not by setting, and the two pages at the bottom of it
are a pair: one per data set, one per setting, both level 0, neither the default.

`limits-without-a-model` is the production one. It covers limits, first-pass yield, Cpk, control
charts, and the same measurements grouped by lot, by fixture, by day and by shift. All six
production stories in `evals/bench/data/` are findable that way, and a page that teaches this
should find at least two of them in front of the reader.

`characterize-a-design` is the engineering-test one. It covers a sweep over line, load and
temperature, the margin to each datasheet limit at every corner, the uncertainty budget behind
those margins and the guardbanded verdict that comes out. All four characterization stories are
findable with arithmetic, and the page should work at least the corner margin and the
cannot-say case in front of the reader.

Include the negative result, on both. Grouping the production data by day and by shift finds
nothing, and being able to say that is worth as much as finding the fixture. A yield number
grouped by lot barely moves for the bad-capacitor lot, while the ripple mean and Cpk for that lot
move enormously: that is the argument for charting measurements rather than counting failures.
In the characterization data, the extra scatter is not any board and not any corner, and saying
so takes one `GROUP BY` on a column nobody thinks to group by.

`test-data-by-conversation` starts from the other end, and must say so in its first paragraph:
the dashboard is built, the charts are up, and the question being asked is not one of them. That
is the honest order. A page that opens by offering a model for work a `GROUP BY` already does is
the thing this site exists to argue against.

## Measurements, margins and uncertainty

Any page that quotes a figure a reader might act on states four things with it: the value, the
expanded uncertainty and its coverage factor, the range the reading was taken on, and the
calibration interval the accuracy row came from. `mdn6100-programming-manual.md` sections 7 and 8
are the method and a worked example; `examples/common/bench.py` has the functions, and every
figure in the manual is recomputed in `tests/test_bench.py`.

Rules for a page that touches this material:

- **Never assemble a budget in prose.** Call `dc_voltage_budget`, `combined_uncertainty` and
  `expanded_uncertainty`, and show the table those produce. A budget written by hand on a page is
  a number this site cannot check.
- **Name every contribution.** A budget's value is that it says which line is the largest, and on
  this bench that line is not always the instrument.
- **Say which lines cancel.** A systematic offset in the leads or the fixture cancels in a
  difference of two readings through the same path, which is why the line and load regulation
  budgets drop it and an absolute voltage budget does not.
- **Use the three-outcome verdict.** `guarded_verdict` returns pass, fail or `cannot say`, and a
  page that quietly turns the third into the first is teaching the habit this whole section
  exists to break.
- **Do not quote more digits than the instrument supports.** An efficiency computed from the
  supply's current readback is a percent-level number whatever the arithmetic prints.

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
- **The data is read, not regenerated.** `from evals.bench import PRODUCTION_CSV` for the
  production log, `CHARACTERIZATION_CSV` for the sweep. Never call `generate()` from either
  generator into `evals/bench/data/` from an example or a test.
- **Uncertainty comes from the shared functions.** `from examples.common.bench import
  dc_voltage_budget, combined_uncertainty, expanded_uncertainty, guarded_verdict`. An example that
  writes its own root sum of squares will drift from the manual, and the manual's tests will not
  catch it.
- **Standard library only**, as everywhere else in `examples/`.
- **Trace steps are honest about `decided_by`.** The rule is in `examples/common/trace.py` and
  has no exceptions: a step is `decided_by: "model"` only when the model's output selected which
  action happens next. Calling a model is not a model decision. On a level-0 recipe every step is
  `code`, which is the whole point of that page.

## Engineering correctness, the bar

- Every limit, tolerance, unit and formula is checked, and if the page teaches a formula, a test
  computes it. `tests/test_bench.py` is the pattern: the datasheet's numbers and the meter's
  accuracy table are recomputed from the model, so the two cannot drift.
- A margin is stated against a named limit from a named document, with the sign convention
  visible: positive is inside the limit. `margin_to_limit` is where that lives.
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
