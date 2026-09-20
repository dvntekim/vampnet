#!/usr/bin/env python3
"""
Out-of-time coverage test — the script behind the headline number.

The claim "N% of unseen winners were already held by the cohort" is only worth
anything if the cohort provably could not see those winners when it was built.
This enforces that by construction:

    TRAIN   winners resolved in a window that ENDS on the freeze date
    COHORT  wallets in the top-PnL of >= R separate TRAIN winners, leaderboards
            also bounded by the freeze date  -> zero post-freeze information
    TEST    winners that emerged AFTER the freeze date and are not TRAIN winners
    RESULT  fraction of TEST winners that the frozen cohort actually held

Anything the cohort could have learned from the test period is excluded on both
sides: the screener window, the leaderboard window, and the token set.

    python3 research/scripts/out_of_time.py --freeze 2026-08-31 --chains robinhood
    python3 research/scripts/out_of_time.py --freeze 2026-08-31 --recurrence 4 \
            --chains robinhood,bnb,base,solana --cap 6000

Writes research/out_of_time_<freeze>.json and, with --write-claims, updates the
`oot` and `cohort` entries of research/claims.json in place.
"""
import argparse
import collections
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from nansen import call                      # noqa: E402
from fetch_balances import fetch             # noqa: E402

EVM = {"bnb", "base", "ethereum", "robinhood", "hyperevm", "arbitrum", "polygon"}
STABLE = {"USDC", "USDT", "USDG", "USDE", "USD1", "USAD", "PYUSD", "RLUSD", "DAI", "WETH",
          "ETH", "WBNB", "BNB", "BTCB", "CBBTC", "WBTC", "DSOL", "SOL", "HYPE", "JITOSOL",
          "MSOL", "USDON"}
EQUITY = {"NVDA", "AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "META", "INTC", "AMD", "PLTR",
          "SPY", "COIN", "MU", "ORCL", "CRWV", "SNDK", "USAR", "BE", "QQQ", "NFLX", "AVGO",
          "SMCI", "MSTR", "IBIT", "HOOD", "DIH", "SPCX"}
skip = lambda s: (s or "").upper() in STABLE | EQUITY


def log(msg):
    print(f"  {msg}", flush=True)


class Budget:
    """Same hard-stop contract as make.py: never silently overspend."""

    def __init__(self, cap):
        self.cap, self.used = cap, 0

    def add(self, headers):
        self.used += int(headers.get("x-nansen-credits-used") or 0)
        if self.used > self.cap:
            raise SystemExit(f"\n!! credit cap of {self.cap} reached ({self.used} used) — stopping.")
        return headers.get("x-nansen-credits-remaining")


def screener(chains, date_from, date_to, cfg, B):
    """Winner universe over an explicit window. Definition is identical on both
    sides of the freeze — only the dates move."""
    st, b, h = call("/api/v1/token-screener", {
        "chains": chains,
        "date": {"from": date_from, "to": date_to},
        "filters": {"market_cap_usd": {"min": cfg["min_mcap"]},
                    "volume": {"min": cfg["min_vol"]},
                    "price_change": {"min": cfg["min_gain"]}},
        "order_by": [{"field": "price_change", "direction": "DESC"}],
        "pagination": {"page": 1, "per_page": 100}})
    B.add(h)
    if st != 200:
        raise SystemExit(f"token-screener returned {st}: {b}")
    return [r for r in b.get("data", []) if not skip(r.get("token_symbol"))]


def frozen_cohort(train, freeze, cfg, B):
    """Wallets that won >= R separate TRAIN tokens, using leaderboards whose window
    ends at the freeze date. No post-freeze row can reach this set."""
    appear = collections.defaultdict(set)
    space = {}
    for i, w in enumerate(train, 1):
        st, b, h = call("/api/v1/tgm/pnl-leaderboard", {
            "chain": w["chain"], "token_address": w["token_address"],
            "date": {"from": cfg["train_from"], "to": freeze},
            "pagination": {"page": 1, "per_page": cfg["lb_depth"]}})
        rem = B.add(h)
        if st == 200 and b.get("data"):
            ev = w["chain"] in EVM
            for r in b["data"]:
                a = r["trader_address"].lower() if ev else r["trader_address"]
                appear[a].add(f'{w["chain"]}|{w["token_symbol"]}')
                space[a] = "evm" if ev else "sol"
        if i % 10 == 0:
            log(f"leaderboards {i}/{len(train)}  rem={rem}")
    coh = {a: sorted(v) for a, v in appear.items() if len(v) >= cfg["recurrence"]}
    return coh, space, len(appear)


