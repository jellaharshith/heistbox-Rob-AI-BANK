"""Resolve a Postgres URL: HEISTBOX_DATABASE_URL if set, else an embedded Postgres 16 (pgserver) under db/pgdata."""
from __future__ import annotations

import os
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
PGDATA = Path(os.environ.get("HEISTBOX_PGDATA", DB_DIR / "pgdata"))

_server = None


def database_url() -> str:
    url = os.environ.get("HEISTBOX_DATABASE_URL", "").strip()
    if url:
        return url
    global _server
    if _server is None:
        import pgserver  # bundled Postgres binaries; no system install needed

        PGDATA.mkdir(parents=True, exist_ok=True)
        # cleanup_mode=None keeps the server running across processes so tests and the server share it
        _server = pgserver.get_server(str(PGDATA), cleanup_mode=None)
    return _server.get_uri()
