import asyncio
import time

from integrations import wajo_call
from kernel import fetch_guardian
from kernel import db_gate


def test_5000_quarantine_stages_escrow_and_dispatches_wajo(monkeypatch):
    calls = []

    async def fake_wajo(**kwargs):
        calls.append(kwargs)
        return {"dry_run": True}

    monkeypatch.setattr(wajo_call, "trigger_wajo_escalation", fake_wajo)
    fetch_guardian.escrow_registry.clear()

    for _ in range(3):  # the same intent quarantined repeatedly calls the CFO once
        asyncio.run(
            fetch_guardian.publish_heist_quarantine(
                "intent-5000", "0xsettle", "ticket_104", 500_000, 2_500, {"status": "UNSAT"}
            )
        )

    assert calls == [{"red_cents": 500_000, "green_cents": 2_500, "settlement_hash": "0xsettle", "intent_hash": "intent-5000"}]
    assert fetch_guardian.escrow_registry["intent-5000"]["status"] == "QUARANTINED"
    assert fetch_guardian.escrow_registry["intent-5000"]["z3_status"] == "UNSAT"


def test_wajo_without_key_is_a_dry_run(monkeypatch, caplog):
    monkeypatch.delenv("WAJO_API_KEY", raising=False)
    monkeypatch.delenv("wajo_api_key", raising=False)
    monkeypatch.setenv("CFO_ALERT_PHONE_NUMBER", "+15555550123")
    monkeypatch.setenv("CHALLENGE_CALLBACK_URL", "https://example.test/verify")
    monkeypatch.setenv("SETTLE_PAGE_URL", "https://demo.example/settle")

    with caplog.at_level("WARNING"):
        result = asyncio.run(wajo_call.trigger_wajo_escalation(133_742, 2_500, "0xabc", "0xintent"))

    payload = result["payload"]
    assert result["dry_run"] is True
    assert payload["to"] == "+15555550123"
    assert payload["callback_url"] == "https://example.test/verify"
    assert payload["settle_url"] == "https://demo.example/settle?settlement=0xabc"
    assert "$1,337.42" in payload["script"] and "$25.00" in payload["script"]
    assert payload["metadata"] == {"intent_hash": "0xintent", "settlement_hash": "0xabc"}
    assert "+15555550123" in payload["fo_message"] and "https://demo.example/settle?settlement=0xabc" in payload["fo_message"]
    assert "WAJO_API_KEY is not configured" in caplog.text


def test_wajo_never_phones_under_pytest(monkeypatch):
    monkeypatch.setenv("WAJO_API_KEY", "wak_test")
    monkeypatch.setenv("CFO_ALERT_PHONE_NUMBER", "+15555550123")

    async def must_not_call(*args, **kwargs):
        raise AssertionError("a test must never reach Wajo")

    monkeypatch.setattr(wajo_call, "mcp_tool_call", must_not_call)
    result = asyncio.run(wajo_call.trigger_wajo_escalation(133_742, 2_500, "0xabc", "0xintent"))
    assert result["dry_run"] is True and "pytest" in result["reason"]


def test_wajo_live_call_uses_ask_fo_and_cools_down(monkeypatch):
    monkeypatch.setenv("WAJO_API_KEY", "wak_test")
    monkeypatch.setenv("CFO_ALERT_PHONE_NUMBER", "+15555550123")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setitem(wajo_call._LAST_LIVE_CALL, "at", 0.0)
    calls = []

    async def fake_mcp(tool, arguments, **kwargs):
        calls.append((tool, arguments))
        return {"structuredContent": {"status": "working", "conversationId": "c1"}}

    monkeypatch.setattr(wajo_call, "mcp_tool_call", fake_mcp)
    first = asyncio.run(wajo_call.trigger_wajo_escalation(133_742, 2_500, "0xabc", "0xintent"))
    second = asyncio.run(wajo_call.trigger_wajo_escalation(9_900, 2_500, "0xdef", "0xother"))
    assert first["dry_run"] is False and first["fo_status"] == "working"
    assert calls[0][0] == "ask_fo" and calls[0][1]["newConversation"] is True and "+15555550123" in calls[0][1]["message"]
    assert second["dry_run"] is True and "WAJO_MIN_CALL_INTERVAL_S" in second["reason"] and len(calls) == 1


def test_gate_dispatch_helper_is_async(monkeypatch):
    calls = []

    async def fake_publish(*args):
        calls.append(args)

    monkeypatch.setattr(fetch_guardian, "publish_heist_quarantine", fake_publish)
    fetch_guardian.escrow_registry.clear()
    db_gate._dispatch_heist_quarantine("intent", "0xsettle", "ticket_104", 500_000, 2_500, {"status": "UNSAT"})
    # The helper hands off to an executor thread when called from this synchronous test.
    for _ in range(100):
        if calls:
            break
        time.sleep(0.001)
    assert calls and calls[0][1] == "0xsettle" and calls[0][3] == 500_000


def test_gate_skips_dispatch_for_an_already_quarantined_intent(monkeypatch):
    calls = []

    async def fake_publish(*args):
        calls.append(args)

    monkeypatch.setattr(fetch_guardian, "publish_heist_quarantine", fake_publish)
    fetch_guardian.escrow_registry.clear()
    fetch_guardian.escrow_registry["intent"] = {"status": "QUARANTINED"}
    db_gate._dispatch_heist_quarantine("intent", "0xsettle", "ticket_104", 500_000, 2_500, {"status": "UNSAT"})
    time.sleep(0.05)
    assert calls == []


def test_escrow_releases_only_after_an_approved_settlement_settles():
    fetch_guardian.escrow_registry.clear()
    fetch_guardian.escrow_registry["intent-faceid-test"] = {"status": "QUARANTINED"}
    h = db_gate.issue_settlement("intent-faceid-test", "ticket_104", "ent_104", 2_500, 497_500, "0x" + "0" * 39 + "1")["settlement_hash"]

    # No approval yet: it cannot settle, and escrow stays held.
    assert db_gate.transition_settlement(h, "APPROVED", "SETTLED")[1] is not None
    assert fetch_guardian.escrow_registry["intent-faceid-test"]["status"] == "QUARANTINED"

    assert db_gate.transition_settlement(h, "PENDING", "APPROVED")[1] is None
    assert db_gate.transition_settlement(h, "PENDING", "APPROVED")[1] is not None  # approval is single-use
    assert db_gate.transition_settlement(h, "APPROVED", "SETTLED")[1] is None
    assert fetch_guardian.escrow_registry["intent-faceid-test"]["status"] == "RELEASED"
