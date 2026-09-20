# Simulator notes

- Confusion: the request says only “make it accurate,” so no numerical extraction-error threshold, exchange-rate timing, exchange-rate source, tax/tip policy, duplicate policy, or missing merchant/date policy can be selected.
- Confusion: it is unspecified whether totals, line items, or both are required, what accounting period applies, whether the organizer is shared, where the finished output should be found, and what record schema it should use.
- Skips: no values were invented for the synthetic receipts; the readable USD fixture has no supplied amounts, and the obscured EUR date/total remain unknown.
- Assumption kept explicit: uncertain records and fields require human review, as requested; this is a proposed test condition rather than a claim that the organizer already performs it.
- Assumption kept explicit: currency is preserved until an exchange-rate policy is chosen; no exchange-rate source or conversion result was supplied.
