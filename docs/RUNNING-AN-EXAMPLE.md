# Running an example

Every technique page and every engineering recipe has one runnable example under `examples/`, and
every page prints the command for it. This file is what that command is, what the two stub models
do, and the convention an example follows so its command demonstrates what its page claims.

Nothing here calls a model. `examples/common/model.py` has live backends, and no test and no
command in this file reaches one. See `docs/FIRST-LIVE-RUN.md` for the run that does.

## The package

    examples/<name>/
      __init__.py
      run.py          the technique, with a `run` function and an integer `LEVEL`
      __main__.py     the command line: `python -m examples.<name> ...`
      README.md       what it shows and how to run it
    tests/test_example_<name>.py

`run.py` is the file a page embeds with `<CodeFile>` and the file `scripts/record_trace.py` and
`scripts/eval_run.py` call. Its shape is fixed: `run(text, model, tracer)` or
`run(text, model, embedder, tracer)`, every keyword-only parameter carrying a default. The full
rule, and what happens to an example that breaks it, is in `docs/WRITING-AN-ENGINEERING-RECIPE.md`
under *The example package*.

`__main__.py` is the command line and nothing else: parse arguments, build a model, call `run`,
print what a reader should see. It holds no part of the technique.

## The arguments

`examples/common/cli.py` has the shared parser most examples use:

    --model      stub | stub:scripted | ollama:<tag> | claude:<id>     (default: stub)
    --embedder   stub | ollama:<tag>                                   (default: --model)
    --question   the input, for the examples that take one

An example with something more to ask for (a scenario, an output path, a serial number) keeps its
own `argparse.ArgumentParser`. There is a `MODEL_HELP` constant in `cli.py` so the `--model` help
text reads the same either way.

## The two stubs

**`--model stub`** is `interactive_stub()`. It answers every call by echoing back the last user
message. It shows that an example runs and what shape its run has, and nothing else. Two things
it cannot show, by construction:

- Anything an example varies in the **system** prompt. The echo only ever reflects the user turn,
  so two runs that differ only in their instructions print identical output.
- Any branch the example takes on **what the model said**. A classifier gets an echo instead of a
  label, a citation parser gets an echo with no citation in it, an agent loop is never offered a
  tool call. Every such example takes its fallback path, every time.

**`--model stub:scripted`** is `scripted_stub()`. It plays an ordered sequence of replies, one per
model call, and the sequence lives in the example's own `__main__.py`:

```python
DEFAULT_QUESTION = "How often should the DW-300's filter be cleaned?"

# Two model calls on this question: classify, then answer inside the lookup route.
SCRIPTED = [
    "lookup",
    "Every 30 cycles. Sources: dw300-manual#6",
]

model = build_cli_model(args.model, example="routing", script=SCRIPTED)
```

A reply is a plain string, or a `StubResponse` where the call has to return a tool call:

```python
SCRIPTED = [
    StubResponse(text="", tool_calls=[ToolCall(name="lookup_part", arguments={"part": "HLV-2205"})]),
    "HLV-2205 is $52.00. Sources: parts-list#2",
]
```

The replies are what a model behaving the way the page describes would say: the right label, a
citation that exists in `evals/corpus/`, a first draft that genuinely fails the example's own
check followed by a revision that passes. A scripted reply that makes the example print an empty
result is the original defect in a new place, and so is one that contradicts what the code around
it produced. A check node that says every citation is supported, in a run where the draft cited a
section retrieval never returned, prints confidently and teaches the opposite of the page.

### An example whose calls run in parallel

`contract_review` checks six rules at once and `parallelization` answers from three sections at
once, both through a `ThreadPoolExecutor`. There is no call order to script against: whichever
thread reaches the model first takes the first reply, so an ordered sequence prints one rule's
finding under another rule's name on some runs. Those sequences are matched on the prompt
instead, and each entry is used once:

```python
SCRIPTED = [
    WhenAsked("Checklist rule payment_terms:", json.dumps({...})),
    WhenAsked("Checklist rule liability_cap:", json.dumps({...})),
]
```

