# Design review checklist

Level 3: check a bill of materials and a netlist summary against DR-0100, Orbeck's seven-rule
design review document, one rule at a time.

Five rules need no model. DR-10 (inductor saturation margin), DR-14 (ceramic capacitor voltage
derating) and DR-20's placement thresholds are arithmetic, and code computes all three. DR-12
(semiconductor derating) has no subject on this board and DR-16 (resistor and capacitor power
derating) has no evidence in the bill of materials, which DR-0100 rule 1 records as not met; code
states both directly.

`--question` is a board revision, not a question: `B`, or a sentence naming one. A revision the
SRB-5030 does not have is refused, and a request naming none gets revision B. The revision picks
both the input ceiling (32.0 V for A and B under ECN-2608-04, 36.0 V for C) and the input
capacitor DR-14 is checked on (50 V on A and B, 63 V on C).

Two rules need reading, not arithmetic: DR-24 (thermal) and DR-30 (test access and markings). One
model pass drafts a finding for each from the rule text and the submitted evidence; a second pass
checks each drafted finding against that rule's full text and rejects one whose reasoning is not
actually what the rule says, even when its status happens to be right. A rejected finding is
recorded as not met, not silently corrected, so a person redoes it.

Run it:

```
python -m examples.bench_design_review_checklist --model stub:scripted
```

All seven rules judged, five by code and two by the model, and one of those two rejected by the
second pass for citing the thermal shutdown as the reason the design passes, which is the
opposite of what DR-24 says.

Every step is `decided_by: "code"`: both model calls always happen, and code always merges their
output the same way. This example proposes no instrument command and touches no electronics; it
checks documents against other documents. The board's pass or fail decision stays a person's.
