# Credit Budget — measured, not estimated

Every unit cost below was **observed** during Stage 1 (81 credits spent). All totals carry a
**+30% buffer** for retries, pagination overruns and exploration.

## Measured unit costs

| Operation | Credits | Notes |
|---|---:|---|
| `search/general` (token query) | **0** | ticker → contract. Free. (500 for *address* queries — never do this) |
| Rejected requests (422/timeout) | **0** | quoted but not billed → schema discovery is free |
| `tgm/token-ohlcv` | 1 | often unnecessary — price is derivable from balances for free |
| `profiler/address/historical-balances` | 1 | **the workhorse**: full daily per-token series, ≤500 rows |
| `profiler/dex-trades` | 1 | per wallet per chain |
| `tgm/who-bought-sold` | 1 | per token per window |
| `tgm/pnl-leaderboard` | 5 | per coin → 100 ranked traders |

### The page-cap economics that drive everything
Measured: 32 wallets over 24 days returned 30–500 rows, median ~290 (~12 tokens/day).
8 of 32 hit the 500 cap. So conservatively **one call ≈ 20 days of history** for an active wallet.

- 1 month of history ≈ **1.5 calls/wallet**
- 3 months ≈ **4.5 calls/wallet**
- 6 months ≈ **9 calls/wallet**
- A rolling 7-day live refresh ≈ **1 call/wallet** (well under the cap)

### Two multipliers to remember
- **Chains multiply everything.** `historical-balances` takes ONE chain. Solana + 3 EVM chains = 4×.
- **The 5-day signal horizon means daily refresh is waste.** Refreshing every 2–3 days costs
  half to a third as much and loses nothing, because the effect only appears at k=5.

---

## Costs by goal

### A. Buildathon demo — ~350 credits
Enough to show a validated, working product on stage.

| Item | Calc | Credits |
|---|---|---:|
| Out-of-sample validation (removes the circularity) | 6 coins × 5 + 60 wallets + baseline | 125 |
| Demo corpus (60 wallets, 1 month, Solana) | 60 × 1.5 + 5 coins × 5 | 115 |
| Contingency | +30% | 72 |
| | | **~350** |

**One month of Pro ($49–69) covers this ~6× over.**

### B. Real product, MVP — ~800 one-time, then ~1,400/month
Solana only, 100-wallet cohort, 3 months of history, refresh every 3 days.

| Item | Calc | Credits |
|---|---|---:|
| Cohort construction | 20 coins × 5 | 100 |
| Backfill 3 months | 100 wallets × 4.5 | 450 |
| Validation + baselines | — | 50 |
| Contingency | +30% | 180 |
| **One-time total** | | **~780** |
| Live: 100 wallets × 10 refreshes/mo | + cohort refresh 50 | 1,050 |
| Contingency | +30% | 315 |
| **Monthly total** | | **~1,400** |

**This fits inside a single Pro plan (2,000/month) with ~600 to spare.** That is the key
finding: a working 100-wallet product costs $49–69/month in API, nothing more.

### C. Scaled product — ~2,500 one-time, then ~5,000/month
250-wallet cohort, 6 months of history, refresh every 2 days, still Solana-only.

| Item | Calc | Credits |
|---|---|---:|
| Cohort construction | 40 coins × 5 | 200 |
| Backfill 6 months | 250 × 9 | 2,250 |
| Contingency | +30% | 735 |
| **One-time total** | | **~3,200** |
| Live: 250 wallets × 15 refreshes/mo | + cohort refresh | 3,850 |
| Contingency | +30% | 1,155 |
| **Monthly total** | | **~5,000** |

Needs Pro (2,000) **plus ~3,000 purchased credits/month**.

### D. Multi-chain
Multiply the backfill and live figures by the number of chains tracked. Solana + BNB + Base +
Robinhood ≈ **4×**. Note BNB launchpad tokens had poor trade enrichment (see FINDINGS.md) —
balances still work there, but verify before committing budget to a chain.

---

## Recommended path

| Step | Spend | Why |
|---|---|---|
| 1. Top up to Pro now | $49–69 → 2,000 credits | You have 7 left; everything is blocked |
| 2. Out-of-sample validation | ~125 | Removes the circularity — the one thing a judge will attack |
| 3. Demo corpus + chart | ~225 | Buildathon deliverable |
| 4. *Then* decide on scale | — | You'll still have ~1,600 of month 1 unspent |

**Total to a validated, demo-ready product: ~350 credits = one month of Pro.**
Month 2 onward, an MVP runs at ~1,400/month — still inside Pro.

## Open question for Nansen
Flexi-credit pricing at volume is still unpublished. It only matters for path C (scaled),
where you'd need ~3,000/month beyond the plan allowance. Worth asking before committing to
250 wallets or multi-chain.

---

## What the live daily job actually costs — measured 2026-09-28

The estimates above were written before anything shipped. These are the real numbers from
the job that has been running unattended since 22 September.

| Stage | Calls | Credits |
|---|---:|---:|
| `historical-balances` — cohort refresh | ~1,100 wallet-chain windows | ~2,200 |
| `token-ohlcv` — market caps for drawn tokens | 80 | 80 |
| **Total per run** | | **~2,280** |

Before adaptive polling the same run cost **2,960**.

### The three levers, and which ones actually pay

**Adaptive polling — real, 23%.** `historical-balances` returns a date range rather than a
snapshot, which is the property the whole thing rests on: a day skipped today is recovered in
full by widening tomorrow's window, so polling a still wallet less often loses nothing. On the
live cohort, 405 of 739 wallets had changed a holding within a day, and **162 had not moved in
over a week**. Cadence is 1 / 2 / 3 days by how long a wallet has been still, each wallet's
window is widened by exactly its own cadence, and the phase offset is a CRC of the address so
it is stable between processes — `hash()` is seeded per run and would re-phase every wallet
nightly, which would let one fall outside the window its cadence widened for.

The cost is freshness: a dormant wallet that wakes is invisible for up to its cadence. That is
why the slowest is 3 days and not a fortnight.

**Narrower ohlcv windows — no credits, much less time.** Billed per call, not per bar, so
asking for 141 days or 3 costs the same 1 credit. But the full window re-read ~11,000
immutable bars a night and was most of a ~55-minute run.

**Bigger pages — already taken.** `per_page` accepts 1,000 for the same cost as 100. The
remaining risk is the page *cap*: running out of pages before the API runs out of rows
truncates silently, so `fetch.truncated` records every window that hit it.

### What does not work
- Dropping wallets by capital. Edges are counted in shared wallets, not dollars; the 439-wallet
  tail holds 11% of the capital and far more than 11% of the rotations. Cutting it took daily
  edge counts from ~150 to 20.
- Reaching further back for more validation windows. `token-screener` retains two months of
  daily data and refuses older ranges outright (see [STABILITY.md](STABILITY.md)).
