from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
import anyio
from mcp import ClientSession
from kernel.crs_mcp import (
    crs_mcp,
    crs_lookup_applicant,
    crs_verify_identity,
    crs_screen_dispute_claimant,
    crs_list_all_personas,
    crs_get_persona_dossier,
    crs_sandbox_stats,
)


def test_crs_tools():
    print("=== 1. Testing crs_list_all_personas() ===")
    personas = crs_list_all_personas()
    assert len(personas) == 20
    print(f"[OK] Found all {len(personas)} CalHacks CRS test personas.")

    print("\n=== 2. Testing crs_lookup_applicant() - Prime (P01) vs Synthetic Fraud (P13) ===")
    p01 = crs_lookup_applicant("Margaret Okafor")
    assert p01["found"] is True
    assert p01["decision"] == "APPROVE"
    assert p01["credit_score"] == 745
    print(f"[OK] P01: {p01['name']} -> {p01['decision']}, Score={p01['credit_score']}, Risk={p01['risk_level']}")

    p13 = crs_lookup_applicant("P13")
    assert p13["found"] is True
    assert p13["decision"] == "DECLINE"
    assert p13["risk_level"] == "HIGH"
    assert p13["credit_score"] == 430
    print(f"[OK] P13: {p13['name']} -> {p13['decision']}, Condition='{p13['condition']}', Rec='{p13['heist_recommendation']}'")

    print("\n=== 3. Testing crs_verify_identity() ===")
    # Verified identity
    v_clean = crs_verify_identity(
        first_name=p01["first_name"],
        last_name=p01["last_name"],
        ssn=p01["ssn"],
    )
    assert v_clean["verified"] is True
    assert v_clean["decision"] == "PASSED"
    print(f"[OK] Clean Identity Verification: {v_clean['decision']} (Confidence: {v_clean['confidence_score']}%)")

    # Synthetic fraud detection
    v_synth = crs_verify_identity(
        first_name=p13["first_name"],
        last_name=p13["last_name"],
        ssn=p13["ssn"],
    )
    assert v_synth["synthetic_fraud_detected"] is True
    assert v_synth["verified"] is False
    print(f"[OK] Synthetic Fraud Detected: {v_synth['decision']} ({v_synth['recommended_action']})")

    print("\n=== 4. Testing crs_screen_dispute_claimant() ===")
    screen_busted = crs_screen_dispute_claimant(
        work_item_id="ticket_104",
        claimant_name="Kayla Brennan",
        claimed_amount_cents=500000,
    )
    assert screen_busted["disqualified"] is True
    assert screen_busted["heistbox_verdict"] == "BUSTED_CRS_FRAUD_SURFACE"
    print(f"[OK] Claimant screening: {screen_busted['claimant']} -> {screen_busted['heistbox_verdict']} ({screen_busted['recommended_gate_action']})")

    screen_clean = crs_screen_dispute_claimant(
        work_item_id="ticket_104",
        claimant_name="Margaret Okafor",
        claimed_amount_cents=2500,
    )
    assert screen_clean["disqualified"] is False
    assert screen_clean["heistbox_verdict"] == "CLEARED_CRS_VERIFIED"
    print(f"[OK] Claimant screening: {screen_clean['claimant']} -> {screen_clean['heistbox_verdict']}")

    print("\n=== 5. Testing CRS MCP Resources ===")
    dossier = json.loads(crs_get_persona_dossier("P09"))
    assert dossier["id"] == "P09"
    print(f"[OK] crs://personas/P09 loaded dossier for: {dossier['name']} ({dossier['condition']})")

    stats = json.loads(crs_sandbox_stats())
    assert stats["total_test_personas"] == 20
    print(f"[OK] crs://sandbox/stats -> {stats['breakdown']}")


async def verify_crs_mcp_client_session():
    print("\n=== 6. Testing Real FastMCP ClientSession Tool Discovery & Calling ===")
    server = crs_mcp._mcp_server
    read_send, read_recv = anyio.create_memory_object_stream(10)
    write_send, write_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, read_recv, write_send, server.create_initialization_options())
        async with ClientSession(write_recv, read_send) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            assert "crs_lookup_applicant" in names
            assert "crs_verify_identity" in names
            assert "crs_screen_dispute_claimant" in names
            assert "crs_list_all_personas" in names
            print(f"[OK] Discovered CRS MCP Tools over ClientSession: {names}")

            # Call tool over MCP
            call_res = await session.call_tool("crs_lookup_applicant", {"query": "P05"})
            result_data = json.loads(call_res.content[0].text)
            assert result_data["found"] is True
            assert result_data["persona_id"] == "P05"
            assert result_data["decision"] == "DECLINE"
            print(f"[OK] ClientSession call_tool('crs_lookup_applicant', query='P05') -> {result_data['name']} ({result_data['condition']})")

            # Read resource over MCP
            res_content = await session.read_resource("crs://sandbox/stats")
            stats_data = json.loads(res_content.contents[0].text)
            assert stats_data["total_test_personas"] == 20
            print(f"[OK] ClientSession read_resource('crs://sandbox/stats') -> {stats_data['sandbox_name']}")

            tg.cancel_scope.cancel()

    print("\n=======================================================")
    print("ALL CRS MCP PROTOCOL TESTS PASSED WITH 100% VERIFICATION!")
    print("=======================================================")


if __name__ == "__main__":
    test_crs_tools()
    anyio.run(verify_crs_mcp_client_session)
