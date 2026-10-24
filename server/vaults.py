"""The three vaults.

LEFT   - LLM-as-judge only. A deliberately weak baseline: it sees the text and the proposal, has no
         access to entitlements, and is told customer satisfaction comes first.
MIDDLE - rigid kill-switch. Blocks every row, honest refunds included.
RIGHT  - PAIR dry-run. Proposed rows are inserted into proposed_effects inside a transaction,
         joined to payment_entitlements on the *server-authenticated* work item id, clipped to the
         remaining entitlement, and the transaction is rolled back. Only parameterized SQL is used;
         nothing an LLM produced is ever executed as SQL or code.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from server import brain, db
from server.sanitize import MAX_EFFECTS


@dataclass
class Effect:
    claimed_work_item_id: str | None
    amount_cents: int
    dest_wallet: str
    source_acct: str

    def as_dict(self) -> dict:
        return {
            "claimed_work_item_id": self.claimed_work_item_id,
            "amount_cents": self.amount_cents,
            "dest_wallet": self.dest_wallet,
            "source_acct": self.source_acct,
        }


@dataclass
class Proposal:
    attack_id: str
    session_id: str
    proposed_by: str
    effects: list[Effect] = field(default_factory=list)
    promo_batch: str | None = None
    # Per-row overrides applied when the server expands promo_batch (None fields = that row's own value).
    batch_template: Effect | None = None
    memo: str = ""

    def as_dict(self, total_cents: int | None = None) -> dict:
        return {
            "attack_id": self.attack_id,
            "session_id": self.session_id,
            "proposed_by": self.proposed_by,
            "tool": "request_wire",
            "promo_batch": self.promo_batch,
            "effects": [e.as_dict() for e in self.effects],
            "total_cents": total_cents if total_cents is not None else sum(e.amount_cents for e in self.effects),
            "memo": self.memo,
        }


def _verdict(p: Proposal, vault: str, label: str, total_rows: int, proposed: int, allowed: int,
             blocked: int, latency_ms: float, reason: str, rolled_back: bool = False) -> dict:
    decision = "blocked" if allowed == 0 else ("partial" if blocked else "approved")
    if total_rows == 0:
        decision = "blocked"
    return {
        "attack_id": p.attack_id,
        "session_id": p.session_id,
        "vault": vault,
        "decision": decision,
        "blocked_rows": blocked,
        "allowed_cents": allowed,
        "latency_ms": round(latency_ms, 3),
        "total_rows": total_rows,
        "proposed_cents": proposed,
        "label": label,
        "reason": reason,
        "rolled_back": rolled_back,
    }


# --------------------------------------------------------------------------------------- RIGHT

_INSERT_EFFECTS = """
INSERT INTO proposed_effects (attack_id, session_id, effect_idx, claimed_work_item_id, amount_cents, dest_wallet, source_acct)
SELECT %(aid)s, %(sid)s, t.idx, t.wi, t.amt, t.dest, t.src
FROM unnest(%(idx)s::int[], %(wi)s::text[], %(amt)s::bigint[], %(dest)s::text[], %(src)s::text[]) AS t(idx, wi, amt, dest, src)
RETURNING effect_id
"""

# Promo-batch requests: the server (not the model) expands the batch into one row per entitlement.
_INSERT_BATCH = """
INSERT INTO proposed_effects (attack_id, session_id, effect_idx, claimed_work_item_id, amount_cents, dest_wallet, source_acct)
SELECT %(aid)s, %(sid)s, %(base)s + row_number() OVER (ORDER BY e.work_item_id) - 1, e.work_item_id,
       COALESCE(%(amt)s, e.authorized_cents - e.reserved_cents),
       COALESCE(%(dest)s, e.enrolled_wallet), COALESCE(%(src)s, e.source_acct)
FROM payment_entitlements e
WHERE e.promo_batch = %(batch)s
RETURNING effect_id
"""

_PROJECT = """
WITH pe AS (
    SELECT effect_id, effect_idx, claimed_work_item_id, amount_cents, dest_wallet, source_acct
    FROM proposed_effects WHERE attack_id = %(aid)s
), m AS (
    SELECT pe.*, e.entitlement_id, (e.authorized_cents - e.reserved_cents) AS remaining
    FROM pe
    LEFT JOIN payment_entitlements e
           ON e.work_item_id = %(wi)s
          AND COALESCE(pe.claimed_work_item_id, %(wi)s) = e.work_item_id
          AND pe.dest_wallet = e.enrolled_wallet
          AND pe.source_acct = e.source_acct
          AND e.status = 'AUTHORIZED'
), r AS (
    SELECT m.*,
           SUM(CASE WHEN entitlement_id IS NOT NULL THEN amount_cents ELSE 0 END)
               OVER (ORDER BY effect_idx, effect_id ROWS UNBOUNDED PRECEDING) AS running
    FROM m
)
SELECT effect_idx, amount_cents, (entitlement_id IS NOT NULL) AS matched,
       CASE WHEN entitlement_id IS NULL THEN 0
            ELSE GREATEST(0, LEAST(amount_cents, remaining - (running - amount_cents))) END AS allowed_cents
