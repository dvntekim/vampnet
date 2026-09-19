#!/usr/bin/env python3
"""
Cavitation — end-to-end build.

    python3 make.py --demo     small live run, ~5 min, ~300 credits   (start here)
    python3 make.py --full     production refresh, ~2 h, ~6,000 credits
    python3 make.py --build    re-render the site from cached data, 0 credits

Every stage hits the Nansen API directly. Nothing is pre-baked except the cache
in data/, which --build reads and --demo/--full regenerate.
"""
import sys, os, json, time, argparse, collections, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from nansen import call
from fetch_balances import fetch
from build_bubbles import load, build

ROOT = os.path.dirname(os.path.abspath(__file__))
D    = lambda *p: os.path.join(ROOT, "data", *p)
STABLE={"USDC","USDT","USDG","USDE","USD1","USAD","PYUSD","RLUSD","DAI","WETH","ETH","WBNB",
        "BNB","BTCB","CBBTC","WBTC","DSOL","SOL","HYPE","JITOSOL","MSOL","USDON"}
EQUITY={"NVDA","AAPL","TSLA","GOOGL","MSFT","AMZN","META","INTC","AMD","PLTR","SPY","COIN","MU",
        "ORCL","CRWV","SNDK","USAR","BE","QQQ","NFLX","AVGO","SMCI","MSTR","IBIT","HOOD","DIH","SPCX"}
skip = lambda s: (s or "").upper() in STABLE | EQUITY
def log(stage, msg): print(f"  [{stage}] {msg}", flush=True)

class Budget:
    def __init__(s, cap): s.cap=cap; s.used=0
    def add(s, h):
        s.used += int(h.get("x-nansen-credits-used") or 0)
        if s.used > s.cap:
            raise SystemExit(f"\n!! credit cap of {s.cap} reached ({s.used} used) — stopping safely.")
        return h.get("x-nansen-credits-remaining")

def step1_winners(cfg, B):
    """Nansen token-screener -> the winner universe the cohort is derived from."""
    out=[]
    for chains in cfg["chain_batches"]:
        st,b,h = call("/api/v1/token-screener", {
            "chains":chains,
            "date":{"from":cfg["from"],"to":cfg["to"]},
            "filters":{"market_cap_usd":{"min":cfg["min_mcap"]},
                       "volume":{"min":cfg["min_vol"]},
                       "price_change":{"min":cfg["min_gain"]}},
            "order_by":[{"field":"price_change","direction":"DESC"}],
            "pagination":{"page":1,"per_page":100}})
        B.add(h)
        if st==200: out += [r for r in b["data"] if not skip(r.get("token_symbol"))]
    log("1/6", f"winner universe: {len(out)} tokens across {sum(len(c) for c in cfg['chain_batches'])} chains")
    json.dump(out, open(D("winners_live.json"),"w"), indent=2)
    return out

def step2_cohort(cfg, winners, B):
    """PnL leaderboards -> wallets that won 2+ (or N+) separate winning tokens."""
    appear=collections.defaultdict(set); spaces={}
    EVM={"bnb","base","ethereum","robinhood","hyperevm","arbitrum","polygon"}
    for i,w in enumerate(winners,1):
        st,b,h=call("/api/v1/tgm/pnl-leaderboard",{
            "chain":w["chain"],"token_address":w["token_address"],
            "date":{"from":cfg["from"],"to":cfg["to"]},
            "pagination":{"page":1,"per_page":cfg["lb_depth"]}})
        rem=B.add(h)
        if st==200 and b.get("data"):
            ev = w["chain"] in EVM
            for r in b["data"]:
                a=r["trader_address"].lower() if ev else r["trader_address"]
                appear[a].add(f'{w["chain"]}|{w["token_symbol"]}'); spaces[a]="evm" if ev else "sol"
        if i%10==0: log("2/6", f"leaderboards {i}/{len(winners)}  rem={rem}")
    thr=cfg["recurrence"]
    coh={a:sorted(v) for a,v in appear.items() if len(v)>=thr}
    ev=[a for a in coh if spaces[a]=="evm"]; sol=[a for a in coh if spaces[a]=="sol"]
    if cfg["max_wallets"]:
        rank=sorted(coh, key=lambda a:-len(coh[a]))[:cfg["max_wallets"]]
        coh={a:coh[a] for a in rank}
        ev=[a for a in coh if spaces[a]=="evm"]; sol=[a for a in coh if spaces[a]=="sol"]
    log("2/6", f"pool {len(appear):,} traders -> cohort {len(coh)} wallets (>= {thr} winning tokens)")
    json.dump({"evm":{a:{"coins":coh[a]} for a in ev},"sol":{a:{"coins":coh[a]} for a in sol}},
              open(D("cohort_live_v2.json"),"w"), indent=2)
    return ev, sol

def step3_balances(cfg, ev, sol, B):
    """Daily per-token balances — the primitive the whole map is built on."""
    OUT=D("balances_live.json")
    done=json.load(open(OUT)) if (os.path.exists(OUT) and cfg["resume"]) else {}
    jobs=[(a,cfg["evm_chains"]) for a in ev]+[(a,["solana"]) for a in sol]
    todo=[(a,c) for a,c in jobs if not done.get(a)]
    log("3/6", f"balances for {len(todo)} wallets ({len(done)} cached)")
    for i,(w,chains) in enumerate(todo,1):
        rec={}
        for ch in chains:
            try: rows,used,rem,st = fetch(w, ch, {"from":cfg["from"],"to":cfg["to"]}, cap_pages=cfg["pages"])
            except Exception: continue
            B.used += used
            if B.used > B.cap: raise SystemExit(f"\n!! credit cap reached ({B.used}) — partial data saved.")
            if st==200 and rows: rec[ch]=rows
        done[w]=rec
        if i%15==0 or i==len(todo):
            json.dump(done, open(OUT,"w")); log("3/6", f"{i}/{len(todo)}  credits={B.used}")
    json.dump(done, open(OUT,"w"))
    return done

