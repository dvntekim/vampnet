"""Turn cohort balances into the JSON the front-end renders."""
import json, collections, statistics as stx

STABLE = {"USDC","USDT","USDG","USDE","USD1","USAD","PYUSD","RLUSD","DAI","FDUSD","BUSD",
          "WETH","ETH","WBNB","BNB","WBTC","BTC","BTCB","CBBTC","SOL","WSOL","DSOL",
          "JITOSOL","MSOL","JUPSOL","WSTETH","STETH","HYPE","USDHL","WHYPE"}
def clean(s): return (s or "").replace("⚠️","").replace("🌱","").strip().upper()

def build(bal):
    hold = collections.defaultdict(lambda: collections.defaultdict(float))
    val  = collections.defaultdict(lambda: collections.defaultdict(float))
    px   = collections.defaultdict(lambda: collections.defaultdict(list))
    wal  = collections.defaultdict(lambda: collections.defaultdict(set))
    sym  = {}
    for w, chains in bal.items():
        for ch, rows in (chains or {}).items():
            for r in rows:
                amt = r.get("token_amount") or 0.0
                v   = r.get("value_usd") or 0.0
                if amt <= 0: continue
                d = r["block_timestamp"][:10]
                key = f"{ch}:{(r.get('token_address') or '').lower()}"
                hold[key][d] += amt; val[key][d] += v
                px[key][d].append(v/amt); wal[key][d].add(w)
                sym[key] = r.get("token_symbol") or key.split(":")[1][:8]
    price = {k: {d: stx.median(v) for d,v in dd.items()} for k,dd in px.items()}
    days = sorted({d for k in val for d in val[k]})
    return hold, price, val, wal, sym, days

def nodes_edges(hold, price, val, wal, sym, days, min_usd=25000, top_n=60):
    """Nodes = tokens with real cohort exposure. Edges = co-rotation (A down, B up, same day)."""
    peak = {k: max(v.values()) for k,v in val.items() if v}
    keys = [k for k in peak if clean(sym[k]) not in STABLE and peak[k] >= min_usd]
    keys = sorted(keys, key=lambda k: -peak[k])[:top_n]
    flows = {}
    for k in keys:
        f={}
        for i in range(1,len(days)):
            d0,d1=days[i-1],days[i]
            a0,a1=hold[k].get(d0,0),hold[k].get(d1,0)
            p=price[k].get(d1) or price[k].get(d0)
            if p: f[d1]=(a1-a0)*p
        flows[k]=f
    nodes=[]
    for k in keys:
        series=[{"d":d,"usd":round(val[k].get(d,0),2),"w":len(wal[k].get(d,set()))} for d in days]
        first=next((d for d in days if val[k].get(d,0)>0), None)
        nodes.append({"id":k,"symbol":sym[k],"chain":k.split(":")[0],
                      "peak_usd":round(peak[k],2),"first_seen":first,
                      "max_wallets":max((len(wal[k].get(d,set())) for d in days), default=0),
                      "series":series})
    edges=collections.defaultdict(lambda: {"usd":0.0,"days":0})
    for i in range(1,len(days)):
        d=days[i]
        outs=[(k,-flows[k].get(d,0)) for k in keys if flows[k].get(d,0) < -1000]
        ins =[(k, flows[k].get(d,0)) for k in keys if flows[k].get(d,0) >  1000]
        tot_in=sum(v for _,v in ins) or 1
        for ko,vo in outs:
            for ki,vi in ins:
                if ko==ki: continue
                share=vi/tot_in
                e=edges[(ko,ki)]; e["usd"]+=vo*share; e["days"]+=1
    el=[{"from":a,"to":b,"usd":round(v["usd"],2),"days":v["days"]}
        for (a,b),v in edges.items() if v["usd"]>5000]
    el.sort(key=lambda e:-e["usd"])
    return nodes, el[:400], days
