#!/usr/bin/env python3
"""
Attention Map — full refresh pipeline.

  python3 scripts/run_pipeline.py --mode cohort   # monthly: rebuild the cohort   (~90 credits)
  python3 scripts/run_pipeline.py --mode daily    # every 2-3 days: refresh data  (~380 credits)
  python3 scripts/run_pipeline.py --mode newcoins # daily: new-coin scan only     (2 credits)

Production config validated 2026-09-18: robinhood, cohort = wallets winning >=2 of the prior
month's winners. 75% out-of-time coverage of the following month's winners.
"""
import sys, os, json, time, argparse, datetime as dt, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nansen import call
from fetch_balances import fetch

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CHAIN = "robinhood"
SPILL = ["bnb", "base"]          # where robinhood traders also operate
STABLE = {"USDC","USDT","USDG","USDE","USD1","USAD","PYUSD","RLUSD","DAI","WETH","ETH","USDON"}
EQUITY = {"NVDA","AAPL","TSLA","GOOGL","MSFT","AMZN","META","INTC","AMD","PLTR","SPY","COIN",
          "MU","ORCL","CRWV","SNDK","USAR","BE","QQQ","NFLX","AVGO","SMCI","MSTR","IBIT","HOOD",
          "DIH","SPCX"}
def skip(sym): return (sym or "").upper() in STABLE | EQUITY
def p(name): return os.path.join(DATA, name)
def ago(days): return (dt.date.today() - dt.timedelta(days=days)).isoformat()
def today():   return dt.date.today().isoformat()

def screen(chains, win, filters, order="price_change", per_page=100):
    st, body, h = call("/api/v1/token-screener", {
        "chains": chains, "date": win, "filters": filters,
        "order_by": [{"field": order, "direction": "DESC"}],
        "pagination": {"page": 1, "per_page": per_page}})
    used = int(h.get("x-nansen-credits-used") or 0)
    rows = [r for r in body.get("data", []) if not skip(r.get("token_symbol"))] if st == 200 else []
    return rows, used, h.get("x-nansen-credits-remaining")

def mode_cohort():
    """Monthly: find last month's winners, build the recurrence cohort."""
    spent = 0
    winners, u, rem = screen([CHAIN], {"from": ago(30), "to": today()},
        {"market_cap_usd": {"min": 2_000_000}, "volume": {"min": 1_000_000},
         "price_change": {"min": 1.0}})
    spent += u
    print(f"winners on {CHAIN} (last 30d, +100%): {len(winners)}  [rem {rem}]")
    appear = collections.defaultdict(set)
    for i, w in enumerate(winners, 1):
        st, body, h = call("/api/v1/tgm/pnl-leaderboard", {
            "chain": CHAIN, "token_address": w["token_address"],
            "date": {"from": ago(30), "to": today()},
            "pagination": {"page": 1, "per_page": 100}})
        spent += int(h.get("x-nansen-credits-used") or 0)
        if st == 200:
            for r in body.get("data", []):
                appear[r["trader_address"].lower()].add(w["token_symbol"])
        print(f"  [{i}/{len(winners)}] {w['token_symbol'][:18]:<20} rem={h.get('x-nansen-credits-remaining')}")
        time.sleep(0.12)
    cohort = {a: sorted(v) for a, v in appear.items() if len(v) >= 2}   # 2+ : breadth beats strictness
    json.dump(cohort, open(p("cohort_live.json"), "w"), indent=2)
    json.dump(winners, open(p("winners_live.json"), "w"), indent=2)
    print(f"\nCOHORT: {len(cohort)} wallets from {len(appear)} traders. credits {spent}")
    return spent

def mode_daily():
    """Every 2-3 days: refresh cohort balances across its chains."""
    cohort = json.load(open(p("cohort_live.json")))
    win = {"from": ago(14), "to": today()}
    out, spent = {}, 0
    chains = [CHAIN] + SPILL
    for i, w in enumerate(cohort, 1):
        rec = {}
        for c in chains:
            rows, used, rem, st = fetch(w, c, win, cap_pages=2)
            spent += used
            if st == 200 and rows: rec[c] = rows
        out[w] = rec
        if i % 10 == 0 or i == len(cohort):
            print(f"  [{i}/{len(cohort)}] spent={spent} rem={rem}")
            json.dump(out, open(p("balances_live.json"), "w"))
        time.sleep(0.1)
    json.dump(out, open(p("balances_live.json"), "w"))
    print(f"\nBALANCES: {len(out)} wallets. credits {spent}")
    return spent

def mode_newcoins():
    """Daily: new tokens with traction, cross-referenced against cohort holdings."""
    spent = 0
    allrows = []
    for chains in (["solana","bnb","base","ethereum","robinhood"], ["hyperevm","arbitrum","polygon"]):
        rows, u, rem = screen(chains, {"from": ago(28), "to": today()},
            {"token_age_days": {"max": 45}, "volume": {"min": 500_000},
             "market_cap_usd": {"min": 1_000_000}}, order="netflow")
        spent += u; allrows += rows
    held = {}
    try:
        bal = json.load(open(p("balances_live.json")))
        for w, chs in bal.items():
            for ch, rws in (chs or {}).items():
                for r in rws:
                    if (r.get("token_amount") or 0) <= 0: continue
                    k = f"{ch}:{(r.get('token_address') or '').lower()}"
                    e = held.setdefault(k, {"wallets": set(), "usd": 0.0})
                    e["wallets"].add(w); e["usd"] = max(e["usd"], r.get("value_usd") or 0)
    except FileNotFoundError:
        print("  (no balances_live.json yet — run --mode daily first)")
    hits = []
    for t in allrows:
        k = f"{t['chain']}:{(t.get('token_address') or '').lower()}"
        if k in held and held[k]["usd"] > 1000:
            hits.append({"symbol": t["token_symbol"], "chain": t["chain"],
                         "age_days": t.get("token_age_days"), "mcap": t.get("market_cap_usd"),
                         "wallets": len(held[k]["wallets"]), "cohort_usd": held[k]["usd"]})
    hits.sort(key=lambda r: -r["cohort_usd"])
    json.dump(hits, open(p("newcoins_live.json"), "w"), indent=2)
    print(f"\nNEW COINS: {len(hits)}/{len(allrows)} already hold cohort capital. credits {spent}")
    for r in hits[:12]:
        print(f"  {r['symbol'][:16]:<18}{r['chain']:<11}{(r['age_days'] or 0):>4.0f}d  "
              f"{r['wallets']:>3}w  ${r['cohort_usd']:>11,.0f}")
    return spent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["cohort","daily","newcoins"])
    a = ap.parse_args()
    n = {"cohort": mode_cohort, "daily": mode_daily, "newcoins": mode_newcoins}[a.mode]()
    print(f"[{a.mode}] credits used: {n}")
