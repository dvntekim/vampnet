"""Build the front-end payload: nodes, activity, time-windowed edges, lifecycle layout."""
import json, math, collections, statistics as stx

STABLE={"USDC","USDT","USDG","USDE","USD1","USAD","PYUSD","RLUSD","DAI","FDUSD","BUSD","WETH",
        "ETH","WBNB","BNB","WBTC","BTC","BTCB","CBBTC","SOL","WSOL","DSOL","JITOSOL","MSOL",
        "JUPSOL","WSTETH","STETH","HYPE","USDHL","WHYPE","USDON","AETHUSDC"}
EQUITY={"NVDA","AAPL","TSLA","GOOGL","MSFT","AMZN","META","INTC","AMD","PLTR","SPY","COIN","MU",
        "ORCL","CRWV","SNDK","USAR","BE","QQQ","NFLX","AVGO","SMCI","MSTR","IBIT","HOOD","DIH",
        "SPCX","TENOV","BASED","HEX"}
def clean(s): return (s or "").replace("⚠️","").replace("🌱","").strip().upper()

def load(paths):
    merged={}
    for p in paths:
        try: merged.update(json.load(open(p)))
        except Exception: pass
    return merged

def index(bal):
    idx=collections.defaultdict(lambda: collections.defaultdict(dict)); sym={}
    for w,chains in bal.items():
        for ch,rows in (chains or {}).items():
            for r in rows:
                a=r.get("token_amount") or 0
                if a<=0: continue
                key=(ch,(r.get("token_address") or "").lower())
                idx[key][r["block_timestamp"][:10]][w]=(a, r.get("value_usd") or 0)
                sym[key]=r.get("token_symbol") or key[1][:8]
    return idx, sym

def build(bal, mcser, top_n=26, min_peak=30000):
    """Build the front-end payload from raw balance rows."""
    idx, sym = index(bal)
    return _build(idx, sym, mcser, top_n, min_peak)


