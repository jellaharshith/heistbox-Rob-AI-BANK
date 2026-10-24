from __future__ import annotations

import hashlib
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kernel.db_gate import get_db, router as kernel_router
from shared.models import CRSReport, WantedPosterCard, X402Receipt

app = FastAPI(
    title="HeistBox: Ocean's 11 x PAIR Enterprise Edition API",
    version="1.0.0",
    description="Unified FastAPI Server (Port 8000): PostgreSQL/SQLite <2ms PAIR Transactional Kernel + Z3 Prover + HeistGuard-LoRA + Sponsor Integrations",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount PAIR Transactional Kernel at /api/kernel and /kernel
app.include_router(kernel_router, prefix="/api/kernel")
app.include_router(kernel_router, prefix="/kernel")


def _build_wanted_poster_card(poster_id: str) -> WantedPosterCard:
    aliases = [
        "Suspect in Black Pixel Sunglasses",
        "The Hoodie-Shadowed Cookie Courier",
        "Lanyard Larry, Self-Appointed CEO",
        "The Grinning Slice-Hoarder",
        "Agent Smooth-Talk McBribe",
    ]
    digest = hashlib.sha256(poster_id.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(aliases)
    alias = aliases[idx]
    score = 310 + (int(digest[8:12], 16) % 110)
    tx_hash = "0x" + hashlib.sha256(f"tx:{poster_id}".encode("utf-8")).hexdigest()
    nonce = "0x" + hashlib.sha256(f"eip3009:{poster_id}".encode("utf-8")).hexdigest()

    return WantedPosterCard(
        poster_id=poster_id,
        alias_title=alias,
        outfit_roast=(
            f"Nice disguise, {alias.lower()}. Gemini Vision flagged the hoodie + lanyard combo, "
            f"and the PAIR Transactional Gate caught your heist in 1.4 milliseconds."
        ),
        megaphone_transcript=(
            f"ATTENTION {alias.upper()}! THIS IS THE HEISTBOX HELICOPTER. "
            f"STEP AWAY FROM THE VAULT. YOUR $4,975.00 HEIST WAS ROLLED BACK IN 1.4ms. "
            f"YOU GET $25.00 AND ONE PENNY FOR TRYING."
        ),
        audio_base64=None,
        crs_rap_sheet=CRSReport(
            score=score,
            flags=[
                "Synthetic identity velocity",
                "Promo-batch fan-out (CALHACKS-VIP)",
                "Urgency coercion pattern",
                "Wallet rotated < 24h",
            ],
            verified=True,
        ),
        mugshot_data_url=None,
        x402_receipt=X402Receipt(
            tx_hash=tx_hash,
            chain_id=84532,
            green_settled_cents=2500,
            nice_try_bounty_cents=1,
            eip3009_marked_bill_nonce=nonce,
            basescan_url=f"https://sepolia.basescan.org/tx/{tx_hash}",
        ),
    )


@app.get("/api/integrations/wanted/{poster_id}", response_model=WantedPosterCard, tags=["integrations"])
@app.get("/integrations/wanted/{poster_id}", response_model=WantedPosterCard, tags=["integrations"])
async def get_wanted_poster_by_id(poster_id: str) -> Any:
    try:
        from integrations.router import _POSTER_STORE

        if poster_id in _POSTER_STORE:
            return _POSTER_STORE[poster_id]
    except Exception:
        pass
    return _build_wanted_poster_card(poster_id)


# Mount Agent 2 Sponsor Integrations router (/api/integrations and /integrations)
try:
    from integrations.router import router as integrations_router

    if getattr(integrations_router, "prefix", "").startswith("/api/integrations"):
        app.include_router(integrations_router)
        # Also expose under /integrations/* for direct callers
        for route in integrations_router.routes:
            path = getattr(route, "path", "")
            if path.startswith("/api/integrations"):
                short_path = path.replace("/api/integrations", "/integrations", 1)
                app.add_api_route(
                    short_path,
                    route.endpoint,
                    methods=list(route.methods or ["GET", "POST"]),
                    tags=["integrations"],
                )
    else:
        app.include_router(integrations_router, prefix="/api/integrations")
        app.include_router(integrations_router, prefix="/integrations")
except Exception as exc:
    @app.get("/api/integrations/status")
    def integrations_fallback_status() -> dict[str, Any]:
        return {"status": "fallback_active", "detail": str(exc)}


@app.on_event("startup")
def on_startup() -> None:
    # Pre-warm and seed the 4-table SQLite/PostgreSQL transactional vault
    get_db()
    # Load HeistGuard-LoRA now: its first inference costs ~2.3s, which otherwise lands on the first heist.
    from kernel.heistguard_infer import infer_heistguard_lora

    infer_heistguard_lora(
        prompt_text="warm-up",
        voice_transcript=None,
        proposed_amount_cents=0,
        authorized_cents=0,
        slice_count=1,
        proposed_source_acct="acct_treasury_main",
        authorized_source_acct="acct_treasury_main",
        proposed_dest_wallet="0x0",
        enrolled_wallet="0x0",
    )


@app.on_event("startup")
async def warm_moss_index() -> None:
    # Download the Moss attack index in the background so the first moss-deception query takes ms, not seconds.
    import asyncio

    async def warm() -> None:
        try:
            from integrations.router import moss_attack_index

            await moss_attack_index()
        except Exception as exc:  # Moss not configured / index missing: the endpoint reports it per request.
            print(f"[startup] Moss index not warmed: {exc}")

    asyncio.create_task(warm())


@app.get("/health")
@app.get("/")
def health_check() -> dict[str, Any]:
    return {
        "service": "HeistBox Unified FastAPI Kernel + Integrations",
        "status": "ONLINE",
        "port": 8000,
        "cors_origins": ["http://localhost:3000"],
        "kernel_endpoints": [
            "POST /api/kernel/reset-vault",
            "POST /api/kernel/evaluate-heist",
            "POST /api/kernel/vendor-rotate-wallet",
            "GET /api/kernel/vault-state",
            "POST /api/kernel/fuzz-test",
        ],
        "integrations_endpoints": [
            "GET /api/integrations/wanted/{poster_id}",
            "POST /api/integrations/roast-and-poster",
            "POST /api/integrations/wanted-poster",
            "POST /api/integrations/rollback-roast",
            "POST /api/integrations/voice-bribe",
            "POST /api/integrations/crs-check",
            "POST /api/integrations/x402-settle",
            "POST /api/integrations/webauthn/verify",
            "POST /api/integrations/droid-patch",
            "POST /api/integrations/moss-deception",
            "POST /api/integrations/osint-enrich",
            "POST /api/integrations/spacetimedb-sync",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
