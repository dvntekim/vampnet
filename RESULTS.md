# Stage 1 — Hypothesis Validation. RESULT: SUPPORTED (with caveats)

**Credits: 81 used, 7 remaining.** Cohort: 32 wallets (top combined PnL on STONK + USELESS,
Solana). Window 2026-08-25 → 2026-09-17. 281 tokens observed, 24 daily snapshots.

## Method that worked

```
1. SOURCE    tgm/pnl-leaderboard            5 cr/coin    real traders, bot-immune (PnL-ranked)
2. COHORT    pooled top-PnL across winners  0 cr         32 wallets
3. EXPOSURE  profiler/address/historical-   1 cr/wallet  DAILY per-token portfolio series
             balances                                    -> token_amount AND value_usd
4. FLOW      Δ(token_amount) × price        0 cr         strips price drift from intent
5. PRICE     value_usd / token_amount       0 cr         free price series for ALL 281 tokens
```

**Key mechanic:** balances, not swaps. Immune to launchpad routing, stablecoin parking,
intermediate losing trades, and non-sequential sizing — every failure mode that killed the
earlier swap-chain approach on BNB.

**Key correction:** attention must be measured as Δ(token_amount) × price, NOT Δ(value_usd).
Portfolio *share* conflates buying with price movement — STONK's share rose 58%→69% while its
dollar value collapsed, purely because the rest of the portfolio shrank faster.

## The rotation chain is real and visible

Cohort USD exposure, by day:

**ANSEM/CARDS (Aug 25-28) → USELESS (Aug 27-Sep 4) → STONK (Sep 5-11) → ZCAT/CATE (Sep 13-14)**

The handoff is explicit in net flow:
- STONK sold: −$1.78M (Sep 9), −$3.13M (Sep 11), −$1.50M (Sep 12)
- ZCAT bought: **+$1,500,331 (Sep 13)**
- CATE bought: **+$359,833 (Sep 14)**

Capital left the peaked winner and landed in the next names with a **1–2 day lag**.

## The predictive test

**Naive test FAILED.** Token-day flow vs forward return: corr +0.05 to +0.14 against SE ≈0.056
at n≈314. Noise. The reverse test (does the cohort chase price?) was equally flat: +0.080.

**Event study SUCCEEDED.** The signal is entirely in *size*:

| Flow bucket | +1d | +2d | +3d | **+5d** | n |
|---|---:|---:|---:|---:|---:|
| All buys | −0.0% | −2.3% | −4.5% | −4.4% | 244 |
| All sells | −3.8% | −8.2% | −3.9% | −5.9% | 87 |
| Buys > $50k | 1.7% | 2.8% | 2.5% | **+17.0%** | 44 |
| **Buys > $250k** | −1.7% | 5.5% | 2.5% | **+67.4%** | 13 |
| **Sells > $250k** | −6.5% | −14.2% | −20.1% | **−24.2%** | 9 |

Baseline median 3d return, all token-days: **−4.2%**.
**Spread between large buys and large sells at 5 days: ~92 percentage points.**

Notable events: STONK +$518K (Sep 5) → +505% in 5d. USELESS +$560K (Aug 31) → +261%.
Counter-example: STONK +$1.59M (Sep 13) → −37% — the cohort bought a dead-cat bounce.

## Product implications

1. **Size-gate everything.** Undifferentiated flow is noise. Only conviction-sized flow
   (>$50k, ideally >$250k) carries signal. Edges below threshold should not be drawn.
2. **The exit signal is the stronger product.** Large sells → −24.2% at 5d is the
   "attention has faded" alarm. It is also easier to sell than an entry signal, because the
   user can verify it against a position they already hold.
3. **5 days is the horizon.** k=1..3 shows nothing; the effect appears at k=5.
4. **Wallet convergence is NOT the signal** (established earlier): MONEROCHAN had the most
   independent buyers (5) and the worst outcome (−69%). Weight edges by USD, never by count.

## What is NOT yet established

- **n=13 and n=9** in the decisive buckets. Suggestive, not proven.
- **One regime, 24 days, one chain.** No evidence this generalises.
- **Cohort is self-selected** from winners of the two coins being studied — a circularity
  that inflates results. A cohort chosen on earlier coins and tested on later ones would fix it.