def _build(idx, sym, mcser, top_n=26, min_peak=30000):
    # base58 (solana) addresses are case-sensitive while our index lowercases
    # everything for EVM; match the mcap series case-insensitively so both work.
    mcser={k.lower():v for k,v in mcser.items()}
    days=sorted({d for k in idx for d in idx[k]})
    stats={}
    for key,bd in idx.items():
        s=clean(sym.get(key,""))
        if s in STABLE or s in EQUITY: continue
        peak=max((sum(v[1] for v in ws.values()) for ws in bd.values()), default=0)
        if peak>=min_peak: stats[key]=peak
    keys=sorted(stats,key=lambda k:-stats[k])[:top_n]
    kid={k:f"{k[0]}:{k[1]}" for k in keys}

    nodes=[]
    for k in keys:
        ku=kid[k]; usd=[];wal=[];mc=[]
        for d in days:
            ws=idx[k].get(d,{})
            usd.append(round(sum(v[1] for v in ws.values()),1)); wal.append(len(ws))
            mc.append(round((mcser.get(ku.lower()) or {}).get(d,0)))
        last=0
        for i,v in enumerate(mc):
            if v: last=v
            elif last: mc[i]=last
        first=next((i for i,v in enumerate(usd) if v>0), 0)
        # ACTIVITY: normalised |d(cohort usd)/dt|, smoothed over 3 days
        raw=[0.0]+[abs(usd[i]-usd[i-1]) for i in range(1,len(days))]
        act=[]
        for i in range(len(raw)):
            w=raw[max(0,i-1):i+2]
            act.append(sum(w)/len(w))
        mxa=max(act) or 1
        act=[round(a/mxa,3) for a in act]
        nodes.append({"id":ku,"sym":sym[k],"chain":k[0],"usd":usd,"wal":wal,"mc":mc,
                      "act":act,"first":first,"peak":round(stats[k])})
    # rank 0 = biggest: the front-end reveals nodes/labels in this order as you zoom in
    for r,n in enumerate(sorted(nodes,key=lambda n:-n["peak"])): n["rank"]=r

    # ---- TRIM leading dead frames -----------------------------------------
    # The balance window can start well before any cohort token exists. Opening
    # the page on an empty canvas reads as a broken chart, so drop those frames
    # (keeping a 3-day run-in) and re-index every series to match.
    firsts=[n["first"] for n in nodes]
    cut=max(0, min(firsts)-3) if firsts else 0
    if cut:
        days=days[cut:]
        for n in nodes:
            for k in ("usd","wal","mc","act"): n[k]=n[k][cut:]
            n["first"]=max(0,n["first"]-cut)

    # ---- co-rotation edges, per-day shared-wallet counts ----
    amt={kid[k]:[{w:v[0] for w,v in idx[k].get(d,{}).items()} for d in days] for k in keys}
    E=collections.defaultdict(lambda:[0]*len(days))
    for i in range(1,len(days)):
        delta={}
        for n in nodes:
            a0,a1=amt[n["id"]][i-1],amt[n["id"]][i]
            delta[n["id"]]={w:(a1.get(w,0)-a0.get(w,0)) for w in set(a0)|set(a1)
                            if (a1.get(w,0)-a0.get(w,0))!=0}
        for a in nodes:
            da=delta[a["id"]]
            outs=[w for w,v in da.items() if v<0]
            if not outs: continue
            for b in nodes:
                if a["id"]==b["id"]: continue
                db=delta[b["id"]]
                sh=sum(1 for w in outs if db.get(w,0)>0)
                if sh>=2: E[(a["id"],b["id"])][i]=sh
    edges=[{"a":a,"b":b,"w":v} for (a,b),v in E.items() if max(v)>=2]
    edges.sort(key=lambda e:-sum(e["w"]))
    # A purely global top-N cap lets the busiest chain crowd everything else out:
    # Robinhood's 367 heavy edges were burying every real Solana rotation. Guarantee
    # each token keeps its strongest few edges, then fill the remainder globally.
    CAP=min(520,len(nodes)*7); PER_NODE=4
    kept=[]; seen=set(); per=collections.Counter()
    for e in edges:
        k=(e["a"],e["b"])
        if per[e["a"]]<PER_NODE or per[e["b"]]<PER_NODE:
            kept.append(e); seen.add(k); per[e["a"]]+=1; per[e["b"]]+=1
    for e in edges:
        if len(kept)>=CAP: break
        k=(e["a"],e["b"])
        if k not in seen: kept.append(e); seen.add(k)
    edges=kept[:CAP]

    # ---- LIFECYCLE LAYOUT -------------------------------------------------
    # angle  = chain (wedge width proportional to how many tokens it holds)
    # radius = when the cohort FIRST entered  -> centre = early, rim = new
    # overlaps are resolved by nudging ANGLE only, so radius stays a clean time axis.
    CH=sorted({n["chain"] for n in nodes},
              key=lambda c:-sum(1 for n in nodes if n["chain"]==c))
    span=max(1,len(days)-1)
    by=collections.defaultdict(list)
    for n in nodes: by[n["chain"]].append(n)
    total=len(nodes); cursor=0.0; GAP=0.10        # radians of padding between wedges
    SEP=0.30 if len(nodes)<=30 else 0.20         # required gap; map is pannable so we can spread
    # percentile rank of first-entry -> even radial spread, order preserved
    order=sorted(nodes, key=lambda n:n["first"])
    rank={n["id"]:i/max(1,len(order)-1) for i,n in enumerate(order)}
    pol={}
    for c in CH:
        grp=sorted(by[c], key=lambda n:n["first"])
        width=2*math.pi*(len(grp)/total)-GAP
        GOLD=0.6180339887498949
        for j,n in enumerate(grp):
            frac=((j*GOLD)%1.0) if len(grp)>12 else (j+0.5)/len(grp)
            pol[n["id"]]=[cursor+GAP/2+width*frac,                      # angle
                          0.26+1.30*rank[n["id"]]]                      # radius
        cursor+=width+GAP
    # angular separation pass — radius is never touched
    ids=[n["id"] for n in nodes]
    for _ in range(900):
        moved=False
        for i in range(len(ids)):
            for j in range(i+1,len(ids)):
                a,b=pol[ids[i]],pol[ids[j]]
                ax,ay=math.cos(a[0])*a[1],math.sin(a[0])*a[1]
                bx,by_=math.cos(b[0])*b[1],math.sin(b[0])*b[1]
                d=math.hypot(bx-ax,by_-ay)
                if d<SEP:
                    push=(SEP-d)*0.35/max(a[1],b[1],0.2)
                    sgn=1 if (b[0]-a[0])%(2*math.pi)<math.pi else -1
                    a[0]-=push*sgn; b[0]+=push*sgn; moved=True
        if not moved: break
    for n in nodes:
        ang,rad=pol[n["id"]]
        n["x"]=round(math.cos(ang)*rad,4)
        n["y"]=round(math.sin(ang)*rad*0.84,4)
    m=max(max(abs(n["x"]),abs(n["y"])) for n in nodes)
    SPAN=0.95 if len(nodes)<=30 else 1.55   # virtual map can exceed the viewport
    for n in nodes:
        n["x"]=round(n["x"]/m*SPAN,4); n["y"]=round(n["y"]/m*SPAN,4)
    return {"days":days,"nodes":nodes,"edges":edges,"chains":CH}


