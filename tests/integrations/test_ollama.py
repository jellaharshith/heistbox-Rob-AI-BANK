import asyncio
import os
import pytest
from integrations import status as status_module


def test_ollama_stub_success(monkeypatch):
    async def fake_get(url, **kwargs):
        return 200, {"models": [{"name": "llama3.1:8b"}]}, 15.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_ollama())
    assert res["state"] == "live"
    assert res["code"] == "LIVE"


def test_ollama_stub_timeout_fallback(monkeypatch):
    async def fake_get(url, **kwargs):
        return 0, "unreachable: ConnectTimeout", 1500.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_ollama())
    assert res["state"] == "offline"
    assert "fallback" in res


@pytest.mark.skipif(
    not os.getenv("HEISTBOX_OLLAMA_URL") and not os.getenv("OLLAMA_HOST"),
    reason="Ollama host not explicitly configured",
)
def test_ollama_live_smoke():
    res = asyncio.run(status_module.probe_ollama())
    assert res["state"] in ("live", "offline")
