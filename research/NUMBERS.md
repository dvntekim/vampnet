# Canonical numbers

Every figure Vampnet displays, in one place, with the run that produced it.

The rule: **no number appears in `README.md`, `SUBMISSION.md` or on the rendered site
unless it is in [`claims.json`](claims.json) with a provenance entry.** `make.py` reads
that file to build the payload, so the site cannot drift from the research behind it.

---

## Two configurations, and why they differ

The repository contains measurements from two runs. They are not interchangeable, and
conflating them is the single easiest way to misread this project.

| | **The map** | **The validation** |
|---|---|---|
| What it is | What the site renders | What the coverage claim is measured on |
| Window | 141 days (May 3 – Sep 20) | 30-day train, 20-day test, frozen Aug 31 |
| Threshold | **4+** winning tokens | **4+** winning tokens — same |
| Cohort | 741 wallets | 15 wallets |
| Chains | robinhood, bnb, base, solana | robinhood, bnb, base, solana — same |
| Built by | `make.py --full` | `research/scripts/out_of_time.py` |

They now differ in **one** dimension: window length. The threshold and the chain set match
the map exactly, which is what makes the coverage figure a statement about this product
rather than about a different configuration that happened to score well.

**Reconciled on 2026-09-20.** The coverage figure is now measured at the map's own 4+
threshold, so the two configurations differ only in window length:

```
train 2026-08-01 → 2026-08-31   75 winning tokens
test  2026-09-01 → 2026-09-20   24 new winners (21 pre-freeze winners excluded)
pool  5,399 traders → frozen cohort 15 wallets (>= 4 TRAIN winners)

COVERAGE 10/24 = 42%      robinhood 7/9 · base 2/3 · bnb 1/6 · solana 0/6
515 credits
```

The frozen cohort is 15 wallets rather than 741 because one month is a short window in
which to win four separate tokens; the map earns 741 at the same threshold over 141 days.
That makes this a test of the *method* at the map's threshold, not of the map's exact
cohort — a distinction worth stating before anyone else does.

**When the cohort arrived.** Balances are only fetched from the first day of the test
window, so entries cannot be observed before it. Four of the ten covered winners
(OPTIMUS, ORBIO, PRISM, WEBSITE) were already held on that first observable day, meaning
the position was taken *at or before* the window opened — the cohort was positioned before
September began, not reacting inside it. The remaining six were picked up on days 2, 3, 4,
6, 6 and 13. No covered winner was first held in the final week.

`price_change` in the artifact is a **ratio, not a percent** (the screener filter is
`min_gain: 1.0`, meaning +100%), so ORBIO's `16` is roughly +1,500%. Read it as a multiple
or the numbers look absurdly small.

Re-run at any freeze date with:

```bash
python3 research/scripts/out_of_time.py \
        --freeze 2026-08-31 --recurrence 4 \
        --chains robinhood,bnb,base,solana --cap 6000 --write-claims
python3 make.py --build
```

---

## The claims

| Claim | Value | Scope | Provenance |
|---|---:|---|---|
| Out-of-time coverage | **78%** (7/9) | Cohort frozen 31 Aug, 4+ threshold, tested on the 9 Robinhood winners that first appeared 1–20 Sep. | [out_of_time_2026-08-31.json](out_of_time_2026-08-31.json) |
| Naive coverage | **42%** (10/24) | The same run across all four chains, unscoped. Printed beside the 78% so it is never read as cross-chain. | [out_of_time_2026-08-31.json](out_of_time_2026-08-31.json) |
| Precision lift | **23×** | 28.6% vs a 1.24% base rate. Leave-one-out: of 2,813 tokens touched, the 35 passing ≥8 wallets AND >$250k peak contained 10 of 35 winners. | [VALIDATED.md](VALIDATED.md#2-precision) · `coverage.py` |
| Median lead | **16 days** | First cohort entry → price peak, across 30 covered winners. Raw median 23d; 16d after removing 7 left-censored entries. 0/30 entered after the peak. | [VALIDATED.md](VALIDATED.md#3-timing) · `coverage.py` |
| Map cohort | **741 wallets** | Cleared 4+ separate winning tokens out of 32,128 traders scanned. Verified 2026-09-20 as `len(data/cohort_v2_balances.json)` — the full run writes one entry per cohort wallet. **Not** the 739 in `cache.json.gz`, which counts wallets appearing in the 150 cached tokens. | `make.py --full` |
| Repeat-winner rate | **8.6% – 0.0%** | Per chain, from 2,808 traders across 34 winning tokens. Robinhood 8.6%, BNB 4.2%, Base 0.8%, Solana 0.2%, Ethereum 0.0%. | [VALIDATED.md](VALIDATED.md#why-trader-persistence-is-an-ecosystem-property) |

### Why 741 and not 708

An earlier draft of `SUBMISSION.md` stated 708 in one paragraph and 741 in another. 741 is
correct. It is confirmed directly from the full run's own output rather than from prose:

```bash
python3 -c "import json;print(len(json.load(open('data/cohort_v2_balances.json'))))"
# 741
```

`step3_balances` writes exactly one entry per cohort wallet, so that length *is*
`len(ev) + len(sol)` — the count of wallets that cleared the recurrence threshold. Two
other numbers float nearby and are not the cohort: **739** (wallets holding one of the 150
cached tokens) and **40** (the `--demo` preset's `max_wallets` cap, which overwrites
`cohort_live_v2.json` whenever a demo run happens after a full one).

## Withdrawn

| Claim | Why |
|---|---|
| ~~91% out-of-time coverage (10 of 11)~~ | No script, run log or table reproduced it; it existed only as a hardcoded literal in `make.py`. **Superseded by measurement** on 2026-09-20: the same protocol at the same 4+ threshold returns 78% on Robinhood and 42% naive. The claim is no longer merely unverified — it has been tested and replaced. |

## What is still not claimed

- **Flow magnitude does not predict returns.** Four falsification tests, all null — see
  [RESULTS.md](RESULTS.md).
- **Crowding is mildly bearish**: ≥3 cohort wallets entering predicted −12.5% at 5 days.
- **Precision is not certainty.** ~71% of high-conviction names never run.
- **Coverage is ecosystem-bound.** Below roughly 4% repeat-winner rate, a cohort strategy
  has no headroom at all. Each chain chip in the masthead carries its own rate rather than hiding it.
- One window, one market regime.
