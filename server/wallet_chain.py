"""Ed25519 hash-chained vendor wallet continuity (PyNaCl).

Each link: link_hash = sha256(prev_hash || f"{vendor_id}|{seq}|{wallet}"), signature = Ed25519(link_hash)
under the vendor's pinned public key. A wallet change is accepted only if the presented link extends
the current head and verifies under that pinned key. The seed discarded the private key, so in this
game no player-supplied link can verify.
"""
from __future__ import annotations

import time

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from db.seed import link_hash
from server import db


def _verify(vk: VerifyKey, h: str, sig_hex: str) -> bool:
    try:
        vk.verify(bytes.fromhex(h), bytes.fromhex(sig_hex))
        return True
    except (BadSignatureError, ValueError, TypeError):
        return False


def check(vendor_id: str, presented: dict | None) -> dict:
    with db.pool().connection() as conn:
        t0 = time.perf_counter()
        key = conn.execute("SELECT public_key_hex FROM vendor_keys WHERE vendor_id = %s", (vendor_id,)).fetchone()
        links = conn.execute(
            "SELECT seq, wallet, prev_hash, link_hash, signature_hex FROM vendor_wallet_chain WHERE vendor_id = %s ORDER BY seq",
            (vendor_id,),
        ).fetchall()
        if key is None or not links:
            return {"vendor_id": vendor_id, "chain_length": 0, "chain_valid": False, "presented_link_valid": False,
                    "head_wallet": "", "reason": "unknown vendor", "latency_ms": round((time.perf_counter() - t0) * 1000, 3)}
        vk = VerifyKey(bytes.fromhex(key["public_key_hex"]))
        prev, chain_ok, why = "00" * 32, True, "chain verified"
        for i, l in enumerate(links):
            if l["seq"] != i or l["prev_hash"] != prev:
                chain_ok, why = False, f"link {i} does not extend link {i - 1}"
                break
            if link_hash(prev, vendor_id, l["seq"], l["wallet"]) != l["link_hash"]:
                chain_ok, why = False, f"link {i} hash mismatch"
                break
            if not _verify(vk, l["link_hash"], l["signature_hex"]):
                chain_ok, why = False, f"link {i} signature invalid"
                break
            prev = l["link_hash"]
        head = links[-1]

        presented_ok = False
        if presented is not None and chain_ok:
            seq = presented.get("seq")
            wallet = str(presented.get("wallet", ""))[:80]
            p_prev = str(presented.get("prev_hash", ""))
            sig = str(presented.get("signature_hex", ""))
            if seq != head["seq"] + 1:
                why = f"presented link seq {seq} does not follow head seq {head['seq']}"
            elif p_prev != head["link_hash"]:
                why = "presented link's prev_hash is not the current head hash"
            elif not _verify(vk, link_hash(p_prev, vendor_id, seq, wallet), sig):
                why = "presented link's Ed25519 signature does not verify under the vendor's pinned key"
            else:
                presented_ok = True
                why = "presented link verified and appended"
                with conn.transaction():
                    h = link_hash(p_prev, vendor_id, seq, wallet)
                    conn.execute(
                        "INSERT INTO vendor_wallet_chain (vendor_id, seq, wallet, prev_hash, link_hash, signature_hex) VALUES (%s, %s, %s, %s, %s, %s)",
                        (vendor_id, seq, wallet, p_prev, h, sig),
                    )
                    conn.execute("UPDATE payment_entitlements SET enrolled_wallet = %s WHERE customer_id = %s",
                                 (wallet, f"seed_{vendor_id}"))
                head = {"wallet": wallet}
        latency_ms = (time.perf_counter() - t0) * 1000
    return {"vendor_id": vendor_id, "chain_length": len(links), "chain_valid": chain_ok,
            "presented_link_valid": presented_ok, "head_wallet": head["wallet"], "reason": why,
            "latency_ms": round(latency_ms, 3)}


def head(vendor_id: str) -> dict | None:
    with db.pool().connection() as conn:
        return conn.execute(
            "SELECT seq, wallet, link_hash FROM vendor_wallet_chain WHERE vendor_id = %s ORDER BY seq DESC LIMIT 1",
            (vendor_id,),
        ).fetchone()
