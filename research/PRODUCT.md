# Product Design — the Attention Map

## Positioning

**"Where proven capital is, and where it just moved."**

Not a prediction engine. We tested that four ways and it failed (RESULTS.md). What we can
claim, and what nobody else can show, is **coverage**: the map contains the winners, and it
contains them early enough to matter.

The honest disclaimer is a feature. Every other tool implies prediction. Stating plainly
"flow magnitude did not predict returns in our backtest; crowding was mildly negative" earns
more trust from an experienced trader than a confident lie, and it is defensible on stage.

---

## The two audiences, one page

| | New trader needs | Experienced trader needs |
|---|---|---|
| Question | "What's happening? Where do I even look?" | "What changed in the last 12h, and who moved?" |
| Format | Narrative, plain language, few numbers | Dense tables, raw USD, wallet drill-down |
| Danger | Mistakes the map for advice | Dismisses it as another whale-watcher |
| Answer | Narrative layer on top, always visible | Every element clicks through to primitives |

Design rule: **one surface, progressive disclosure.** The headline reads as English; every
number is one click from the wallet addresses and timestamps that produced it.

---

## Screen 1 — THE MAP (hero)

A force-directed graph. **Chains are territories, tokens are nodes, flow is motion.**

- Node size = cohort USD exposure. Node colour = chain.
- Edge = capital that moved between two tokens in the window, thickness = USD.
- **Sidelined node** = stables/native. Swells in risk-off. Often the most informative node.
- Time scrubber across the bottom — scrub and watch attention physically migrate.
- Dead-end edges (destination subsequently died) drawn dashed and greyed.

Why this and not a Sankey: rotation is many-to-many and non-linear (A→D while others go D→C).
A Sankey forces a false left-to-right ordering. The graph shows the trend without inventing
a sequence that doesn't exist.

**The one-line narrative sits above the graph**, auto-generated:
> *"In the last 7 days, tracked winners moved $6.0M out of BNB and into Robinhood chain.
> Biggest new position: ZCAT ($1.5M, 3 wallets)."*

That single sentence is what a new trader came for, and it is derived, not written.

---

## Screen 2 — FIRST SIGHTINGS (the monthly engine)

**The most valuable panel, and the answer to "how do we show new liquidity flowing to new coins."**

A live feed of tokens appearing in a tracked wallet **for the first time ever**:

| Token | Chain | Age | First seen | Wallets in | USD in | Cohort first? |
|---|---|---|---|---|---|---|

- Ranked by (number of distinct cohort wallets) × (USD), filtered to tokens under ~60 days old.
- "Cohort first?" flags tokens where a tracked winner bought **before** the token hit any
  volume screener — the earliest possible signal, and the most defensible thing we produce.
- This panel is what makes the product worth opening daily for the next month. It updates
  itself: as new coins launch, new first-sightings appear, no manual curation.

Honest label on the panel: *"First sightings are where proven capital is looking. Most will
not work out — in our data, more cohort wallets entering predicted slightly worse returns."*

---

## Screen 3 — COVERAGE (the credibility panel)

The evidence that the map is worth trusting, stated as a testable number:

> **"Of the last 37 tokens that gained 200%+ with real liquidity, our cohort held N of them.
> Median first entry: X days before peak."**

This is the claim we can actually defend, and it should be recomputed live and displayed
permanently. It is also the strongest possible answer to a judge asking "does this work?"

---

## Screen 4 — WALLET DRILL-DOWN (experienced traders)

Click any node or edge → the wallets behind it.
- Portfolio over time (the stacked area chart that made the STONK→ZCAT rotation obvious)
- Which winning coins this wallet has won on (its recurrence record — why it's in the cohort)
- Cross-chain footprint: the same address's positions on every EVM chain, side by side

**The hero anecdote lives here:** `0x554a02baa307…` won on four separate coins across three
chains. A single-chain tool cannot see that this person exists. Feature it.

---

## What we deliberately do NOT show

- **Price predictions or buy signals.** Falsified; claiming them is the fastest way to lose credibility.
- **Nansen labels or PnL ranks.** Prohibited for redistribution. Used internally for cohort
  selection and bot filtering only.
- **Wallet count as edge weight.** More wallets predicted *worse* outcomes. Weight by USD.
- **Intraday motion.** The meaningful horizon is ~5 days; minute-level updates would show bots.

---

## Metrics shown (all derived, zero extra API cost)

| Metric | Definition | Audience |
|---|---|---|
| Cohort exposure | Σ value_usd by token/chain | both |
| Net flow | **Δ(token_amount) × price** (drift removed) | both |
| First sightings | tokens newly present in any cohort wallet | both |
| Abandonment | tokens fully exited by ≥2 wallets | experienced |
| Chain share | % of cohort capital per chain | new |
| Concentration | Herfindahl over cohort holdings | experienced |
| Coverage | % of screener-defined winners the cohort held | credibility |

## Attribution
"Powered by Nansen API" visible on every screen. Required: token-screener, who-bought-sold,
flow endpoints are ✅-with-attribution. Balances need no attribution but we credit anyway.
