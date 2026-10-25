import asyncio
import os
import pytest
from integrations import status as status_module


def test_x402_stub_success(monkeypatch):
    monkeypatch.setenv("X402_SIGNER_PRIVATE_KEY", "0x" + "1" * 64)

    async def fake_get(url, method="GET", json_body=None, **kwargs):
        if json_body and json_body.get("method") == "eth_chainId":
            return 200, {"result": "0x14a34"}, 50.0  # 84532
        if json_body and json_body.get("method") == "eth_getBalance":
            return 200, {"result": "0x1000000000000000"}, 50.0
        if json_body and json_body.get("method") == "eth_call":
            return 200, {"result": "0x0000000000000000000000000000000000000000000000000000000002faf080"}, 50.0  # 50 USDC
        return 200, {"result": "0x0"}, 50.0

    monkeypatch.setattr(status_module, "_get", fake_get)
    res = asyncio.run(status_module.probe_x402())
    assert res["state"] == "live"
    assert "84532" in res["detail"]


def test_x402_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("X402_SIGNER_PRIVATE_KEY", "0x" + "1" * 64)

    async def fake_get_timeout(url, **kwargs):
        return 0, "unreachable: ConnectTimeout", 3000.0

    monkeypatch.setattr(status_module, "_get", fake_get_timeout)
    res = asyncio.run(status_module.probe_x402())
    assert res["state"] == "offline"
    assert "unavailable" in res["detail"] or "unreachable" in res["detail"]


@pytest.mark.skipif(
    not os.getenv("X402_SIGNER_PRIVATE_KEY"),
    reason="X402_SIGNER_PRIVATE_KEY not configured",
)
def test_x402_live_smoke():
    """Live smoke test: read-only RPC chainId + balance check.

    SAFETY: NEVER sign or broadcast an on-chain transaction.
    """
    res = asyncio.run(status_module.probe_x402())
    assert res["state"] in ("live", "missing_key", "offline")
    # Private key must never appear in detail
    assert os.getenv("X402_SIGNER_PRIVATE_KEY") not in res["detail"]
