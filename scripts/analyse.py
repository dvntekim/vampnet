import json, collections, statistics as st

def load():
    raw = json.load(open("data/cohort_balances.json"))
    # holdings[token][day] = summed token_amount ; prices[token][day] = median unit price
    hold = collections.defaultdict(lambda: collections.defaultdict(float))
    px   = collections.defaultdict(lambda: collections.defaultdict(list))
    val  = collections.defaultdict(lambda: collections.defaultdict(float))
    sym  = {}
    for w, rows in raw.items():
        for r in rows:
            d = r["block_timestamp"][:10]; t = r["token_address"]
            amt = r.get("token_amount") or 0.0; v = r.get("value_usd") or 0.0
            if amt <= 0: continue
            hold[t][d] += amt; val[t][d] += v
            px[t][d].append(v/amt)
            sym[t] = r.get("token_symbol") or t[:8]
    price = {t: {d: st.median(v) for d, v in dd.items()} for t, dd in px.items()}
    return hold, price, val, sym, raw

STABLE = {"USDC","USDT","SOL","WSOL","USDS","JITOSOL","MSOL","JUPSOL","BSOL","USDE","JLP"}
def clean(s): return s.replace("⚠️","").replace("🌱","").strip().upper()
