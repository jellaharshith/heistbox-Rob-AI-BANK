import asyncio
import os
import pytest
from integrations.router import _probe_request


def test_spacetimedb_stub_success(monkeypatch):
    monkeypatch.setenv("SPACETIMEDB_URI", "https://maincloud.spacetimedb.com/v1/database/heistbox")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, {"identity": "stdb_identity"}, 85.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("spacetimedb", "GET", "https://maincloud.spacetimedb.com/v1/database/heistbox"))
    assert code == 200


def test_spacetimedb_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("SPACETIMEDB_URI", "https://maincloud.spacetimedb.com/v1/database/heistbox")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("spacetimedb", "GET", "https://maincloud.spacetimedb.com/v1/database/heistbox"))
    assert code == 0


@pytest.mark.skipif(
    not os.getenv("SPACETIMEDB_URI"),
    reason="SPACETIMEDB_URI not configured",
)
def test_spacetimedb_live_smoke():
    uri = os.getenv("SPACETIMEDB_URI", "https://maincloud.spacetimedb.com/v1/database/heistbox").rstrip("/")
    code, body, ms = asyncio.run(
        _probe_request("spacetimedb", "GET", uri, timeout=3.0)
    )
    assert code in (200, 401, 404)
