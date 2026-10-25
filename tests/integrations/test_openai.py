import asyncio
import os
import pytest
from integrations import status as status_module


def test_openai_stub_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-mock")

    async def fake_get(url, **kwargs):
        return 200, {"data": [{"id": "gpt-4o"}]}, 150.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_openai())
    assert res["state"] == "live"
    assert "no HeistBox code path calls OpenAI" in res["detail"]


def test_openai_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-mock")

    async def fake_get(url, **kwargs):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_openai())
    assert res["state"] == "offline"


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not configured",
)
def test_openai_live_smoke():
    res = asyncio.run(status_module.probe_openai())
    assert res["state"] in ("live", "offline")
    assert os.getenv("OPENAI_API_KEY") not in res["detail"]
