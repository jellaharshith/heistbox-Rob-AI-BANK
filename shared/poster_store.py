"""Persist public poster cards and server-recorded defense reports across restarts."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("HEISTBOX_POSTER_DB", Path(__file__).resolve().parents[1] / "db" / "poster_reports.sqlite3"))


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=5)
    connection.execute("CREATE TABLE IF NOT EXISTS public_artifacts (kind TEXT, id TEXT, payload TEXT NOT NULL, PRIMARY KEY(kind, id))")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def put(kind: str, identifier: str, payload: dict):
    with _connect() as connection:
        connection.execute("INSERT OR REPLACE INTO public_artifacts(kind,id,payload) VALUES(?,?,?)",
                           (kind, identifier, json.dumps(payload)))


def get(kind: str, identifier: str):
    with _connect() as connection:
        row = connection.execute("SELECT payload FROM public_artifacts WHERE kind=? AND id=?", (kind, identifier)).fetchone()
    return json.loads(row[0]) if row else None


def record_defense(request, verdict):
    """Store a deliberately limited view, excluding signing challenges and camera data."""
    pair = verdict.heistbox_pair
    tool = verdict.extracted_tool_call or {}
    report = {
        "evidence_kind": "server-recorded",
        "request_id": verdict.request_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "prompt_text": request.prompt_text,
        "verdict_code": verdict.verdict_code,
        "busted": verdict.busted,
        "blocked_cents": pair.red_stripped_cents,
        "preserved_cents": pair.green_repaired_cents,
        "unauthorized_paid_cents": pair.robbed_cents,
        "rows_checked": pair.touched_rows_total,
        "rows_blocked": pair.unauthorized_rows_rolled_back,
        "gate_ms": verdict.clocks.postgres_pair_ms,
        "proof_status": pair.z3_proof.status,
        "proof_checks": pair.z3_proof.theorems_verified,
        "tainted_spans": pair.heistguard_lora.tainted_spans,
        "deception_probability": pair.heistguard_lora.deception_prob,
        "tool_name": tool.get("tool_name", "proposed transaction"),
        "parser_backend": tool.get("parser_backend", "unreported"),
        "proposed_source": tool.get("arguments", {}).get("source_acct", ""),
        "proposed_destination": tool.get("arguments", {}).get("dest_wallet", ""),
        "naive_exposure_cents": verdict.left_vault_llm_judge.robbed_cents,
        "firewall_froze_refund": verdict.center_firewall.honest_refund_frozen,
    }
    put("defense", verdict.request_id, report)


def load_poster(identifier: str):
    return get("poster", identifier)


def save_poster(card: dict):
    put("poster", card["poster_id"], card)
