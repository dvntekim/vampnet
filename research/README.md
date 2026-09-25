# Research log

How the product arrived at what it claims. Kept because the central result —
that flow magnitude does *not* predict returns — came from falsifying our own
thesis, and the record of that is more useful than the conclusion alone.

Read in this order:

| File | What it covers |
|---|---|
| **[NUMBERS.md](NUMBERS.md)** | **Start here. Every displayed figure, its scope, and the run that produced it** |
| [RESEARCH.md](RESEARCH.md) | Nansen API survey; why prediction markets and perps were the clean lanes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | First design (swap-chain tracing) and the two corrections that killed it |
| [FINDINGS.md](FINDINGS.md) | The BNB pilot failure: launchpad settlement is invisible to DEX-trade endpoints |
| [RESULTS.md](RESULTS.md) | Four falsification tests of "does flow predict returns". All null |
| [VALIDATED.md](VALIDATED.md) | What survived: coverage, precision lift, lead time, and the persistence finding |
| [STABILITY.md](STABILITY.md) | How hard the coverage headline is. Moving the freeze date, and the API retention limit that caps how far back any sweep can reach |
| [PRODUCT.md](PRODUCT.md) | Interface design rationale |
| [BUDGET.md](BUDGET.md) | Measured credit costs per pipeline stage |

`scripts/` holds the analysis code behind those documents — leave-one-out
coverage, the frozen-cohort out-of-time test, the event studies, and the earlier
pipeline.

| Script | Produces |
|---|---|
| [scripts/out_of_time.py](scripts/out_of_time.py) | The coverage headline. Builds a cohort that provably cannot see the test period, then measures what it held. `--write-claims` updates `claims.json` in place |
| [scripts/coverage.py](scripts/coverage.py) | Leave-one-out coverage, precision lift, lead time, first sightings |
| [scripts/walk_forward.py](scripts/walk_forward.py) | Re-runs the frozen-cohort test at several freeze dates and records which ones the API still has data for |
| [scripts/fresh_inflows.py](scripts/fresh_inflows.py) | Counts the fresh inflows a top-N edge cap would discard, by replaying the renderer's own edge selection |
| [scripts/fresh_signal_backtest.py](scripts/fresh_signal_backtest.py) | Every fresh-inflow signal and what the token's market cap did next. In-sample: for picking illustrations, not for claims |

`make.py` imports none of it, with one deliberate exception: it reads
[claims.json](claims.json) so that no headline number can be hardcoded into the
pipeline. Changing a displayed figure means re-measuring it.
