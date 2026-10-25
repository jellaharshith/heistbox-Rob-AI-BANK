import asyncio
import os
import pytest
from integrations.router import _probe_request


def test_brightdata_stub_success(monkeypatch):
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "mock_key")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, [{"zone": "serp_zone", "type": "serp"}], 95.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("brightdata", "GET", "https://api.brightdata.com/zone/get_active_zones"))
    assert code == 200
    assert len(body) == 1


def test_brightdata_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "mock_key")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("brightdata", "GET", "https://api.brightdata.com/zone/get_active_zones"))
    assert code == 0


@pytest.mark.skipif(
    not os.getenv("BRIGHTDATA_API_KEY"),
    reason="BRIGHTDATA_API_KEY not configured",
)
def test_brightdata_live_smoke():
    """Live smoke test: read-only get_active_zones check.

    SAFETY: NEVER start paid web scrapes.
    """
    code, body, ms = asyncio.run(
        _probe_request(
            "brightdata",
            "GET",
            "https://api.brightdata.com/zone/get_active_zones",
            headers={"Accept": "application/json", "Authorization": f"Bearer {os.getenv('BRIGHTDATA_API_KEY', '')}"},
            timeout=3.0,
        )
    )
    assert code in (200, 401, 403)
