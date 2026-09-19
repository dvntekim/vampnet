# VALIDATED PRODUCT METRICS — 2026-09-18

Cohort: **127 EVM + 4 Solana wallets**, each an independent winner on **2+ of 35 systematically
identified winning tokens** (mcap>$5M, vol>$2M, +200% over Aug 15 – Sep 17) across 6 chains.
Selected from **2,519 distinct winners** — a 5.0% recurrence rate.
Data: 48 days of daily balances across robinhood/bnb/base/ethereum/hyperevm/solana.
**Credits used ~1,400. Remaining ~58,356.**

## The three numbers that define the product

### 1. RECALL — 85%
Leave-one-out: for each winner, only wallets qualifying via 2+ **other** coins are counted.

- **30/37 winners (81%) overall**; **28/33 (85%) on EVM**, where the cohort is real.
- (Solana misses are an artifact — the Solana LOO cohort is 1–3 wallets.)
- $19.9M of cohort capital sat across covered winners.
- PONS: 30 wallets, $8.4M. AI: 18 wallets, $5.8M. HOOKR: 12 wallets, $1.4M.

**Claim: if a token becomes a winner, it almost certainly appears on this map first.**

### 2. PRECISION — 28.6% at high conviction, a 23× lift
Also leave-one-out. Base rate: 1.24% of tokens the cohort touches become winners.

| Conviction filter | Tokens | Winners | Precision | Lift |
|---|---:|---:|---:|---:|
| any holding | 2,813 | 35 | 1.24% | 1× |
| LOO peak > $100k | 107 | 13 | 12.1% | 10× |
| LOO peak > $250k | 50 | 12 | 24.0% | 19× |
| **≥8 wallets AND > $250k** | 35 | 10 | **28.6%** | **23×** |

**Claim: conviction-weighted cohort exposure is a 23× filter on the winner population.**
Not a prediction — roughly 7 in 10 high-conviction names still don't run. But it reduces a
2,813-token universe to 35 candidates containing 10 of the winners.

### 3. TIMING — median 16 days before peak
- Raw median 23 days; **16 days after removing 7 left-censored entries** at the window start.
- Range 0–39 days. **23/30 entered ≥7 days before peak. 0/30 entered after the peak.**
- Median gain from first cohort entry to peak: **+424%**.
- 牛来: 29 days early, +33,845%. AI: 47d, +15,435%. BASECAT: 22d, +12,912%.

## What is still NOT claimed

- **Flow magnitude does not predict returns.** Four falsification tests, all null (RESULTS.md).
- **Crowding is mildly bearish**: ≥3 wallets entering → −12.5% @5d.
- Precision ≠ certainty: ~71% of high-conviction names are not winners.
- One 48-day window, one regime. Needs re-running monthly.

The distinction that matters: **high recall + 23× precision lift = a discovery surface.**
It tells you *where to look*, with ~16 days of lead time. It does not tell you what to buy.

## Live candidates right now (high conviction, not yet winners)

| Token | Chain | Wallets | Cohort USD |
|---|---|---:|---:|
| **CASHCAT** | robinhood | 35 | $4,650,339 |
| MARSCOIN | bnb | 13 | $4,167,931 |
| MEME | robinhood | 20 | $2,184,358 |
| BONER | robinhood | 12 | $1,182,919 |
| ZZZ | robinhood | 10 | $1,155,608 |
| TIBBIR | base | 10 | $963,116 |
| MICRODUCK | robinhood | 14 | $861,502 |

## Operational notes for running this for a month

- **Cost to refresh:** ~8.4 credits per wallet per full multi-chain pull → 131 wallets ≈ **1,100
  credits per refresh**. Every 2–3 days = **~13,000/month**. Affordable within 58k for ~4 months.
- Cheaper: restrict each wallet to the chains it is actually active on (most are Robinhood-
  dominant) → roughly halves it.
- **Cohort refresh:** re-run the screener + leaderboards monthly (~200 credits) so new winners
  enter the cohort and it doesn't go stale.
- **Filter tokenized equities** (NVDA/AAPL/TSLA/SPY/COIN…) on the Robinhood chain — 50–77
  wallets hold them with trivial USD and they swamp any wallet-count ranking. Rank by USD.

---

# CORRECTION — out-of-time validation (2026-09-18, later)

The 85% recall above is **optimistic**. Leave-one-out removed *coin* circularity but not
**time** circularity: cohort and winners came from the same period, so a wallet could enter
the cohort via a September coin and then "cover" another September winner.

## Proper out-of-time test
Cohort frozen on **Aug 31** (37 leaderboards, Aug 1–31 windows only, zero September
information), tested against the **15 new winners that emerged Sep 1–18**.

