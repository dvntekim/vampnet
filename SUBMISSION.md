# Cavitation — submission case

Scored against the four criteria, with the evidence for each.

---

## 1. Data Integration — 25%
> *Nansen data drives the logic — not just appears on screen.*

**The cohort is a Nansen derivation, and the cohort is the entire product.**

We do not display Nansen data. The model is made of it:

| Layer | Endpoint | Why it is logic, not decoration |
|---|---|---|
| Winner universe | `token-screener` | "Winning token" is defined programmatically (mcap > $5M, vol > $2M, +200%) across 8 chains — not a hand-picked list |
| **Cohort selection** | `tgm/pnl-leaderboard` | **32,128 traders** scanned across 63 winning tokens; only wallets that won **4+ separate tokens** qualify. This is the central construct |
| Exposure | `profiler/address/historical-balances` | 741 wallets × 141 days × 4 chains of daily per-token balances |
| Market cap | `tgm/token-ohlcv` | Bubble ring size |
| **Prices** | *derived from Nansen rows* | `value_usd ÷ token_amount` — **no external price feed anywhere in the stack** |
| **Rotations** | *derived from Nansen rows* | Same wallet reducing A while increasing B on the same day |

Six endpoint families, two derived layers, zero third-party data. **Remove Nansen and there
is no product — not a missing chart, no product.**

**Depth evidence — four API behaviours we found and engineered around:**
- `per_page` accepts **1,000**, not 100, for the same 5 credits → 10× the candidate pool free
- Rejected requests are quoted but **never billed** → schema discovery costs nothing
- `token-screener` daily data has a **2-month retention wall**; `pnl-leaderboard` has none
- Base58 (Solana) addresses are **case-sensitive** while EVM is not — silently zeroed five tokens until caught

**Two methodological choices Nansen forced:**
1. **Balances, not swaps.** Our first architecture traced DEX swaps and broke: on BNB launchpad
   tokens the settlement path isn't classified as a DEX trade, so a wallet holding **$1.2M
   showed 8 trades and $0 bought**. Balances measure position, not execution.
2. **Flow = Δ(token_amount) × price, never Δ(value_usd)** — share conflates buying with price
   drift. One wallet's STONK share rose 58%→69% *while its dollar value collapsed*.

---

## 2. Creativity & Originality — 25%
> *A use case nobody thought to build. We've seen dashboards.*

**It is not a dashboard.** It is a pannable spatial map where **position itself carries
meaning**. A four-force layout, solved once at build time, places every token: co-rotation
springs pull tokens that actually trade into each other adjacent, a weak per-chain anchor
forms visible territories, and a radial time bias keeps early entries at each cluster's
core and new ones at its rim. Scrubbing animates only size, glow and edges — nodes never
move, so the map is a place you learn rather than a chart that reshuffles.

The chain anchor is weak on purpose. A token rotating hard with another chain drifts
toward it, and **that drift is the finding** — a hard chain boundary would have forbidden
the single most interesting thing in the data. Clustering cut median edge length 41% and
p90 57% versus the polar layout it replaced.

**Three things that are genuinely new:**

**A cohort defined by repetition, not by label.** Everyone else pipes Nansen's Smart Money
tag straight through. We asked a harder question — *who wins more than once?* — and found
that out of 32,128 traders scanned, only **741** cleared four or more separate tokens. One
wallet won **26**. That 741 is the cohort the map draws, recorded in the shipped payload as
`stats.cohort`.

**A market-structure finding nobody has published.** Repeat-winner rate varies **40× by chain**:

| Chain | Repeat-winner rate | Out-of-time coverage |
|---|---:|---:|
| Robinhood | **8.6%** | **60%** |
| BNB | 4.2% | 0% |
| Base | 0.8% | 0% |
| Solana | **0.2%** | 0% |

Counter-intuitively, **Solana — the busiest memecoin chain — has the least persistent
winners** (one repeat winner in 499). That number is the hard ceiling on whether *any*
cohort strategy can work on a chain, and no existing tool measures it. We ship it as a
first-class panel rather than hiding it.

**We falsified our own thesis and shipped only what survived.** Four independent tests of
"does flow predict returns" — token-level correlation, five alternative signal formulations,
a cross-chain recurrence cohort, chain-level aggregation — **all null**. Crowding was mildly
*negative* (≥3 wallets entering → −12.5% at 5d). So the product claims discovery, not
prediction. That is a harder thing to demo and a much harder thing to argue with.

