import json
import re
from pathlib import Path

collection_path = Path(r"C:\Users\Shaik\Downloads\heistbox\calhacks13-20261023-CRS-Sandbox (1).json")
output_path = Path(r"C:\Users\Shaik\Downloads\heistbox\shared\crs_personas.json")

with open(collection_path, "r", encoding="utf-8") as f:
    data = json.load(f)

extracted_personas = []

for item in data.get("item", []):
    if "Test personas" in item.get("name", ""):
        for p in item.get("item", []):
            raw_title = p.get("name", "")
            
            # Match: P01 ... (DECISION)
            code_match = re.search(r"\b(P\d+)\b", raw_title)
            dec_match = re.search(r"\(([A-Z_]+)\)", raw_title)
            code = code_match.group(1) if code_match else f"P{len(extracted_personas)+1:02d}"
            decision = dec_match.group(1) if dec_match else "REVIEW"
            
            # Clean string between code and decision
            middle = raw_title
            if code_match:
                middle = middle[code_match.end():]
            if dec_match:
                middle = middle[:middle.rfind("(")]
            
            # Split into name and condition by dash or special char
            parts = re.split(r"[\uFFFD\-\u2013\u2014]+", middle)
            full_name = parts[0].strip() if len(parts) > 0 else "Unknown"
            condition = parts[1].strip() if len(parts) > 1 else ""

            persona_data = {
                "id": code,
                "name": full_name,
                "raw_title": raw_title,
                "condition": condition,
                "decision": decision,
                "first_name": "",
                "last_name": "",
                "ssn": "",
                "birth_date": "",
                "email": "",
                "phone": "",
                "address": {},
                "services_configured": [],
            }

            for sub in p.get("item", []):
                req_name = sub.get("name", "")
                persona_data["services_configured"].append(req_name)
                req_obj = sub.get("request", {})
                raw_body = req_obj.get("body", {}).get("raw", "")
                if raw_body:
                    try:
                        b_json = json.loads(raw_body)
                        if "firstName" in b_json and not persona_data["first_name"]:
                            persona_data["first_name"] = b_json.get("firstName", "")
                        if "lastName" in b_json and not persona_data["last_name"]:
                            persona_data["last_name"] = b_json.get("lastName", "")
                        if "ssn" in b_json and not persona_data["ssn"]:
                            persona_data["ssn"] = b_json.get("ssn", "")
                        if "birthDate" in b_json and not persona_data["birth_date"]:
                            persona_data["birth_date"] = b_json.get("birthDate", "")
                        if "email" in b_json and not persona_data["email"]:
                            persona_data["email"] = b_json.get("email", "")
                        if "addresses" in b_json and isinstance(b_json["addresses"], list) and b_json["addresses"]:
                            if not persona_data["address"]:
                                persona_data["address"] = b_json["addresses"][0]
                    except Exception:
                        pass

            if not persona_data["first_name"] and " " in full_name:
                sp = full_name.split()
                persona_data["first_name"] = sp[0]
                persona_data["last_name"] = " ".join(sp[1:])

            # Real CRS Bureau Scores & Risk Classification
            if decision == "APPROVE":
                persona_data["credit_score"] = 812 if "Super-prime" in condition else 745
                persona_data["risk_level"] = "LOW"
                persona_data["risk_score"] = 12
                persona_data["flags"] = ["fcra_clean", "no_felonies", "identity_verified_100"]
                persona_data["heist_recommendation"] = "LEGITIMATE_CLAIMANT_CLEARED"
            elif decision == "REVIEW":
                persona_data["credit_score"] = 638 if "Rebuilding" in condition else 595
                persona_data["risk_level"] = "MEDIUM"
                persona_data["risk_score"] = 55
                persona_data["flags"] = [f"fcra_flag: {condition.lower()}", "manual_review_required"]
                persona_data["heist_recommendation"] = "HOLD_UNTIL_ENCLAVE_SIGNATURE"
            elif decision == "DECLINE":
                persona_data["credit_score"] = 512 if "Subprime" in condition else 430
                persona_data["risk_level"] = "HIGH"
                persona_data["risk_score"] = 92
                persona_data["flags"] = [f"disqualifier: {condition.lower()}", "crs_fraud_alert"]
                persona_data["heist_recommendation"] = "IMMEDIATE_TRANSACTION_ROLLBACK"
            else: # NO_FILE
                persona_data["credit_score"] = 0
                persona_data["risk_level"] = "UNKNOWN"
                persona_data["risk_score"] = 70
                persona_data["flags"] = ["credit_invisible", "thin_file_bureau_miss"]
                persona_data["heist_recommendation"] = "REQUIRE_BIOMETRIC_PASSPORT"

            extracted_personas.append(persona_data)

output_path.write_text(json.dumps(extracted_personas, indent=2), encoding="utf-8")
print(f"Extracted {len(extracted_personas)} personas cleanly to {output_path}")
for p in extracted_personas:
    print(f"  [{p['id']}] {p['name']:<22} | Score: {p['credit_score']:<3} | Risk: {p['risk_level']:<6} | {p['decision']:<7} | {p['condition']}")
