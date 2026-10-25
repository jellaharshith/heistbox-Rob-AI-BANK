import asyncio
from integrations import status as status_module


def test_osint_public_stub_success(monkeypatch):
    async def fake_get(url, **kwargs):
        if "consumerfinance" in url:
            return 200, [{"company": "Example Bank"}], 45.0
        if "rdap" in url:
            return 200, {"handle": "example.com"}, 50.0
        return 200, {}, 40.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_osint_public())
    assert res["state"] == "live"
    assert "CFPB ok" in res["detail"]


def test_osint_public_stub_timeout_fallback(monkeypatch):
    async def fake_get(url, **kwargs):
        return 0, "unreachable: ConnectTimeout", 3000.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_osint_public())
    assert res["state"] == "offline"
    assert res["fallback"] == "OSINT fields left empty"


def test_osint_public_live_smoke():
    """Live smoke test: read-only CFPB and RDAP queries."""
    res = asyncio.run(status_module.probe_osint_public())
    assert res["state"] in ("live", "offline")
