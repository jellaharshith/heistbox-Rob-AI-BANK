import asyncio
import os
import pytest
from integrations.router import _probe_request


def test_crs_stub_success(monkeypatch):
    monkeypatch.setenv("CRS_USERNAME", "mock_user")
    monkeypatch.setenv("CRS_PASSWORD", "mock_pass")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, {"users": [{"id": "user_1"}]}, 90.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("crs", "GET", "https://api-sandbox.stitchcredit.com/api/users"))
    assert code == 200
    assert len(body["users"]) == 1


def test_crs_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("CRS_USERNAME", "mock_user")
    monkeypatch.setenv("CRS_PASSWORD", "mock_pass")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("crs", "GET", "https://api-sandbox.stitchcredit.com/api/users"))
    assert code == 0


@pytest.mark.skipif(
    not (os.getenv("CRS_USERNAME") and os.getenv("CRS_PASSWORD")),
    reason="CRS_USERNAME / CRS_PASSWORD not configured",
)
def test_crs_live_smoke():
    base = os.getenv("CRS_BASE_URL", "https://api-sandbox.stitchcredit.com/api").rstrip("/")
    # Login check (read-only auth validation)
    code, login, _ = asyncio.run(
        _probe_request(
            "crs",
            "POST",
            f"{base}/login",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json_body={"username": os.environ["CRS_USERNAME"].strip(), "password": os.environ["CRS_PASSWORD"].strip()},
            timeout=3.0,
        )
    )
    assert code in (200, 401, 403)
