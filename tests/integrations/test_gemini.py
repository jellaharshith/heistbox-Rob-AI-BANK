import asyncio
import os
import pytest
from integrations import status as status_module


def test_gemini_stub_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key")

    async def fake_get(url, **kwargs):
        return 200, {"models": [{"name": "models/gemini-flash-latest"}]}, 120.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_gemini())
    assert res["state"] == "live"
    assert "gemini-flash-latest" in res["detail"]


def test_gemini_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key")

    async def fake_get(url, **kwargs):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_gemini())
    assert res["state"] == "offline"
    assert res["fallback"] == "regex extractor (after Claude)"


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not configured",
)
def test_gemini_live_smoke():
    res = asyncio.run(status_module.probe_gemini())
    assert res["state"] in ("live", "offline")
    assert os.getenv("GEMINI_API_KEY") not in res["detail"]
