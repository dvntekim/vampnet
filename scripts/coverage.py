"""Leave-one-out coverage test + first-sightings engine."""
import json, collections, statistics as stx

def load_balances(*paths):
    merged = {}
    for p in paths:
        try: merged.update(json.load(open(p)))
        except Exception: pass
    return merged

def index_holdings(bal):
    """(chain, token_addr) -> {day -> {wallet: (amount, usd)}}"""
    idx = collections.defaultdict(lambda: collections.defaultdict(dict))
    sym = {}
    for w, chains in bal.items():
        for ch, rows in (chains or {}).items():
            for r in rows:
                amt = r.get("token_amount") or 0
                if amt <= 0: continue
                key = (ch, (r.get("token_address") or "").lower())
                idx[key][r["block_timestamp"][:10]][w] = (amt, r.get("value_usd") or 0)
                sym[key] = r.get("token_symbol") or ""
    return idx, sym

def leave_one_out_cohort(cohort_file, exclude_coin):
    """Wallets that still qualify (2+ coins) WITHOUT the excluded coin."""
    coh = json.load(open(cohort_file))
    out = set()
    for w, d in coh.items():
        coins = {c for c in d["coins"] if c != exclude_coin}
        if len(coins) >= 2:
            out.add(w)
    return out

def coverage(winners, cohort_file, idx, sym, ohlcv_peak=None):
    """For each winner: did the leave-one-out cohort independently hold it, and how early?"""
    rows = []
    for w in winners:
        key = (w["chain"], (w["token_address"] or "").lower())
        coin_key = f"{w['token_symbol']}|{w['chain']}"
        loo = leave_one_out_cohort(cohort_file, coin_key)
        days = sorted(idx.get(key, {}))
        holders_by_day = idx.get(key, {})
        first_day, first_wallets, peak_wallets, peak_usd = None, 0, 0, 0.0
        for d in days:
            hs = set(holders_by_day[d]) & loo
            if hs and first_day is None:
                first_day, first_wallets = d, len(hs)
            if hs:
                peak_wallets = max(peak_wallets, len(hs))
                peak_usd = max(peak_usd, sum(holders_by_day[d][x][1] for x in hs))
        rows.append({"symbol": w["token_symbol"], "chain": w["chain"],
                     "price_change": w.get("price_change"),
                     "loo_cohort_size": len(loo),
                     "covered": first_day is not None,
                     "first_day": first_day, "first_wallets": first_wallets,
                     "peak_wallets": peak_wallets, "peak_usd": peak_usd})
    return rows

def first_sightings(idx, sym, max_age_days=None, min_wallets=2):
    """Tokens newly appearing in cohort wallets: the monthly discovery engine."""
    out = []
    for key, bydat in idx.items():
        days = sorted(bydat)
        if not days: continue
        first = days[0]
        holders = set()
        peak_w, peak_usd = 0, 0.0
        for d in days:
            holders |= set(bydat[d])
            peak_w = max(peak_w, len(bydat[d]))
            peak_usd = max(peak_usd, sum(v[1] for v in bydat[d].values()))
        if peak_w >= min_wallets:
            out.append({"chain": key[0], "token": key[1], "symbol": sym.get(key, ""),
                        "first_seen": first, "distinct_wallets": len(holders),
                        "peak_concurrent": peak_w, "peak_usd": peak_usd})
    out.sort(key=lambda r: (-r["peak_concurrent"], -r["peak_usd"]))
    return out
