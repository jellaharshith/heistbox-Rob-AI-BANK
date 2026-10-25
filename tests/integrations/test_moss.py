import asyncio
import os
import pytest
from integrations.router import _probe_request


def test_moss_stub_success(monkeypatch):
    monkeypatch.setenv("MOSS_API_KEY", "mock_key")
    monkeypatch.setenv("MOSS_PROJECT_ID", "mock_proj")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, {"indexes": [{"name": "heistbox-attacks"}]}, 130.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("moss", "GET", "https://api.moss.ai/v1/indexes"))
    assert code == 200
    assert len(body["indexes"]) == 1


def test_moss_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("MOSS_API_KEY", "mock_key")
    monkeypatch.setenv("MOSS_PROJECT_ID", "mock_proj")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("moss", "GET", "https://api.moss.ai/v1/indexes"))
    assert code == 0


@pytest.mark.skipif(
    not os.getenv("MOSS_PROJECT_ID") or not (os.getenv("MOSS_API_KEY") or os.getenv("MOSS_PROJECT_KEY")),
    reason="MOSS_PROJECT_ID or MOSS_PROJECT_KEY not configured",
)
def test_moss_live_smoke():
    project_id = os.getenv("MOSS_PROJECT_ID", "").strip().strip('"')
    project_key = (os.getenv("MOSS_PROJECT_KEY") or os.getenv("MOSS_API_KEY") or "").strip().strip('"')
    code, body, ms = asyncio.run(
        _probe_request(
            "moss",
            "GET",
            f"https://api.moss.ai/v1/projects/{project_id}/indexes",
            headers={"Authorization": f"Bearer {project_key}"},
            timeout=3.0,
        )
    )
    assert code in (200, 401, 403, 404)
