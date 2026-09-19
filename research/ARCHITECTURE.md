# Liquidity Rotation Graph — Foundational Architecture

The design that produces token→token liquidity-flow edges from the Nansen API,
robust to the failure modes found in the MARSCOIN pilot, and economically viable live.

---

## 1. The core reframe

**Wrong question (what we tried):** *"What did this wallet buy next?"*
→ `profiler/dex-trades`, 1 credit **per wallet per chain**, and it depends on Nansen
correctly classifying a swap. Launchpad settlement (flap.sh `execute(address[],uint256)`)
is not classified, so the trace silently returns nothing.

**Right question:** *"Who sold A? Who bought B?"*
→ `tgm/who-bought-sold`, **1 credit per token**. The edge is a local set intersection:

```
edge(A → B, window w)  =  sellers(A, w)  ∩  buyers(B, w)
weight_usd             =  Σ min(sold_usd(a), bought_usd(a))  for a in the intersection
weight_wallets         =  |intersection|
```

N tokens → the **entire N×N rotation matrix** for N credits. Cost scales with the size of
the universe, not with the number of wallets — a 10–100× reduction.

### Why this is more robust, not just cheaper
`who-bought-sold` is a **token-scoped aggregate**. It answers "did this address's position in
this token increase or decrease," which does not require the intermediate swap to be
classified as a DEX trade. The MARSCOIN leaderboard proved Nansen *knows* the position
changed (max balance $1.2M, netflow −$2.4M) even when `dex-trades` showed nothing.
We were querying the one endpoint that depended on the broken classifier.

### Three problems it solves for free
- **Stablecoin pass-through.** We never inspect what the wallet swapped *into*, only that it
  exited A and entered B inside the window. The USDC leg becomes irrelevant instead of
  requiring matching logic. This was previously the hardest part of the design.
- **Bots / MMs / routers.** A wallet appearing in too many tokens' sets in one window is
  infrastructure. Filter by **set degree** — pure local arithmetic, zero credits.
- **Cross-chain EVM.** EVM chains share an address space, so union the per-chain sets for a
  token before intersecting. No identity inference needed.

### The one thing it loses
Set intersection over a window discards **intra-window ordering** — we learn that a wallet
sold A and bought B in the same window, not which came first. Recovered by **time slicing**:

```
edge(A → B, t)  =  sellers(A, t)  ∩  ( buyers(B, t) ∪ buyers(B, t+1) )
```

Narrower slices = better direction, linearly more credits. Slice width is the single tuning
knob trading precision against cost.

---

## 2. Three-tier evidence model

Different methods carry different evidential weight. The product should **show which is
which** — it is both honest and a good visual feature.

| Tier | Method | Endpoint | Cost | Evidence | Immune to |
|---|---|---|---|---|---|
| **1. Traced** | Set intersection | `tgm/who-bought-sold` | 1 / token / window | Same wallet exited A, entered B | pass-through, bots |
| **2. Confirmed** | Balance delta | `profiler/address/historical-balances` | 1 / wallet | Position in A fell, position in B rose | **swap classification, launchpads, FOMO routing** |
| **3. Inferred** | Flow correlation | `tgm/flow-intelligence` | 1 / token | Outflow(A) correlates with inflow(B) | wallet identity entirely — works cross-chain |

**Tier 1 is the backbone** — it builds the whole graph cheaply.
**Tier 2 is the repair kit.** Balance deltas measure *position*, not *execution*, so no
settlement path can hide from them. This is the direct answer to the MARSCOIN failure: the
TRYFOMO wallet's trades were invisible, but its balance still went $1.2M → $0. Spend Tier 2
credits only on high-value edges or where Tier 1 looks suspiciously empty.
**Tier 3 bridges Solana↔EVM**, the one boundary no address matching can cross, and
double-checks Tier 1. Statistical, never presented as traced.

Render traced edges solid, inferred edges dashed. A trader who can see which is which will
trust the tool more than one shown a single confident-looking number.

---

## 3. Data model

