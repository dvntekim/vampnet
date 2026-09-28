"""Paginated multi-chain historical-balances fetcher with a hard credit cap."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nansen import call

def fetch(address, chain, win, cap_pages=6):
    """Returns (rows, credits_used, remaining, status).

    Truncation is recorded on `fetch.truncated` rather than returned, so callers
    that do not care keep working unchanged. It matters: running out of pages
    before the API runs out of rows drops holdings silently, and a wallet that
    quietly loses half its tokens takes its co-occurrences — and so its edges —
    with it. That failure is invisible in the output, which is exactly why it
    needs to be counted somewhere."""
    rows, used, rem, page = [], 0, None, 1
    hit_cap = True
    while page <= cap_pages:
        st, body, h = call("/api/v1/profiler/address/historical-balances", {
            "address": address, "chain": chain, "date": win,
            "pagination": {"page": page, "per_page": 500}})
        u = h.get("x-nansen-credits-used")
        rem = h.get("x-nansen-credits-remaining") or rem
        if u: used += int(u)
        if st != 200:
            return rows, used, rem, st
        rows.extend(body["data"])
        if body["pagination"]["is_last_page"]:
            hit_cap = False
            break
        page += 1
        time.sleep(0.1)
    if hit_cap:
        fetch.truncated.append((address, chain, win.get("from"), win.get("to")))
    return rows, used, rem, 200


# Wallet-chain windows that needed more pages than they were given.
fetch.truncated = []
