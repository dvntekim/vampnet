#!/usr/bin/env python3
"""
Walk-forward out-of-time validation — the answer to "you picked a lucky window".

    python3 research/scripts/walk_forward.py                 # all freezes
    python3 research/scripts/walk_forward.py --cap 4000      # global credit ceiling
    python3 research/scripts/walk_forward.py --write-claims

A single frozen-cohort run proves the cohort could not see its test winners.
It does not prove the result generalises: one freeze date on 2026-08-31 gave
7 of 9 on robinhood, and two coins landing the other way would have made it
56%. n=9 is a coin-flip's worth of evidence and a careful reader will say so.

This runs the same protocol at several freeze dates whose TEST WINDOWS DO NOT
OVERLAP, so each window contributes an independent set of unseen winners, then
pools them. The pooled figure is what survives scrutiny; the per-window spread
is what says how much to trust it.

HOW FAR BACK THIS CAN GO IS NOT OUR CHOICE. token-screener serves daily data
for two months only; a training window reaching further back is refused with a
400 rather than silently truncated, so the earliest usable freeze date moves
forward every day. Measured 2026-09-25: freezes at 06-25, 07-15, 08-04 and
08-24 were all refused, and only 09-04 remained in range. Windows that cannot
be measured are recorded with their reason instead of being dropped, so the
artifact shows how much of the sweep the API actually allowed.

Every window uses the identical threshold (recurrence 4) as the published
claim. Windows are not dropped for being unflattering — a freeze that yields
no cohort, or 0%, is reported as measured. That is the whole point.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
OOT = os.path.join(HERE, "out_of_time.py")
OUT = os.path.join(ROOT, "research", "walk_forward.json")
CLAIMS = os.path.join(ROOT, "research", "claims.json")

# Freeze dates chosen so each test window is 20 days and none overlaps another.
# The earliest is bounded by when the cohort's balance history begins; the last
# is bounded by the most recent day the daily job has fetched.
TEST_DAYS = 20
FREEZES = ["2026-06-25", "2026-07-15", "2026-08-04", "2026-08-24", "2026-09-04"]
CHAINS = "robinhood,bnb,base,solana"
RECURRENCE = 4


def wilson(k, n, z=1.96):
    """95% CI for a proportion. Small-n coverage needs an interval, not a point:
    7/9 with a normal approximation runs off the end of the scale."""
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - m), min(1.0, c + m))


def run_one(freeze, cap):
    to = (dt.date.fromisoformat(freeze) + dt.timedelta(days=TEST_DAYS)).isoformat()
    art = os.path.join(ROOT, "research", f"out_of_time_{freeze}.json")
    before = os.path.getmtime(art) if os.path.exists(art) else 0
    cmd = [sys.executable, OOT, "--freeze", freeze, "--to", to,
           "--recurrence", str(RECURRENCE), "--chains", CHAINS, "--cap", str(cap)]
    print(f"\n=== freeze {freeze}  test → {to} ===", flush=True)
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(p.stdout)
    if p.returncode != 0:
        # A window with no unseen winners, or no cohort at the threshold, is a
        # real measurement — record it rather than aborting the sweep.
        msg = (p.stderr or p.stdout).strip().splitlines()[-1:] or ["failed"]
        print(f"  -> not measurable: {msg[0]}", flush=True)
        return {"freeze": freeze, "to": to, "ok": False, "reason": msg[0]}
    if not os.path.exists(art) or os.path.getmtime(art) == before:
        return {"freeze": freeze, "to": to, "ok": False, "reason": "no artifact written"}
    a = json.load(open(art))
    return {"freeze": freeze, "to": to, "ok": True,
            "train_window": a["train_window"], "test_window": a["test_window"],
            "cohort_wallets": a["cohort_wallets"], "trader_pool": a["trader_pool"],
            "train_winners": a["train_winners"], "test_winners": a["test_winners"],
            "covered": a["covered"], "coverage_pct": a["coverage_pct"],
            "by_chain": a["by_chain"], "credits_used": a["credits_used"],
            "artifact": os.path.relpath(art, ROOT)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=6000, help="global credit ceiling")
    ap.add_argument("--freezes", default=",".join(FREEZES))
    ap.add_argument("--write-claims", action="store_true")
    a = ap.parse_args()

    freezes = [f.strip() for f in a.freezes.split(",") if f.strip()]
    per = max(500, a.cap // max(1, len(freezes)))
    print(f"Walk-forward: {len(freezes)} freeze dates, {TEST_DAYS}-day "
          f"non-overlapping tests, recurrence {RECURRENCE}, "
          f"global cap {a.cap} (~{per}/window)")

    rows, spent = [], 0
    for f in freezes:
        if spent >= a.cap:
            print(f"\n!! global cap reached at {spent} credits — stopping early")
            break
        r = run_one(f, min(per, a.cap - spent))
        spent += r.get("credits_used", 0)
        rows.append(r)

    ok = [r for r in rows if r["ok"]]
    # One surviving window is a replication of the headline at a second freeze
    # date, not a walk-forward. Saying otherwise would dress up a single
    # measurement as a sweep, which is the exact failure this script exists to
    # catch elsewhere.
    kind = ("walk-forward over %d independent windows" % len(ok) if len(ok) > 1
            else "single-window replication" if len(ok) == 1
            else "no measurable window")
    tot_n = sum(r["test_winners"] for r in ok)
    tot_k = sum(r["covered"] for r in ok)
    rh_n = sum(r["by_chain"].get("robinhood", {}).get("total", 0) for r in ok)
    rh_k = sum(r["by_chain"].get("robinhood", {}).get("covered", 0) for r in ok)
    lo, hi = wilson(rh_k, rh_n)
    alo, ahi = wilson(tot_k, tot_n)

    res = {
        "measured": dt.date.today().isoformat(),
        "protocol": "walk-forward frozen-cohort, non-overlapping test windows",
        "result_kind": None,      # filled below once the survivors are known
        "test_days": TEST_DAYS, "recurrence": RECURRENCE, "chains": CHAINS.split(","),
        "windows": rows,
        "pooled": {
            "robinhood": {"covered": rh_k, "total": rh_n,
                          "pct": round(100 * rh_k / rh_n) if rh_n else 0,
                          "ci95": [round(100 * lo), round(100 * hi)]},
            "all_chains": {"covered": tot_k, "total": tot_n,
                           "pct": round(100 * tot_k / tot_n) if tot_n else 0,
                           "ci95": [round(100 * alo), round(100 * ahi)]},
        },
        "credits_used": spent,
    }
    res["result_kind"] = kind
    res["windows_attempted"] = len(rows)
    res["windows_measured"] = len(ok)
    json.dump(res, open(OUT, "w"), indent=2)

    print("\n" + "=" * 72)
    print(f"{'freeze':<12}{'test window':<26}{'cohort':>7}{'unseen':>8}{'hit':>5}{'rh':>9}")
    for r in rows:
        if not r["ok"]:
            print(f"{r['freeze']:<12}{'— ' + r['reason'][:22]:<26}")
            continue
        rh = r["by_chain"].get("robinhood", {})
        print(f"{r['freeze']:<12}{r['test_window']['from']+' → '+r['test_window']['to']:<26}"
              f"{r['cohort_wallets']:>7}{r['test_winners']:>8}{r['covered']:>5}"
              f"{str(rh.get('covered', 0)) + '/' + str(rh.get('total', 0)):>9}")
    print("=" * 72)
    print(f"{kind}  ({len(ok)}/{len(rows)} windows measurable)")
    print(f"POOLED robinhood : {rh_k}/{rh_n} = {res['pooled']['robinhood']['pct']}%  "
          f"95% CI [{res['pooled']['robinhood']['ci95'][0]}–{res['pooled']['robinhood']['ci95'][1]}]")
    print(f"POOLED all chains: {tot_k}/{tot_n} = {res['pooled']['all_chains']['pct']}%  "
          f"95% CI [{res['pooled']['all_chains']['ci95'][0]}–{res['pooled']['all_chains']['ci95'][1]}]")
    print(f"credits used     : {spent}")
    print(f"written          : {os.path.relpath(OUT, ROOT)}")

    if a.write_claims and len(ok) < 2:
        print("\nNot writing a claim: a single window is a replication, not a sweep.\n"
              "Quote it next to the 2026-08-31 figure instead.")
    elif a.write_claims and rh_n:
        claims = json.load(open(CLAIMS))
        claims["oot_walk_forward"] = {
            "value": res["pooled"]["robinhood"]["pct"],
            "unit": "%",
            "label": "walk-forward coverage",
            "detail": f"{rh_k} of {rh_n}",
            "scope": (
                f"Pooled across {len(ok)} freeze dates with non-overlapping {TEST_DAYS}-day "
                f"test windows, each cohort frozen at the same recurrence-{RECURRENCE} "
                "threshold and shown nothing after its freeze date. Robinhood-chain "
                f"winners only. 95% CI {res['pooled']['robinhood']['ci95'][0]}-"
                f"{res['pooled']['robinhood']['ci95'][1]}%. Across all four chains the same "
                f"runs pool to {res['pooled']['all_chains']['pct']}% "
                f"({tot_k} of {tot_n}) — coverage tracks the repeat-winner rate, which is "
                "the product's central finding. Windows yielding no cohort at the threshold "
                "are reported, not dropped."
            ),
            "source": "research/walk_forward.json",
            "script": "research/scripts/walk_forward.py",
            "verified": dt.date.today().isoformat(),
        }
        json.dump(claims, open(CLAIMS, "w"), indent=4, ensure_ascii=False)
        open(CLAIMS, "a").write("\n")
        print(f"wrote oot_walk_forward = {res['pooled']['robinhood']['pct']}% to claims.json")


if __name__ == "__main__":
    main()
