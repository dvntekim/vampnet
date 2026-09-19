"""Minimal Nansen API client (stdlib only). Credit-safe by default."""
import json, os, re, sys, time, urllib.request, urllib.error

BASE = "https://api.nansen.ai"
ENVF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

def _key():
    if os.environ.get("NANSEN_API_KEY"):
        return os.environ["NANSEN_API_KEY"].strip()
    with open(ENVF) as f:
        for line in f:
            if line.startswith("NANSEN_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("NANSEN_API_KEY not found in env or .env")

# Guard: address-shaped search queries cost 500 credits on search/general.
ADDR = re.compile(r"^(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})$|\.(eth|sol)$")

MAX_RETRY = 3

def call(path, body=None, method=None):
    """Returns (status, parsed_json_or_text, credit_headers)."""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    m = method or ("POST" if data is not None else "GET")
    req = urllib.request.Request(url, data=data, method=m)
    req.add_header("apikey", _key())
    req.add_header("Content-Type", "application/json")
    last = None
    for _attempt in range(MAX_RETRY):
      try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read().decode()
            hdrs = {k: v for k, v in r.headers.items() if k.lower().startswith("x-nansen")}
            try:
                return r.status, json.loads(raw), hdrs
            except json.JSONDecodeError:
                return r.status, raw, hdrs
      except urllib.error.HTTPError as e:
        raw = e.read().decode()
        hdrs = {k: v for k, v in e.headers.items() if k.lower().startswith("x-nansen")}
        try:
            return e.code, json.loads(raw), hdrs
        except json.JSONDecodeError:
            return e.code, raw, hdrs
      except Exception as ex:
        last = ex
        time.sleep(2 * (_attempt + 1))
    raise last

def search_token(q):
    """FREE for token/entity queries. Refuses address-shaped input (would cost 500)."""
    if ADDR.search(q.strip()):
        raise ValueError(f"refusing address-shaped query {q!r}: costs 500 credits")
    return call("/api/v1/search/general", {"search_query": q})
