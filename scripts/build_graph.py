"""Rotation graph builder: leaderboard exiters -> traced destinations."""
import sys, json, time, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nansen import call

STABLE = {"USDC","USDT","SOL","WSOL","USDS","JITOSOL","MSOL","JUPSOL","BSOL","USDE"}

def trace(addr, chain, win, per_page=500):
    st, body, h = call("/api/v1/profiler/dex-trades", {
        "address": addr, "chain": chain, "date": win,
        "pagination": {"page": 1, "per_page": per_page}})
    used = h.get("x-nansen-credits-used")
    rem  = h.get("x-nansen-credits-remaining")
    return (body["data"] if st == 200 else []), used, rem, st

def build(source_sym, chain, win, exiters, top_n=12):
    edges = collections.defaultdict(lambda: {"usd": 0.0, "wallets": set()})
    detail = {}
    ranked = sorted(exiters.items(), key=lambda x: -x[1])[:top_n]
    for i, (addr, net_out) in enumerate(ranked, 1):
        tr, used, rem, st = trace(addr, chain, win)
        buys = collections.defaultdict(float)
        for t in tr:
            sym = t.get("token_bought_symbol")
            if sym and sym.upper() not in STABLE and sym.upper() != source_sym:
                buys[sym] += t.get("trade_value_usd") or 0
        for sym, usd in buys.items():
            # attribute at most what they took out of the source
            edges[sym]["usd"] += min(usd, net_out)
            edges[sym]["wallets"].add(addr)
        detail[addr] = {"net_out": net_out, "trades": len(tr), "buys": dict(buys)}
        print(f"  [{i:>2}/{len(ranked)}] {addr[:20]}… out=${net_out:>11,.0f} trades={len(tr):<4} "
              f"dests={len(buys):<3} used={used} rem={rem}")
        time.sleep(0.15)
    out = [{"to": k, "usd": v["usd"], "wallets": len(v["wallets"])} for k, v in edges.items()]
    out.sort(key=lambda e: -e["usd"])
    return out, detail
