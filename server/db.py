from __future__ import annotations

import time

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from db.migrate import migrate
from db.pg import database_url
from db.seed import seed

_pool: ConnectionPool | None = None


def init_db(reseed: bool = True) -> dict:
    """Start (or connect to) Postgres, apply migrations, ensure seed rows exist."""
    global _pool
    url = database_url()
    _pool = ConnectionPool(url, min_size=2, max_size=20, kwargs={"row_factory": dict_row}, open=True)
    with _pool.connection() as conn:
        conn.autocommit = True
        applied = migrate(conn)
        has_seed = conn.execute("SELECT count(*) AS n FROM vendor_keys").fetchone()["n"] > 0
        seeded = seed(conn) if (reseed or not has_seed) else None
        conn.autocommit = False
    return {"migrations_applied": applied, "seed": seeded, "url_host": url.split("@")[-1]}


def pool() -> ConnectionPool:
    assert _pool is not None, "init_db() not called"
    return _pool


def ping() -> tuple[bool, float | None, str | None]:
    t = time.perf_counter()
    try:
        with pool().connection() as conn:
            conn.execute("SELECT 1")
        return True, round((time.perf_counter() - t) * 1000, 3), None
    except Exception as e:  # noqa: BLE001
        return False, None, type(e).__name__


def close() -> None:
    if _pool is not None:
        _pool.close()
