# Nansen Buildathon — Idea Research

Context: goal is a real product with users (not just a demo), ~1 week of build time,
lanes = trader alpha tooling + perps/prediction markets, no API key yet as of writing.

---

## 1. The finding that reframes everything: the redistribution rules

Nansen publishes [Data Redistribution Guidelines](https://docs.nansen.ai/guides/redistribution-guide)
(updated 18/11/2025). They are binding on anything customer-facing. Summary:

**🚫 Prohibited — cannot be displayed in any public or customer-facing interface, ever:**

| Endpoint | Note |
|---|---|
| `profiler/address/labels` | The Nansen label itself ("Smart Money", "Fund") |
| `smart-money/holdings` | |
| `smart-money/dex-trades` | |
| `smart-money/perp-trades` | |
| `smart-money/dcas` | |
| `tgm/pnl-leaderboard` | |
| `perp-leaderboard` | Hyperliquid top-trader leaderboard |

The guidelines go further and name the product shapes explicitly as prohibited:
"Smart Money Tracker" features, "Profitable Wallet Scanner" tools, "Smart Trader
Leaderboards", "Elite Wallet Following" services, public smart-money dashboards,
real-time smart-money alerts, and **automated smart-money trade copying services**.

**⚠️ Restricted — needs written approval + "significant modification"** (must combine with
another substantial independent data source, and not be reverse-engineerable back to
Nansen's raw classifications):
`smart-money/inflows` (netflow), `tgm/holders` with the smart-money filter,
`tgm/perp-positions` with the smart-money filter.

**✅ Allowed, attribution required** ("Powered by Nansen API" visible near the data):
*every* prediction-market endpoint, `tgm/perp-screener`, `tgm/perp-trades`,
`tgm/dex-trades`, `tgm/token-screener`, `tgm/who-bought-sold`, `tgm/flow-intelligence`,
`tgm/flows`, `tgm/transfers`, `profiler/address/transactions`,
`profiler/address/counterparty`, `profiler/address/related-wallets`.

**✅ Allowed, no attribution needed:**
`profiler/address/balances`, `profiler/address/historical-balances`,
`profiler/perp-positions`, `profiler/perp-trades`, `profiler/address/pnl` + `pnl-summary`.

### Why this matters

The two showcased buildathon builds — a smart-money shell terminal and a thesis canvas
that shows "who's accumulating and who's selling" — sit squarely on the prohibited and
restricted lists. They're Nansen-commissioned promos, so they presumably have a blessing.
A third party shipping the same shape to real users does not.

**The practical read: the lanes that are fully clean to build a real business on are
exactly the two picked — perps (profiler perp positions/trades, perp screener) and
prediction markets (all twelve endpoints, allowed with attribution).** The crowded
smart-money lane is the one you legally can't own.

---

## 2. Credit economics — this constrains architecture more than anything else

Pro is **$49–69/mo for 2,000 credits/month**. That is ~66 credits/day. It is a top-up to a
floor, not a recurring 2,000 grant — if your balance is above 2,000 on the 1st, nothing
is added. Free is 100 trial credits then a 10/day top-up.

Costs: most endpoints 1 credit; Smart Money endpoints, `tgm/holders`, `tgm/indicators`,
`profiler/counterparties`, PM top-holders/pnl-by-market/position-detail are 5; historical
(`/v1beta1/`) endpoints are 5× their live counterpart; `address/labels` is **100**;
`premium-labels` is **500**; `premium_labels=true` on leaderboards is **150/call**;
`agent/fast` is 200 and `agent/expert` is **750**. Rate limits: 75/s, 1,500/min on Pro.

Worked examples:

- A "cross-venue wallet page" ≈ PM address-summary (1) + PM pnl-by-address (1) + PM
  trades-by-address (1) + HL perp positions (1) + HL perp trades (1) + spot balances (1)
  + related-wallets (1) + counterparties (5) ≈ **12 credits per lookup → ~166 lookups
  for the entire month** on Pro.
- A parity monitor over 20 markets refreshed hourly = 20 × 2 × 24 = **960 credits/day** —
  the whole month's budget in two days.

**Conclusions:**

1. A naive live dashboard is financially impossible on the standard plan. Any real
   product needs purchased flexi-credits (price not published — ask) or a partnership.
2. Correct architecture: a server-side poller over a **small curated watchlist**, results
   cached and served to all users from your own store; per-user on-demand lookups metered.
   Never call Nansen per page-load per user.
3. Use Nansen for what **only** Nansen has (identity, cross-venue joins, labels-derived
   analysis, PnL history). Polymarket's own CLOB API is free and public for high-frequency
   price/orderbook polling. Spending 1 credit on a quote you can get free is a bug.

Trading endpoints are the exception: **spot and perp trading consume zero plan credits.**

---

## 3. Competitive reality in the two chosen lanes

**Hyperliquid analytics is saturated.** Hyperdash (acquired by pvp.trade, now a full
terminal with liquidation heatmaps, cohort analysis, copy trading and execution),
HyperTracker (1.5M+ wallets, 215k+ open positions on one heatmap), Buildix (311+ pair
screener, CVD, VPIN, whale feed), CoinGlass. Do not build a liquidation heatmap or a
whale feed — those are solved by better-capitalized incumbents, and the leaderboard
endpoint you'd need is prohibited for redistribution anyway.

**Polymarket tooling is crowded on the *flow* side, thin on the *pricing* side.**
Existing: Struct Explorer, PolymarketScan, Polycopy, Kairos, Polymarket Analytics, Dune
dashboards. All whale trackers and copy-trade tools. What's documented as *missing*:

- A study of Bitcoin threshold markets found a **mean 6.3 percentage-point gap** between
  Binance-implied and Polymarket-implied probabilities, persistent with an **AR(1)
  half-life of ~4 hours**, mean-reverting, and profitable after conservative costs on a
  delta-hedged proxy.
- Practitioner write-ups report 5–7% mispricings against options-implied vol and note
  **no bot is continuously enforcing parity** between the options surface and Polymarket.

That gap is the clearest documented, unexploited edge in either lane.

**The structural gap nobody has closed: every one of these tools is single-venue.**
Nothing joins Polymarket ↔ Hyperliquid ↔ spot onchain ↔ wallet identity. Nansen's API is
the only place all four sit behind one key.

---

## 4. What is genuinely differentiated in the Nansen API

Discounting anything you could get free elsewhere:

1. **SAFE proxy → owner resolution on Polymarket.** `prediction-market/top-holders`
   computes positions from ERC-1155 transfers on Polygon "with SAFE proxy wallet
   resolution to identify actual users", returning both `address` and `owner_address`.
   **That `owner_address` is the join key that links a Polymarket trader to their EVM
   identity** — and therefore to their Hyperliquid positions, spot bags, counterparties
   and funding history. This is the single most defensible primitive in the API.
2. **Entity graph:** `related-wallets`, `first-funder`, `counterparties` (+ batch, 10
   addresses per call). Nothing else offers this at this quality.
3. **Point-in-time history (`/api/v1beta1/`, beta):** historical token screener, top
   holders, smart money positions, quant scores, address balances — reconstructed with
   the labels and prices valid on that date. Genuine backtesting without look-ahead bias.
   Polymarket history back to Nov 2022; Hyperliquid perps reliable from May 2025.
4. **Execution in the same API, zero credits:** spot quote → prepare → sign locally →
   execute (Solana and Base, plus SOL↔Base bridge routes), and the full Hyperliquid perp
   prepare → sign → execute flow including builder-fee approval. Keys never leave the
   user. Almost no submission will use this.
5. **Smart Alerts:** server-side alerting with Telegram/Slack/Discord/HMAC-signed webhook
   delivery, including realtime windows. You don't have to build alert infrastructure.
   (Note: smart-money-flow alerts to end users run into the redistribution rules;
   `common-token-transfer` and `smart-contract-call` alerts are fine.)

**Already built by Nansen — do not rebuild:** an MCP server (24 tools,
`https://mcp.nansen.ai/ra/mcp`) and a CLI. "Nansen MCP server" is not a project.

---

## 5. Candidate products

### A. Parity desk for crypto threshold markets  ⭐ recommended

Polymarket's "Will BTC be above $X on date D" markets, priced against the risk-neutral
probability implied by Hyperliquid perps (price, funding, open interest) and realized
vol from token OHLCV. For each market show: implied probability, model probability, the
gap, **the depth actually available at that gap** (orderbook endpoint — this is what
separates a real signal from a screenshot), and EV after fees. Alert when the gap exceeds
a threshold and the depth can absorb size.

- **Endpoints:** `prediction-market/market-screener`, `/ohlcv`, `/orderbook`,
  `tgm/perp-screener`, `tgm/token-ohlcv`. Optionally `/trade/perp/*` to execute the
  hedge leg.
- **Redistribution:** every endpoint ✅ allowed with attribution. Completely clean.
- **Why Nansen:** honestly, Polymarket's own API could supply prices. Nansen's real
  contributions are the perp side, the PnL/trade history to *backtest* the signal, and
  one vendor for the whole stack. Frame it truthfully.
- **Who pays:** systematic traders, small funds. Clear willingness to pay for a monitor.
- **Moat:** the pricing model plus the execution integration, not the data.
- **Risk:** the model *is* the product. A naive Black-Scholes wrapper is worthless. Also
  the classic tension — a working edge is worth more used than sold; sell the monitor,
  not the strategy.
- **1-week scope:** yes. Poller + model + table + Telegram alerts via Smart Alerts.

### B. Cross-venue exposure graph — "the whole position"  ⭐ most uniquely Nansen

Paste an address (or open a market) and see an entity's *total* directional exposure
across Polymarket, Hyperliquid perps and spot at once. Classify the relationships:
hedge (long spot / short perp), conviction stack (long perp + YES on the correlated PM
market), contradiction (bullish PM position while distributing spot). Resolve SAFE
proxies so a Polymarket whale and a Hyperliquid whale are recognisably the same person.

- **Endpoints:** `prediction-market/top-holders` (for `owner_address`), `/pnl-by-address`,
  `/address-summary`, `/trades-by-address`, `profiler/perp-positions`, `/perp-trades`,
  `profiler/address/balances`, `/related-wallets`, `/counterparties`.
- **Redistribution:** all ✅ (PM + related-wallets + counterparties need attribution).
  **Do not display the Nansen label itself** — `address/labels` is prohibited.
- **Why Nansen:** genuinely nobody else can do this. The SAFE-proxy join key does not
  exist anywhere else.
- **Who pays:** fuzzier. Traders wanting to know whether a whale's bet is conviction or a
  hedge; also researchers and journalists.
- **Kill risk — validate first:** Polymarket traders and Hyperliquid traders may be
  largely disjoint populations. If overlap is rare, the product has nothing to show.
  **Measure the overlap rate before committing a single day to this.**
- **1-week scope:** yes, if scoped to one page: address in → exposure out.

### C. Informed-flow detector for Polymarket

For a given market, take top holders → resolve to owners → pull first-funder,
counterparties and related wallets for each → score how plausibly informed each holder is
(e.g. the largest YES holder on "will protocol X launch a token" was funded by an address
that also funded X's deployer).

- **Why Nansen:** first-funder + counterparties + related-wallets at scale. Uniquely
  possible.
- **Demo value:** highest of the three. Editorially irresistible.
- **Monetization:** weakest. Top-of-funnel, not a product.
- **Redistribution:** related-wallets and counterparties ✅ with attribution.
  `first-funder` is **not listed** in the guidelines table — ambiguous, ask Nansen.
- **Serious caution:** publicly scoring named onchain addresses as "insiders" is
  defamation-adjacent. Frame as "funding-graph proximity", never as an accusation, and
  keep a disclaimer.

### D. Signal backtester for onchain theses

Use `/api/v1beta1/` point-in-time endpoints to answer "does X actually predict returns?"
Real product for quant desks, and the endpoints are new enough that almost nobody will
use them.
- **Blocker:** the interesting signals are smart-money-derived — restricted or prohibited
  for redistribution. A backtest *result* is plausibly "significant modification", but
  that needs written approval. Also 5× credit cost. Hard to ship in a week.

### E. Don't build
Liquidation heatmaps, whale feeds, smart-money terminals, top-trader leaderboards, copy-
trading off a Nansen leaderboard, an MCP server. Saturated, prohibited, or already shipped
by Nansen.

---

## 6. Recommendation

**A as the product, B as the differentiator.** Ship the parity desk — it has a clean
buyer, clean redistribution status, and a documented unexploited edge — and use the
cross-venue identity join (B) as the feature that makes it obviously Nansen-native and
impossible to clone from Polymarket's free API: *not just that the gap exists, but who is
on the other side of it and what else they're holding.*

That combination is the one thing in either lane that is simultaneously unbuilt, legal to
ship, and buildable in a week.

---

## 7. Next 24 hours — validate before building

Get a **free** key at `https://app.nansen.ai/auth/agent-setup` (100 trial credits) and
smoke-test four things. Each answer can kill an idea, so do this before writing product code.

1. **Does `prediction-market/top-holders` actually populate `owner_address`?**
   If SAFE proxies aren't resolved in practice, idea B loses its join key.
2. **What's the Polymarket ↔ Hyperliquid ↔ spot overlap rate?** Pull top holders from
   ~10 large markets, resolve to owners, check how many have Hyperliquid positions or
   meaningful spot balances. Low overlap kills B.
3. **Is `tgm/perp-screener` returning usable funding + open interest**, and how many
   crypto-threshold markets does `market-screener` surface with real liquidity? Thin
   liquidity kills A.
4. **How fresh is the PM orderbook really?** Docs say polled from Polymarket's CLOB
   roughly every 60s with MD5 change detection — confirm, because the tradeable depth
   number is the core of A.

Also worth asking the organizers directly:
- Credit grant for participants, and the price of flexi-credits at volume (the $49/mo
  plan cannot support a live product).
- Whether buildathon entries get a redistribution waiver, and what the approval timeline
  looks like for the restricted endpoints.
- Judging criteria — still not published anywhere findable.