- **8 of 32 wallets truncated** at the 500-row page cap; the most active are under-counted.
- **Only 3 of 100 wallets recur** across STONK and USELESS top-100s. The "same smart money
  rotates between winners" premise is weaker than assumed — largely different people win
  each coin.

## Next test that would settle it

Pick the cohort from coins that peaked **before** the test window, then measure their flow
against outcomes in a **later, unseen** window. That removes the circularity and turns this
from a description into a prediction. Estimated ~150-200 credits.

---

# FINAL VERDICT (2026-09-18) — predictive hypothesis FALSIFIED, descriptive product CONFIRMED

Time-boxed research attempt complete. ~285 credits. **59,722 remaining.**

## Four independent tests. All null.

| # | Test | Cohort | Result |
|---|---|---|---|
| 1 | Coin holdout | 32 Solana wallets, top-PnL | buys >$250k: **−8.2%** @5d vs −6.5% baseline |
| 2 | Alternative formulations (5) | same | every variant within ±1.6pp of baseline |
| 3 | **Cross-chain recurrence cohort** | 22 wallets winning 2+ coins, 5 EVM chains | all buckets ≈0% vs −2.0% baseline, n=1,150 events |
| 4 | Chain-level aggregation | same | inflow vs outflow spread: −0.4pp / −0.3pp / +0.5pp |

Verified not to be a data artifact: 0% of forward returns were exactly zero; nonzero median −2.0%.

**The Stage 1 "+67.4%" was entirely circular** — driven by STONK and USELESS, the two coins the
cohort was selected for winning. On held-out coins the edge vanishes completely.

Also falsified: **crowding is mildly bearish.** ≥3 cohort wallets entering → −12.5% @5d
(−5.5pp vs baseline). Consistent with MONEROCHAN (5 wallets, −69%). More smart money visibly
in a name means the move is late, not early.

## What IS confirmed, and is the product

**Capital migration is real, large, and measurable.** The 22 cross-coin recurring winners
(selected from 676 distinct winners across 7 EVM coins — a 3.2% recurrence rate) moved in
formation across chains:

| | 2026-08-01 | 2026-09-12 |
|---|---:|---:|
| BNB | **64.9%** | 18.4% |
| Robinhood | 21.2% | **77.0%** |
| Base | 0.3% | 2.9% |

Single largest event: **−$6,032,816** out of BNB in the first week of September.

One wallet — `0x554a02baa3074062c4262c0b998db596dd6ab9e2` — won on **four** separate coins
across **three chains** (MARSCOIN/BNB, BASECAT/Base, BONER + MEME/Robinhood). That wallet is
the single best advertisement for why multi-chain tracking matters.

Also observed (Solana, Stage 1): **ANSEM/CARDS → USELESS → STONK → ZCAT/CATE**, with the
handoff explicit in drift-removed flow.

## Honest product positioning

**Ship:** the most accurate map of where proven winners' capital is migrating — across chains
and tokens — that anyone has built. Nobody else can make it: it needs Nansen's PnL leaderboards
to identify real winners (bot-immune), balance history to track exposure (routing-immune), and
multi-chain address matching to follow them.

**Do not claim:** that it predicts which coin pumps next. We tested that four ways and it does
not. Any entry making that claim is one motivated judge away from being falsified on stage.

**The negative result is an asset.** Very few buildathon entries will have tested their own
thesis hard enough to break it. "We built the instrument, ran four falsification tests, and
ship only what survived" is a more credible story than an untested claim.

## Methodological notes for the build

- Measure flow as **Δ(token_amount) × price**, never Δ(value_usd) — share conflates buying with drift.
- **PnL leaderboard** for wallet selection (bot-immune: churner PnL ≈ 0). `who-bought-sold`
  is volume-ranked and 80% churners — unusable for sourcing.
- **Balances, not swaps.** Immune to launchpad routing, stablecoin parking, non-sequential sizing.
- Price series derive free from `value_usd / token_amount` — no OHLCV calls needed.
- EVM chains share an address space; Solana does not. Cross-chain wallet identity is free on EVM.
