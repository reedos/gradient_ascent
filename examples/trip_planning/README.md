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
python -m examples.trip_planning --model stub --question "Plan a trip from Wrenfield to Aldercliff."
```

The interactive stub never calls a tool, so this prints a placeholder answer rather than pausing
for a booking; see `tests/test_example_trip_planning.py` for the scripted runs that reach `book`.

What this does not do: no real airline, hotel or booking site, no payment, no calendar or email
sent anywhere, and no second booking in one run, since `book` always stops the loop.
