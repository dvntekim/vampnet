#!/usr/bin/env python3
"""
Coverage against a third party's winner list, not our own screener's.

    python3 research/scripts/independent_calls.py

Every coverage number in this repository so far shares a weakness: the test
winners are chosen by our own `token-screener` thresholds. A reader can fairly
ask whether the thresholds were picked, consciously or not, to select coins the
cohort happened to hold.

This removes that objection by taking the winner list from outside: the daily
memecoin recaps published by @mellometrics, which are editorial, dated, and
written with no knowledge of this project. The question becomes:

    Of the coins a working trader publicly called out, how many was the cohort
    already holding — and did it hold them BEFORE the call was published?

The second half is the part that matters. Holding a coin the same day someone
writes it up is unremarkable. Holding it a week earlier is the claim.

DISAMBIGUATION. A ticker like NPC exists on seven chains, and picking the
largest by market cap is wrong — the recap's NPC is a $2.6m pump.fun launch,
not a $192m Robinhood token with the same three letters. Each candidate is
therefore scored against the market cap the recap itself states, using
token-ohlcv over the days around publication, and the closest match wins. A
candidate that is nowhere near the stated figure is discarded rather than
counted, because a wrong match inflates coverage in both directions.
"""
import collections
import datetime as dt
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from nansen import call, search_token          # noqa: E402
from build_bubbles import load_cache            # noqa: E402

OUT = os.path.join(ROOT, "research", "independent_calls.json")
CACHE = os.path.join(ROOT, "data", "cache.json.gz")

# Published by @mellometrics. (symbol, market cap the recap states, in USD).
# Transcribed verbatim; nothing filtered for being convenient.
RECAPS = {
    "2026-09-22": [
        ("MUSEBOOK", 46e6), ("AGRIPPA", 9.8e6), ("MONITOR", 13.5e6), ("SI", 10e6),
        ("NOSH", 5e6), ("CREDITS", 1.4e6), ("JEANPHIL", 8.5e6), ("GP", 21e6),
        ("GROK", 6.7e6), ("FOMOPAY", 4.5e6), ("AGI", 3e6), ("X7", 3e6),
        ("SUIT", 1.9e6), ("TRENDS", 1.3e6),
    ],
    "2026-09-23": [
        ("GP", 32.5e6), ("CRACKER", 22e6), ("DUEL", 3.4e6), ("SANTA", 1.8e6),
        ("GNOME", 1.3e6), ("WISE", 1.2e6), ("SPIKE", 4e6), ("SI", 10.3e6),
        ("GROK", 6.3e6), ("PRISM", 25e6), ("MASK", 5e6), ("PRIORS", 2.3e6),
        ("HADES", 1.6e6), ("RUNUP", 1.4e6), ("QUANTA", 1.4e6), ("BUCKET", 5.7e6),
        ("AGI", 3.4e6), ("HYPERCAT", 3.3e6), ("FAMILIARS", 3.2e6),
        ("SHARTCOIN", 2.8e6), ("BOP", 2e6), ("GOON", 1.2e6), ("BLUF", 1e6),
    ],
    "2026-09-24": [
        ("NPC", 2.6e6), ("SEND", 15e6), ("CONDO", 2.3e6), ("GO", 10e6),
        ("OG", 0.45e6), ("NEET", 50e6), ("AGRIPPA", 12.6e6), ("JOLLY", 4e6),
        ("GOCOLLECT", 2e6), ("MASK", 8.7e6), ("FAMILIARS", 3.7e6),
        ("PRIORS", 3.3e6), ("QUANTA", 1.5e6), ("STONKBLEND", 1.3e6),
        ("SHARTCOIN", 5e6), ("GOON", 2.4e6), ("FOOMS", 1.6e6), ("SI", 0.85e6),
    ],
}
TOL = 0.45          # a candidate must land within +/-45% of the stated cap


def peak_mcap(chain, address, day):
    """Highest market cap in the week ending on the recap date. A recap reports
    the peak a coin 'hit', which can be a few days before it is written up, so a
    three-day probe missed real matches — MONITOR and NOSH both fell out that
    way despite the cohort demonstrably holding them."""
    lo = (dt.date.fromisoformat(day) - dt.timedelta(days=7)).isoformat()
    st, b, _ = call("/api/v1/tgm/token-ohlcv", {
        "chain": chain, "token_address": address,
        "timeframe": "1d", "date": {"from": lo, "to": day}})
    if st != 200 or not (b or {}).get("data"):
        return 0.0
    best = 0.0
    for r in b["data"]:
        m = r.get("market_cap")
        v = (m.get("close") if isinstance(m, dict) else m) or 0
        best = max(best, float(v or 0))
    return best


