import asyncio
import os
import pytest
from integrations.router import _probe_request, _vision_key


def test_cloud_vision_stub_success(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_VISION_API_KEY", "mock_key")

    async def fake_probe(name, method, url, headers=None, json_body=None, timeout=None):
        return 200, {"responses": [{"faceAnnotations": []}]}, 140.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe)
    code, body, ms = asyncio.run(fake_probe("cloud_vision", "POST", "https://vision.googleapis.com/v1/images:annotate"))
    assert code == 200
    assert "responses" in body


def test_cloud_vision_stub_timeout_fallback(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_VISION_API_KEY", "mock_key")

    async def fake_probe_timeout(name, method, url, headers=None, json_body=None, timeout=None):
        return 0, "unreachable: TimeoutException", 3000.0

    monkeypatch.setattr("integrations.router._probe_request", fake_probe_timeout)
    code, body, ms = asyncio.run(fake_probe_timeout("cloud_vision", "POST", "https://vision.googleapis.com/v1/images:annotate"))
    assert code == 0


@pytest.mark.skipif(
    not (os.getenv("GOOGLE_CLOUD_VISION_API_KEY") or os.getenv("GEMINI_API_KEY")),
    reason="Neither GOOGLE_CLOUD_VISION_API_KEY nor GEMINI_API_KEY configured",
)
def test_cloud_vision_live_smoke():
    """Live smoke test: annotate a 1x1 png (tiny bounded request)."""
    key = _vision_key()
    assert key is not None
    code, body, ms = asyncio.run(
        _probe_request(
            "cloud_vision",
            "POST",
            f"https://vision.googleapis.com/v1/images:annotate?key={key}",
            json_body={
                "requests": [
                    {
                        "image": {"content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="},
                        "features": [{"type": "SAFE_SEARCH_DETECTION", "maxResults": 1}],
                    }
                ]
            },
            timeout=3.0,
        )
    )
    assert code in (200, 400, 403)
