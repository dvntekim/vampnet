#!/usr/bin/env python3
"""
Check that every displayed number still matches the run artifact behind it.

    python3 research/scripts/check_claims.py

claims.json is the single source of truth for what the site displays, but it is
written by hand as often as by `out_of_time.py --write-claims`, and a hand edit
can quietly disagree with the JSON it cites. This closes that gap: for every
claim whose `source` names a run artifact in research/, the value is recomputed
from that artifact and compared.

Claims sourced from a prose document are reported as unverifiable here rather
than passed silently — that is a statement about what this check covers, not a
failure.

Run by the PR workflow. Exits non-zero on a mismatch.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLAIMS = os.path.join(ROOT, "research", "claims.json")


def artifact_for(source):
    """The run artifact a claim cites, if it cites one."""
    m = re.search(r"(out_of_time_[\d-]+\.json)", source or "")
    if not m:
        return None
    path = os.path.join(ROOT, "research", m.group(1))
    return path if os.path.exists(path) else m.group(1)      # str = named but missing


def main():
    claims = json.load(open(CLAIMS))
    failures, checked, skipped = [], 0, []

    for key, c in claims.items():
        if key.startswith("_"):
            continue
        # Derived from the shipped payload, not from a research run: recompute it
        # by importing the script that produces it, so a config change to the
        # renderer surfaces here instead of quietly invalidating the prose.
        if key == "independent_calls":
            art = os.path.join(ROOT, "research", "independent_calls.json")
            if not os.path.exists(art):
                failures.append(f"{key}: research/independent_calls.json is missing")
                continue
            a = json.load(open(art))["robinhood"]
            checked += 1
            detail = f"{a['distinct_held']} of {a['distinct_called']}"
            if c["value"] != a["distinct_pct"]:
                failures.append(f"{key}: claims.json says {c['value']}, the run says {a['distinct_pct']}")
            elif c.get("detail") != detail:
                failures.append(f"{key}: detail is {c.get('detail')!r}, the run implies {detail!r}")
            else:
                print(f"  ok   {key} = {a['distinct_pct']}% ({detail}) ← research/independent_calls.json")
            continue
        if key == "fresh_below_cap":
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import fresh_inflows
            total, below = fresh_inflows.count()
            checked += 1
            detail = f"{below:,} of {total:,}"
            if c["value"] != below:
                failures.append(
                    f"{key}: claims.json says {c['value']}, the payload gives {below}")
            elif c.get("detail") != detail:
                failures.append(
                    f"{key}: detail is {c.get('detail')!r}, the payload implies {detail!r}")
            else:
                print(f"  ok   {key} = {below} ({detail}) ← data/bubbles80.json")
            continue
        art = artifact_for(c.get("source", ""))
        if art is None:
            skipped.append((key, c.get("source", "(no source)")))
            continue
        if isinstance(art, str) and not os.path.exists(art):
            failures.append(f"{key}: cites {art}, which is not in the repository")
            continue

        a = json.load(open(art))
        rel = os.path.relpath(art, ROOT)

        # what each claim should equal, recomputed from the artifact
        if key == "oot":
            rh = a["by_chain"].get("robinhood")
            if not rh:
                failures.append(f"{key}: {rel} has no robinhood row")
                continue
            want, detail = rh["pct"], f"{rh['covered']} of {rh['total']}"
        elif key == "naive_oot":
            want, detail = a["coverage_pct"], f"{a['covered']} of {a['test_winners']}"
        elif key == "cohort":
            want, detail = a["cohort_wallets"], None
        else:
            skipped.append((key, f"{rel} (no rule for this key)"))
            continue

        checked += 1
        if c["value"] != want:
            failures.append(f"{key}: claims.json says {c['value']}, {rel} says {want}")
        elif detail and c.get("detail") != detail:
            failures.append(f"{key}: detail is {c.get('detail')!r}, {rel} implies {detail!r}")
        else:
            print(f"  ok   {key} = {c['value']}{c['unit']} "
                  f"{'(' + detail + ') ' if detail else ''}← {rel}")

    for key, src in skipped:
        print(f"  --   {key} not machine-checkable here (source: {src})")

    if failures:
        print("\nMISMATCH between claims.json and the artifacts it cites:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    print(f"\n{checked} claim(s) verified against run artifacts, {len(skipped)} not covered.")


if __name__ == "__main__":
    main()
