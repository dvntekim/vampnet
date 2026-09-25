"""Build the front-end payload: nodes, activity, time-windowed edges, clustered layout."""
import json, math, random, collections, statistics as stx
import datetime as _dt

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

    # ---- TRIM to where the map is worth looking at -------------------------
    # The trim above only drops frames before any token exists, which is not the
    # same as a frame worth showing: two tokens holding $0.1M with no rotation
    # between them is a legibly empty canvas. Measured on the 141-day window, the
    # first 63 frames carried no edge at all and 69 of 141 carried fewer than
    # five — half the scrubber was dead screen, and dragging it was the first
    # thing a visitor did.
    #
    # Rotations are what this product is for, so legibility is defined by them
    # rather than by token count or capital. A short run-in keeps tokens visibly
    # arriving before they start rotating, so the opening frame is not abrupt.
    # The run happens partway through the current day, so the last frame holds a
    # few hours of balances rather than a day's. It looked like a collapse — the
    # final frame carried 15 rotations where the day before carried 90 — and
    # since the engine opens on the newest frame, that partial day was the first
    # thing anyone saw. Drop it; the next run re-fetches it complete.
    while len(days) > 2 and days[-1] >= _dt.date.today().isoformat():
        days = days[:-1]
        for e in edges: e["w"] = e["w"][:-1]
        for n in nodes:
            for k in ("usd","wal","mc","act"): n[k] = n[k][:-1]

    live=next((i for i in range(len(days))
               if sum(1 for e in edges if e["w"][i]>=2)>=LEGIBLE_EDGES), 0)
    cut=max(0, live-RUN_IN_DAYS)
    if cut:
        days=days[cut:]
        for e in edges: e["w"]=e["w"][cut:]
        for n in nodes:
            for k in ("usd","wal","mc","act"): n[k]=n[k][cut:]
            # A token that predates the cut is not newly entered — it is simply
            # already there. Clamping `first` to 0 would make the engine tag it
            # NEW for the first fortnight of the timeline and draw it a birth
            # animation it never had. Park it beyond the newness horizon instead.
            n["first"]=n["first"]-cut if n["first"]>=cut else -(NEW_DAYS+1)
        edges=[e for e in edges if max(e["w"])>=2]

    CH=sorted({n["chain"] for n in nodes},
              key=lambda c:-sum(1 for n in nodes if n["chain"]==c))
    layout(nodes, edges)
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
# How many simultaneous rotations make a frame worth opening on, and how much
# run-in to keep before it. Raising LEGIBLE_EDGES starts the timeline later and
# denser; RUN_IN_DAYS buys back a few frames of tokens arriving first.
LEGIBLE_EDGES = 3
RUN_IN_DAYS = 5
# Must match CONFIG.newDays in build_site.py — a token older than the trim is
# parked beyond this horizon so it is never mistaken for a new entry.
NEW_DAYS = 14


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


# =============================================================================
# LAYOUT — where a token sits, and why.
#
# Two earlier attempts imposed a structure the data does not have. The first was
# a polar scatter (angle = chain, radius = first-entry), which decoupled position
# from connectivity so a rotation between two tokens was drawn as a long arc
# across empty space. The second seated chains around a ring, which was worse in
# a specific way: 92% of flow is INSIDE a chain and 87% is inside Robinhood
# alone, so a ring spends a quarter of the canvas on Solana — six tokens, 0.2% of
# flow and, because an EVM keypair cannot hold a Solana token, structurally zero
# cross-chain edges — while compressing everything worth looking at into a blob.
#
# So nothing is imposed now. Position is solved from the rotations alone:
#
#   springs    tokens that rotate into each other are pulled together
#   repulsion  radius-aware, so big caps do not overlap and small ones pack
#   collision  a hard floor on centre distance
#   gravity    a weak pull to the origin, which keeps disconnected tokens from
#              drifting off rather than placing anything
#   cohesion   a weak pull toward the centre of the node's own community
#   separation a push between whole communities, so their hulls do not merge
#
# Cohesion is not a taxonomy being imposed. The communities are detected from
# these same edges; left alone they interleave spatially, so the groups the data
# contains are real but unreadable. This separates them on screen without
# deciding what they are.
#
# Chains then separate themselves, because their edges do. That grouping becomes
# something the map demonstrates rather than something it asserts, and the space
# each chain occupies is the space its activity earns.
#
# Communities are detected on the same graph and carried to the front-end as
# n["comm"], which draws the hulls. Robinhood's 54 tokens resolve into several
# rotation neighbourhoods instead of one red mass — and the neighbourhoods are
# not chain-pure, which is the part a chain-shaped layout could never have shown.
#
# Positions are solved here, at build time, and frozen. The renderer never moves
# a node: that is what keeps scrubbing at 60fps.
# =============================================================================
SPRING, REPEL, COLLIDE = 0.85, 0.00040, 1.08
STEP, ITERS, MAXSTEP   = 0.42, 700, 0.030
MASS_PER_DEGREE        = 0.35    # hubs are heavy, so they anchor rather than fling
RESOLUTION             = 1.0     # community granularity; higher splits more
META_GAP               = 1.22    # clearance between neighbourhood discs
BRIDGE                 = 0.16    # how far a cross-neighbourhood rotation may pull a token


