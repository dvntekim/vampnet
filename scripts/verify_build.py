#!/usr/bin/env python3
"""
Gate a build before it is published. Exits non-zero if anything is wrong.

    python3 scripts/verify_build.py

Both CI paths call this: the pull-request check, and the daily job immediately
before it pushes to main. One definition, so the two cannot drift apart and let
a broken build through on the path that happens to be behind.

The checks are deliberately about the *contract*, not just the file size. A
payload missing its claims block passes every size and count check and then
throws in the browser on D.claims.oot, which is exactly the failure that reached
main once already.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "docs", "index.html")
PAYLOAD = os.path.join(ROOT, "data", "bubbles80.json")


def main():
    if not os.path.exists(SITE) or not os.path.exists(PAYLOAD):
        sys.exit(f"missing build artefact: need both {SITE} and {PAYLOAD}")

    html = open(SITE, encoding="utf-8").read()
    payload = json.load(open(PAYLOAD))
    stats = payload.get("stats", {})
    claims = payload.get("claims", {})

    checks = {
        "site is a sane size":      os.path.getsize(SITE) > 200_000,
        "payload is embedded":      "const D = {" in html,
        "nodes present":            len(payload.get("nodes", [])) >= 20,
        "edges present":            len(payload.get("edges", [])) >= 20,
        "timeline present":         len(payload.get("days", [])) >= 30,
        "chains present":           len(payload.get("chains", [])) >= 1,
        # the masthead and the credibility strip read these
        "claims block present":     all(k in claims for k in ("oot", "lift", "lead")),
        "claims carry a scope":     all(claims.get(k, {}).get("scope")
                                        for k in ("oot", "lift", "lead")),
        "cohort size present":      isinstance(stats.get("cohort"), int) and stats["cohort"] > 0,
        "every node is placed":     all(isinstance(n.get("x"), (int, float))
                                        and isinstance(n.get("y"), (int, float))
                                        for n in payload.get("nodes", [])),
        "node positions are finite": all(abs(n.get("x", 0)) < 1e3 and abs(n.get("y", 0)) < 1e3
                                         for n in payload.get("nodes", [])),
    }

    for name, ok in checks.items():
        print(("  ok   " if ok else "  FAIL ") + name)
    if not all(checks.values()):
        sys.exit("refusing to publish a broken build")

    print(f"\n{len(payload['nodes'])} nodes · {len(payload['edges'])} edges · "
          f"{payload['days'][0]} → {payload['days'][-1]} · "
          f"cohort {stats['cohort']} · coverage {claims['oot']['value']}%")


if __name__ == "__main__":
    main()
