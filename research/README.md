# Research log

How the product arrived at what it claims. Kept because the central result —
that flow magnitude does *not* predict returns — came from falsifying our own
thesis, and the record of that is more useful than the conclusion alone.

Read in this order:

| File | What it covers |
|---|---|
| [RESEARCH.md](RESEARCH.md) | Nansen API survey; why prediction markets and perps were the clean lanes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | First design (swap-chain tracing) and the two corrections that killed it |
| [FINDINGS.md](FINDINGS.md) | The BNB pilot failure: launchpad settlement is invisible to DEX-trade endpoints |
| [RESULTS.md](RESULTS.md) | Four falsification tests of "does flow predict returns". All null |
| [VALIDATED.md](VALIDATED.md) | What survived: coverage, precision lift, lead time, and the persistence finding |
| [PRODUCT.md](PRODUCT.md) | Interface design rationale |
| [BUDGET.md](BUDGET.md) | Measured credit costs per pipeline stage |

`scripts/` holds the analysis code behind those documents — leave-one-out
coverage, the event studies, and the earlier pipeline. None of it is on the
production path; `make.py` does not import from here.