```
Node (token)
  chain, address, symbol
  mcap_series, price_series          # tgm/token-ohlcv, 1 credit
  peak_date, peak_mcap, drawdown     # derived
  status: rising | peaked | fading | dead     # derived from forward return
  attention_half_life_hours          # derived, see §4

Edge (rotation)
  from_token, to_token, window_start, window_end
  usd_weight, wallet_count
  tier: traced | confirmed | inferred
  outcome: live | dead_end           # set when destination's forward return resolves

Wallet (internal only — never displayed)
  address, chains[], degree, is_bot
  labels[]                           # INTERNAL USE ONLY, see §6
```

`outcome: dead_end` is the feature you asked for: capital rotated in, the destination failed.
It costs nothing extra — it falls out of the destination node's own price series.

---

## 4. Derived metrics (the part competitors don't have)

- **Attention half-life** — bucket *unique new buyers* per slice from `who-bought-sold`, fit
  an exponential decay, report in hours. This is the literal measurement of "attention faded."
- **Destination concentration** — Herfindahl index over a token's outbound edges. High = a
  coherent rotation into one successor (tradeable). Low = dispersal/exit (bearish for all).
- **Rotation velocity** — median hours between exiting A and entering B, per slice. Falling
  velocity across the market is a risk-on signal; rising is capitulation.
- **Dead-end rate** — share of outbound USD that landed in tokens that subsequently died.
  A per-source-token credibility score: which coins' exiting holders actually pick winners.

All four are computed locally from data already paid for. Zero marginal credits.

---

## 5. Cost model

Let **N** = universe size, **W** = windows retained.

| Operation | Formula | Example |
|---|---|---|
| Backfill the graph | N × W | 30 tokens × 14 days = **420** |
| Live daily update | N | 30 tokens = **30/day ≈ 900/month** |
| Node price series | N (refresh cheap) | 30 = **30** |
| Tier-2 repairs | 1 × wallets repaired | budget ~50/month |
| Tier-3 cross-chain | N | 30 = **30** |

**~960 credits/month for a live 30-token rotation graph — inside a single Pro plan.**

**Past windows are immutable and cache permanently.** Backfill is paid once, ever. The
marginal cost of an extra day is N credits. This is the property that makes the product
economically viable, and it is why this design works where wallet-tracing did not.

---

## 6. Redistribution compliance (binding on the shipped product)

- `tgm/who-bought-sold`, `tgm/flow-intelligence`, `tgm/dex-trades`, `token-screener` —
  ✅ allowed **with attribution**. Tier 1 and Tier 3 are clean.
- `profiler/address/historical-balances` — ✅ allowed, **no attribution required**. Tier 2 clean.
- `tgm/pnl-leaderboard`, `address/labels` — 🚫 **prohibited from display**. Use them
  internally for bot filtering and wallet selection; **never render a label or a PnL rank.**
- Ship "Powered by Nansen API" visibly.

The architecture is deliberately built so the *displayed* graph derives only from allowed
endpoints, with prohibited data confined to internal filtering.

---

## 7. What must be verified before spending (≈3 credits)

Three unknowns, each of which changes the design:

1. **Does `who-bought-sold` return a complete address list with USD amounts, or only a top-N?**
   *(free 422 probe for fields, 1 credit for real data on STONK)*
   If top-N only, edges are whale-weighted — acceptable, arguably desirable, but must be known.
   If no USD amounts, edges become wallet-count-weighted. Still works, weaker.
2. **Does `historical-balances` return a usable time series across all held tokens?** (1 credit)
   Tier 2 depends entirely on this. If it only returns current top holdings, Tier 2 dies and
   launchpad tokens stay untraceable.
3. **Does the intersection actually produce non-trivial edges on a real pair?** (1 credit)
   Run `sellers(STONK) ∩ buyers(X)` on one window. If intersections are empty at realistic
   window widths, the whole premise is wrong and we stop.

**Check 3 is the kill switch.** If it fails, the answer to "is there a way" is no.

---

## 8. Honest failure modes

- **Top-N truncation** biases edges toward whales and may miss retail rotation entirely.
- **Wash trading / one entity, many wallets** inflates edge weights. `related-wallets` could
  collapse them but costs 1 credit/wallet — probably not worth it.
- **Window width is a real trade-off**, not a solved problem. Too wide loses direction; too
  narrow misses rotations and costs more.
- **Solana↔EVM stays inferred, never traced.** No amount of cleverness fixes this; it is a
  keypair-space boundary.
