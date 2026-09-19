# Test data by conversation

Level 4. `examples/bench_limits_without_a_model` already charts limits, first-pass yield and Cpk
from the production log. This example answers the question that dashboard does not: the model
writes one short Python snippet, and a sandbox, never the model, runs it against the August 31
retest export, the August 27 soak log or the September characterization sweep.

Before any table is handed to anything, code range-checks its volts column against the widest
node this board has anywhere (0 to 40 V) and corrects it when the raw numbers turn out to be
millivolts under a header that says volts. That check runs every time, on every table, whether or
not the model ever calls the tool, and it says what it found either way.

Run it:

```
python -m examples.bench_test_data_by_conversation --model stub --question "Do the retested boards actually pass?"
python -m examples.bench_test_data_by_conversation --model stub --question "Did any soak unit fail to settle?"
python -m examples.bench_test_data_by_conversation --model stub --question "Is any block of the sweep impossible?"
```

The sandbox in `run_snippet` is an allow-listed grammar, checked node by node before `exec` ever
sees it: the same shape `examples/code_execution` uses for one arithmetic expression, extended to
short table-analysis scripts (no import, no attribute access, no `while`, loops nested no more
than two deep). See the recipe page for what that does and does not protect against.
