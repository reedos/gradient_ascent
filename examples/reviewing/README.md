# Reviewing: one review surface

Given a drafted answer (its text and the citations it names) and the synthetic corpus, report
which figures the answer states are carried by no section it cites, and which citations carry
none of them.

This is a presence check, not a truth check: it says a number appears in the text the answer
points at, not that the section supports the claim, that the right sources were chosen, or that
the answer is complete. A person still does all of that. Figures are compared as values, so
`$1,200` and `1200` are one figure and `52` is not a match for `1152`; identifiers such as
`HLV-2205`, `DW300` and `dw300-manual#3` state no quantity and are ignored. Units are dropped and
a date written in prose is read as separate numbers; both are pinned as limits in
`tests/test_example_reviewing.py`.

No model is called; every step is `decided_by: "code"`.

Run it:

```
python -m examples.reviewing --scenario clean
python -m examples.reviewing --scenario mismatch
python -m examples.reviewing --scenario missing
```

Each run prints the figures the answer states, the citations it names, whether the check came back
clean, and the specific thing to look at where it did not.

`clean` cites only a section carrying the figure it states. `mismatch` adds a citation that
carries none. `missing` states a figure nothing carries and cites a section that does not exist.
