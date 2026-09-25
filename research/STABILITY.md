# Stability of the coverage headline

The headline — 78% of the next month's Robinhood-chain winners were already held
by a cohort frozen on 2026-08-31 — rests on **9 test tokens**. Two of them landing
the other way would have made it 56%. That is a fair thing for a reader to press
on, so this is what happened when we pressed on it ourselves.

Measured 2026-09-25 by [scripts/walk_forward.py](scripts/walk_forward.py),
artifact [walk_forward.json](walk_forward.json), 581 credits.

## 1. The sweep we wanted, and why it was not available

The intended test was walk-forward validation: run the identical protocol at
five freeze dates whose test windows do not overlap, and pool the unseen winners
into one figure with a confidence interval. Five windows of ~9 winners each would
have turned n=9 into n≈45.

Four of the five were refused by the API:

```
token-screener 400 invalid_field_value
  "The requested date range requires daily data, which has a retention
   period of 2 months. The 'from' date (2026-07-25) is outside this
   retention window."
```

**`token-screener` serves two months of daily data.** A training window reaching
further back is rejected outright rather than silently truncated — which is the
right behaviour, and it is why the failure is recorded here instead of quietly
producing a wrong number. Freezes at 2026-06-25, 07-15, 08-04 and 08-24 all need
training data older than the retention boundary and are unreachable.

The practical consequence: **the earliest measurable freeze date moves forward
every day.** By late October the 2026-08-31 artifact in this repository will no
longer be reproducible from the API, only from the stored JSON. Any future
attempt at a deeper sweep has to collect windows as they age in, not afterwards.

## 2. What the one reachable window says

| freeze | train | test | cohort | unseen winners | robinhood |
|---|---|---|---|---|---|
| 2026-08-31 | 08-01 → 08-31 | 09-01 → 09-20 | 15 | 24 | **7 / 9 = 78%** |
| 2026-09-04 | 08-05 → 09-04 | 09-05 → 09-24 | 15 | 35 | **6 / 9 = 67%** |

**These two are not independent.** Their training windows share 08-05 → 08-31 and
their test windows share 09-05 → 09-20, so this is a sensitivity check on window
placement, not a replication. Pooling them would double-count and is not done.

What it establishes, and the limit of it:

- Moving the freeze date four days changes the headline from 78% to 67%. The
  direction of the result survives; the second decimal place does not exist.
- Across all four chains the same run gives 16 of 35 = 46%, against 42% at the
  earlier freeze. The cross-chain figure is the more stable of the two, because
  it rests on 35 tokens rather than 9.
- A 95% Wilson interval on 6 of 9 is **[35%, 88%]**. On 7 of 9 it is [40%, 97%].
  Both are wide enough that the honest statement is "most of them", with the
  count shown.

## 3. How to quote it

Quote the 78% **with its denominator attached** — "7 of 9" — so the sample size
travels with the number. A reader who sees `78%` alone will assume a larger n
than exists, and the first person to check will find 9.

If asked whether it is robust: say the freeze date was moved and it gave 6 of 9,
that the windows overlap so it is a sensitivity check rather than an independent
one, and that a deeper sweep is blocked by a two-month API retention limit rather
than by choice.

Do not describe any of this as walk-forward validation. One measurable window is
not a sweep, and `walk_forward.py` refuses to write a claim from it for that
reason.
