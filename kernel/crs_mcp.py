"""
crs_mcp.py
Official FastMCP Server for Credit Reporting Services (CRS) Sandbox.
Exposes Model Context Protocol (MCP) tools and resources for CalHacks-13:
- crs_lookup_applicant
- crs_verify_identity
- crs_screen_dispute_claimant
- crs_list_all_personas
- crs://personas/{persona_id}
- crs://sandbox/stats
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from fastmcp import FastMCP

crs_mcp = FastMCP("CRS-CreditReporting-Gatekeeper")

BASE_DIR = Path(__file__).resolve().parent.parent
CRS_JSON_PATH = BASE_DIR / "shared" / "crs_personas.json"


def _load_personas() -> list[dict[str, Any]]:
    if CRS_JSON_PATH.exists():
        try:
            with open(CRS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


@crs_mcp.tool()
def crs_lookup_applicant(query: str) -> dict[str, Any]:
    """
    Looks up an applicant in the CRS Credit Reporting Services Sandbox by Name, SSN, or Persona ID (e.g. 'P13', 'Kayla Brennan', '666701005').
    Returns credit score, risk classification, decision (APPROVE/REVIEW/DECLINE), and fraud indicators.
    """
    personas = _load_personas()
    q = query.strip().lower()

    for p in personas:
        if (
            q == p.get("id", "").lower()
            or q in p.get("name", "").lower()
            or q in p.get("first_name", "").lower()
            or q in p.get("last_name", "").lower()
            or q == p.get("ssn", "").lower()
        ):
            return {
                "found": True,
                "persona_id": p.get("id"),
                "name": p.get("name"),
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "ssn": p.get("ssn"),
                "birth_date": p.get("birth_date"),
                "address": p.get("address"),
                "decision": p.get("decision"),
                "condition": p.get("condition"),
                "credit_score": p.get("credit_score"),
                "risk_level": p.get("risk_level"),
                "risk_score": p.get("risk_score"),
                "flags": p.get("flags"),
                "heist_recommendation": p.get("heist_recommendation"),
                "bureaus_supported": ["TransUnion (tu-prequal-fico9)", "Experian (exp-prequal-vantage4)", "Equifax (efx-prequal-vantage4)"],
                "data_source": "CalHacks13-20261023-CRS-Sandbox",
            }

    return {
        "found": False,
        "query": query,
        "message": f"No applicant matching '{query}' found in CRS Sandbox. Use crs_list_all_personas to see available personas.",
    }


@crs_mcp.tool()
def crs_verify_identity(first_name: str, last_name: str, ssn: str, address_line1: str = "", state: str = "") -> dict[str, Any]:
    """
    Simulates TransUnion TruValidate / Identity Manager Verification against CRS Sandbox records.
    Verifies name, SSN, and current address to detect synthetic fraud, deceased indicators, or identity mismatches.
    """
    personas = _load_personas()
    clean_ssn = ssn.replace("-", "").strip()

    for p in personas:
        p_ssn = str(p.get("ssn", "")).replace("-", "").strip()
        if clean_ssn and p_ssn == clean_ssn:
            name_match = (
                first_name.strip().lower() == str(p.get("first_name", "")).lower()
                and last_name.strip().lower() == str(p.get("last_name", "")).lower()
            )
            addr_obj = p.get("address", {})
            addr_line = str(addr_obj.get("addressLine1", "")).lower()
            addr_state = str(addr_obj.get("state", "")).lower()

            addr_match = True
            if address_line1 and addr_line:
                addr_match = address_line1.strip().lower() in addr_line or addr_line in address_line1.strip().lower()
            if state and addr_state:
                addr_match = addr_match and (state.strip().lower() == addr_state)

            is_synthetic = "synthetic" in str(p.get("condition", "")).lower()
            is_deceased = "deceased" in str(p.get("condition", "")).lower()
            is_mismatch = "mismatch" in str(p.get("condition", "")).lower() or not name_match

            verified = name_match and addr_match and not is_synthetic and not is_deceased and not is_mismatch

            return {
                "verified": verified,
                "persona_id": p.get("id"),
                "ssn_match": True,
                "name_match": name_match,
                "address_match": addr_match,
                "synthetic_fraud_detected": is_synthetic,
                "deceased_flag": is_deceased,
                "identity_mismatch": is_mismatch,
                "confidence_score": 98 if verified else 22,
                "decision": "PASSED" if verified else "REJECTED_FRAUD_PREVENTION",
                "recommended_action": p.get("heist_recommendation"),
            }

    return {
        "verified": False,
        "ssn_match": False,
        "name_match": False,
        "confidence_score": 0,
        "decision": "SSN_NOT_FOUND_IN_BUREAU",
        "recommended_action": "MANUAL_DOCUMENT_VERIFICATION",
    }


@crs_mcp.tool()
def crs_screen_dispute_claimant(work_item_id: str, claimant_name: str, claimed_amount_cents: int) -> dict[str, Any]:
    """
    Cross-checks a bank dispute claimant against CRS credit, criminal, and eviction databases.
    Applies PAIR interior projection policies: if the claimant is high-risk, recommends CTE rollback of unauthorized funds.
    """
    lookup = crs_lookup_applicant(claimant_name)
    if not lookup.get("found"):
        # Default benign assessment if not a targeted adversary
        return {
            "work_item_id": work_item_id,
            "claimant": claimant_name,
            "crs_status": "UNINDEXED_CLAIMANT",
            "risk_score": 30,
            "recommended_gate_action": "APPLY_STANDARD_ENTITLEMENT_CAP",
            "pair_interior_projection_approved": True,
        }

    risk_level = lookup.get("risk_level", "MEDIUM")
    decision = lookup.get("decision", "REVIEW")
    credit_score = lookup.get("credit_score", 600)
    flags = lookup.get("flags", [])

    high_risk_disqualifiers = [
        "disqualifier: synthetic identity / fraud",
        "disqualifier: felony conviction",
        "disqualifier: chapter 13 active",
        "disqualifier: deceased indicator",
        "disqualifier: identity mismatch",
        "disqualifier: eviction history",
    ]
    disqualified = any(f in flags for f in high_risk_disqualifiers) or decision == "DECLINE"

    return {
        "work_item_id": work_item_id,
        "claimant": claimant_name,
        "persona_id": lookup.get("persona_id"),
        "credit_score": credit_score,
        "risk_level": risk_level,
        "decision": decision,
        "condition": lookup.get("condition"),
        "flags": flags,
        "claimed_amount_cents": claimed_amount_cents,
        "claimed_dollars": f"${claimed_amount_cents / 100:.2f}",
        "disqualified": disqualified,
        "recommended_gate_action": "ENFORCE_STRICT_ROW_LOCK_ROLLBACK" if disqualified else "ALLOW_PREAUTHORIZED_ANCHOR",
        "heistbox_verdict": "BUSTED_CRS_FRAUD_SURFACE" if disqualified else "CLEARED_CRS_VERIFIED",
    }


@crs_mcp.tool()
def crs_list_all_personas() -> list[dict[str, Any]]:
    """Returns the list of all 20 CalHacks CRS Sandbox test personas with credit profiles and risk levels."""
    personas = _load_personas()
    return [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "condition": p.get("condition"),
            "decision": p.get("decision"),
            "credit_score": p.get("credit_score"),
            "risk_level": p.get("risk_level"),
            "ssn": p.get("ssn"),
        }
        for p in personas
    ]


@crs_mcp.resource("crs://personas/{persona_id}")
def crs_get_persona_dossier(persona_id: str) -> str:
    """Returns the comprehensive raw JSON bureau dossier for a specific CRS persona (e.g. P01 to P20)."""
    personas = _load_personas()
    for p in personas:
        if p.get("id", "").upper() == persona_id.upper():
            return json.dumps(p, indent=2)
    return json.dumps({"error": f"Persona {persona_id} not found"}, indent=2)


@crs_mcp.resource("crs://sandbox/stats")
def crs_sandbox_stats() -> str:
    """Returns summary statistics across the 20 CRS test cases."""
    personas = _load_personas()
    approvals = sum(1 for p in personas if p.get("decision") == "APPROVE")
    reviews = sum(1 for p in personas if p.get("decision") == "REVIEW")
    declines = sum(1 for p in personas if p.get("decision") == "DECLINE")
    no_files = sum(1 for p in personas if p.get("decision") == "NO_FILE")

    stats = {
        "sandbox_name": "CalHacks13-20261023-CRS-Sandbox",
        "total_test_personas": len(personas),
        "breakdown": {
            "APPROVE": approvals,
            "REVIEW": reviews,
            "DECLINE": declines,
            "NO_FILE": no_files,
        },
        "bureaus": ["TransUnion", "Experian", "Equifax", "PitchPoint BLJ", "AtData FraudFinder", "CIC Criminal & Eviction"],
    }
    return json.dumps(stats, indent=2)


if __name__ == "__main__":
    crs_mcp.run()
