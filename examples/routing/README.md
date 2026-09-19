# Routing

Level 3: one model call classifies the question as `lookup`, `numeric` or `unclear`, and the
code reads that word and dispatches to one of three fixed handlers. Only the lookup handler calls
the model a second time; the numeric handler answers from an exact part-number match with no
model call at all, and the fallback answers nothing on purpose.

The classify step is not a level-4 tool choice: the model answers a plain classification prompt
with one word, and the code parses that word and looks it up in a fixed dict, the way `rag.run`
parses citations out of free text. The model never reaches into the set of handlers itself.

Run it:

```
python -m examples.routing --model stub:scripted
```

The label the classifier returned, the route the code picked from that label, and the cited answer
the route produced: three lines, one per decision.

Every step is `decided_by: "code"`: the classification call, the label parse, and the dispatch
are all decisions the code makes, even though the label's *value* comes from the model.
