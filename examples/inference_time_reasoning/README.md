# Inference-time reasoning: self-consistency

Level 1: self-consistency by majority vote. The same numeric question is sent to the model five
times (independent calls, not a conversation), each reply is asked to end with a line the code
can parse (`Answer: <number>`), and the code returns whichever number the largest share of the
five samples agree on.

The sample count and the vote are both fixed, so every step is `decided_by: "code"`: the model
only ever chooses what one sample says, never what the run does with the set of them.

Run it:

```
python -m examples.inference_time_reasoning --model stub:scripted
```

All five samples printed, three of them agreeing on 79.50 and two landing elsewhere, then the
tally and the majority answer. Any one sample could have been either of the wrong two.
