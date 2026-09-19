"""Multi-chain cohort analysis: exposure, cross-chain rotation, out-of-sample signal test."""
import json, collections, statistics as stx

STABLE = {"USDC","USDT","USDS","USDE","DAI","WETH","ETH","WBNB","BNB","WBTC","BTC",
          "USD1","FDUSD","BUSD","CBBTC","WSTETH","STETH"}
# coins the cohort was SELECTED on -> must be excluded from any predictive test
SELECTED = {"MARSCOIN","BASECAT","BONER","PONS","MEME","SLINK"}

def clean(s):
    return (s or "").replace("⚠️","").replace("🌱","").strip().upper()

def load(path="data/evm_cohort_balances.json"):
    raw = json.load(open(path))
    # key tokens by (chain, address) so the same symbol on two chains stays distinct
    hold = collections.defaultdict(lambda: collections.defaultdict(float))
    val  = collections.defaultdict(lambda: collections.defaultdict(float))
    px   = collections.defaultdict(lambda: collections.defaultdict(list))
    sym  = {}
    wallet_pos = collections.defaultdict(lambda: collections.defaultdict(dict))
    for w, chains in raw.items():
        for ch, rows in chains.items():
            for r in rows:
                amt = r.get("token_amount") or 0.0
                v   = r.get("value_usd") or 0.0
                if amt <= 0: continue
                d = r["block_timestamp"][:10]
                key = (ch, r["token_address"])
                hold[key][d] += amt
                val[key][d]  += v
                px[key][d].append(v/amt)
                sym[key] = r.get("token_symbol") or r["token_address"][:8]
                wallet_pos[key][d][w] = amt
    price = {k: {d: stx.median(v) for d,v in dd.items()} for k,dd in px.items()}
    return hold, price, val, sym, wallet_pos, raw

def flow_events(hold, price, val, sym, wallet_pos, days, exclude_selected=True, min_usd=1000):
    di = {d:i for i,d in enumerate(days)}
    ev=[]
    for key in val:
        s = clean(sym[key])
        if s in STABLE: continue
        if exclude_selected and s in SELECTED: continue
        for i in range(1,len(days)):
            d0,d1 = days[i-1], days[i]
            a0,a1 = hold[key].get(d0,0), hold[key].get(d1,0)
            p1 = price[key].get(d1)
            if not p1: continue
            flow = (a1-a0)*p1
            if abs(flow) < min_usd: continue
            h0=set(wallet_pos[key].get(d0,{})); h1=set(wallet_pos[key].get(d1,{}))
            fwd={}
            for k in (1,3,5,7,10):
                if i+k < len(days):
                    p2 = price[key].get(days[i+k])
                    if p2 and abs(p2/p1-1) < 20: fwd[k]=p2/p1-1
            ev.append({"chain":key[0],"sym":sym[key],"day":d1,"flow":flow,
                       "new_entrants":len(h1-h0),"holders":len(h1),
                       "exposure":val[key].get(d1,0),"fwd":fwd})
    return ev

def bucket_table(ev, buckets, horizons=(1,3,5,7,10)):
    allv={k:[e["fwd"][k] for e in ev if k in e["fwd"]] for k in horizons}
    base={k:(stx.median(v)*100 if v else None) for k,v in allv.items()}
    print(f"{'bucket':<30}" + "".join(f"{'k='+str(k):>11}" for k in horizons) + "      n")
    print(f"{'BASELINE (all events)':<30}" +
          "".join((f"{base[k]:>10.1f}%" if base[k] is not None else f"{'-':>11}") for k in horizons) +
          f"{len(ev):>7}")
    for name, pred in buckets:
        b=[e for e in ev if pred(e)]
        cells=""
        for k in horizons:
            v=[e["fwd"][k] for e in b if k in e["fwd"]]
            cells += f"{stx.median(v)*100:>10.1f}%" if len(v)>=3 else f"{'-':>11}"
        print(f"{name:<30}{cells}{len(b):>7}")
    return base
