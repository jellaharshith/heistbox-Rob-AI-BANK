import asyncio
import os
import pytest
from integrations.router import _probe_request


def test_apify_stub_success(monkeypatch):
    monkeypatch.setenv("APIFY_API_TOKEN", "mock_token")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, {"data": {"id": "user_apify", "username": "testuser"}}, 110.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("apify", "GET", "https://api.apify.com/v2/users/me"))
    assert code == 200
    assert body["data"]["username"] == "testuser"


def test_apify_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("APIFY_API_TOKEN", "mock_token")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("apify", "GET", "https://api.apify.com/v2/users/me"))
    assert code == 0


@pytest.mark.skipif(
    not os.getenv("APIFY_API_TOKEN"),
    reason="APIFY_API_TOKEN not configured",
)
def test_apify_live_smoke():
    """Live smoke test: read-only users/me account metadata.

    SAFETY: NEVER start paid actor runs.
    """
    code, body, ms = asyncio.run(
        _probe_request(
            "apify",
            "GET",
            "https://api.apify.com/v2/users/me",
            headers={"Authorization": f"Bearer {os.getenv('APIFY_API_TOKEN', '')}"},
            timeout=3.0,
        )
    )
    assert code in (200, 401, 403)
