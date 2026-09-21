#!/usr/bin/env python3
"""
Count the fresh inflows a top-N edge cap would discard.

    python3 research/scripts/fresh_inflows.py [--write-claims]

The map guarantees a line to any rotation out of an established top-20 name into
a token the cohort has only just entered, whether or not that rotation wins the
day's volume contest. The claim behind that guarantee is that such rotations are
usually small, so a plain top-N cap throws most of them away. This script is the
provenance for that number: it replays the renderer's own edge selection over
every frame of the published payload and counts how many qualifying inflows the
cap would have dropped.

It reimplements edgeAt/isNew/bigName from engine.js deliberately. Reading the
constants out of build_site.py rather than restating them means the count cannot
silently drift from what the site actually draws.
"""
import argparse
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAYLOAD = os.path.join(ROOT, "data", "bubbles80.json")
BUILD = os.path.join(ROOT, "build_site.py")
CLAIMS = os.path.join(ROOT, "research", "claims.json")


def config():
    """Pull the edge/fresh constants out of the CONFIG block in build_site.py."""
    src = open(BUILD).read()
    want = ("edgeWindow", "edgeMinShared", "maxEdges",
            "newDays", "freshSourceRank", "freshMinShared")
    out = {}
    for name in want:
        m = re.search(rf"\b{name}\s*:\s*(\d+)", src)
        if not m:
            sys.exit(f"{name} not found in build_site.py — the CONFIG block moved")
        out[name] = int(m.group(1))
    return out


def edge_at(w, t, window, last):
    """engine.js edgeAt: peak shared-wallet count in a +/-window neighbourhood,
    linearly de-weighted by distance from t."""
    best = 0.0
    lo, hi = max(0, math.floor(t) - window), min(last, math.ceil(t) + window)
    for i in range(lo, hi + 1):
        v = w[i]
        if not v:
            continue
        best = max(best, v * max(0.0, 1 - abs(i - t) / (window + 1)))
    return best


def count():
    """(total, below_cap) fresh-inflow token-day events. Used by check_claims.py."""
    C = config()
    D = json.load(open(PAYLOAD))
    nodes = {n["id"]: n for n in D["nodes"]}
    last = len(D["days"]) - 1
    total = below = 0
    for t in range(last + 1):
        live = []
        for e in D["edges"]:
            w = edge_at(e["w"], t, C["edgeWindow"], last)
            if w >= C["edgeMinShared"]:
                live.append((w, e))
        live.sort(key=lambda r: -r[0])
        drawn = {id(e) for _, e in live[:C["maxEdges"]]}
        for w, e in live:
            a, b = nodes[e["a"]], nodes[e["b"]]
            if w < C["freshMinShared"]:
                continue
            if not (0 <= t - b["first"] <= C["newDays"]):
                continue
            if 0 <= t - a["first"] <= C["newDays"]:
                continue
            if a["rank"] >= C["freshSourceRank"]:
                continue
            total += 1
            if id(e) not in drawn:
                below += 1
    return total, below


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-claims", action="store_true",
                    help="record the result in research/claims.json")
    args = ap.parse_args()

    C = config()
    D = json.load(open(PAYLOAD))
    nodes = {n["id"]: n for n in D["nodes"]}
    last = len(D["days"]) - 1

    def is_new(n, t):
        age = t - n["first"]
        return 0 <= age <= C["newDays"]

    def big_name(n):
        return n["rank"] < C["freshSourceRank"]

    total = below = 0
    distinct_total, distinct_below = set(), set()
    per_day = []

    for t in range(last + 1):
        live = []
        for e in D["edges"]:
            w = edge_at(e["w"], t, C["edgeWindow"], last)
            if w >= C["edgeMinShared"]:
                live.append((w, e))
        live.sort(key=lambda r: -r[0])
        drawn = {id(e) for _, e in live[:C["maxEdges"]]}

        day_t = day_b = 0
        for w, e in live:
            a, b = nodes[e["a"]], nodes[e["b"]]
            if w < C["freshMinShared"]:
                continue
            if not (is_new(b, t) and not is_new(a, t) and big_name(a)):
                continue
            total += 1
            day_t += 1
            distinct_total.add((e["a"], e["b"]))
            if id(e) not in drawn:
                below += 1
                day_b += 1
                distinct_below.add((e["a"], e["b"]))
        per_day.append((D["days"][t], day_t, day_b))

    pct = round(100 * below / total) if total else 0
    print(f"config: {C}")
    print()
    print(f"fresh inflows (token-day events)   : {total:,}")
    print(f"  ... below the top-{C['maxEdges']} edge cap       : {below:,}  ({pct}%)")
    print(f"distinct token pairs               : {len(distinct_total):,}")
    print(f"  ... below the cap on every frame : {len(distinct_below - (distinct_total - distinct_below)):,}")
    print()
    busiest = sorted(per_day, key=lambda r: -r[1])[:5]
    print("busiest frames (day, inflows, of which below cap):")
    for d, a, b in busiest:
        print(f"  {d}  {a:>3}  {b:>3}")

    if args.write_claims:
        claims = json.load(open(CLAIMS))
        claims["fresh_below_cap"] = {
            "value": below,
            "unit": "",
            "label": "fresh inflows below the cap",
            "detail": f"{below:,} of {total:,}",
            "scope": (
                f"Token-day events across the {last + 1}-frame window where a token the "
                f"cohort entered within {C['newDays']} days receives a rotation of at least "
                f"{C['freshMinShared']} shared wallets from an established top-"
                f"{C['freshSourceRank']} name. Counted against the top-{C['maxEdges']} "
                "edge cap the renderer would otherwise apply, replaying engine.js's own "
                "edgeAt selection frame by frame. Counts events, not distinct pairs: one "
                "pair persisting over several days counts once per day, which is what the "
                "cap discards it on."
            ),
            "source": "data/bubbles80.json",
            "script": "research/scripts/fresh_inflows.py",
            "verified": __import__("datetime").date.today().isoformat(),
        }
        json.dump(claims, open(CLAIMS, "w"), indent=4, ensure_ascii=False)
        open(CLAIMS, "a").write("\n")
        print(f"\nwrote fresh_below_cap = {below} of {total} to research/claims.json")


if __name__ == "__main__":
    main()
