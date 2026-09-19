import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nansen import call

def leaderboards(winners, win, per_page=100, out="data/winner_leaderboards.json"):
    res, spent = {}, 0
    for i, w in enumerate(winners, 1):
        key = f"{w['token_symbol']}|{w['chain']}"
        st, body, h = call("/api/v1/tgm/pnl-leaderboard", {
            "chain": w["chain"], "token_address": w["token_address"],
            "date": win, "pagination": {"page": 1, "per_page": per_page}})
        u = h.get("x-nansen-credits-used"); spent += int(u or 0)
        rem = h.get("x-nansen-credits-remaining")
        if st == 200 and body.get("data"):
            res[key] = {"chain": w["chain"], "address": w["token_address"],
                        "price_change": w.get("price_change"), "rows": body["data"]}
            print(f"[{i:>2}/{len(winners)}] {key:<26} traders={len(body['data']):<4} rem={rem}", flush=True)
        else:
            print(f"[{i:>2}/{len(winners)}] {key:<26} HTTP {st} rem={rem}", flush=True)
        time.sleep(0.12)
    json.dump(res, open(out, "w"), indent=2)
    return res, spent
