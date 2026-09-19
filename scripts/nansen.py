"""Nansen API client — standard library only.

Credit safety is the point of this module:
  * `call` surfaces the X-Nansen-Credits-* headers so callers can budget.
  * `search_token` refuses address-shaped queries, which cost 500 credits on
    search/general versus 0 for a token or entity name.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

BASE = "https://api.nansen.ai"
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
MAX_RETRIES = 3
TIMEOUT_S = 90

# 0x-prefixed EVM, base58 Solana, or an ENS/SNS name. See search_token.
ADDRESS_LIKE = re.compile(r"^(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})$|\.(eth|sol)$")


def _api_key():
    """Read the key from the environment, falling back to a local .env file."""
    key = os.environ.get("NANSEN_API_KEY")
    if key:
        return key.strip()
    try:
        with open(ENV_FILE) as fh:
            for line in fh:
                if line.startswith("NANSEN_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    except FileNotFoundError:
        pass
    raise SystemExit("NANSEN_API_KEY not set. Add it to .env or export it.")


def _credit_headers(headers):
    return {k: v for k, v in headers.items() if k.lower().startswith("x-nansen")}


def call(path, body=None, method=None):
    """Make one API request.

    Returns (status_code, parsed_body, credit_headers). HTTP errors are returned
    rather than raised: a 422 carries the field-level validation detail, and the
    API does not bill rejected requests. Only transport failures are retried.
    """
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method or ("POST" if data is not None else "GET"),
    )
    request.add_header("apikey", _api_key())
    request.add_header("Content-Type", "application/json")

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                raw = response.read().decode()
                headers = _credit_headers(response.headers)
                try:
                    return response.status, json.loads(raw), headers
                except json.JSONDecodeError:
                    return response.status, raw, headers
        except urllib.error.HTTPError as error:
            raw = error.read().decode()
            headers = _credit_headers(error.headers)
            try:
                return error.code, json.loads(raw), headers
            except json.JSONDecodeError:
                return error.code, raw, headers
        except Exception as error:  # transport-level; retry with backoff
            last_error = error
            time.sleep(2 * (attempt + 1))
    raise last_error


def search_token(query):
    """Resolve a ticker to its contract. Free for token and entity names."""
    if ADDRESS_LIKE.search(query.strip()):
        raise ValueError(f"{query!r} looks like an address; that query costs 500 credits")
    return call("/api/v1/search/general", {"search_query": query})
