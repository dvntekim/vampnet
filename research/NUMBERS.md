# Canonical numbers

Every figure Cavitation displays, in one place, with the run that produced it.

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
| Window | 141 days (May 1 – Sep 18) | 48 days, frozen Aug 31 |
| Cohort | 741 wallets, **4+** winning tokens | 125 wallets, **2+** winning tokens |
| Chains | robinhood, bnb, base, solana | robinhood only |
| Built by | `make.py --full` | `research/scripts/out_of_time.py` |

The map runs at 4+ because a stricter cohort produces a denser, more legible graph.
The coverage claim is measured at 2+ on Robinhood because that is the configuration the
out-of-time test was actually run on, and because the pilot found that tightening the
threshold *shrinks* coverage faster than it raises quality (38% at 4+ vs 75% at 2+ —
see [VALIDATED.md](VALIDATED.md#design-rule-breadth-beats-strictness)).

**These have not yet been reconciled on the same run.** Doing so is one command:

```bash
python3 research/scripts/out_of_time.py \
        --freeze 2026-08-31 --recurrence 4 \
        --chains robinhood,bnb,base,solana --cap 6000 --write-claims
python3 make.py --build
```

That measures the shipped map's own cohort out-of-time and rewrites `claims.json` with
whatever it finds. Until it is run, the displayed coverage figure is the one that has a
measurement behind it, not the one that flatters the map.

---

## The claims

| Claim | Value | Scope | Provenance |
|---|---:|---|---|
| Out-of-time coverage | **75%** (6/8) | Cohort frozen 31 Aug with zero September information, tested against the 8 Robinhood winners that emerged 1–18 Sep. Naive cross-chain coverage on the same test: 20%. | [VALIDATED.md](VALIDATED.md#production-configuration) · `out_of_time.py` |
| Precision lift | **23×** | 28.6% vs a 1.24% base rate. Leave-one-out: of 2,813 tokens touched, the 35 passing ≥8 wallets AND >$250k peak contained 10 of 35 winners. | [VALIDATED.md](VALIDATED.md#2-precision) · `coverage.py` |
| Median lead | **16 days** | First cohort entry → price peak, across 30 covered winners. Raw median 23d; 16d after removing 7 left-censored entries. 0/30 entered after the peak. | [VALIDATED.md](VALIDATED.md#3-timing) · `coverage.py` |
| Repeat-winner rate | **8.6% – 0.0%** | Per chain, from 2,808 traders across 34 winning tokens. Robinhood 8.6%, BNB 4.2%, Base 0.8%, Solana 0.2%, Ethereum 0.0%. | [VALIDATED.md](VALIDATED.md#why-trader-persistence-is-an-ecosystem-property) |

## Withdrawn

| Claim | Why |
|---|---|
| ~~91% out-of-time coverage (10 of 11)~~ | No script, run log or table in this repository reproduces it. It existed only as a hardcoded literal in `make.py`. The same repository's out-of-time test reports 20% naive / 60% Robinhood-only / 75% production over the 48-day window. Recorded under `_pending` in `claims.json` and re-testable with the command above. |

## What is still not claimed

- **Flow magnitude does not predict returns.** Four falsification tests, all null — see
  [RESULTS.md](RESULTS.md).
- **Crowding is mildly bearish**: ≥3 cohort wallets entering predicted −12.5% at 5 days.
- **Precision is not certainty.** ~71% of high-conviction names never run.
- **Coverage is ecosystem-bound.** Below roughly 4% repeat-winner rate, a cohort strategy
  has no headroom at all. The Persistence panel reports this per chain rather than hiding it.
- One window, one market regime.
