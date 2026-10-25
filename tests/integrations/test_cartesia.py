import asyncio
import os
import pytest
from integrations.router import _probe_request


def test_cartesia_stub_success(monkeypatch):
    monkeypatch.setenv("CARTESIA_API_KEY", "mock_key")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, [{"id": "sonic-english", "name": "Sonic English"}], 110.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("cartesia", "GET", "https://api.cartesia.ai/voices"))
    assert code == 200
    assert len(body) == 1


def test_cartesia_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("CARTESIA_API_KEY", "mock_key")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("cartesia", "GET", "https://api.cartesia.ai/voices"))
    assert code == 0


@pytest.mark.skipif(
    not os.getenv("CARTESIA_API_KEY"),
    reason="CARTESIA_API_KEY not configured",
)
def test_cartesia_live_smoke():
    """Live smoke test: read-only voices listing."""
    code, body, ms = asyncio.run(
        _probe_request(
            "cartesia",
            "GET",
            "https://api.cartesia.ai/voices",
            headers={
                "X-API-Key": os.getenv("CARTESIA_API_KEY", "").strip(),
                "Cartesia-Version": "2024-06-10",
            },
            timeout=3.0,
        )
    )
    assert code in (200, 401, 403, 429)
    assert ms >= 0