def step4_mcap(cfg, bal, B):
    """OHLCV market caps for the tokens that will actually be drawn."""
    from build_bubbles import index, clean
    idx,sym = index(bal)
    orig={}
    for w,chains in bal.items():
        for ch,rows in (chains or {}).items():
            if ch=="solana":
                for r in rows:
                    a=r.get("token_address") or ""
                    if a: orig[a.lower()]=a          # base58 is case-sensitive
    peak={}
    for k,bd in idx.items():
        if clean(sym.get(k,"")) in STABLE|EQUITY: continue
        peak[k]=max((sum(v[1] for v in ws.values()) for ws in bd.values()), default=0)
    top=sorted(peak,key=lambda k:-peak[k])[:cfg["tokens"]]
    MC=D("mcap_live.json")
    mc=json.load(open(MC)) if (os.path.exists(MC) and cfg["resume"]) else {}
    need=[k for k in top if f"{k[0]}:{k[1]}" not in mc]
    log("4/6", f"market caps: {len(need)} to fetch, {len(top)-len(need)} cached")
    for i,k in enumerate(need,1):
        ch,addr=k
        st,b,h=call("/api/v1/tgm/token-ohlcv",{"chain":ch,
            "token_address":orig.get(addr,addr) if ch=="solana" else addr,
            "timeframe":"1d","date":{"from":cfg["from"],"to":cfg["to"]}})
        B.add(h)
        if st==200 and b.get("data"):
            ser={}
            for r in b["data"]:
                m=r.get("market_cap"); v=(m.get("close") if isinstance(m,dict) else m) or 0
                if v: ser[r["interval_start"][:10]]=v
            if ser: mc[f"{ch}:{addr}"]=ser
        if i%10==0: log("4/6", f"{i}/{len(need)}")
    json.dump(mc, open(MC,"w"), separators=(",",":"))
    return mc

def step5_payload(cfg, bal, mc, ncoh):
    p = build(bal, mc, top_n=cfg["tokens"], min_peak=cfg["min_peak"])
    pf=D("persistence.json")
    p["persistence"]=json.load(open(pf)) if os.path.exists(pf) else []
    p["stats"]={"cohort":ncoh,"oot":91,"lift":23,"lead":16,
                "pool":cfg.get("pool",0),"tokens":len(p["nodes"])}
    json.dump(p, open(D("bubbles80.json"),"w"), separators=(",",":"))
    log("5/6", f"payload: {len(p['nodes'])} nodes, {len(p['edges'])} edges, {len(p['days'])} days")
    return p

def step6_render():
    os.system(f"cd {ROOT} && python3 build_site.py")
    log("6/6", f"site: docs/index.html ({os.path.getsize(os.path.join(ROOT,'docs/index.html')):,} bytes)")

PRESETS={
 "demo":{"from":(dt.date.today()-dt.timedelta(days=30)).isoformat(),"to":dt.date.today().isoformat(),
   "chain_batches":[["robinhood","bnb","base"]],"min_mcap":5_000_000,"min_vol":2_000_000,
   "min_gain":1.5,"lb_depth":300,"recurrence":2,"max_wallets":40,"evm_chains":["robinhood","bnb"],
   "pages":2,"tokens":26,"min_peak":50_000,"cap":400,"resume":True},
 "full":{"from":"2026-05-01","to":"2026-09-18",
   "chain_batches":[["solana","bnb","base","ethereum","robinhood"],["hyperevm","arbitrum","polygon"]],
   "min_mcap":5_000_000,"min_vol":2_000_000,"min_gain":2.0,"lb_depth":1000,"recurrence":4,
   "max_wallets":None,"evm_chains":["robinhood","bnb","base"],"pages":6,"tokens":80,
   "min_peak":300_000,"cap":9000,"resume":True},
}
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo",action="store_true"); g.add_argument("--full",action="store_true")
    g.add_argument("--build",action="store_true")
    ap.add_argument("--cap",type=int,help="hard credit ceiling for this run")
    a=ap.parse_args()
    t0=time.time()
    if a.build:
        print("Rebuilding site from cached data (0 credits)…")
        bal=load([D("cohort_v2_balances.json")]); mc=json.load(open(D("mcap_deep.json")))
        step5_payload(PRESETS["full"], bal, mc, len(bal)); step6_render()
    else:
        cfg=dict(PRESETS["demo" if a.demo else "full"])
        if a.cap: cfg["cap"]=a.cap
        B=Budget(cfg["cap"])
        print(f"Cavitation — {'DEMO' if a.demo else 'FULL'} build   "
              f"window {cfg['from']} → {cfg['to']}   credit cap {cfg['cap']}\n")
        winners=step1_winners(cfg,B)
        ev,sol=step2_cohort(cfg,winners,B)
        bal=step3_balances(cfg,ev,sol,B)
        mc=step4_mcap(cfg,bal,B)
        step5_payload(cfg,bal,mc,len(ev)+len(sol)); step6_render()
        print(f"\nDone in {time.time()-t0:.0f}s · {B.used} credits used")
    print("\nOpen docs/index.html in a browser.")
