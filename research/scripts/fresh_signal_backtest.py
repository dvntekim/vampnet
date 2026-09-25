#!/usr/bin/env python3
"""
Every fresh-inflow signal on the map, and what the token's market cap did next.

    python3 research/scripts/fresh_signal_backtest.py

A signal is the first day a top-20 name sends >= 3 shared wallets into a token
the cohort entered within the last 14 days (same rule as engine.js, but read
from the raw day's count, not the +/-1 day smoothed edge, so nothing from the
next day leaks in). Entry is the NEXT day's market cap, because you only see a
day's balances after it closes.

IN-SAMPLE. The 80 tokens are chosen by peak cohort capital over the whole
window, and the cohort is chosen by who won over the whole window. Use this to
pick illustrations and to find patterns worth an out-of-time test. Do not put
its numbers in claims.json as a performance claim.
"""
import json, os, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = json.load(open(os.path.join(ROOT, "data", "bubbles80.json")))
N = {n["id"]: n for n in D["nodes"]}
days = D["days"]; last = len(days) - 1
NEW_DAYS, SRC_RANK, MIN_SHARED = 14, 20, 3

sig = {}
for t in range(last + 1):
    for e in D["edges"]:
        w = e["w"][t]
        if w < MIN_SHARED:
            continue
        a, b = N[e["a"]], N[e["b"]]
        for src, dst in ((a, b), (b, a)):
            if (0 <= t - dst["first"] <= NEW_DAYS
                    and not 0 <= t - src["first"] <= NEW_DAYS
                    and src["rank"] < SRC_RANK):
                sig.setdefault(dst["id"], {}).setdefault(t, []).append((src["sym"], w))

rows = []
for tid, by_t in sig.items():
    n = N[tid]; t0 = min(by_t); te = min(t0 + 1, last); mc = n["mc"]
    if not mc[te]:
        continue
    after = mc[te:]; pk = max(after); tp = te + after.index(pk)
    wallets = sum(w for _, w in by_t[t0])
    rows.append(dict(sym=n["sym"], signal=days[t0], sources=by_t[t0], wallets=wallets,
                     entry=mc[te], peak=pk, peak_day=days[tp], peak_x=pk / mc[te],
                     end_x=mc[-1] / mc[te]))

rows.sort(key=lambda r: -r["peak_x"])
for r in rows:
    print(f"{r['sym']:11} {r['signal']}  wallets {r['wallets']:>3}  entry ${r['entry']/1e6:6.2f}M"
          f"  peak ${r['peak']/1e6:7.2f}M {r['peak_day']}  x{r['peak_x']:6.2f}  end x{r['end_x']:5.2f}")

def summary(label, g):
    px = [r["peak_x"] for r in g]; ex = [r["end_x"] for r in g]
    print(f"{label:28} n={len(g):>2}  median peak x{st.median(px):5.2f}  >=5x {sum(x >= 5 for x in px):>2}"
          f"  median at {days[-1]} x{st.median(ex):4.2f}  lost half {sum(x < 0.5 for x in ex):>2}")

print()
summary("all signals", rows)
summary("quiet (<=5 wallets)", [r for r in rows if r["wallets"] <= 5])
summary("loud (>=6 wallets)", [r for r in rows if r["wallets"] >= 6])
