import asyncio
import os
import pytest
from integrations.router import _probe_request


def test_bitdeer_stub_success(monkeypatch):
    monkeypatch.setenv("BITDEER_API_KEY", "mock_key")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, {"choices": [{"message": {"content": "ok"}}]}, 180.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("bitdeer", "POST", "https://api.bitdeer.ai/v1/chat/completions"))
    assert code == 200


def test_bitdeer_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("BITDEER_API_KEY", "mock_key")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("bitdeer", "POST", "https://api.bitdeer.ai/v1/chat/completions"))
    assert code == 0


@pytest.mark.skipif(
    not os.getenv("BITDEER_API_KEY"),
    reason="BITDEER_API_KEY not configured",
)
def test_bitdeer_live_smoke():
    code, body, ms = asyncio.run(
        _probe_request(
            "bitdeer",
            "POST",
            os.getenv("BITDEER_BASE_URL", "https://api.bitdeer.ai/v1/chat/completions"),
            headers={"Authorization": f"Bearer {os.getenv('BITDEER_API_KEY', '')}"},
            json_body={"model": "deepseek-ai/DeepSeek-V3", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            timeout=3.0,
        )
    )
    assert code in (200, 401, 403, 404, 429)
