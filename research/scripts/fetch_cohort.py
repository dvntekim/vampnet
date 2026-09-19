import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_balances import fetch

def run(cohort_file, chains, win, out, cap_pages=4):
    coh = json.load(open(cohort_file))
    wallets = list(coh.keys())
    done = {}
    if os.path.exists(out):
        try: done = json.load(open(out))
        except Exception: done = {}
    total = 0
    for i, w in enumerate(wallets, 1):
        if w in done and done[w]:
            continue
        rec = {}
        line = f"[{i:>3}/{len(wallets)}] {w[:14]}… "
        rem = None
        for c in chains:
            rows, used, rem, st = fetch(w, c, win, cap_pages=cap_pages)
            total += used
            if st == 200 and rows:
                rec[c] = rows; line += f"{c[:4]}:{len(rows)} "
        done[w] = rec
        print(line + f"| spent={total} rem={rem}", flush=True)
        if i % 10 == 0:
            json.dump(done, open(out, "w"))
    json.dump(done, open(out, "w"))
    return done, total