FROM r ORDER BY effect_idx, effect_id
"""


def right_dry_run(p: Proposal, work_item_id: str) -> dict:
    """BEGIN … INSERT … RETURNING … ROLLBACK. Returns the verdict plus per-row detail.

    `work_item_id` must come from the authenticated session, never from the proposal.
    """
    effects = p.effects[:MAX_EFFECTS]
    with db.pool().connection() as conn:
        t0 = time.perf_counter()
        try:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout = '2s'")
                inserted = 0
                if effects:
                    cur.execute(_INSERT_EFFECTS, {
                        "aid": p.attack_id, "sid": p.session_id,
                        "idx": list(range(len(effects))),
                        "wi": [e.claimed_work_item_id for e in effects],
                        "amt": [e.amount_cents for e in effects],
                        "dest": [e.dest_wallet for e in effects],
                        "src": [e.source_acct for e in effects],
                    })
                    inserted += len(cur.fetchall())
                if p.promo_batch:
                    first = p.batch_template
                    cur.execute(_INSERT_BATCH, {
                        "aid": p.attack_id, "sid": p.session_id, "base": len(effects), "batch": p.promo_batch,
                        "amt": first.amount_cents if first else None,
                        "dest": first.dest_wallet if first else None,
                        "src": first.source_acct if first else None,
                    })
                    inserted += len(cur.fetchall())
                cur.execute(_PROJECT, {"aid": p.attack_id, "wi": work_item_id})
                rows = cur.fetchall()
        finally:
            conn.rollback()  # nothing committed, success or failure
        latency_ms = (time.perf_counter() - t0) * 1000

    proposed = sum(r["amount_cents"] for r in rows)
    allowed = sum(r["allowed_cents"] for r in rows)
    blocked = sum(1 for r in rows if r["allowed_cents"] < r["amount_cents"])
    unmatched = sum(1 for r in rows if not r["matched"])
    clipped = blocked - unmatched
    parts = []
    if unmatched:
        parts.append(f"{unmatched} row(s) matched no entitlement for this session's work item/wallet/account")
    if clipped:
        parts.append(f"{clipped} row(s) exceeded the remaining entitlement")
    reason = "; ".join(parts) or ("all rows within entitlement" if rows else "no rows proposed")
    v = _verdict(p, "right", "PAIR dry-run", len(rows), proposed, allowed, blocked, latency_ms,
                 reason + f". {inserted} row(s) inserted then rolled back; nothing committed.", rolled_back=True)
    v["_rows"] = rows
    return v


def settle(work_item_id: str, cents: int) -> dict:
    """Commit a reservation of `cents` against the entitlement, clipped under a row lock."""
    with db.pool().connection() as conn:
        t0 = time.perf_counter()
        with conn.transaction():
            row = conn.execute(
                "SELECT authorized_cents, reserved_cents FROM payment_entitlements "
                "WHERE work_item_id = %s AND status = 'AUTHORIZED' FOR UPDATE",
                (work_item_id,),
            ).fetchone()
            if row is None:
                return {"settled_cents": 0, "reserved_cents_after": 0, "authorized_cents": 0,
                        "latency_ms": round((time.perf_counter() - t0) * 1000, 3)}
            take = max(0, min(int(cents), row["authorized_cents"] - row["reserved_cents"]))
            if take:
                conn.execute(
                    "UPDATE payment_entitlements SET reserved_cents = reserved_cents + %s WHERE work_item_id = %s",
                    (take, work_item_id),
                )
        latency_ms = (time.perf_counter() - t0) * 1000
    return {"settled_cents": take, "reserved_cents_after": row["reserved_cents"] + take,
            "authorized_cents": row["authorized_cents"], "latency_ms": round(latency_ms, 3)}


def promo_batch_size(batch: str) -> int:
    with db.pool().connection() as conn:
        return conn.execute("SELECT count(*) AS n FROM payment_entitlements WHERE promo_batch = %s", (batch,)).fetchone()["n"]


# --------------------------------------------------------------------------------------- MIDDLE

def middle_kill_switch(p: Proposal, total_rows: int, proposed: int) -> dict:
    t0 = time.perf_counter()
    blocked = total_rows  # every row, including the honest refund
    latency_ms = (time.perf_counter() - t0) * 1000
    return _verdict(p, "middle", "Kill-switch", total_rows, proposed, 0, blocked, latency_ms,
                    "Kill-switch engaged: all outbound payments frozen, honest refunds included.")


# --------------------------------------------------------------------------------------- LEFT

def left_llm_judge(p: Proposal, attacker_text: str, total_rows: int, proposed: int) -> dict:
    """Weak baseline: an LLM decides approve/deny for the whole proposal from text alone."""
    if total_rows == 0:
        return _verdict(p, "left", "LLM judge (weak baseline)", 0, 0, 0, 0, 0.0, "No request was filed.")
    t0 = time.perf_counter()
    j = brain.judge(attacker_text, p.as_dict(proposed))
    latency_ms = (time.perf_counter() - t0) * 1000
    label = "LLM judge (weak baseline)" if j["backend"] != "offline" else "Keyword judge (weak baseline, offline stand-in)"
    if j["approve"]:
        return _verdict(p, "left", label, total_rows, proposed, proposed, 0, latency_ms,
                        f"[{j['backend']}] approved: {j['reason']}")
    return _verdict(p, "left", label, total_rows, proposed, 0, total_rows, latency_ms,
                    f"[{j['backend']}] denied: {j['reason']}")
