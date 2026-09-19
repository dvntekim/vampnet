"""Paginated multi-chain historical-balances fetcher with a hard credit cap."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nansen import call

def fetch(address, chain, win, cap_pages=6):
    """Returns (rows, credits_used, remaining)."""
    rows, used, rem, page = [], 0, None, 1
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
            break
        page += 1
        time.sleep(0.1)
    return rows, used, rem, 200
