import asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from integrations.router import router


def test_status_endpoint_shape():
    app = FastAPI()
    app.include_router(router)

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/integrations/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "services" in data
            assert "providers" in data
            assert "generated_at" in data
            assert len(data["services"]) == 22

            # Every service must match uniform shape
            for svc_id, svc in data["services"].items():
                assert "state" in svc
                assert "latency_ms" in svc
                assert "detail" in svc
                assert "code" in svc
                assert "label" in svc
                assert "fallback" in svc
                assert svc["state"] in ("live", "offline", "missing_key", "unverified", "local", "dry_run")

            # Wajo status
            w_resp = await client.get("/api/integrations/wajo/status")
            assert w_resp.status_code == 200
            w_data = w_resp.json()
            assert "state" in w_data
            assert "latency_ms" in w_data
            assert "detail" in w_data
            assert "configured" in w_data
            assert "cfo_phone_masked" in w_data

            # Wajo audit
            a_resp = await client.get("/api/integrations/wajo/audit?limit=10")
            assert a_resp.status_code == 200
            a_data = a_resp.json()
            assert "entries" in a_data
            assert "count" in a_data
            assert "max_kept" in a_data

    asyncio.run(_run())
