"""Demo seed data (play money). Idempotent: rewrites only the seeded rows, leaves session rows alone."""
from __future__ import annotations

import hashlib

import psycopg
from nacl.signing import SigningKey

PROMO_BATCH = "VIP-NIGHT"
PROMO_ROWS = 40
PROMO_CENTS = 5000
VENDOR_ID = "vendor_acme"
VENDOR_WORK_ITEM = "inv_acme_1042"
VENDOR_SOURCE = "acct_vendor_payables"
GENESIS_PREV = "00" * 32


def link_hash(prev_hash_hex: str, vendor_id: str, seq: int, wallet: str) -> str:
    payload = f"{vendor_id}|{seq}|{wallet}".encode("utf-8")
    return hashlib.sha256(bytes.fromhex(prev_hash_hex) + payload).hexdigest()


def seed(conn: psycopg.Connection) -> dict:
    with conn.transaction():
        conn.execute("DELETE FROM payment_entitlements WHERE customer_id LIKE 'seed_%%'")
        rows = [
            (
                f"ent_vip_{i:03d}",
                f"wi_vip_{i:03d}",
                f"seed_cust_{i:03d}",
                PROMO_BATCH,
                PROMO_CENTS,
                "acct_refunds",
                f"0x{(0xA11CE000 + i):08x}{'0' * 32}",
            )
            for i in range(1, PROMO_ROWS + 1)
        ]
        rows.append(("ent_acme_1042", VENDOR_WORK_ITEM, "seed_vendor_acme", None, 120000, VENDOR_SOURCE, "PLACEHOLDER"))
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO payment_entitlements
                   (entitlement_id, work_item_id, customer_id, promo_batch, authorized_cents, source_acct, enrolled_wallet)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                rows,
            )

        # Vendor wallet chain: genesis + one legitimate rotation, both signed by the vendor key.
        # The private key exists only for the duration of this function, so nobody (players
        # included) can produce another valid link later.
        key = SigningKey.generate()
        pub_hex = key.verify_key.encode().hex()
        conn.execute("DELETE FROM vendor_wallet_chain WHERE vendor_id = %s", (VENDOR_ID,))
        conn.execute(
            "INSERT INTO vendor_keys (vendor_id, public_key_hex) VALUES (%s, %s) "
            "ON CONFLICT (vendor_id) DO UPDATE SET public_key_hex = EXCLUDED.public_key_hex",
            (VENDOR_ID, pub_hex),
        )
        prev = GENESIS_PREV
        head_wallet = ""
        for seq, wallet in enumerate(["0xAC0E000000000000000000000000000000000001", "0xAC0E000000000000000000000000000000000002"]):
            h = link_hash(prev, VENDOR_ID, seq, wallet)
            sig = key.sign(bytes.fromhex(h)).signature.hex()
            conn.execute(
                "INSERT INTO vendor_wallet_chain (vendor_id, seq, wallet, prev_hash, link_hash, signature_hex) VALUES (%s, %s, %s, %s, %s, %s)",
                (VENDOR_ID, seq, wallet, prev, h, sig),
            )
            prev, head_wallet = h, wallet
        del key
        conn.execute("UPDATE payment_entitlements SET enrolled_wallet = %s WHERE work_item_id = %s", (head_wallet, VENDOR_WORK_ITEM))

    n = conn.execute("SELECT count(*) FROM payment_entitlements WHERE customer_id LIKE 'seed_%%'").fetchone()[0]
    return {"seeded_entitlements": n, "promo_batch": PROMO_BATCH, "vendor_chain_links": 2, "vendor_head_wallet": head_wallet}
