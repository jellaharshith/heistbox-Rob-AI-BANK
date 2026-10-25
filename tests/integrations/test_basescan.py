import asyncio
import os
import pytest
from integrations import status as status_module


def test_basescan_stub_success(monkeypatch):
    monkeypatch.setenv("BASESCAN_API_KEY", "mock_key")

    async def fake_get(url, **kwargs):
        return 200, {"result": "0x123456"}, 45.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_basescan())
    assert res["state"] == "live"


def test_basescan_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("BASESCAN_API_KEY", "mock_key")

    async def fake_get(url, **kwargs):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_basescan())
    assert res["state"] == "offline"


@pytest.mark.skipif(
    not os.getenv("BASESCAN_API_KEY"),
    reason="BASESCAN_API_KEY not configured",
)
def test_basescan_live_smoke():
    res = asyncio.run(status_module.probe_basescan())
    assert res["state"] in ("live", "offline", "missing_key")
