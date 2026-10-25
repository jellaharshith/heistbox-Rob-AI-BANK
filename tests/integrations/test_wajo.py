import asyncio
import os
import pytest
import httpx

from integrations import wajo_call


def test_wajo_stub_success(monkeypatch):
    """Stubbed MCP response succeeds, updates last event and audit log."""
    wajo_call.clear_audit()
    monkeypatch.setenv("WAJO_API_KEY", "wak_mock_key")
    monkeypatch.setenv("CFO_ALERT_PHONE_NUMBER", "+15555550123")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setitem(wajo_call._LAST_LIVE_CALL, "at", 0.0)

    async def fake_tool_call(tool, args, timeout=None):
        if tool == "list_fo_conversations":
            return {"conversations": []}
        if tool == "ask_fo":
            return {"structuredContent": {"status": "working", "conversationId": "conv_123"}}
        raise ValueError(f"Unexpected tool {tool}")

    monkeypatch.setattr(wajo_call, "mcp_tool_call", fake_tool_call)

    # 1. Probe check
    pr = asyncio.run(wajo_call.probe())
    assert pr["ok"] is True
    assert pr["code"] == "LIVE"

    # 2. Escalation check
    res = asyncio.run(wajo_call.trigger_wajo_escalation(100_000, 2_500, "0xsettle1", "0xintent1"))
    assert res["dry_run"] is False
    assert res["fo_status"] == "working"

    # 3. Status check
    st = asyncio.run(wajo_call.status(fresh=True))
    assert st["state"] == "live"
    assert st["escalations_recorded"] >= 1


def test_wajo_stub_timeout_fallback(monkeypatch):
    """A slow/timing out Wajo server does not crash; falls back gracefully and audits the event."""
    wajo_call.clear_audit()
    monkeypatch.setenv("WAJO_API_KEY", "wak_mock_key")
    monkeypatch.setenv("CFO_ALERT_PHONE_NUMBER", "+15555550123")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setitem(wajo_call._LAST_LIVE_CALL, "at", 0.0)

    async def fake_tool_call_timeout(tool, args, timeout=None):
        raise asyncio.TimeoutError("Wajo upstream timed out")

    monkeypatch.setattr(wajo_call, "mcp_tool_call", fake_tool_call_timeout)

    # Escalation must not raise; degrades to error record with fallback payload
    res = asyncio.run(wajo_call.trigger_wajo_escalation(200_000, 2_500, "0xsettle2", "0xintent2"))
    assert res["dry_run"] is False
    assert "timeout" in res.get("error", "").lower()

    # Audit must record the timeout
    audits = wajo_call.audit_entries(limit=10)
    assert len(audits) >= 1
    assert audits[0]["outcome"] == "timeout"


@pytest.mark.skipif(
    not (os.getenv("WAJO_API_KEY") or os.getenv("wajo_api_key")),
    reason="WAJO_API_KEY not configured in environment",
)
def test_wajo_live_smoke():
    """Live smoke test: read-only list_fo_conversations probe ONLY.

    SAFETY: NEVER calls ask_fo (it phones a real person).
    """
    res = asyncio.run(wajo_call.probe(timeout=3.0))
    assert res["code"] in ("LIVE", "AUTH_ERROR", "UNREACHABLE")
    assert res["latency_ms"] >= 0
    # Ensure no secrets leak
    key = os.getenv("WAJO_API_KEY") or os.getenv("wajo_api_key")
    assert key not in res["detail"]
