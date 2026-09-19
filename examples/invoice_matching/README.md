# Invoice matching

Level 3: one model call reads an invoice's text into fixed fields (supplier, purchase order
number, invoice number, currency, line items, stated total). Everything after that is code: a
lookup against four invented purchase orders, and a three-way match against what the receiving
dock logged, quantity invoiced against quantity received, unit price against the ordered price,
and the invoice's own stated total recomputed from its own lines. Anything that does not
reconcile to the cent pauses for a person instead of posting.

Run it:

```
python -m examples.invoice_matching --model stub:scripted
```

The purchase order found, the three-way comparison clean to the cent, and $756.00 posted to a
named supplier. Pass `--decision approve` or `--decision reject` to resume a match that paused.

`--model stub` never returns a valid extraction, so the same run pauses with `extraction_failed`
and the JSON error that caused it, which is what an unreadable invoice looks like here.

What it does not do: read a PDF or a scan. `run` takes the invoice's own text, already pulled from
whatever file the supplier sent; turning a PDF into text is a separate, ordinary step this recipe
does not model. It also never issues a payment: posting here means the match cleared, not that
money moved.

Money is integer cents throughout, and every supplier, part number and purchase order is invented.
