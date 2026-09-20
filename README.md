# Cavitation

**A map of where proven onchain capital moves next, built entirely on the Nansen API.**

Scrub 141 days and watch capital from 741 wallets — each of which won **four or more
separate memecoins** — rotate between 80 tokens across four chains. Ring = market cap,
glowing core = cohort capital, edges = co-rotation. Only what is moving lights up.

**Live: https://dvnykim.github.io/cavitation/**

---

## Run it

```bash
git clone https://github.com/dvnykim/cavitation && cd cavitation
read -rs -p "Nansen API key: " K && printf 'NANSEN_API_KEY=%s\n' "$K" > .env && chmod 600 .env

python3 make.py --demo        # live build from the API
open docs/index.html
```

Python 3.9+, standard library only. No dependencies, no build step, no server.

| Command | Scope | Time | Credits |
|---|---|---|---|
| `make.py --demo` | 30-day window, 40-wallet cohort | ~2 min | ~260 |
| `make.py --full` | 141 days, 741 wallets | ~2 h | ~6,000 |
| `make.py --daily` | Incremental: top 300 wallets, new days only | ~35 min | ~1,200 |
| `make.py --build` | Re-render from cache | ~5 s | **0** |

`--cap N` sets a hard credit ceiling. Every stage resumes from cache, so an interrupted
run loses nothing.

### Daily automation

`.github/workflows/daily.yml` runs `--daily` at 06:10 UTC, verifies the build, and pushes —
GitHub Pages then redeploys itself. Add your key as the repository secret
`NANSEN_API_KEY` (Settings → Secrets and variables → Actions) and it runs unattended.

The job refreshes the 300 wallets holding **88% of cohort capital** rather than all 741,
which is what keeps it affordable; a `--full` run sweeps the long tail when you want it.
Continuity between runs comes from `data/cache.json.gz` — a 2.6 MB compaction of the
660 MB of raw balance rows, holding per-wallet detail for the 150 tokens that matter.
It rebuilds a byte-identical payload to the raw path.

---

## What it claims

Validated out-of-time: the cohort was frozen on 31 August with **zero** September data,
then tested against September's winners.

| | |
|---|---|
| **75%** | of unseen September winners were already held by the frozen cohort (6 of 8, Robinhood chain) |
| **23×** | precision lift — 28.6% of high-conviction holdings became 200%+ winners vs a 1.24% base rate |
| **~16 days** | median lead from first cohort entry to price peak |

Every one of those numbers lives in [`research/claims.json`](research/claims.json) with the
run that produced it, and `make.py` reads that file rather than hardcoding anything — so the
site cannot drift from the research. [`research/NUMBERS.md`](research/NUMBERS.md) is the
readable version, including the one claim we withdrew for lack of an artifact.

**The coverage figure and the map are measured on different cohorts** (125 wallets at 2+ on
Robinhood vs the 741 at 4+ that the map draws), because that is the configuration the
out-of-time test was run on. Reconciling them on one run is a single command, documented in
[NUMBERS.md](research/NUMBERS.md#two-configurations-and-why-they-differ).

**What it does not claim: that flow magnitude predicts returns.** We tested that four ways
— token-level correlation, five alternative signal formulations, a cross-chain recurrence
cohort, and chain-level aggregation — and every result was null. Crowding was mildly
*negative*: three or more cohort wallets entering predicted −12.5% at five days.

This is a discovery surface. It tells you where to look, not what to buy.

---

## How Nansen drives it

Nansen is not rendered here; the model is made of it.

| Layer | Endpoint |
|---|---|
| Winner universe — defined programmatically, not hand-picked | `token-screener` |
| **Cohort** — 32,128 traders scanned, wallets winning 4+ tokens qualify | `tgm/pnl-leaderboard` |
| Daily per-token exposure | `profiler/address/historical-balances` |
| Market cap | `tgm/token-ohlcv` |
| **Prices** — `value_usd ÷ token_amount` from the balance rows | *derived* |
| **Rotations** — same wallet reduces A while increasing B | *derived* |

No external price feed anywhere in the stack. Remove Nansen and there is no product.

**Two choices worth stating.** We track *balances, not swaps*: on BNB launchpad tokens the
settlement path is not classified as a DEX trade, so a wallet holding $1.2M showed eight
trades and $0 bought. Balances measure position, not execution. And flow is
`Δ(token_amount) × price`, never `Δ(value_usd)` — portfolio share conflates buying with
price drift.

---

## Layout

```
make.py              entry point: API → rendered site
build_site.py        payload + engine.js → single HTML file
engine.js            canvas renderer, camera, transport, panels
scripts/
  nansen.py            API client with credit accounting
  fetch_balances.py    paginated balance fetch
  build_bubbles.py     cohort → nodes, edges, activity, clustered layout
  restamp.py           re-solve layout / refresh claims, no API key, 0 credits
docs/index.html      the published site (generated)
docs/og.png          social card (regenerate after a visual change)
research/claims.json every displayed number, with the run that produced it
research/            how the claims were validated — see research/README.md
```

`data/bubbles80.json` is the only contract between backend and front-end. Every visual
constant sits in three blocks at the top of the generated HTML — `THEME`, `MOTION`,
`CONFIG` — so the design can be rewritten without touching the pipeline.

**Position carries meaning.** Nodes never move between frames, which is what keeps it at
60fps. Placement is solved once at build time by a four-force layout: co-rotation springs
pull tokens that actually trade into each other adjacent, radius-aware repulsion stops the
big caps colliding, a weak per-chain anchor forms visible territories, and a radial time
bias keeps early entries toward each cluster's core and new ones at its rim.

The chain anchor is deliberately weak: a token rotating hard with another chain drifts
toward it, and that drift is information a hard boundary would have hidden. Clustering cut
median edge length by 41% and p90 by 57% against the previous polar layout — a rotation is
now a short link between neighbours instead of an arc across empty canvas.

---

## Controls

| | |
|---|---|
| drag · scroll | pan with inertia · zoom to cursor |
| `space` · `←` `→` | play-pause · step one day |
| `R` · `H` · `/` | reframe · hide panel · search |
| hover | market cap, cohort capital, wallets, **Fed by / Feeding** |

Right rail: **Rank** · **Flows** (what is draining into what) · **Movers** (7-day gainers
and bleeders) · **Persist** (repeat-winner rate per chain, and the ~4% floor below which a
cohort cannot work) · **Search**.

Above the map, a one-line narrative is regenerated from the payload every frame — never
written by hand. Bottom left, the three validated numbers are on screen permanently, each
carrying its measurement scope on hover.

---

## Limits

- **Solana ↔ EVM rotations are unobservable.** The address spaces are disjoint — an EVM
  keypair cannot hold a Solana token, and the method requires the same wallet on both
  sides. Solana ↔ Solana edges do appear, but the Solana cohort is 33 wallets because
  Solana's repeat-winner rate is 0.2%.
- **Coverage is ecosystem-bound.** 75% on Robinhood; near zero on chains below ~4%
  repeat-winner rate. The Persistence panel reports this per chain rather than hiding it.
- **Co-rotation is not causation.** Edges are labelled "Fed by / Feeding" on shared-wallet
  evidence. Direct A→B attribution was tested and is not reliable.
- One 141-day window, one market regime.

---

## Attribution

Powered by the Nansen API. Cohort-selection endpoints (`tgm/pnl-leaderboard`) are used
only internally to choose wallets — no Nansen label, PnL rank or Smart Money
classification is displayed, per Nansen's Data Redistribution Guidelines.

MIT licensed.
