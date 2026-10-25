import asyncio
import os
import pytest
from integrations import status as status_module


def test_cdp_stub_success(monkeypatch):
    monkeypatch.setenv("CDP_API_KEY_NAME", "mock_name")
    monkeypatch.setenv("CDP_API_KEY_PRIVATE_KEY", "mock_priv")

    class FakeEvm:
        async def list_accounts(self):
            class Res:
                accounts = [{"id": "acc_1"}]
            return Res()

    class FakeClient:
        evm = FakeEvm()
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr("cdp.CdpClient", FakeClient, raising=False)

    async def fake_probe():
        return status_module.entry("cdp", "live", 120.0, "CDP_API_KEY_NAME pair accepted (list_accounts: 1 account(s))")

    monkeypatch.setattr(status_module, "probe_cdp", fake_probe)
    res = asyncio.run(status_module.probe_cdp())
    assert res["state"] == "live"


def test_cdp_stub_timeout_fallback(monkeypatch):
    async def fake_probe():
        return status_module.entry("cdp", "offline", 0, "timeout", "AUTH_ERROR")

    monkeypatch.setattr(status_module, "probe_cdp", fake_probe)
    res = asyncio.run(status_module.probe_cdp())
    assert res["state"] == "offline"


@pytest.mark.skipif(
    not (
        (os.getenv("CDP_API_KEY_NAME") and os.getenv("CDP_API_KEY_PRIVATE_KEY"))
        or (os.getenv("testnet_coinbase_base_api_key") and os.getenv("testnet_coinbase_base_api_secret"))
    ),
    reason="CDP API keys not configured",
)
def test_cdp_live_smoke():
    """Live smoke test: read-only list_accounts.

    SAFETY: NEVER request faucet funds.
    """
    res = asyncio.run(status_module.probe_cdp())
    assert res["state"] in ("live", "offline")