A `when` has to appear in one call's prompt and in no other's. A sequence is either all ordered
or all matched, never half of each, and `tests/test_scripted_stub.py` checks both rules.

### Running past the end of the sequence

An example that grows a model call, or takes a branch the sequence was not written for, asks for
a reply that is not there. That raises `ScriptExhausted`, which names the call number, how many
replies the sequence holds, and what that call was asking for:

    routing: the scripted stub ran out on model call 3; SCRIPTED in examples/routing/__main__.py has 2 replies.
      call 3 system: You answer questions about Halvorsen appliances using only the numbered sources below. End your answer wi...
      call 3 user:   Sources: [dw300-manual#6] Maintenance and Filter Cleaning The DW-300 uses a manual fine filter at the bot...
    Add the reply that call should get to SCRIPTED, in order, and to the sequence tests/test_example_routing.py asserts against.

Not an `IndexError`, and not an empty string. Both of those read as "the example is broken" when
what happened is that the sequence fell behind the example.

### What the sequence is not for

`stub:scripted` is a `__main__` spec only. `scripts/eval_run.py` and `scripts/record_trace.py`
take `stub`, `ollama:<tag>` and `claude:<id>`, and build their own stubs; a scripted sequence is a
fixture for a demonstration, and a score or a recorded trace taken from one would be a
measurement of a string somebody typed. `build_model` in `examples/common/model.py` rejects the
spec for that reason.

## The input an example is meant to be run with

Most examples answer a question and any question will do. A few take something narrower as their
first argument: a serial number that has to be in the production log, a date, the name of a
document section. Such an example names a working one as `SAMPLE_INPUT` in its `run.py`. That
constant is the one convention for this: `scripts/record_trace.py` falls back to it when
`--question` is left out, and an example's `__main__` passes it to `parse_args` as
`default_question` so the demo command needs no argument either.

Where there is no `SAMPLE_INPUT`, `__main__.py` sets its own `DEFAULT_QUESTION`, which is the
question the scripted sequence was written for. Either way `--question` still works, and a
reader who asks something else gets the same scripted replies: the sequence is a fixture, not an
answering machine.

`DEMO_ARGV` in `__main__.py` is the rest of the demo command where one flag is needed to show the
thing (`--structured`, `--decision reject`, `--scenario injected`). It is what the tests run, so
the command that is tested is the command the page prints.

## The guard that keeps the sequence honest

`tests/test_scripted_stub.py` runs every example's own demo command against its own `SCRIPTED` and
fails when:

- an example has neither a `SCRIPTED` nor an entry in that file's `NO_SCRIPT` saying why it calls
  no model,
- the command exits nonzero, prints nothing, or runs out of replies,
- or the scripted output is identical to the echo stub's, which means the replies never reach
  what the command prints.

Each example's own `tests/test_example_<name>.py` additionally asserts that the sequence it
scripts for its end-to-end test is the same sequence `SCRIPTED` holds. A sequence kept anywhere
but beside the example drifts from it silently, and the first symptom is a page whose
Run it command demonstrates a truncated version of something else.

## Adding an example

1. Write `run.py` to the shape above, with a `LEVEL`.
2. Write `__main__.py`: the shared parser or your own, a `SCRIPTED` sequence, and printing that
   shows the reader the thing the page claims. Where the demonstration is a routing decision, a
   rejected citation, a retry or a pause, it lives in the tracer rather than in the returned text,
   so print those steps too.
3. Write `tests/test_example_<name>.py`, binding its canonical sequence to `SCRIPTED`.
4. Run `python -m unittest tests.test_scripted_stub -v` and read the output of your own command.
5. Put the command in the example's `README.md`. Pages embed that line with `<CodeFile>` rather
   than retyping it, so the README is where a command is edited, and a page that pins it by
   `start`/`end` needs `scripts/validate.py` run afterwards.
6. Add the example to `EXAMPLE_NAMES` or `NOT_SCORED` in `scripts/eval_run.py`, which has a test
   that fails until you do.
