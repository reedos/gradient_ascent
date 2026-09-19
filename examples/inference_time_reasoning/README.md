# Inference-time reasoning: self-consistency

Level 1: self-consistency by majority vote. The same numeric question is sent to the model five
times (independent calls, not a conversation), each reply is asked to end with a line the code
can parse (`Answer: <number>`), and the code returns whichever number the largest share of the
five samples agree on.

The sample count and the vote are both fixed, so every step is `decided_by: "code"`: the model
only ever chooses what one sample says, never what the run does with the set of them.

Run it:

```
python -m examples.inference_time_reasoning --model stub --question "What is the total price to replace the heating elements on both a DW-300 and a DW-480?"
```
