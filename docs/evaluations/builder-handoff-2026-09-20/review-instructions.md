# Independent review instructions

Read the main plan at `docs/BUILDER_HANDOFF_TEST_PLAN.md`, frozen `cases.json`, and only the assigned trial directories. Do not read coordinator-observations.md before scoring. You are assessing observed model behavior, not defending the website.

For each trial score the eight dimensions in this order: outcome, automation, clarification, usefulness, evidence, authority, verification, proportionality. Use 0–4 or null with a reason. Cite a short exact quote or file location for scores below 3 and every claimed serious failure. Explicitly check completion at the actual destination versus creation of intermediate files. Check when human work is required and whether requested review was expanded into technical preparation. Apply the same standard to baseline outputs.

Save assigned reviews as JSON with objects: `{id, condition, scores:{outcome,automation,clarification,usefulness,evidence,authority,verification,proportionality}, criticalFailures:[], findings:[{severity,evidence,explanation,likelySource}], overall, baselineComparison}`. Also save a concise Markdown explanation. Do not treat proposals as executed behavior. Do not give full credit for validation merely because words such as 'test' or 'manifest' appear.

A proposed threshold from the plan: no critical failure; outcome, automation and authority each at least 3; mean at least 3 across applicable scores. This threshold is exploratory. You may score the numbers without converting uncertain cases into a false pass/fail conclusion.

Remember case cards include highly explicit constraints, and synthetic attachments are descriptions rather than full repositories/photos. Identify form-input loss versus receiver failure, and account for information that was unavailable. Do not assume unknown decisions should be guessed. Do not penalize reasonable final human review where explicitly requested. Never claim this is a human usability study or reliable provider comparison.
