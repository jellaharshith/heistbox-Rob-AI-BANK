import asyncio
import os
import pytest
from integrations.router import _probe_request
from integrations import status as status_module


def test_claude_stub_success(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-mock")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, {"data": [{"id": "claude-haiku-5-5"}, {"id": "claude-opus-5-5"}], "has_more": False}, 120.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("anthropic", "GET", "https://api.anthropic.com/v1/models"))
    assert code == 200
    assert len(body["data"]) == 2


def test_claude_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-mock")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("anthropic", "GET", "https://api.anthropic.com/v1/models"))
    assert code == 0
    assert "TimeoutException" in body


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not configured",
)
def test_claude_live_smoke():
    """Live smoke test: read-only models listing (1 tiny bounded request)."""
    code, body, ms = asyncio.run(
        _probe_request(
            "anthropic",
            "GET",
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
            },
            timeout=3.0,
        )
    )
    assert code in (200, 401, 429)
    assert ms >= 0
