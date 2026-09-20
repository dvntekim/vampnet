"""Build the front-end payload: nodes, activity, time-windowed edges, clustered layout."""
import json, math, random, collections, statistics as stx

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
    # base58 (solana) addresses are case-sensitive while our index lowercases
    # everything for EVM; match the mcap series case-insensitively so both work.
    mcser={k.lower():v for k,v in mcser.items()}
    idx,sym=index(bal)
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

    CH=sorted({n["chain"] for n in nodes},
              key=lambda c:-sum(1 for n in nodes if n["chain"]==c))
    layout(nodes, edges)
    return {"days":days,"nodes":nodes,"edges":edges,"chains":CH}


# =============================================================================
# LAYOUT — where a token sits, and why.
#
# The previous layout was a polar scatter: angle = chain, radius = first-entry
# percentile. It made position meaningful but decoupled it from connectivity, so
# two tokens sharing forty wallets could sit on opposite rims and the rotation
# between them was drawn as a long arc across empty space. Long arcs are noise;
# the eye cannot follow them, and the map read as scattered rather than as flow.
#
# This clusters instead. Four forces, in order of strength:
#
#   springs   tokens that actually rotate into each other are pulled adjacent,
#             so a rotation becomes a SHORT link between neighbours
#   repulsion radius-aware, so big bubbles do not overlap but small ones pack
#   anchor    each chain gets a weak centroid — territories form, but a token
#             rotating hard with another chain can drift toward it, and that
#             drift is itself information a hard wedge would have forbidden
#   time      inside a cluster, early entries sit toward the core and new ones
#             toward the rim, preserving "centre is conviction" as a local read
#
# Positions are solved here, at build time, and frozen. The renderer never moves
# a node: that is what keeps scrubbing at 60fps and makes the map a place you
# learn rather than a chart that reshuffles.
# =============================================================================
SPRING, REPEL, COLLIDE = 0.85, 0.00040, 1.08
ANCHOR, CORE, SPREAD   = 0.80, 0.11, 0.30
STEP, ITERS, MAXSTEP   = 0.42, 700, 0.030
CLEARANCE              = 1.45   # gap between adjacent chain territories
# The anchor force is soft, so solved positions overshoot their target ring;
# CLEARANCE is sized for where nodes actually land, not where they are aimed.
# A hub with thirty rotations accumulates thirty spring forces and, unchecked,
# overshoots the whole map in one step and never recovers. Two standard guards:
# mass grows with degree, and no node may move more than MAXSTEP per iteration.
MASS_PER_DEGREE        = 0.35


def _chain_ring(nodes, link, chains):
    """Seat chains around a circle so the strongest inter-chain rotation lands on
    adjacent seats — the dominant direction of flow then reads around the ring
    instead of criss-crossing it."""
    between = collections.Counter()
    for a, b, w in link:
        ca, cb = nodes[a]["chain"], nodes[b]["chain"]
        if ca != cb:
            between[frozenset((ca, cb))] += w
    order, rest = [chains[0]], set(chains[1:])
    while rest:
        last = order[-1]
        nxt = max(rest, key=lambda c: between.get(frozenset((last, c)), 0.0))
        order.append(nxt)
        rest.discard(nxt)

    size = {c: sum(1 for n in nodes if n["chain"] == c) for c in order}
    # sqrt, not linear: one chain holding two thirds of the tokens would otherwise
    # leave the other three without enough arc to be legible
    tot = sum(math.sqrt(size[c]) for c in order)
    mean = sum(size.values()) / len(order)

    # A cluster's internal spread has to track its population, or 54 tokens pack
    # into the same disc as 5: one becomes an unreadable knot, the other a balloon
    # of empty hull. Everything downstream is normalised, so only ratios matter.
    spread = {c: math.sqrt(size[c] / mean) for c in order}

    theta, cursor = {}, 0.0
    for c in order:
        frac = math.sqrt(size[c]) / tot
        theta[c] = 2 * math.pi * (cursor + frac / 2)
        cursor += frac

    if len(order) == 1:
        return {order[0]: (0.0, 0.0)}, spread

    # Seat the ring wide enough that no two adjacent clusters can touch, solved
    # from the chord between them rather than guessed at.
    ring = 0.0
    for i, c in enumerate(order):
        d = order[(i + 1) % len(order)]
        dth = (theta[d] - theta[c]) % (2 * math.pi)
        half = math.sin(min(dth, 2 * math.pi - dth) / 2) or 1e-6
        reach = (spread[c] + spread[d]) * (CORE + SPREAD) * CLEARANCE
        ring = max(ring, reach / (2 * half))

    return {c: (math.cos(theta[c]) * ring, math.sin(theta[c]) * ring) for c in order}, spread


