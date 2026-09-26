# Vampnet

**A map of where proven onchain capital moves next, built entirely on the Nansen API.**

Scrub 141 days and watch capital from 741 wallets — each of which won **four or more
separate memecoins** — rotate between 80 tokens across four chains. Ring = market cap,
glowing core = cohort capital, edges = co-rotation. Only what is moving lights up.

**Live: https://dvntekim.github.io/vampnet/**

---

## Run it

```bash
git clone https://github.com/dvntekim/vampnet && cd vampnet
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

### Checks

`.github/workflows/pr.yml` runs on every pull request: every module compiles, the
headline numbers resolve out of `research/claims.json`, the site rebuilds, `docs/index.html`
is confirmed in sync with `engine.js` and `build_site.py`, and `scripts/verify_build.py`
gates the result. The daily job runs that same gate before it publishes, so the two
cannot drift apart.

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
| **78%** | of unseen September winners were already held by the frozen cohort (7 of 9, Robinhood chain) |
| **42%** | the same run counted naively across all four chains (10 of 24) — coverage tracks repeat-winner rate |
| **23×** | precision lift — 28.6% of high-conviction holdings became 200%+ winners vs a 1.24% base rate |
| **~16 days** | median lead from first cohort entry to price peak |

Every one of those numbers lives in [`research/claims.json`](research/claims.json) with the
run that produced it, and `make.py` reads that file rather than hardcoding anything — so the
site cannot drift from the research. [`research/NUMBERS.md`](research/NUMBERS.md) is the
readable version, including the claim we withdrew and then superseded by measuring it.

**Both figures come from one frozen-cohort run at the map's own 4+ threshold**
(`research/out_of_time_2026-08-31.json`). The cohort was built only from winners that
resolved before 31 August and tested on the 24 that first appeared afterwards — 21 tokens
already winning before the freeze were excluded, so nothing the cohort could have learned
from the test period reaches it.

We lead with the Robinhood number because the product's central finding is that coverage is
ecosystem-bound, and we print the naive number beside it so the 78% is never read as a
cross-chain result. Per chain: robinhood 7/9, base 2/3, bnb 1/6, **solana 0/6** — which is
what an 0.2% repeat-winner rate predicts.

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
  verify_build.py      the publish gate — both CI workflows run it
  measure_perf.js      paste into DevTools: draw cost and frame interval, kept apart
research/scripts/
  out_of_time.py       frozen-cohort coverage test; --write-claims updates claims.json
  check_claims.py      fails if a displayed number drifts from its run artifact
docs/index.html      the published site (generated)
docs/og.png          social card (regenerate after a visual change)
research/claims.json every displayed number, with the run that produced it
research/            how the claims were validated — see research/README.md
```

`data/bubbles80.json` is the only contract between backend and front-end. Every visual
constant sits in three blocks at the top of the generated HTML — `THEME`, `MOTION`,
`CONFIG` — so the design can be rewritten without touching the pipeline.

**Position carries meaning, and nothing about it is imposed.** Nodes never move between
frames, which is what keeps it at 60fps. Placement is solved once at build time from the
rotations alone — no chain grid, no time axis.

Seating chains around a ring was tried and was wrong for this data: **92% of flow is inside
a chain and 87% is inside Robinhood alone**, so a ring spent a quarter of the canvas on
Solana — six tokens, 0.2% of flow and structurally zero cross-chain edges, because an EVM
keypair cannot hold a Solana token — while compressing everything worth looking at into a
blob.

So the map is built the other way round. Communities are detected on the rotation graph
(Louvain; label propagation collapses Robinhood's dense subgraph into one useless blob of
74). Each neighbourhood is solved on its own, then packed as a disc, then its members take
that slot — separation is a property of the construction rather than something a force has
to win. A token that rotates with another neighbourhood drifts toward it, bounded, because
that bridge is worth seeing.

Chains then separate themselves, because their edges do. Several neighbourhoods are **not**
chain-pure, which is the part a chain-shaped layout could never have shown.

---

## Controls

| | |
|---|---|
| drag · scroll | pan with inertia · zoom to cursor |
| `space` · `←` `→` | play-pause · step one day |
| `R` · `H` · `/` | reframe · hide panel · search |
| hover | market cap, cohort capital, wallets, **Fed by / Feeding** |

Frames on the map are rotation neighbourhoods, labelled by their biggest token; `⁑` marks
one that spans more than one chain.

**Fresh inflow.** A token the cohort entered days ago, being fed by a name it has held for
months, is the most actionable thing here — and it is almost always small in absolute
terms, so a top-N edge cap is exactly what throws it away: **more than four in five of those
rotations fall below that cap**
([`fresh_inflows.py`](research/scripts/fresh_inflows.py) replays the renderer's own edge
selection frame by frame and prints the exact count for the current data; it is recorded in
[claims.json](research/claims.json) and re-checked on every refresh). So they are drawn regardless of it, in the
reserved accent, into a bracketed node tagged with its age. The feeder has to be a top-20
name, or the signal is just churn. The **Fresh** panel ranks them by how much standing the
feeders have, so `PONS → RAM` on RAM's first day outranks a larger flow between two
unknowns.

Right rail: **Rank** · **Flows** (what is draining into what) · **Movers** (7-day gainers
and bleeders) · **Search**. Repeat-winner rate per chain — the ceiling on whether a cohort
can work there — is on each chain chip in the masthead.

Above the map, a one-line narrative is regenerated from the payload every frame — never
written by hand. Bottom left, the three validated numbers are on screen permanently, each
carrying its measurement scope on hover.

---

## Limits

- **Solana ↔ EVM rotations are unobservable.** The address spaces are disjoint — an EVM
  keypair cannot hold a Solana token, and the method requires the same wallet on both
  sides. Solana ↔ Solana edges do appear, but the Solana cohort is 33 wallets because
  Solana's repeat-winner rate is 0.2%.
- **Coverage is ecosystem-bound.** 78% on Robinhood; near zero on chains below ~4%
  repeat-winner rate. Each chain chip carries its own rate rather than hiding it.
- **Co-rotation is not causation.** Edges are labelled "Fed by / Feeding" on shared-wallet
  evidence. Direct A→B attribution was tested and is not reliable.
- One 141-day window, one market regime.

---

## Attribution

Powered by the Nansen API. Cohort-selection endpoints (`tgm/pnl-leaderboard`) are used
only internally to choose wallets — no Nansen label, PnL rank or Smart Money
classification is displayed, per Nansen's Data Redistribution Guidelines.

MIT licensed.