def communities(n_count, link, resolution=RESOLUTION, seed=7, iters=40):
    """Louvain local-moving, one phase. Returns a community id per node.

    Label propagation was tried first and is not usable here: on a subgraph as
    dense as Robinhood's it converges to a single label, returning one community
    of 74 and telling you nothing. Modularity with a resolution term splits it.
    """
    rnd = random.Random(seed)
    adj = collections.defaultdict(list)
    degree = collections.defaultdict(float)
    for a, b, w in link:
        adj[a].append((b, w)); adj[b].append((a, w))
        degree[a] += w; degree[b] += w
    m2 = sum(w for _, _, w in link) * 2 or 1.0

    com = list(range(n_count))
    tot = {i: degree[i] for i in range(n_count)}
    order = list(range(n_count))
    for _ in range(iters):
        rnd.shuffle(order)
        moved = False
        for i in order:
            if not adj[i]:
                continue
            here = com[i]
            tot[here] -= degree[i]
            into = collections.Counter()
            for j, w in adj[i]:
                into[com[j]] += w
            best, best_gain = here, into.get(here, 0.0) - resolution * tot.get(here, 0.0) * degree[i] / m2
            for c, w in into.items():
                gain = w - resolution * tot.get(c, 0.0) * degree[i] / m2
                if gain > best_gain + 1e-12:
                    best, best_gain = c, gain
            com[i] = best
            tot[best] = tot.get(best, 0.0) + degree[i]
            moved = moved or best != here
        if not moved:
            break

    size = collections.Counter(com)
    rank = {c: i for i, (c, _) in enumerate(size.most_common())}
    return [rank[c] for c in com]


def _relax(idx, link, rad, iters, seed, centre_pull=0.0, anchor=None):
    """Spring/repulsion/collision solve over the node indices in `idx`.

    Returns {node index: (x, y)} in local coordinates. Used twice: once inside
    each neighbourhood, and once over the neighbourhoods themselves.
    """
    rnd = random.Random(seed)
    n = len(idx)
    if n == 0:
        return {}
    if n == 1:
        return {idx[0]: (0.0, 0.0)}
    at = {v: i for i, v in enumerate(idx)}
    ln = [(at[a], at[b], w) for a, b, w in link if a in at and b in at]
    r = [rad[v] for v in idx]

    mass = [1.0] * n
    for a, b, w in ln:
        mass[a] += MASS_PER_DEGREE * w
        mass[b] += MASS_PER_DEGREE * w

    px, py = [0.0] * n, [0.0] * n
    for i in range(n):
        a = rnd.random() * 2 * math.pi
        d = (0.15 + 0.5 * math.sqrt(rnd.random())) * math.sqrt(n)
        px[i], py[i] = math.cos(a) * d * 0.12, math.sin(a) * d * 0.12

    for it in range(iters):
        cool = (1 - it / iters) ** 1.2
        fx, fy = [0.0] * n, [0.0] * n
        for a, b, w in ln:
            dx, dy = px[b] - px[a], py[b] - py[a]
            d = math.hypot(dx, dy) or 1e-6
            rest = (r[a] + r[b]) * 1.9 + 0.02
            f = SPRING * w * (d - rest)
            ux, uy = dx / d, dy / d
            fx[a] += f * ux; fy[a] += f * uy
            fx[b] -= f * ux; fy[b] -= f * uy
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = px[j] - px[i], py[j] - py[i]
                d2 = dx * dx + dy * dy
                d = math.sqrt(d2) or 1e-6
                ux, uy = dx / d, dy / d
                rep = REPEL * (r[i] + r[j]) / max(d2, 0.0016)
                fx[i] -= rep * ux; fy[i] -= rep * uy
                fx[j] += rep * ux; fy[j] += rep * uy
                floor = (r[i] + r[j]) * COLLIDE
                if d < floor:
                    push = (floor - d) * 0.5
                    fx[i] -= push * ux; fy[i] -= push * uy
                    fx[j] += push * ux; fy[j] += push * uy
        if centre_pull:
            for i in range(n):
                fx[i] -= centre_pull * px[i]
                fy[i] -= centre_pull * py[i]
        lim = MAXSTEP * cool
        for i in range(n):
            dx = fx[i] / mass[i] * STEP * cool
            dy = fy[i] / mass[i] * STEP * cool
            m = math.hypot(dx, dy)
            if m > lim:
                dx, dy = dx / m * lim, dy / m * lim
            px[i] += dx; py[i] += dy
    cx = sum(px) / n; cy = sum(py) / n
    return {idx[i]: (px[i] - cx, py[i] - cy) for i in range(n)}