**Interaction detail:** scrub velocity drives a capped RGB split — the aesthetic is a
readout of how fast *you* are moving through time, held to 3px so the one interaction we
most want judged never degrades into looking broken.

---

## 3. Functionality & Workability — 25%
> *Live data loads. End to end. No crashes.*

**One command, measured — not claimed:**

```
$ python3 make.py --demo --cap 400

  [1/6] winner universe: 35 tokens across 3 chains
  [2/6] pool 7,576 traders -> cohort 40 wallets (>= 2 winning tokens)
  [3/6] balances for 20 wallets
  [4/6] market caps: 26 to fetch
  [5/6] payload: 26 nodes, 105 edges, 31 days
  [6/6] site: docs/index.html (84,398 bytes)

Done in 119s · 261 credits used
```

**119 seconds, live from the Nansen API to a rendered site.**

**Built not to break:**
- **Hard credit cap** (`--cap N`) stops safely and keeps partial data
- **Every stage resumes from cache.** We killed a 741-wallet fetch mid-run at wallet 255 and
  resumed with zero loss — this is tested, not theoretical
- **Retry with backoff** on network failure (a socket timeout did kill an early run; that is
  why the retry exists)
- **Zero dependencies** beyond the Python 3.9 standard library. No npm, no build step
- **Single 444 KB HTML file.** No server, no backend at runtime

**Performance, measured in-browser:**

Measured on the authors' hardware against the build tagged in git history. The layout and
hull rendering landed after this table was taken — **re-measure before submitting**, with
`scripts/measure_perf.js` (paste into the DevTools console).

These are **draw cost**: how long `draw()` takes to render a frame. Not frame interval,
which is floored by the display's refresh rate — 16.7 ms on a 60 Hz panel — and so cannot
fall below it however fast the renderer gets. The harness reports both, separately, because
reading an interval as a cost makes a fast renderer look slow.

| | p90 draw cost |
|---|---:|
| Idle | **9.0 ms** |
| Panning | **9.3 ms** |
| Zooming | **9.3 ms** |

60fps with headroom, and panning costs the same as standing still — because node draw order
and edge selection are cached rather than rebuilt per frame (that change alone took it from
28.6 ms to 9.0 ms). Zero console errors.

---

## 4. Documentation & Submission — 25%
> *Clean README. Another builder can run it in under 10 minutes.*

`README.md` gets a builder from clone to running in **under 5 minutes**:

- Three commands with a time/credit table (`--demo` 2 min · `--full` 2 h · `--build` 0 credits)
- Architecture diagram naming the single backend↔frontend contract (`data/bubbles80.json`)
- Every claim paired with its evidence, **and a table of what we explicitly do not claim**
- A **Known limits** section stating where the product fails and why

**No number is hardcoded.** Every figure the site displays is read from
`research/claims.json`, which carries the scope and the run that produced it;
`research/NUMBERS.md` is the readable view. We withdrew one claim under this rule — a 91%
coverage figure that no script in the repository reproduced — and shipped the 75% that
`research/scripts/out_of_time.py` measures instead. The test builds a cohort that provably
cannot see the evaluation period, so the number is falsifiable by anyone with an API key:

```bash
python3 research/scripts/out_of_time.py --freeze 2026-08-31 --chains robinhood --write-claims
```

That last section is deliberate. Stating that Solana↔EVM rotations are structurally
unobservable, that coverage collapses below ~4% recurrence, and that co-rotation is not
causation costs nothing and makes every other number more credible.

### Suggested recording (no narration needed)

| s | Action | What it shows |
|---|---|---|
| 0–10 | Terminal: `python3 make.py --demo` | Live API, stage-by-stage, credits counted |
| 10–20 | Site loads, boot sequence resolves | End to end, no crash |
| 20–40 | Press Play at 2× | 141 days of capital migrating |
| 40–55 | Hover the largest node in the Robinhood cluster | Cohort capital, wallets in, **Fed by** / **Feeding** — green in, red out |
| 55–70 | Flows and Movers tabs | Live rotations and 7-day gainers/bleeders |
| 70–85 | Search "CASHCAT" → click | Camera flies to it, full rotation card |
| 85–100 | **Persist** tab | 8.6% Robinhood vs 0.2% Solana against the 4% floor — the finding |
| 100–110 | Toggle a chain chip off and back on | The map reframes to the remaining territories; then `H` for a clean screenshot |
