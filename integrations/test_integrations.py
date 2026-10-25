import hashlib
import json
import os
import pytest
import importlib

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    router_module = importlib.import_module("integrations.router")
    from .router import marked_bill_nonce, router
except ImportError:
    pytest.skip("FastAPI test dependencies unavailable", allow_module_level=True)

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture(autouse=True)
def isolate_dotenv_reload(monkeypatch):
    """Keep request tests from re-importing secrets from the developer .env."""
    monkeypatch.setattr(router_module, "DOTENV_RELOAD_ENABLED", False, raising=False)

def test_marked_bill_nonce_uses_zero_prefix_and_canonical_json():
    diff = {"z": 1, "a": [True, "x"]}
    canonical = json.dumps(diff, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    expected = "0x" + hashlib.sha256(b"\x00" + canonical).hexdigest()
    assert marked_bill_nonce(diff) == expected

RECIPIENT = "0x0000000000000000000000000000000000000104"


def _approved_settlement(green_cents: int = 2500, wallet: str = RECIPIENT) -> str:
    """Issue a kernel settlement and mark it approved, as /webauthn/verify does after a valid assertion."""
    from kernel import db_gate
    entry = db_gate.issue_settlement("0x" + "11" * 32, "ticket_104", "ent_104", green_cents, 133_742, wallet)
    _, error = db_gate.transition_settlement(entry["settlement_hash"], "PENDING", "APPROVED")
    assert error is None
    return entry["settlement_hash"]


def _settlement_status(settlement_hash: str) -> str:
    from kernel import db_gate
    return db_gate.get_settlement(settlement_hash)["status"]


def test_x402_returns_real_402_challenge(monkeypatch):
    monkeypatch.delenv("X402_SIGNER_PRIVATE_KEY", raising=False)
    async def fake_rpc(method, params):
        return {"eth_chainId": "0x14a34", "eth_blockNumber": "0x1234", "eth_getBlockByNumber": {"hash": "0xblock"}}[method]
    monkeypatch.setattr(router_module, "_rpc", fake_rpc)
    h = _approved_settlement()
    response = client.post("/api/integrations/x402-settle", json={"settlement_hash": h})
    assert response.status_code == 402
    assert response.json()["accepts"][0]["chain_id"] == 84532
    assert response.json()["accepts"][0]["amount"] == "25.01"
    assert response.json()["marked_bill_nonce"].startswith("0x")
    assert _settlement_status(h) == "APPROVED"  # a challenge consumes nothing


def test_x402_refuses_without_an_approved_settlement(monkeypatch):
    from kernel import db_gate
    monkeypatch.delenv("X402_SIGNER_PRIVATE_KEY", raising=False)
    assert client.post("/api/integrations/x402-settle", json={"amount_usdc": "25.01", "recipient": RECIPIENT}).status_code == 403
    assert client.post("/api/integrations/x402-settle", json={"settlement_hash": "0x" + "ab" * 32}).status_code == 403
    pending = db_gate.issue_settlement("0x" + "22" * 32, "ticket_104", "ent_104", 2500, 0, RECIPIENT)["settlement_hash"]
    assert client.post("/api/integrations/x402-settle", json={"settlement_hash": pending}).status_code == 403

def _fake_chain(usdc_units: int, sent: list):
    async def fake_rpc(method, params):
        if method == "eth_sendRawTransaction":
            sent.append(params[0])
            return "0x" + "ab" * 32
        return {
            "eth_chainId": "0x14a34",
            "eth_blockNumber": "0x1234",
            "eth_getBlockByNumber": {"hash": "0xblock"},
            "eth_getBalance": hex(10**15),
            "eth_gasPrice": hex(10**6),
            "eth_call": hex(usdc_units),
            "eth_getTransactionCount": "0x0",
        }[method]
    return fake_rpc


def test_x402_broadcast_is_a_valid_eip3009_transfer(monkeypatch):
    from eth_abi import decode
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    from eth_utils import keccak
    import rlp

    signer = Account.create()
    monkeypatch.setenv("X402_SIGNER_PRIVATE_KEY", signer.key.hex())
    monkeypatch.delenv("X402_TESTNET_SCALE", raising=False)
    sent: list = []
    monkeypatch.setattr(router_module, "_rpc", _fake_chain(26_000_000, sent))
    recipient = RECIPIENT
    h = _approved_settlement()
    # Client-supplied amount/recipient/diff are ignored: the settlement record decides them.
    attacker = "0x000000000000000000000000000000000000dead"
    body = client.post("/api/integrations/x402-settle", json={"settlement_hash": h, "pair_surgical_diff": {"row": 1}, "amount_usdc": "9999.00", "recipient": attacker}).json()
    assert body["broadcast"] is True, body["broadcast_reason"]
    assert _settlement_status(h) == "SETTLED"
    assert client.post("/api/integrations/x402-settle", json={"settlement_hash": h}).status_code == 403  # single use
    raw = bytes.fromhex(sent[0].removeprefix("0x"))
    tx_fields = rlp.decode(raw[1:] if raw[0] < 0x7f else raw)
    data = next(f for f in tx_fields if isinstance(f, bytes) and f[:4] == keccak(text="transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)")[:4])
    frm, to, value, after, before, nonce, v, r, s = decode(
        ["address", "address", "uint256", "uint256", "uint256", "bytes32", "uint8", "bytes32", "bytes32"], data[4:]
    )
    assert frm.lower() == signer.address.lower() and to.lower() == recipient and value == 25_010_000
    assert "0x" + nonce.hex() == body["marked_bill_nonce"]
    typed = encode_typed_data(
        domain_data={"name": "USDC", "version": "2", "chainId": 84532, "verifyingContract": router_module.USDC_BASE_SEPOLIA},
        message_types={"TransferWithAuthorization": [{"name": n, "type": t} for n, t in [("from", "address"), ("to", "address"), ("value", "uint256"), ("validAfter", "uint256"), ("validBefore", "uint256"), ("nonce", "bytes32")]]},
        message_data={"from": frm, "to": to, "value": value, "validAfter": after, "validBefore": before, "nonce": nonce},
    )
    assert Account.recover_message(typed, vrs=(v, r, s)).lower() == signer.address.lower()


def test_x402_testnet_scale_shrinks_onchain_value(monkeypatch):
    from eth_abi import decode
    from eth_account import Account
    import rlp

    monkeypatch.setenv("X402_SIGNER_PRIVATE_KEY", Account.create().key.hex())
    monkeypatch.setenv("X402_TESTNET_SCALE", "0.01")
    sent: list = []
    monkeypatch.setattr(router_module, "_rpc", _fake_chain(1_000_000, sent))  # 1 test USDC covers 0.2501
    body = client.post("/api/integrations/x402-settle", json={"settlement_hash": _approved_settlement()}).json()
    assert body["broadcast"] is True and body["requested_usdc"] == "25.01"
    assert body["onchain_usdc"] == 0.2501 and body["testnet_scale"] == 0.01
    raw = bytes.fromhex(sent[0].removeprefix("0x"))
    data = next(f for f in rlp.decode(raw[1:] if raw[0] < 0x7f else raw) if isinstance(f, bytes) and len(f) > 200)
    assert decode(["address", "address", "uint256"], data[4:100])[2] == 250_100


def test_x402_never_broadcasts_an_underfunded_transfer(monkeypatch):
    monkeypatch.delenv("X402_TESTNET_SCALE", raising=False)
    from eth_account import Account

    monkeypatch.setenv("X402_SIGNER_PRIVATE_KEY", Account.create().key.hex())
    sent: list = []
    monkeypatch.setattr(router_module, "_rpc", _fake_chain(1_000_000, sent))
    h = _approved_settlement()
    body = client.post("/api/integrations/x402-settle", json={"settlement_hash": h}).json()
    assert body["broadcast"] is False and sent == []
    assert "1.00 test USDC" in body["broadcast_reason"] and "25.01" in body["broadcast_reason"]
    assert _settlement_status(h) == "APPROVED"  # nothing moved, so the approval can be retried


def test_x402_rejects_wrong_marked_bill_nonce(monkeypatch):
    async def fake_rpc(method, params):
        return {"eth_chainId": "0x14a34", "eth_blockNumber": "0x1234", "eth_getBlockByNumber": {"hash": "0xblock"}}[method]
    monkeypatch.setattr(router_module, "_rpc", fake_rpc)
    response = client.post("/api/integrations/x402-settle", json={"settlement_hash": _approved_settlement(), "signature": "0xabc", "authorization": {"nonce": "0xwrong"}})
    assert response.status_code == 400


def test_settlement_hash_binds_amount_and_recipient():
    from kernel import db_gate
    base = ("0x" + "33" * 32, "ticket_104", "ent_104")
    h = db_gate.compute_settlement_hash(*base, 2500, RECIPIENT, "n1")
    assert h != db_gate.compute_settlement_hash(*base, 2501, RECIPIENT, "n1")
    assert h != db_gate.compute_settlement_hash(*base, 2500, "0x000000000000000000000000000000000000dead", "n1")
    assert h != db_gate.compute_settlement_hash(*base, 2500, RECIPIENT, "n2")
    # Two issues of the same intent get different challenges, so an old assertion cannot be replayed.
    a = db_gate.issue_settlement(*base, 2500, 0, RECIPIENT)["settlement_hash"]
    b = db_gate.issue_settlement(*base, 2500, 0, RECIPIENT)["settlement_hash"]
    assert a != b
    # A non-EVM enrolled wallet settles to the fixed placeholder, never to a client-chosen address.
    assert db_gate.issue_settlement(*base, 2500, 0, "0xCFPB0001")["recipient"] == db_gate.SETTLE_FALLBACK_RECIPIENT


def test_get_settlement_returns_server_record():
    h = _approved_settlement(green_cents=1234)
    body = client.get(f"/api/integrations/settlement/{h}").json()
    assert body["green_cents"] == 1234 and body["recipient"] == RECIPIENT and body["status"] == "APPROVED"
    assert client.get(f"/api/integrations/settlement/0x{'cd' * 32}").status_code == 404


def test_webauthn_rejects_challenge_the_kernel_did_not_issue(monkeypatch):
    import base64
    monkeypatch.delenv("ENV", raising=False)
    store = {"cred-1": {"public_key": "AA", "sign_count": 0}}
    monkeypatch.setattr(router_module, "_load_webauthn_store", lambda: store)
    challenge = base64.urlsafe_b64encode(b"\x99" * 32).decode().rstrip("=")
    body = client.post(
        "/api/integrations/webauthn/verify",
        json={"intent_hash": challenge, "credential_id": "cred-1", "assertion": {"client_data_b64": "x", "authenticator_data": "y", "signature": "z"}, "rp_id": "localhost", "expected_origin": "http://localhost:3000"},
    ).json()
    assert body["verified"] is False and "not a settlement hash issued" in body["reason"]


def test_demo_enclave_bypass_is_off_unless_env_is_set(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    body = client.post("/api/integrations/webauthn/verify", json={"intent_hash": "abc", "demo_enclave_bypass": True}).json()
    assert body["verified"] is False

def test_roast_requires_live_sponsors(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_REMIX_KEY", raising=False)
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)
    response = client.post("/api/integrations/roast-and-poster", json={"judge_name": "Ada"})
    assert response.status_code == 502
    assert "SPONSOR_UNCONFIGURED" in response.json()["detail"]

def test_voice_bribe_requires_live_sponsor(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = client.post("/api/integrations/voice-bribe", json={})
    assert response.status_code == 502

def test_demo_enclave_is_local_only():
    old = os.environ.get("ENV")
    os.environ["ENV"] = "test"
    try:
        body = client.post("/api/integrations/webauthn/verify", json={"intent_hash": "abc", "demo_enclave_bypass": True}).json()
        assert body["verified"] is True and body["settlement_approved"] is False
    finally:
        if old is None: os.environ.pop("ENV", None)
        else: os.environ["ENV"] = old

def test_droid_patch_reports_missing_cli(monkeypatch):
    import shutil
    monkeypatch.setenv("FACTORY_API_KEY", "fk-test")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    response = client.post("/api/integrations/droid-patch", json={"payload": {"verdict_code": "BUSTED_PAIR_SPLIT"}})
    assert response.status_code == 503
    assert "droid CLI not installed" in response.json()["detail"]


def test_provider_requires_live_credentials(monkeypatch):
    monkeypatch.delenv("FACTORY_API_KEY", raising=False)
    response = client.post("/api/integrations/droid-patch", json={"payload": {"rollback": True}})
    assert response.status_code == 502


def test_wanted_poster_alias_and_get_by_id(monkeypatch):
    # Without vision/voice keys the poster must refuse (502) rather than invent one. Clear the keys so the
    # test never depends on (or calls) the live sponsors configured in the developer's .env.
    for key in ("GEMINI_API_KEY", "GEMINI_API_REMIX_KEY", "GOOGLE_CLOUD_VISION_API_KEY", "CARTESIA_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    created = client.post("/api/integrations/wanted-poster", json={"poster_id": "WP-TEST123", "judge_name": "Grace"})
    assert created.status_code == 502


def test_spacetimedb_sync_fallback():
    body = client.post("/api/integrations/spacetimedb-sync", json={"payload": {"request_id": "req_1"}}).json()
    assert body["synced"] is True
    assert body["module"] == "heistbox_telemetry"


def test_remix_poster_endpoint():
    # 1. Missing mugshot returns 400
    res = client.post("/api/integrations/remix-poster", json={"judge_name": "Alice"})
    assert res.status_code == 400

    # 2. Valid request returns structured remix payload
    png_1x1 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    res2 = client.post(
        "/api/integrations/remix-poster",
        json={
            "judge_name": "Judge Alice",
            "alias_title": "The Cookie Bandit",
            "outfit_roast": "Hoodie and sunglasses inside the vault.",
            "mugshot_data_url": f"data:image/png;base64,{png_1x1}",
        },
    )
    assert res2.status_code == 200
    data = res2.json()
    assert data["remix_status"] == "success"
    assert "remix_poster_url" in data
    assert str(data["remix_poster_url"]).startswith("data:")
    assert data["provider"] in ("claude-vision", "openai", "gemini")

def test_health_provenance_reports_unconfigured_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.get("/api/integrations/health-provenance")
    assert response.status_code == 200
    body = response.json()
    assert body["integrations"]["cloud_vision"]["status"] == "unconfigured"
    assert body["integrations"]["cloud_vision"]["live_mode"] is False

def test_wajo_status_is_never_claimed_live(monkeypatch):
    import asyncio
    monkeypatch.delenv("WAJO_API_KEY", raising=False)
    monkeypatch.delenv("wajo_api_key", raising=False)
    assert asyncio.run(router_module._wajo_check())["state"] == "MISSING_KEY"
    monkeypatch.setenv("WAJO_API_KEY", "wak_test")
    monkeypatch.setenv("CFO_ALERT_PHONE_NUMBER", "+15555550123")
    monkeypatch.setenv("WAJO_MCP_URL", "https://does-not-exist.invalid/fo")
    unreachable = asyncio.run(router_module._wajo_check())
    assert unreachable["state"] == "UNREACHABLE" and unreachable["live_mode"] is False
    assert "+1" not in unreachable["detail"]


def test_fetchai_status_reports_in_process_guardian():
    check = router_module._fetchai_check()
    assert check["state"] == "UNVERIFIED" and check["live_mode"] is False
    assert "in-process" in check["detail"] and "not registered on Agentverse" in check["detail"]


def test_status_uses_required_state_names(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    body = client.get("/api/integrations/status").json()
    assert set(body["providers"].values()) <= {"LIVE", "MISSING", "AUTH_ERROR", "UNVERIFIED", "QUOTA_EXCEEDED", "UNREACHABLE"}
    assert body["providers"]["cloud_vision"] == "MISSING"

def test_configure_keys_rejects_unknown_secrets():
    response = client.post("/api/integrations/configure-keys", json={"keys": {"NOT_A_PROVIDER_KEY": "secret"}})
    assert response.status_code == 422

def test_osint_enrich_uses_real_source_payloads(monkeypatch):
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "test-bright")
    monkeypatch.delenv("BRIGHTDATA_SERP_ZONE", raising=False)
    monkeypatch.setattr(router_module, "_BRIGHTDATA_SERP_ZONE", None)
    async def fake_probe(method, url, json_body=None, headers=None, timeout=None):
        if "rdap.org" in url: return 200, {"ldhName": "example.com", "events": [{"eventAction": "registration", "eventDate": "1995-08-14"}]}, 1.0
        if "_suggest_company/" in url: return 200, ["EXAMPLE CORP"], 1.0
        if "consumerfinance" in url:
            assert "company=EXAMPLE+CORP" in url
            return 200, {"hits": {"total": {"value": 42}}}, 1.0
        if "sec.gov" in url: return 200, {"name": "Example Corp", "cik": "0000000001"}, 1.0
        if "get_active_zones" in url: return 200, [{"name": "calhacks13", "type": "serp"}], 1.0
        if "brightdata.com/request" in url:
            assert json_body["zone"] == "calhacks13" and "brd_json=1" in json_body["url"]
            return 200, {"organic": [{"rank": 1, "title": "Example Corp scam warning", "link": "https://x", "description": ""}]}, 1.0
        return 404, {}, 1.0
    monkeypatch.setattr(router_module, "_probe_request", fake_probe)
    response = client.post("/api/integrations/osint-enrich", json={"payload": {"domain": "example.com", "vendor_name": "Example Corp", "cik": "0000000001"}})
    assert response.status_code == 200
    body = response.json()
    assert body["live_mode"] is True
    assert body["vendor_domain_verified"] is True
    assert body["cfpb_company"] == "EXAMPLE CORP" and body["cfpb_complaints_against_company"] == 42
    assert body["web_fraud_search"]["fraud_mentions"] == 1
    assert {"rdap", "cfpb", "sec_edgar", "brightdata"} <= set(body["sources"])

def test_cartesia_audio_is_normalized_to_wav():
    raw_pcm = b"\x00\x00" * 20
    encoded = router_module._normalise_cartesia_audio({"audio": __import__("base64").b64encode(raw_pcm).decode()})
    assert encoded and __import__("base64").b64decode(encoded).startswith(b"RIFF")

def test_crs_network_drop_uses_persona_cache(monkeypatch):
    monkeypatch.setenv("CRS_USERNAME", "test-user")
    monkeypatch.setenv("CRS_PASSWORD", "test-pass")
    monkeypatch.setattr(router_module, "_CRS_TOKENS", {})
    async def unreachable(*args, **kwargs): return 0, "unreachable: ConnectError", 1.0
    monkeypatch.setattr(router_module, "_probe_request", unreachable)
    response = client.post("/api/integrations/crs-check", json={"mask_id": "ceo_wire"})
    assert response.status_code == 200
    body = response.json()
    assert body["live_mode"] is False
    assert body["source"] == "shared/crs_personas.json"
    assert body["crs_rap_sheet"]["persona_id"] == "P05"
    assert "login failed" in body["reason"]


def test_crs_check_pulls_transunion_report_after_login(monkeypatch):
    monkeypatch.setenv("CRS_USERNAME", "test-user")
    monkeypatch.setenv("CRS_PASSWORD", "test-pass")
    monkeypatch.setattr(router_module, "_CRS_TOKENS", {})
    calls = []
    async def fake_probe(method, url, json_body=None, headers=None):
        calls.append(url)
        if url.endswith("/users/login"):
            return 200, {"token": "tok-1", "refreshToken": "ref-1"}, 1.0
        assert headers["Authorization"] == "Bearer tok-1"
        assert json_body["firstName"] == "KAYLA" and json_body["ssn"]
        return 200, {"creditReport": {"scoreModels": [{"score": {"value": "431"}}]}}, 2.0
    monkeypatch.setattr(router_module, "_probe_request", fake_probe)
    body = client.post("/api/integrations/crs-check", json={"identity": {"persona_id": "P13"}}).json()
    assert body["live_mode"] is True and body["source"] == "crs-sandbox"
    assert body["crs_rap_sheet"]["score"] == 431 and body["crs_rap_sheet"]["persona_id"] == "P13"
    assert calls[0].endswith("/users/login") and calls[1].endswith("tu-prequal-fico9")