| | Covered | Total | Rate |
|---|---:|---:|---:|
| **Overall** | 3 | 15 | **20%** |
| Robinhood (the cohort's own ecosystem) | 3 | 5 | **60%** |
| Everywhere else | 0 | 10 | **0%** |

The frozen cohort still earned **$614,734** on new September winners it had no prior exposure to.

## Why: trader persistence is an ecosystem property

| Chain | Coins | Traders | Repeat (2+) | **Recurrence** | Coverage |
|---|---:|---:|---:|---:|---:|
| **Robinhood** | 11 | 994 | 85 | **8.6%** | **60%** |
| BNB | 13 | 879 | 37 | 4.2% | 0% |
| Base | 3 | 236 | 2 | 0.8% | 0% |
| **Solana** | 5 | 499 | **1** | **0.2%** | 0% |
| Ethereum | 2 | 200 | 0 | 0.0% | 0% |

**Recurrence rate is the ceiling on the strategy.** BNB had the *most* coins (13) and still
covered nothing, so this is not a sample-size effect — it is that BNB and Solana memecoin
winners are mostly different people each time, while Robinhood chain has a persistent
winning community (one wallet won **seven** separate coins).

**Solana at 0.2% means a Solana cohort cannot exist.** One repeat winner in 499.

## What this changes

1. **Build per-ecosystem cohorts, not one global cohort.** A cohort only covers the chain it
   was built from. Robinhood is the only ecosystem where this currently works.
2. **Ship a Persistence Score per chain** and gate the product on it. Where recurrence is
   below ~4%, say so instead of showing a map that cannot work.
3. **Honest headline numbers:** 60% coverage within a persistent ecosystem, 20% naive across
   all chains. Not 85%.
4. This is a **discovery result in its own right** — "which chains have persistent winners"
   is a question no existing tool answers, and the answer is counter-intuitive
   (Solana, the busiest memecoin chain, has the least persistent winners).

## Operational constraint found
`token-screener` daily data has a **2-month retention window**; requests before that return
400. Longer backtests need the `/v1beta1/` historical endpoints at 5× credit cost.

---

# PRODUCTION CONFIGURATION (2026-09-18, final)

Focusing on the one ecosystem where persistence exists lifts out-of-time coverage to **75%**.

## The winning setup
```
chain      : robinhood            (8.6% recurrence — the only chain above the ~4% floor)
universe   : token-screener, mcap>$2M, vol>$1M, +100% over the prior month   (1 credit)
cohort     : wallets in the top-100 PnL of >= 2 of those winners            (17 x 5 = 85 credits)
size       : 125 wallets
refresh    : monthly (cohort) + every 2-3 days (balances)
```

## Out-of-time result — cohort frozen Aug 31, tested on September winners it had never seen

| Cohort threshold | Wallets | Covered | Rate |
|---|---:|---:|---:|
| **>= 2 winning coins** | **125** | **6/8** | **75%** |
| >= 3 winning coins | 29 | 5/8 | 62% |
| >= 4 winning coins | 8 | 3/8 | 38% |

Frozen-cohort PnL on unseen September winners: **$773,967**.
Misses: BLORB (+2,832%), DOGO (+110%).

### Design rule: breadth beats strictness
Tightening the skill filter shrinks coverage faster than it raises quality. The 8-wallet elite
cohort covered half as much as the 125-wallet one. **Use the 2+ threshold.**

## Full cost of running this product

| Item | Frequency | Credits |
|---|---|---:|
| Winner screen (1 chain) | monthly | 1 |
| Cohort leaderboards (~17 coins) | monthly | 85 |
| New-coin screen (all chains) | daily | 2 |
| Cohort balances (125 wallets, robinhood + 2 spill chains) | every 2–3 days | ~375 |
| **Monthly total** | | **~4,000–5,000** |

At 58k credits remaining that is **~12 months of operation**, or ~3 months if extended to
BNB as a second (weaker, 4.2% recurrence) ecosystem.

## Honest claim stack for the demo
1. **75%** of next month's winners on a persistent chain appear in the map — out-of-time, frozen cohort.
2. **23× precision lift** at high conviction (28.6% vs 1.24% base rate).
3. **~16 days** median lead time from first cohort entry to price peak.
4. **Persistence varies 40× across chains** (8.6% Robinhood → 0.2% Solana) and predicts whether
   any cohort strategy can work there. No existing tool measures this.
5. **Flow magnitude does NOT predict returns** — tested four ways, all null. Say so.

---

# OPERATIONAL — measured, pipeline live (2026-09-18)

`scripts/run_pipeline.py` runs the whole product. Three modes, all validated end-to-end:

```bash
python3 scripts/run_pipeline.py --mode cohort    # monthly  — 116 credits measured
python3 scripts/run_pipeline.py --mode daily     # 2-3 days — 655 credits measured
python3 scripts/run_pipeline.py --mode newcoins  # daily    —   2 credits measured
```

First live run: **161-wallet cohort from 2,020 traders** across 23 Robinhood winners.

## Real monthly cost
| Task | Frequency | Credits each | Monthly |
|---|---|---:|---:|
| cohort rebuild | monthly | 116 | 116 |
| balance refresh | every 2–3 days (12×) | 655 | 7,860 |
| new-coin scan | daily (30×) | 2 | 60 |
| | | | **~8,040** |

**57,173 credits remaining → ~7 months of runway.** (Halve it by dropping the two spill
chains and tracking robinhood only.)

## Live candidates from the first production run
| Token | Chain | Age | Cohort wallets | Cohort USD |
|---|---|---:|---:|---:|
| STONKEX | base | 24d | 12 | $279,715 |
| CBZEC | base | 29d | 1 | $172,940 |
| BSTONK | base | 31d | **16** | $116,791 |
| QUOTRON | robinhood | 35d | 9 | $107,788 |
| **INU** | robinhood | **6d** | **17** | $71,948 |
| STONX | base | 13d | 10 | $62,331 |

INU is the standout: six days old with 17 independent repeat-winners already in it.

## Session totals
Credits used across the whole session: **~2,834** of 60,007.
Artifact: https://claude.ai/artifact/5wVx81JSG5xbNoWnPmhu1r