- **Correlation is not causation.** Two coins can co-rotate because both are downstream of a
  third narrative. Present as *observed co-rotation*, never as "X vampired Y."

---

# ADDENDUM — corrections from the STONK validation run (2026-09-17)

Two foundational assumptions in §1–2 were **wrong** and are corrected here. The pipeline below
is the one that actually works, validated end-to-end on STONK (Solana).

## Correction 1 — `who-bought-sold` CANNOT source wallets

The §1 premise was that `sellers(A) ∩ buyers(B)` produces the edge. It produces *an* edge, but
the seller set is unusable for sourcing:

| Method | Net outflow found (STONK, same period) |
|---|---|
| `who-bought-sold`, top 500 by `sold_volume_usd` | **$305,927** |
| `tgm/pnl-leaderboard`, top 100 by PnL | **$36,365,918** |

**119× difference.** Cause: **80% of the top 500 sellers are churners** (|net|/gross < 0.2).
A bot cycling $10M in and $10M out outranks a trader who sold $200K once, and the API exposes
**no net sort and no net filter** — `order_by` accepts only gross fields (`bought_volume_usd`,
`sold_volume_usd`, `token_trade_volume`, `trade_volume_usd`, and token equivalents).

Also disproved: the **directional-purity filter**. Zero of the top 500 STONK sellers sold
≥80% one-way. At a 3-day horizon large traders *churn*; clean exits do not exist. Use **net
position change**, never purity.

## Correction 2 — the working pipeline

```
1. SOURCE   tgm/pnl-leaderboard        5 cr/token   -> real net exiters, bot-immune
              ranked by realised PnL, so churners (PnL≈0) never surface.
              Gives netflow_amount_usd and still_holding_balance_ratio —
              the net-exposure fields who-bought-sold refuses to sort by.
2. DISCOVER profiler/dex-trades        1 cr/wallet  -> where that wallet actually went
              Works on Solana (real DEXs). FAILS on BNB launchpad tokens.
3. WEIGHT   tgm/who-bought-sold        1 cr/token   -> confirm/scale edges (still useful here)
4. OUTCOME  tgm/token-ohlcv            1 cr/token   -> winner vs dead end
   RESOLVE  search/general             0 cr         -> symbol -> address, FREE
```

Cost for one source coin, 12 exiters, 8 destinations: **5 + 12 + 8 ≈ 25 credits.**

`pnl-leaderboard` is 🚫 prohibited for *display* — it is used only to **select wallets**
internally. Displayed edges derive from `dex-trades` / `who-bought-sold` (✅ with attribution).

## Correction 3 — wallet convergence does NOT predict outcome

Validated result, STONK exiters, rotation ~Sep 11–13 → Sep 16:

| Destination | Wallets | USD | Return | Peak |
|---|---:|---:|---:|---:|
| ALLINU | 4 | $79,192 | **+524%** | +524% |
| UBER | 4 | $43,692 | **+109%** | +109% |
| ZCAT | 3 | $179,724 | +16% | +31% |
| CLANKER | 4 | $47,342 | −14% | +5% |
| MONEROCHAN | **5** | $78,215 | **−69%** | +58% |

USD-weighted basket: **+101%** over 5 days — the thesis has support.
But the **highest-convergence destination was the worst performer.** Do not ship
"thicker edge = better bet." MONEROCHAN peaked +58% before dying, so the rotation was
directionally right and the *exit* was wrong — the product must distinguish these.

## Open gaps before this is a product

1. **No baseline.** +101% is meaningless until compared with a random Solana memecoin basket
   over the same window. If the whole market ran, the signal is zero. **Highest priority.**
2. **n=5.** Statistically nothing. Needs ~50+ destination outcomes across several source coins.
3. **500-trade page cap** truncated 5 of 12 traces — the most active wallets are under-counted.
   Needs pagination.
4. **Only 15% of outflow traced** ($2.1M of $14.5M). The rest went to stables, or beyond the
   page cap. Two wallets had **zero** destinations — sidelined capital, itself a signal.
5. **Power-law dependence.** The basket return is driven by one outlier (ALLINU +524%).
   Median destination return is far less impressive than the mean.
