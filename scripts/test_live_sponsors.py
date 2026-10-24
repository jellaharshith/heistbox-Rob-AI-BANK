"""Failing smoke test for configured sponsor credentials.

Run with the API server active. This intentionally does not substitute mocks:
every reported LIVE provider must come from an HTTP/RPC response.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    request = urllib.request.Request("http://127.0.0.1:8000/api/integrations/status")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 200:
                print(f"status endpoint HTTP {response.status}")
                return 1
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"unable to reach live API: {exc}")
        return 1
    providers = payload.get("providers", {})
    expected = ("anthropic", "gemini", "cartesia", "crs", "x402", "brightdata", "apify")
    missing = [provider for provider in expected if providers.get(provider) != "LIVE"]
    for provider in expected:
        print(f"{provider}: {providers.get(provider, 'MISSING')} ({payload.get('latency_ms', {}).get(provider, 'n/a')} ms)")
    if missing:
        print("not live: " + ", ".join(missing))
        return 1
    print("all configured sponsor probes returned LIVE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
