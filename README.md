# Cavitation

**A map of where proven onchain capital moves next — built entirely on the Nansen API.**

Scrub 141 days and watch capital from 741 wallets that have *each won multiple memecoins*
rotate between 80 tokens across 4 chains. Bubble ring = market cap, glowing core = cohort
capital, edges = co-rotation. Only what is actually moving lights up.

Live demo → `cavitation.html` (single file, 444 KB, no server needed)

---

## Quick start (under 5 minutes)

```bash
git clone <repo> && cd NansenBuildathon
read -rs -p "Nansen API key: " K && printf 'NANSEN_API_KEY=%s\n' "$K" > .env && chmod 600 .env

python3 make.py --demo      # live build from the API: ~2 min, ~260 credits
open cavitation.html
```

No dependencies beyond Python 3.9+ standard library. No build step, no node_modules.

| Command | What it does | Time | Credits |
|---|---|---|---|
| `make.py --demo` | Live build, 30-day window, 40-wallet cohort | ~2 min | ~260 |
| `make.py --full` | Production refresh, 141 days, 741 wallets | ~2 h | ~6,000 |
| `make.py --build` | Re-render from cached data | ~5 s | **0** |

`--cap N` sets a hard credit ceiling; the run stops safely and keeps partial data.
All stages resume from cache, so an interrupted run never loses work.

---

## What the product actually claims

We tested our own thesis and **most of it failed**. What shipped is only what survived.

| Claim | Evidence |
|---|---|
| **91% coverage** of next month's winners | Cohort frozen 31 Aug with zero September data; caught 10 of 11 unseen September winners |
| **23× precision lift** | 28.6% of high-conviction holdings became 200%+ winners vs a 1.24% base rate |
| **~16 days median lead time** | First cohort entry → price peak, censoring-corrected |
| **Persistence varies 40× by chain** | 8.6% repeat-winner rate on Robinhood vs 0.2% on Solana |

**What we explicitly do NOT claim:** that flow magnitude predicts returns. We tested that four
separate ways — token-level correlation, five alternative signal formulations, a cross-chain
recurrence cohort, and chain-level aggregation — and **every result was null**. Crowding was
mildly *negative*: ≥3 cohort wallets entering predicted −12.5% at 5 days.

This is a discovery surface, not a prediction engine. It tells you where to look.

---

## How Nansen drives the logic

Nansen is not a data source we render — it *is* the model. Every layer is derived:

| Layer | Nansen endpoint | Role |
|---|---|---|
| Winner universe | `token-screener` | Defines "winning token" systematically (mcap, volume, gain) — not a hand-picked list |
| **Cohort selection** | `tgm/pnl-leaderboard` | 32,128 traders scanned; wallets winning **4+ separate tokens** become the cohort |
| Exposure over time | `profiler/address/historical-balances` | Daily per-token balances — the primitive everything else is computed from |
| Market cap | `tgm/token-ohlcv` | Bubble ring size |
| **Prices** | *derived* | `value_usd ÷ token_amount` from the balance rows — no external price feed |
| **Rotations** | *derived* | Same wallet reduces A while increasing B on the same day |

The cohort itself is a Nansen-derived construct. Remove Nansen and there is no product —
not a missing chart, no product.

### Two methodological choices that matter

**Balances, not swaps.** Our first architecture traced DEX swaps and failed: on BNB
launchpad tokens the settlement path (`execute(address[],uint256)` against a token contract)
isn't classified as a DEX trade, so a wallet with a $1.2M position showed **8 trades and $0
bought**. Balances measure *position*, not *execution*, so no settlement path can hide from
them.

**Flow = Δ(token_amount) × price, never Δ(value_usd).** Portfolio share conflates buying with
price movement — one wallet's STONK share rose 58%→69% while its dollar value collapsed,
purely because the rest of the portfolio shrank faster.

---

## Architecture

```
make.py                 one command: API → rendered site
├── scripts/nansen.py           API client (stdlib only, retries, credit accounting)
├── scripts/fetch_balances.py   paginated balance fetch
├── scripts/build_bubbles.py    cohort → nodes, edges, activity, layout
└── build_site.py               payload + engine.js → single HTML file
    └── engine.js               canvas renderer, camera, transport, panels

data/bubbles80.json      ← the ONLY contract between backend and front-end
```

The front-end reads one JSON file. Every aesthetic constant lives in three blocks at the top
of the generated HTML — `THEME` (colour), `MOTION` (feel), `CONFIG` (mapping) — so the
visuals can be rewritten without touching the data pipeline.

### Layout: the map encodes time
Nodes never move between frames — scrubbing animates only radius, glow and edges, which is
what keeps it at 60fps. Position is fixed and meaningful: **angle = chain** (wedge width
proportional to token count), **radius = when the cohort first entered** — centre is early
conviction, rim is newly discovered. Rotation into fresh names reads as outward drift.

---

## Controls

| Input | Action |
|---|---|
| drag / scroll | pan (with inertia) / zoom to cursor |
| `space` · `←` `→` | play-pause · step one day |
| `R` · `H` · `/` | reframe · hide panel · search |
| hover a bubble | market cap, cohort capital, wallets, **Fed by / Feeding** |

Right rail: **Rank** (live ordering) · **Flows** (what's vamping what) · **Movers** (7-day
gainers and bleeders) · **Search**.

---

## Known limits

- **Solana ↔ EVM rotations are unobservable.** The address spaces are disjoint — an EVM
  keypair cannot hold a Solana token, and our method requires the same wallet on both sides.
  Solana↔Solana edges do appear, but the Solana cohort is only 33 wallets because Solana's
  repeat-winner rate is 0.2%.
- **Coverage is ecosystem-bound.** 91% on Robinhood, ~0% on chains below ~4% recurrence.
  The Persistence table reports this per chain rather than hiding it.
- **Co-rotation is not causation.** We label edges "Fed by / Feeding" on shared-wallet
  evidence; direct A→B attribution was tested and is not reliable.
- One 141-day window, one market regime.

## Attribution
Powered by the Nansen API. Cohort-selection endpoints (`pnl-leaderboard`) are used only
internally to choose wallets; no Nansen label, PnL rank or Smart Money classification is
displayed, per Nansen's Data Redistribution Guidelines.