def held(bal, test):
    """Did the frozen cohort hold each TEST winner at any point in the test window?"""
    idx = collections.defaultdict(lambda: collections.defaultdict(set))
    for wallet, chains in bal.items():
        for ch, rows in (chains or {}).items():
            for r in rows:
                if (r.get("token_amount") or 0) <= 0:
                    continue
                key = (ch, (r.get("token_address") or "").lower())
                idx[key][r["block_timestamp"][:10]].add(wallet)
    out = []
    for w in test:
        key = (w["chain"], (w["token_address"] or "").lower())
        days = sorted(idx.get(key, {}))
        first = days[0] if days else None
        out.append({
            "symbol": w.get("token_symbol"), "chain": w["chain"],
            "price_change": w.get("price_change"),
            "covered": first is not None,
            "first_held": first,
            "peak_wallets": max((len(idx[key][d]) for d in days), default=0),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freeze", required=True, help="cohort sees nothing after this date")
    ap.add_argument("--to", default=dt.date.today().isoformat(), help="end of the test window")
    ap.add_argument("--train-days", type=int, default=30, help="length of the training window")
    ap.add_argument("--recurrence", type=int, default=2, help="winning tokens a wallet must hit")
    ap.add_argument("--chains", default="robinhood", help="comma-separated")
    ap.add_argument("--lb-depth", type=int, default=100, help="PnL leaderboard rows per token")
    ap.add_argument("--min-mcap", type=int, default=2_000_000)
    ap.add_argument("--min-vol", type=int, default=1_000_000)
    ap.add_argument("--min-gain", type=float, default=1.0, help="price_change floor, 1.0 = +100%%")
    ap.add_argument("--pages", type=int, default=6, help="balance pages per wallet")
    ap.add_argument("--cap", type=int, default=3000, help="hard credit ceiling")
    ap.add_argument("--write-claims", action="store_true",
                    help="update research/claims.json with the measured result")
    a = ap.parse_args()

    if a.freeze >= a.to:
        raise SystemExit("--freeze must be before --to, or there is no out-of-time period.")

    chains = [c.strip() for c in a.chains.split(",") if c.strip()]
    train_from = (dt.date.fromisoformat(a.freeze) - dt.timedelta(days=a.train_days)).isoformat()
    test_from = (dt.date.fromisoformat(a.freeze) + dt.timedelta(days=1)).isoformat()
    cfg = {"min_mcap": a.min_mcap, "min_vol": a.min_vol, "min_gain": a.min_gain,
           "lb_depth": a.lb_depth, "recurrence": a.recurrence, "train_from": train_from}
    B = Budget(a.cap)

    print(f"Out-of-time test   train {train_from} → {a.freeze}   "
          f"test {test_from} → {a.to}   chains {','.join(chains)}   cap {a.cap}\n")

    train = screener(chains, train_from, a.freeze, cfg, B)
    log(f"[1/4] TRAIN winners: {len(train)}")

    test_all = screener(chains, test_from, a.to, cfg, B)
    train_keys = {(w["chain"], (w["token_address"] or "").lower()) for w in train}
    test = [w for w in test_all
            if (w["chain"], (w["token_address"] or "").lower()) not in train_keys]
    log(f"[2/4] TEST winners: {len(test)} new "
        f"({len(test_all) - len(test)} already winners before the freeze, excluded)")
    if not test:
        raise SystemExit("No unseen winners in the test window — nothing to measure.")

    coh, space, pool = frozen_cohort(train, a.freeze, cfg, B)
    log(f"[3/4] pool {pool:,} traders → frozen cohort {len(coh)} wallets "
        f"(>= {a.recurrence} TRAIN winners)")
    if not coh:
        raise SystemExit("Frozen cohort is empty — lower --recurrence or widen --train-days.")

    ev = [w for w in coh if space[w] == "evm"]
    sol = [w for w in coh if space[w] == "sol"]
    evm_chains = [c for c in chains if c in EVM]
    bal = {}
    for i, wallet in enumerate(ev + sol, 1):
        chs = evm_chains if space[wallet] == "evm" else ["solana"]
        rec = {}
        for ch in chs:
            try:
                rows, used, rem, st = fetch(wallet, ch, {"from": test_from, "to": a.to},
                                            cap_pages=a.pages)
            except Exception:
                continue
            B.used += used
            if B.used > B.cap:
                raise SystemExit(f"\n!! credit cap reached ({B.used}) — partial data, not written.")
            if st == 200 and rows:
                rec[ch] = rows
        bal[wallet] = rec
        if i % 15 == 0 or i == len(coh):
            log(f"[4/4] balances {i}/{len(coh)}  credits={B.used}")

    rows = held(bal, test)
    covered = sum(1 for r in rows if r["covered"])
    rate = round(100.0 * covered / len(rows))

    by_chain = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        by_chain[r["chain"]][1] += 1
        by_chain[r["chain"]][0] += 1 if r["covered"] else 0

    result = {
        "measured": dt.date.today().isoformat(),
        "protocol": "frozen-cohort out-of-time",
        "train_window": {"from": train_from, "to": a.freeze},
        "test_window": {"from": test_from, "to": a.to},
        "chains": chains,
        "recurrence": a.recurrence,
        "cohort_wallets": len(coh),
        "trader_pool": pool,
        "train_winners": len(train),
        "test_winners": len(rows),
        "covered": covered,
        "coverage_pct": rate,
        "by_chain": {c: {"covered": v[0], "total": v[1],
                         "pct": round(100.0 * v[0] / v[1]) if v[1] else 0}
                     for c, v in sorted(by_chain.items())},
        "credits_used": B.used,
        "detail": sorted(rows, key=lambda r: (not r["covered"], r["symbol"] or "")),
    }
    out = os.path.join(ROOT, "research", f"out_of_time_{a.freeze}.json")
    json.dump(result, open(out, "w"), indent=2)

    print(f"\n  COVERAGE  {covered}/{len(rows)} = {rate}%   "
          f"cohort {len(coh)} wallets, {a.recurrence}+ threshold")
    for c, v in sorted(by_chain.items()):
        print(f"    {c:<12} {v[0]}/{v[1]}")
    for r in rows:
        if not r["covered"]:
            print(f"    MISS  {r['symbol']} ({r['chain']})")
    print(f"\n  {B.used} credits · written to {os.path.relpath(out, ROOT)}")

    if a.write_claims:
        cf = os.path.join(ROOT, "research", "claims.json")
        claims = json.load(open(cf))
        claims["oot"].update({
            "value": rate, "detail": f"{covered} of {len(rows)}",
            "scope": (f"Cohort frozen {a.freeze} with zero post-freeze information, tested "
                      f"against the {len(rows)} winners that emerged {test_from} to {a.to} on "
                      f"{', '.join(chains)}."),
            "source": f"research/out_of_time_{a.freeze}.json",
            "script": "research/scripts/out_of_time.py",
            "verified": result["measured"]})
        claims["cohort"].update({
            "value": len(coh),
            "scope": (f"wallets in the top-{a.lb_depth} PnL of >= {a.recurrence} separate "
                      f"{'/'.join(chains)} winners, frozen {a.freeze}"),
            "source": f"research/out_of_time_{a.freeze}.json",
            "verified": result["measured"]})
        claims.pop("_pending", None)
        json.dump(claims, open(cf, "w"), indent=2)
        print("  research/claims.json updated · rebuild the site with: python3 make.py --build")


if __name__ == "__main__":
    main()
