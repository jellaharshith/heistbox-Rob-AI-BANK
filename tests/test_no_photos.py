"""
Assertion test: photos never reach the server.

1. POST /api/session and /api/attack reject any field carrying a data: URI.
2. Both endpoints reject bodies over 10 KB.
3. No migration defines an image-like column or a binary (BYTEA) column.
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server import app as app_module  # noqa: E402

# Not used as a context manager, so the lifespan (Postgres, room loop) never starts.
client = TestClient(app_module.app)

ENDPOINTS = ["/api/session", "/api/attack"]
PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()
DATA_URIS = [
    f"data:image/png;base64,{PNG_B64}",
    f"DATA:image/jpeg;base64,{PNG_B64}",
    "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>",
    f"data:application/octet-stream;base64,{PNG_B64}",
]


def _body(path: str, field: str, value) -> dict:
    base = {"alias": "Ghost"} if path == "/api/session" else {"session": "s_x", "text": "hi"}
    base[field] = value
    return base


@pytest.fixture
def handlers_not_called(monkeypatch):
    """Fail loudly if a rejected request ever reaches a handler."""
    def boom(*_a, **_k):
        raise AssertionError("handler reached with image data")
    monkeypatch.setattr(app_module.store, "create_session", boom)
    monkeypatch.setattr(app_module, "run_scenario", boom)


@pytest.mark.parametrize("path", ENDPOINTS)
@pytest.mark.parametrize("uri", DATA_URIS)
@pytest.mark.parametrize("field", ["alias", "text", "mask", "photo", "avatar"])
def test_data_uri_rejected(path, uri, field, handlers_not_called):
    r = client.post(path, json=_body(path, field, uri), headers={"Authorization": "Bearer t"})
    assert r.status_code in (413, 422), r.text


@pytest.mark.parametrize("path", ENDPOINTS)
def test_nested_data_uri_rejected(path, handlers_not_called):
    r = client.post(path, json=_body(path, "extra", {"images": [DATA_URIS[0]]}))
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("path", ENDPOINTS)
def test_body_over_10kb_rejected(path, handlers_not_called):
    r = client.post(path, json=_body(path, "blob", "A" * (10 * 1024 + 1)))
    assert r.status_code == 413, r.text


@pytest.mark.parametrize("path", ENDPOINTS)
def test_raw_non_json_image_rejected(path, handlers_not_called):
    r = client.post(path, content=b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024),
                    headers={"Content-Type": "image/png"})
    assert r.status_code == 413, r.text


def test_small_clean_session_still_allowed(monkeypatch):
    monkeypatch.setattr(app_module.store, "create_session", lambda alias: {"alias": alias})
    r = client.post("/api/session", json={"alias": "Ghost"})
    assert r.status_code == 200 and r.json() == {"alias": "Ghost"}


# Matched against underscore-separated name tokens so e.g. "suspicion" doesn't trip on "pic".
IMAGE_COLUMN = re.compile(
    r"(?:^|_)(?:image|img|photo|picture|pic|avatar|selfie|face|portrait|thumbnail|thumb|jpe?g|png|mugshot)s?(?:_|$)",
    re.I,
)


def _columns(sql: str):
    """Yield (table, column, type) for every CREATE TABLE / ADD COLUMN in the migration text."""
    sql = re.sub(r"--[^\n]*", "", sql)
    for m in re.finditer(r"CREATE TABLE(?: IF NOT EXISTS)?\s+(\w+)\s*\((.*?)\);", sql, re.S | re.I):
        table, body = m.group(1), m.group(2)
        for line in re.split(r",\s*\n", body):
            parts = line.split()
            if len(parts) >= 2 and parts[0].upper() not in {"CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "CHECK"}:
                yield table, parts[0], parts[1]
    for m in re.finditer(r"ALTER TABLE\s+(\w+)\s+ADD COLUMN(?: IF NOT EXISTS)?\s+(\w+)\s+(\w+)", sql, re.I):
        yield m.group(1), m.group(2), m.group(3)


def test_schema_has_no_image_column():
    migrations = sorted((PROJECT_ROOT / "db" / "migrations").glob("*.sql"))
    assert migrations, "no migrations found"
    cols = [c for f in migrations for c in _columns(f.read_text(encoding="utf-8"))]
    assert cols, "parsed no columns; parser is broken"
    offenders = [c for c in cols if IMAGE_COLUMN.search(c[1]) or c[2].upper() in {"BYTEA", "BLOB", "OID"}]
    assert not offenders, f"image-like columns in schema: {offenders}"
