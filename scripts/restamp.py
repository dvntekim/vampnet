#!/usr/bin/env python3
"""
Re-solve the layout and re-read the claims for an existing payload. Zero credits.

`make.py --build` re-derives the payload from the raw balance cache, which is
hundreds of megabytes and is not in the repository. Everything downstream of that
derivation — where nodes sit, and which headline numbers are displayed — depends
only on data/bubbles80.json, so this re-applies both without an API key:

    python3 scripts/restamp.py            # re-solve layout + refresh claims
    python3 scripts/restamp.py --claims   # claims only, leave positions alone
    python3 build_site.py                 # render

Use it after editing the layout constants in scripts/build_bubbles.py or a value
in research/claims.json. It is a development tool; a real refresh is `make.py`.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build_bubbles import layout                     # noqa: E402

PAYLOAD = os.path.join(ROOT, "data", "bubbles80.json")
CLAIMS = os.path.join(ROOT, "research", "claims.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", action="store_true", help="refresh claims only")
    ap.add_argument("--layout", action="store_true", help="re-solve layout only")
    a = ap.parse_args()
    do_layout = a.layout or not a.claims
    do_claims = a.claims or not a.layout

    if not os.path.exists(PAYLOAD):
        raise SystemExit(f"{os.path.relpath(PAYLOAD, ROOT)} not found — run make.py first.")
    p = json.load(open(PAYLOAD))

    if do_layout:
        layout(p["nodes"], p["edges"])
        xs = [n["x"] for n in p["nodes"]]
        ys = [n["y"] for n in p["nodes"]]
        print(f"  layout: {len(p['nodes'])} nodes solved  "
              f"x [{min(xs):+.2f},{max(xs):+.2f}]  y [{min(ys):+.2f},{max(ys):+.2f}]")

    if do_claims:
        C = json.load(open(CLAIMS))
        p["claims"] = {k: {"value": C[k]["value"], "unit": C[k]["unit"],
                           "label": C[k]["label"], "detail": C[k].get("detail", ""),
                           "scope": C[k]["scope"], "verified": C[k]["verified"]}
                       for k in ("oot", "lift", "lead")}
        p.setdefault("stats", {}).update(
            {k: C[k]["value"] for k in ("oot", "lift", "lead")})
        print("  claims: " + " · ".join(
            f"{C[k]['label']} {C[k]['value']}{C[k]['unit']}" for k in ("oot", "lift", "lead")))

    json.dump(p, open(PAYLOAD, "w"), separators=(",", ":"))
    print(f"  wrote {os.path.relpath(PAYLOAD, ROOT)} — now run: python3 build_site.py")


if __name__ == "__main__":
    main()
