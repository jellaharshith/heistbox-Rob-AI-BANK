"""Apply db/migrations/*.sql in order, then (optionally) seed.

    python -m db.migrate            # migrate only
    python -m db.migrate --seed     # migrate + reseed demo data (idempotent)
    python -m db.migrate --reset    # drop everything, migrate, seed
"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from db.pg import database_url

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def migrate(conn: psycopg.Connection) -> list[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
    applied = []
    for f in sorted(MIGRATIONS.glob("*.sql")):
        if f.stem in done:
            continue
        with conn.transaction():
            conn.execute(f.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (f.stem,))
        applied.append(f.stem)
    return applied


def reset(conn: psycopg.Connection) -> None:
    with conn.transaction():
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


def main(argv: list[str]) -> None:
    url = database_url()
    with psycopg.connect(url, autocommit=True) as conn:
        if "--reset" in argv:
            reset(conn)
            print("schema dropped")
        applied = migrate(conn)
        print("migrations applied:", applied or "none (up to date)")
        if "--seed" in argv or "--reset" in argv:
            from db.seed import seed

            print("seed:", seed(conn))
    print("database:", url.split("@")[-1])


if __name__ == "__main__":
    main(sys.argv[1:])
