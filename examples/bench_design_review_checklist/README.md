# Design review checklist

Level 3: check a bill of materials and a netlist summary against DR-0100, Orbeck's seven-rule
design review document, one rule at a time.

Five rules are arithmetic and code computes all of them: DR-10 (inductor saturation margin),
DR-12 and DR-14 (semiconductor and ceramic-capacitor voltage derating), DR-16 (resistor and
capacitor power derating) and DR-20's placement thresholds. No model reads any of those.

Two rules need reading, not arithmetic: DR-24 (thermal) and DR-30 (test access and markings). One
model pass drafts a finding for each from the rule text and the submitted evidence; a second pass
checks each drafted finding against that rule's full text and rejects one whose reasoning is not
actually what the rule says, even when its status happens to be right. A rejected finding is
recorded as not met, not silently corrected, so a person redoes it.

Run it:

```
python -m examples.bench_design_review_checklist --model stub --question B
```

Every step is `decided_by: "code"`: both model calls always happen, and code always merges their
output the same way. This example proposes no instrument command and touches no electronics; it
checks documents against other documents. The board's pass or fail decision stays a person's.
