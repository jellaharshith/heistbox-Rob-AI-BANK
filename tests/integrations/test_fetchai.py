import asyncio
from kernel import fetch_guardian


def test_fetchai_stub_success():
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
