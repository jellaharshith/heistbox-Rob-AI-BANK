import asyncio
from kernel import fetch_guardian


def test_fetchai_stub_success(monkeypatch):
    from integrations import wajo_call

    async def fake_wajo(**kwargs):
        return {"dry_run": True}

    monkeypatch.setattr(wajo_call, "trigger_wajo_escalation", fake_wajo)
    fetch_guardian.escrow_registry.clear()
    asyncio.run(
        fetch_guardian.publish_heist_quarantine(
            "intent-fetch-test", "0xsettle-test", "ticket-101", 100_000, 2_500, {"status": "UNSAT"}
        )
    )
    assert "intent-fetch-test" in fetch_guardian.escrow_registry
    assert fetch_guardian.escrow_registry["intent-fetch-test"]["status"] == "QUARANTINED"

    rel = fetch_guardian.release_escrow("intent-fetch-test")
    assert rel is not None
    assert rel["status"] == "RELEASED"


def test_fetchai_stub_failure_fallback():
    # Attempting to release a non-existent intent returns None, cleanly falling back
    rel = fetch_guardian.release_escrow("intent-non-existent")
    assert rel is None


def test_fetchai_live_smoke():
    # In-process guardian is active and initialized
    assert hasattr(fetch_guardian, "escrow_registry")
    assert isinstance(fetch_guardian.escrow_registry, dict)


def test_fetchai_uagents_sdk_integration(monkeypatch):
    import uagents
    from integrations import wajo_call

    async def fake_wajo(**kwargs):
        return {"dry_run": True}

    monkeypatch.setattr(wajo_call, "trigger_wajo_escalation", fake_wajo)
    assert isinstance(fetch_guardian.guardian_agent, uagents.Agent)
    assert fetch_guardian.FETCHAI_AGENT_ADDRESS.startswith("agent1q")
    assert len(fetch_guardian.FETCHAI_AGENT_ADDRESS) > 20
    assert hasattr(fetch_guardian, "escrow_protocol")

    # Test single escrow getter
    fetch_guardian.escrow_registry.clear()
    asyncio.run(
        fetch_guardian.publish_heist_quarantine(
            "intent-uagent-test", "0xsettle-uagent", "ticket-202", 50_000, 1_000
        )
    )
    entry = fetch_guardian.get_escrow("intent-uagent-test")
    assert entry is not None
    assert entry["agent_address"] == fetch_guardian.FETCHAI_AGENT_ADDRESS
    assert entry["status"] == "QUARANTINED"

    # Test release via HeistReleaseEvent
    rel = fetch_guardian.release_escrow("intent-uagent-test", released_by="BIOMETRIC_PASSKEY")
    assert rel["status"] == "RELEASED"
    assert rel["released_by"] == "BIOMETRIC_PASSKEY"
