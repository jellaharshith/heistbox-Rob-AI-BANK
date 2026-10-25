"""Routes the pre-3D app (main.py, port 8000) serves, defined once and mounted by both apps.

main.py and server/app.py each call `mount_legacy(app, port=...)`, so the kernel (/api/kernel, /kernel),
the integrations router (/api/integrations, /integrations), the wanted-poster card routes and the
/health + / banner exist in exactly one place. Startup work lives in `warm_kernel` / `warm_moss`, which
each app calls from its own startup hook.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, FastAPI, HTTPException  # noqa: E402

from kernel.db_gate import get_db, router as kernel_router  # noqa: E402
from shared.models import CRSReport, WantedPosterCard, X402Receipt  # noqa: E402

wanted_router = APIRouter()


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


# Registered before the integrations router, so this handler answers /wanted/{id} (same precedence main.py always had).
@wanted_router.get("/api/integrations/wanted/{poster_id}", response_model=WantedPosterCard, tags=["integrations"])
@wanted_router.get("/integrations/wanted/{poster_id}", response_model=WantedPosterCard, tags=["integrations"])
async def get_wanted_poster_by_id(poster_id: str) -> Any:
    try:
        from integrations.router import _POSTER_STORE

        if poster_id in _POSTER_STORE:
            return _POSTER_STORE[poster_id]
        from shared.poster_store import load_poster
        saved = load_poster(poster_id)
        if saved:
            return saved
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Poster not found")


def _mount_integrations(app: FastAPI) -> None:
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
        detail = str(exc)

        @app.get("/api/integrations/status")
        def integrations_fallback_status() -> dict[str, Any]:
            return {"status": "fallback_active", "detail": detail}


def mount_legacy(app: FastAPI, port: int = 8000) -> None:
    """Mount every route main.py has always served onto `app`."""
    app.include_router(kernel_router, prefix="/api/kernel")
    app.include_router(kernel_router, prefix="/kernel")
    app.include_router(wanted_router)
    _mount_integrations(app)

    @app.get("/health")
    @app.get("/")
    def health_check() -> dict[str, Any]:
        return {
            "service": "HeistBox Unified FastAPI Kernel + Integrations",
            "status": "ONLINE",
            "port": port,
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
                "POST /api/integrations/remix-poster",
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


def warm_kernel() -> None:
    """Pre-warm and seed the kernel's SQLite vault, then load HeistGuard-LoRA (its first inference costs ~2.3s)."""
    get_db()
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


def warm_moss() -> asyncio.Task:
    """Download the Moss attack index in the background so the first moss-deception query takes ms, not seconds."""

    async def warm() -> None:
        try:
            from integrations.router import moss_attack_index

            await moss_attack_index()
        except Exception as exc:  # Moss not configured / index missing: the endpoint reports it per request.
            print(f"[startup] Moss index not warmed: {exc}")

    return asyncio.create_task(warm())
