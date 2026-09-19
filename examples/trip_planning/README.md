# Trip planning, with bookings held for approval

Level 5: a loop with three read-only tools, `search_routes`, `search_stays` and `opening_hours`,
called as many times as the trip needs. A fourth tool, `book`, is different: the loop never runs
it. A `book` call stops the run and returns a `PendingBooking` checkpoint holding the exact call,
its price in cents and its cancellation terms. Nothing is booked until a separate call, `approve`,
runs it, and only after a person decides.

`approve` binds the approval to the exact call: it recomputes a fingerprint of the call about to
run and refuses one whose price, date or reference changed since approval.

Routes, stays and opening hours are invented and live in `run.py` as module constants.

Run it:

```
python -m examples.trip_planning --model stub:scripted
```

The run searches, then reaches a `book` call, and stops there: what prints is the held call's
fare and its cancellation terms, and nothing is bought. Add `--decision approve` to run the held
booking in the same command.

`--model stub` never calls a tool at all, so the same command prints a placeholder answer and
never reaches the checkpoint.

What this does not do: no real airline, hotel or booking site, no payment, no calendar or email
sent anywhere, and no second booking in one run, since `book` always stops the loop.
