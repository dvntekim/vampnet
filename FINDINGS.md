# Stage 1 Pilot — MARSCOIN (BNB). Findings

**Credits: 13 used, 75 remaining** (88 start). Free 422-probe technique confirmed: rejected
requests are quoted but not billed, so schema discovery costs nothing.

## What worked

**Price history is clean and the case is textbook.** MARSCOIN launched 2026-07-27 at $0.000198,
chopped around $0.04 through August, ran 3.6× from Sept 1–5 ($0.066 → $0.241, volume $3.6M →
$55.7M), peaked at a **$245M mcap on 2026-09-05**, and bled to $91M by Sept 16 (**−62%**).

**The top-trader leaderboard is high quality.** 50 traders, median 29 trades, no router or
contract labels, no infrastructure addresses. **The router-contamination risk did not
materialise** — these are real people and funds.

- **35 of 50 fully exited**, realising **$9.4M** combined
- 11 still hold, $1.2M unrealised
- Top trader: **$2.1M realised, 656% ROI, fully exited**

**The FOMO thesis is directly visible.** The #1 trader is labelled
`Uses "TRYFOMO" HL Referral Code`. Two others carry `BIGTROUT300` and `MMREFCSI` referral
labels. Nansen tags wallets by which platform funnel they came through — an unexpected
social-graph signal, relevant to both the rotation thesis and the socialfi angle.

## What broke: BNB launchpad tokens are poorly enriched

The rotation trace requires seeing a wallet sell A and buy B. On BNB that data is largely
missing or unusable:

| Source | Expected | Actual |
|---|---|---|
| Leaderboard (wallet `0x0c175c…`) | $1.2M max position, $2.4M net outflow, 247 trades | — |
| `profiler/dex-trades`, full lifetime window | those buys and sells | **8 trades total**; MARSCOIN **bought $0**, sold $22K |
| `tgm/dex-trades` (token level, peak window) | enriched trades | 100 rows, **all symbols and USD values null** |
| `profiler/address/transactions` | the missing flow | 100 txns, but 98 are dividend/airdrop spam (`batchDistributeDividend`), **0 symbols, 0 USD values, 0 MARSCOIN events** |

Coverage is also **inconsistent between wallets**: `0x84b296deed` traced fine (500 trades,
MARSCOIN bought $116K / sold $532K), while the top TRYFOMO wallet was nearly invisible.

### Diagnosis
These BNB tokens trade through **launchpad contracts** (flap.sh) rather than standard DEX
pairs — the transaction method is `execute(address[],uint256)` against a token contract, not a
swap against a pair. Nansen's DEX-trade classifier doesn't capture that path, and the token
metadata (symbol, USD value) isn't enriched for these contracts either.

Notably, the wallet routed through **FOMO is the least traceable one** — consistent with the
platform settling trades off the standard DEX path. The complication arrived in a different
form than predicted: not "top wallets are routers," but "real traders are invisible."

## Conclusion

The **method** is sound — the leaderboard gives real traders with clean exit data. The
**substrate** is wrong. BNB launchpad memecoins don't produce traceable rotation.

**Recommended: re-run the pilot on STONK (Solana).** $139.7M mcap, **$35.6M daily volume**
through real Solana DEXs, which is Nansen's strongest coverage area for memecoins. Trades
should carry proper symbols and USD values.

Trade-off: Solana can't be followed cross-chain (separate keypair space), so this proves
rotation tracing works before extending to the cross-chain question — rather than failing at
both simultaneously.

Estimated cost: ~5 (leaderboard) + 1 (OHLCV) + ~15 (wallet traces) + ~10 (destination prices)
≈ **31 credits**, leaving ~44.