def layout(nodes, edges, aspect=0.80, iters=ITERS, seed=7):
    """Solve node positions in place. Sets n["x"], n["y"] on every node."""
    n_count = len(nodes)
    if not n_count:
        return
    rnd = random.Random(seed)                      # seeded: builds are reproducible
    ix = {n["id"]: i for i, n in enumerate(nodes)}

    # what the eye actually has to fit is the market-cap ring, not the node centre
    mcmax = max((max(n["mc"]) for n in nodes), default=1) or 1
    rad = [0.030 + 0.070 * math.sqrt((max(n["mc"]) or 0) / mcmax) for n in nodes]

    # edge strength, log-compressed so one enormous pair cannot dominate the solve
    link = []
    for e in edges:
        a, b = ix.get(e["a"]), ix.get(e["b"])
        if a is None or b is None or a == b:
            continue
        w = sum(e["w"])
        if w > 0:
            link.append((a, b, math.log1p(w)))
    if link:
        top = max(l[2] for l in link) or 1.0
        link = [(a, b, w / top) for a, b, w in link]

    chains = sorted({n["chain"] for n in nodes},
                    key=lambda c: -sum(1 for n in nodes if n["chain"] == c))
    anchor, spread = _chain_ring(nodes, link, chains)

    # first-entry percentile -> where inside its cluster a token wants to sit
    tpct = [0.0] * n_count
    for r, i in enumerate(sorted(range(n_count), key=lambda i: nodes[i]["first"])):
        tpct[i] = r / max(1, n_count - 1)

    # heavier nodes are the well-connected ones, so hubs anchor the clusters
    # instead of being flung around by the tokens hanging off them
    mass = [1.0] * n_count
    for a, b, w in link:
        mass[a] += MASS_PER_DEGREE * w
        mass[b] += MASS_PER_DEGREE * w

    px, py = [0.0] * n_count, [0.0] * n_count
    for i, n in enumerate(nodes):
        ax, ay = anchor[n["chain"]]
        a = rnd.random() * 2 * math.pi
        r = (0.05 + 0.20 * math.sqrt(rnd.random())) * spread[n["chain"]]
        px[i], py[i] = ax + math.cos(a) * r, ay + math.sin(a) * r

    for it in range(iters):
        cool = (1 - it / iters) ** 1.2
        fx, fy = [0.0] * n_count, [0.0] * n_count

        for a, b, w in link:                       # co-rotation springs
            dx, dy = px[b] - px[a], py[b] - py[a]
            d = math.hypot(dx, dy) or 1e-6
            rest = (rad[a] + rad[b]) * 1.9 + 0.02
            f = SPRING * w * (d - rest)
            ux, uy = dx / d, dy / d
            fx[a] += f * ux; fy[a] += f * uy
            fx[b] -= f * ux; fy[b] -= f * uy

        for i in range(n_count):                   # repulsion + hard collision
            for j in range(i + 1, n_count):
                dx, dy = px[j] - px[i], py[j] - py[i]
                d2 = dx * dx + dy * dy
                d = math.sqrt(d2) or 1e-6
                ux, uy = dx / d, dy / d
                rep = REPEL * (rad[i] + rad[j]) / max(d2, 0.0016)
                fx[i] -= rep * ux; fy[i] -= rep * uy
                fx[j] += rep * ux; fy[j] += rep * uy
                floor = (rad[i] + rad[j]) * COLLIDE
                if d < floor:
                    push = (floor - d) * 0.5
                    fx[i] -= push * ux; fy[i] -= push * uy
                    fx[j] += push * ux; fy[j] += push * uy

        for i, n in enumerate(nodes):              # chain anchor + time-in-cluster
            ax, ay = anchor[n["chain"]]
            dx, dy = px[i] - ax, py[i] - ay
            d = math.hypot(dx, dy) or 1e-6
            want = (CORE + SPREAD * tpct[i]) * spread[n["chain"]]
            f = ANCHOR * (d - want)
            fx[i] -= f * dx / d; fy[i] -= f * dy / d

        lim = MAXSTEP * cool
        for i in range(n_count):
            dx = fx[i] / mass[i] * STEP * cool
            dy = fy[i] / mass[i] * STEP * cool
            m = math.hypot(dx, dy)
            if m > lim:                            # hard displacement clamp
                dx, dy = dx / m * lim, dy / m * lim
            px[i] += dx
            py[i] += dy

    span = max(max(abs(px[i]), abs(py[i])) for i in range(n_count)) or 1.0
    for i, n in enumerate(nodes):
        n["x"] = round(px[i] / span, 4)
        n["y"] = round(py[i] / span * aspect, 4)   # flatten to suit a wide viewport
