"""Sessions, per-session agent memory, leaderboard. All parameterized SQL."""
from __future__ import annotations

import hashlib
import hmac
import json
import random
import secrets

from psycopg.types.json import Jsonb

from server import config, db
from server.presets import preset_info
from server.sanitize import clean_alias

_ADJ = ["Velvet", "Neon", "Quiet", "Crimson", "Lucky", "Midnight", "Silver", "Rusty", "Cosmic", "Sly"]
_NOUN = ["Fox", "Badger", "Heron", "Raccoon", "Otter", "Magpie", "Lynx", "Weasel", "Moth", "Gecko"]


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def create_session(alias: str) -> dict:
    alias = clean_alias(alias)
    alias = alias or f"{random.choice(_ADJ)} {random.choice(_NOUN)} {random.randint(10, 99)}"
    session_id = "s_" + secrets.token_hex(8)
    token = "t_" + secrets.token_urlsafe(24)
    wi = "wi_" + session_id
    wallet = "0xC0FFEE" + secrets.token_hex(17)  # 0x + 40 hex
    with db.pool().connection() as conn, conn.transaction():
        conn.execute(
            "INSERT INTO payment_entitlements (entitlement_id, work_item_id, customer_id, authorized_cents, source_acct, enrolled_wallet) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ("ent_" + session_id, wi, "cust_" + session_id, config.ENTITLEMENT_CENTS, config.SESSION_SOURCE_ACCT, wallet),
        )
        conn.execute("INSERT INTO sessions (session_id, token_sha256, alias, work_item_id) VALUES (%s, %s, %s, %s)",
                     (session_id, _sha(token), alias, wi))
        conn.execute("INSERT INTO leaderboard (session_id, alias) VALUES (%s, %s)", (session_id, alias))
    return {"session_id": session_id, "token": token, "alias": alias, "entitlement": entitlement(wi),
            "presets": preset_info(), "ws_path": "/ws"}


def authenticate(session_id: str, token: str) -> dict | None:
    with db.pool().connection() as conn:
        row = conn.execute("SELECT session_id, token_sha256, alias, work_item_id FROM sessions WHERE session_id = %s",
                           (session_id,)).fetchone()
    if row is None or not hmac.compare_digest(row["token_sha256"], _sha(token or "")):
        return None
    return {"session_id": row["session_id"], "alias": row["alias"], "work_item_id": row["work_item_id"]}


def entitlement(work_item_id: str) -> dict:
    """lookup_entitlement tool: the real row, read live."""
    with db.pool().connection() as conn:
        return conn.execute(
            "SELECT work_item_id, authorized_cents, reserved_cents, enrolled_wallet, source_acct "
            "FROM payment_entitlements WHERE work_item_id = %s", (work_item_id,)).fetchone()


def memory(session_id: str) -> dict[str, dict]:
    with db.pool().connection() as conn:
        rows = conn.execute("SELECT agent_id, attempts, suspicion, notes FROM agent_memory WHERE session_id = %s",
                            (session_id,)).fetchall()
    return {r["agent_id"]: r for r in rows}


def remember(session_id: str, agent_id: str, suspicion: float, note: str) -> dict:
    with db.pool().connection() as conn:
        return conn.execute(
            """INSERT INTO agent_memory (session_id, agent_id, attempts, suspicion, notes)
               VALUES (%(s)s, %(a)s, 1, %(sus)s, %(n)s)
               ON CONFLICT (session_id, agent_id) DO UPDATE SET
                   attempts = agent_memory.attempts + 1,
                   suspicion = GREATEST(agent_memory.suspicion, %(sus)s),
                   notes = (CASE WHEN jsonb_array_length(agent_memory.notes) >= 8
                                 THEN agent_memory.notes - 0 ELSE agent_memory.notes END) || %(n)s,
                   updated_at = now()
               RETURNING attempts, suspicion""",
            {"s": session_id, "a": agent_id, "sus": max(0.0, min(1.0, suspicion)), "n": Jsonb([note[:200]])},
        ).fetchone()


def record_attack(session_id: str, preset: str | None, blocked: int, left_would: int, right_settled: int, stars: int) -> None:
    with db.pool().connection() as conn:
        conn.execute(
            """UPDATE leaderboard SET attempts = attempts + 1, blocked_rows = blocked_rows + %(b)s,
                   left_would_pay_cents = left_would_pay_cents + %(l)s,
                   right_settled_cents = right_settled_cents + %(r)s,
                   max_wanted_stars = GREATEST(max_wanted_stars, %(st)s),
                   best_preset = CASE WHEN %(b)s >= best_preset_blocked THEN %(p)s ELSE best_preset END,
                   best_preset_blocked = GREATEST(best_preset_blocked, %(b)s),
                   updated_at = now()
               WHERE session_id = %(s)s""",
            {"s": session_id, "b": blocked, "l": left_would, "r": right_settled, "st": stars, "p": preset or "free_text"},
        )


_LB = """
SELECT rank() OVER (ORDER BY blocked_rows DESC, attempts DESC, created_at) AS rank,
       session_id, alias, attempts, blocked_rows, left_would_pay_cents, right_settled_cents, max_wanted_stars, best_preset
FROM leaderboard WHERE attempts > 0
"""


def _entry(r: dict) -> dict:
    return {k: r[k] for k in ("rank", "alias", "attempts", "blocked_rows", "left_would_pay_cents",
                              "right_settled_cents", "max_wanted_stars", "best_preset")}


def leaderboard(limit: int = 20) -> list[dict]:
    with db.pool().connection() as conn:
        rows = conn.execute(_LB + " ORDER BY rank LIMIT %s", (max(1, min(100, limit)),)).fetchall()
    return [_entry(r) for r in rows]


# Constant SQL text (no interpolation): _LB is a module constant and session_id is a bound parameter.
_POSTER = "SELECT * FROM (" + _LB + ") t WHERE session_id = %s"


def reset_suspicion(session_id: str) -> None:
    """Called after a 5-star bust: the session's heat resets, attempts and notes are kept."""
    with db.pool().connection() as conn:
        conn.execute("UPDATE agent_memory SET suspicion = 0, updated_at = now() WHERE session_id = %s", (session_id,))


def poster(session_id: str) -> dict | None:
    with db.pool().connection() as conn:
        r = conn.execute(_POSTER, (session_id,)).fetchone()
        if r is None:
            base = conn.execute("SELECT alias FROM leaderboard WHERE session_id = %s", (session_id,)).fetchone()
            if base is None:
                return None
            r = {"rank": None, "alias": base["alias"], "attempts": 0, "blocked_rows": 0, "left_would_pay_cents": 0,
                 "right_settled_cents": 0, "max_wanted_stars": 0, "best_preset": None}
    e = _entry(r)
    rank = r["rank"]
    e["rank"] = rank or 0
    headline = (f"WANTED: {e['alias']}. {e['attempts']} heist attempt(s), {e['blocked_rows']} row(s) stopped by the vault"
                + (f", {e['max_wanted_stars']} star(s)" if e["max_wanted_stars"] else ""))
    return {"alias": e["alias"], "rank": rank, "stats": e, "headline": headline}


def notes_list(mem_row: dict | None) -> list[str]:
    if not mem_row:
        return []
    n = mem_row["notes"]
    return n if isinstance(n, list) else json.loads(n)
