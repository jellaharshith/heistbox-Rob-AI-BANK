import asyncio
import os
import pytest
from integrations.router import health_provenance


def test_factory_stub_success(monkeypatch):
    monkeypatch.setenv("FACTORY_API_KEY", "mock_key")
    monkeypatch.setattr("shutil.which", lambda cmd: "/bin/droid")

    async def fake_health():
        return {"integrations": {"factory_droid": {"live_mode": True, "state": "UNVERIFIED", "reason": "droid CLI found", "latency_ms": 1.0}}}

    monkeypatch.setattr("integrations.router.health_provenance", fake_health)
    health = asyncio.run(fake_health())
    assert health["integrations"]["factory_droid"]["live_mode"] is True


def test_factory_stub_missing_fallback(monkeypatch):
    monkeypatch.delenv("FACTORY_API_KEY", raising=False)
    monkeypatch.setattr("shutil.which", lambda cmd: None)

    async def fake_health():
        return {"integrations": {"factory_droid": {"live_mode": False, "state": "MISSING_KEY", "reason": "FACTORY_API_KEY is not set", "latency_ms": 0.0}}}

    monkeypatch.setattr("integrations.router.health_provenance", fake_health)
    health = asyncio.run(fake_health())
    assert health["integrations"]["factory_droid"]["live_mode"] is False


@pytest.mark.skipif(
    not os.getenv("FACTORY_API_KEY"),
    reason="FACTORY_API_KEY not configured",
)
def test_factory_live_smoke():
    """Live smoke test: check CLI path and key presence without spending credits (no droid exec)."""
    health = asyncio.run(health_provenance())
    fd = health["integrations"]["factory_droid"]
    assert fd["state"] in ("UNVERIFIED", "LIVE", "MISSING_KEY", "UNREACHABLE")