# ---------------------------------------------------------------------------
# Compact cache
#
# The raw balance rows are ~660 MB, which cannot live in git or a CI cache.
# Only the tokens we actually draw need per-wallet detail, and re-encoding
# against day/wallet index tables removes the repeated address strings:
# 661 MB -> 4.6 MB (1.4 MB gzipped).
# ---------------------------------------------------------------------------
import gzip

CACHE_TOKENS = 150      # tokens kept with per-wallet detail


def _sig(x):
    """Amounts are stored verbatim.

    Rounding here is a false economy: fixed decimals zero out tokens held in tiny
    unit amounts, and even 10 significant figures perturbs the delta-vs-zero test
    that edge detection depends on, silently changing 8 of 520 edges. Exact storage
    costs 0.7 MB and guarantees the cached path matches the raw path byte for byte.
    """
    return x


def save_cache(idx, sym, path, top_n=CACHE_TOKENS):
    """Write the compact cache. `idx`/`sym` come from index()."""
    peak = {}
    for key, by_day in idx.items():
        if clean(sym.get(key, "")) in STABLE | EQUITY:
            continue
        peak[key] = max((sum(v[1] for v in ws.values()) for ws in by_day.values()), default=0)
    keep = sorted(peak, key=lambda k: -peak[k])[:top_n]

    days = sorted({d for k in keep for d in idx[k]})
    day_ix = {d: i for i, d in enumerate(days)}
    wallets = sorted({w for k in keep for ws in idx[k].values() for w in ws})
    wal_ix = {w: i for i, w in enumerate(wallets)}

    tokens = {}
    for key in keep:
        rows = []
        for day, holders in sorted(idx[key].items()):
            for wallet, (amount, usd) in holders.items():
                rows.append([day_ix[day], wal_ix[wallet], amount, usd])
        tokens[f"{key[0]}:{key[1]}"] = {"sym": sym[key], "chain": key[0], "rows": rows}

    blob = json.dumps({"days": days, "wallets": wallets, "tokens": tokens},
                      separators=(",", ":")).encode()
    with gzip.open(path, "wb", compresslevel=9) as fh:
        fh.write(blob)
    return len(days), len(wallets), len(tokens)


def load_cache(path):
    """Read the compact cache back into the (idx, sym) shape build() expects."""
    with gzip.open(path, "rb") as fh:
        blob = json.loads(fh.read())
    days, wallets = blob["days"], blob["wallets"]
    idx = collections.defaultdict(lambda: collections.defaultdict(dict))
    sym = {}
    for token_id, rec in blob["tokens"].items():
        chain, address = token_id.split(":", 1)
        key = (chain, address)
        sym[key] = rec["sym"]
        for day_i, wal_i, amount, usd in rec["rows"]:
            idx[key][days[day_i]][wallets[wal_i]] = (amount, usd)
    return idx, sym


def merge_rows(idx, sym, wallet, chain, rows):
    """Fold freshly fetched balance rows for one wallet-chain into an index."""
    for r in rows:
        amount = r.get("token_amount") or 0
        if amount <= 0:
            continue
        key = (chain, (r.get("token_address") or "").lower())
        idx[key][r["block_timestamp"][:10]][wallet] = (amount, r.get("value_usd") or 0)
        sym.setdefault(key, r.get("token_symbol") or key[1][:8])


def trim_window(idx, keep_days):
    """Drop frames older than the rolling window so the cache stays bounded."""
    days = sorted({d for k in idx for d in idx[k]})
    if len(days) <= keep_days:
        return days
    cutoff = days[-keep_days]
    for key in list(idx):
        for day in [d for d in idx[key] if d < cutoff]:
            del idx[key][day]
        if not idx[key]:
            del idx[key]
    return sorted({d for k in idx for d in idx[k]})


def build_from_index(idx, sym, mcser, top_n=26, min_peak=30000):
    """build() without the raw-rows step, for the cached/daily path."""
    return _build(idx, sym, mcser, top_n, min_peak)