def layout(nodes, edges, aspect=0.80, seed=7):
    """Solve node positions in place. Sets n["x"], n["y"], n["comm"].

    Compound, in two phases. A single global solve finds the neighbourhoods but
    leaves them interleaved in space — topologically right, visually unreadable,
    with four frames stacked over the same patch of canvas. So the
    neighbourhoods are placed first, as a graph of their own where each is a
    disc the size of its contents, and each one's members are then solved inside
    its slot. Separation is then a property of the construction rather than
    something a force has to win.
    """
    n_count = len(nodes)
    if not n_count:
        return
    ix = {n["id"]: i for i, n in enumerate(nodes)}
    mcmax = max((max(n["mc"]) for n in nodes), default=1) or 1
    rad = [0.030 + 0.070 * math.sqrt((max(n["mc"]) or 0) / mcmax) for n in nodes]

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

    comm = communities(n_count, link)
    for i, c in enumerate(comm):
        nodes[i]["comm"] = c
    members = collections.defaultdict(list)
    for i, c in enumerate(comm):
        members[c].append(i)

    # ---- phase 1: solve each neighbourhood on its own, in local coordinates ----
    local, radius = {}, {}
    for c, mem in members.items():
        local[c] = _relax(mem, link, rad, iters=ITERS, seed=seed + c, centre_pull=0.10)
        radius[c] = max((math.hypot(x, y) + rad[i] for i, (x, y) in local[c].items()),
                        default=0.1)

    # ---- phase 2: pack the neighbourhoods as discs -----------------------------
    # A force solve was tried here and is the wrong tool for eight items: the
    # meta weights are on a different scale to the node weights, so the springs
    # and the degree-mass swamped the repulsion and every neighbourhood settled
    # on the origin. Packing is deterministic, cannot overlap by construction,
    # and lets the most strongly connected pair be seated next to each other.
    keys = sorted(members, key=lambda c: -len(members[c]))
    between = collections.Counter()
    for a, b, w in link:
        ca, cb = comm[a], comm[b]
        if ca != cb:
            between[(min(ca, cb), max(ca, cb))] += w
    affinity = lambda a, b: between.get((min(a, b), max(a, b)), 0.0)

    centre = {keys[0]: (0.0, 0.0)}
    for c in keys[1:]:
        need = radius[c] * META_GAP
        best, best_score = None, None
        step = radius[keys[0]] * 0.25 or 0.05
        probe = need + radius[keys[0]] * META_GAP
        while best is None and probe < 40 * step:
            for k in range(72):
                th = 2 * math.pi * k / 72
                x, y = math.cos(th) * probe, math.sin(th) * probe
                if any(math.hypot(x - ox, y - oy) < need + radius[o] * META_GAP
                       for o, (ox, oy) in centre.items()):
                    continue
                # among free spots, sit closest to whatever this pack trades with
                pull = sum(affinity(c, o) / (math.hypot(x - ox, y - oy) or 1e-6)
                           for o, (ox, oy) in centre.items())
                score = pull - 0.04 * math.hypot(x, y)
                if best_score is None or score > best_score:
                    best, best_score = (x, y), score
            probe += step
        centre[c] = best or (probe, 0.0)

    # ---- phase 3: members take their neighbourhood's slot ----------------------
    px, py = [0.0] * n_count, [0.0] * n_count
    for c, mem in members.items():
        ox, oy = centre.get(c, (0.0, 0.0))
        for i in mem:
            lx, ly = local[c][i]
            px[i], py[i] = ox + lx, oy + ly

    # A token that rotates with another neighbourhood is allowed to drift toward
    # it. That drift is the bridge between two packs and is worth seeing, so it
    # is bounded rather than forbidden.
    drift = collections.defaultdict(lambda: [0.0, 0.0])
    for a, b, w in link:
        if comm[a] == comm[b]:
            continue
        for i, j in ((a, b), (b, a)):
            ox, oy = centre.get(comm[i], (0.0, 0.0))
            tx, ty = centre.get(comm[j], (0.0, 0.0))
            drift[i][0] += (tx - ox) * BRIDGE * w
            drift[i][1] += (ty - oy) * BRIDGE * w
    for i, (dx, dy) in drift.items():
        # bounded by the node's own neighbourhood: a bridge should lean a token
        # toward its other pack, not tear it out and stretch the frame across
        # the map behind it
        cap = radius[comm[i]] * 0.85
        m = math.hypot(dx, dy)
        if m > cap:
            dx, dy = dx / m * cap, dy / m * cap
        px[i] += dx; py[i] += dy

    cx = sum(px) / n_count; cy = sum(py) / n_count
    span = max(max(abs(px[i] - cx), abs(py[i] - cy)) for i in range(n_count)) or 1.0
    for i, n in enumerate(nodes):
        n["x"] = round((px[i] - cx) / span, 4)
        n["y"] = round((py[i] - cy) / span * aspect, 4)