def main():
    idx, sym = load_cache(CACHE)
    held = {}
    for key, bd in idx.items():
        s = (sym.get(key) or "").upper()
        if not s:
            continue
        days = sorted(bd)
        rec = (key[0], days[0], days[-1], max(len(w) for w in bd.values()))
        # keep the earliest first-held entry if a symbol appears twice
        if s not in held or days[0] < held[s][1]:
            held[s] = rec

    rows, spent, seen = [], 0, {}
    for day, calls in sorted(RECAPS.items()):
        for symbol, stated in calls:
            if (symbol, day) in seen:
                continue
            seen[(symbol, day)] = True
            st, b, h = search_token(symbol)
            spent += int(h.get("x-nansen-credits-used") or 0)
            cands = [t for t in (b or {}).get("tokens", [])
                     if (t.get("symbol") or "").upper() == symbol]
            # One candidate is not ambiguous, so there is nothing to disambiguate
            # and no reason to make it clear a market-cap bar it was never being
            # compared against. Probing only matters when a ticker is contested.
            if len(cands) == 1:
                match, best_err = cands[0], 0.0
            else:
                best, best_err = None, 9e9
                for t in cands[:6]:                   # cap the probing per ticker
                    mc = peak_mcap(t["chain"], t["address"], day)
                    spent += 1
                    if not mc:
                        continue
                    err = abs(mc - stated) / stated
                    if err < best_err:
                        best, best_err = t, err
                    time.sleep(0.05)
                match = best if best and best_err <= TOL else None
            hit = held.get(symbol)
            # only count a holding as a hit when the chain agrees
            covered = bool(match and hit and hit[0] == match["chain"])
            lead = None
            if covered:
                lead = (dt.date.fromisoformat(day) - dt.date.fromisoformat(hit[1])).days
            rows.append({
                "recap_date": day, "symbol": symbol, "stated_mcap": stated,
                "chain": match["chain"] if match else None,
                "address": match["address"] if match else None,
                "match_error": round(best_err, 3) if match else None,
                "cohort_holds": covered,
                "first_held": hit[1] if covered else None,
                "lead_days": lead,
                "peak_wallets": hit[3] if covered else None,
            })
            time.sleep(0.05)

    resolved = [r for r in rows if r["chain"]]
    by_chain = collections.Counter(r["chain"] for r in resolved)
    rh = [r for r in resolved if r["chain"] == "robinhood"]
    rh_hit = [r for r in rh if r["cohort_holds"]]
    leads = sorted(r["lead_days"] for r in rh_hit)
    med = leads[len(leads) // 2] if leads else None
    # A coin called on two days is one coin. Counting call-instances would let a
    # repeated mention move the percentage, which says nothing about coverage.
    d_all = {r["symbol"] for r in rh}
    d_hit = {r["symbol"] for r in rh_hit}
    d_lead = sorted(min(r["lead_days"] for r in rh_hit if r["symbol"] == s) for s in d_hit)
    d_med = d_lead[len(d_lead) // 2] if d_lead else None

    res = {"measured": dt.date.today().isoformat(),
           "source": "@mellometrics daily memecoin recaps, 22-24 Sep 2026",
           "protocol": "third-party winner list; ticker disambiguated by stated market cap",
           "tolerance": TOL, "calls": len(rows), "resolved": len(resolved),
           "by_chain": dict(by_chain),
           "robinhood": {"calls": len(rh), "calls_held": len(rh_hit),
                         "median_lead_days": med,
                         "held_before_the_call": sum(1 for r in rh_hit if r["lead_days"] > 0),
                         "distinct_called": len(d_all), "distinct_held": len(d_hit),
                         "distinct_pct": round(100 * len(d_hit) / len(d_all)) if d_all else 0,
                         "distinct_median_lead_days": d_med,
                         "missed": sorted(d_all - d_hit)},
           "credits_used": spent, "detail": rows}
    json.dump(res, open(OUT, "w"), indent=2)

    print(f"calls transcribed      : {len(rows)}")
    print(f"resolved to a token    : {len(resolved)}  (within +/-{int(TOL*100)}% of stated cap)")
    print(f"unresolved / ambiguous : {len(rows) - len(resolved)}")
    print("\nchains the calls land on:")
    for c, n in by_chain.most_common():
        print(f"   {c:<12}{n}")
    print(f"\nOn robinhood, where this cohort operates:")
    print(f"   distinct coins called  : {len(d_all)}")
    print(f"   already held by cohort : {len(d_hit)}  ({res['robinhood']['distinct_pct']}%)")
    print(f"   held BEFORE the call   : {len(d_hit)} of {len(d_hit)}")
    print(f"   median lead            : {d_med} days")
    print("\n   symbol        recap     first held    lead  wallets")
    for r in sorted(rh_hit, key=lambda r: -(r["lead_days"] or 0)):
        print(f"   {r['symbol']:<12}{r['recap_date']}  {r['first_held']}  {r['lead_days']:>5}d  {r['peak_wallets']:>5}")
    miss = [r for r in rh if not r["cohort_holds"]]
    if miss:
        print("\n   missed: " + ", ".join(r["symbol"] for r in miss))
    print(f"\ncredits used: {spent}")
    print(f"written     : {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
