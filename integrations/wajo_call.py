"""Wajo.ai voice escalation client.

Wajo has no REST "dispatch a call" endpoint. Calls are placed by asking the user's Fo agent through Wajo's MCP
server: JSON-RPC `tools/call` of `ask_fo` on https://mcp.api.wajo.ai/fo, authenticated with a `wak_` key in
X-API-Key (https://wajo.ai/docs/mcp-server.md). Fo acts from the key owner's Wajo account.
"""

import json
import logging
import os
import threading
import time
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_WAJO_MCP_URL = "https://mcp.api.wajo.ai/fo"
_LAST_LIVE_CALL = {"at": 0.0}
_CALL_LOCK = threading.Lock()


def _callback_url() -> str:
    return os.getenv(
        "CHALLENGE_CALLBACK_URL",
        "http://localhost:8000/api/integrations/webauthn/verify",
    )


def settle_url(settlement_hash: str) -> str:
    """Phone-openable page that signs this exact settlement with Face ID (SETTLE_PAGE_URL for a tunnel)."""
    base = os.getenv("SETTLE_PAGE_URL", "http://localhost:3000/settle").rstrip("/")
    return f"{base}?settlement={settlement_hash}"


def _usd(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def wajo_api_key() -> str | None:
    # The documented name is uppercase; retain compatibility with this repo's
    # existing lowercase `.env` entry as well.
    return os.getenv("WAJO_API_KEY") or os.getenv("wajo_api_key")


def wajo_mcp_url() -> str:
    return os.getenv("WAJO_MCP_URL") or DEFAULT_WAJO_MCP_URL


def _cooldown_s() -> float:
    try:
        return max(0.0, float(os.getenv("WAJO_MIN_CALL_INTERVAL_S", "300")))
    except ValueError:
        return 300.0


async def mcp_tool_call(tool: str, arguments: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    """One stateless MCP tools/call; returns the JSON-RPC `result` or raises with the server's error."""
    api_key = wajo_api_key()
    if not api_key:
        raise RuntimeError("WAJO_API_KEY is not configured")
    body = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            wajo_mcp_url(),
            json=body,
            headers={"X-API-Key": api_key, "Accept": "application/json, text/event-stream"},
        )
    if response.status_code != 200:
        raise RuntimeError(f"Wajo MCP HTTP {response.status_code}: {response.text[:200]}")
    # Streamable HTTP answers with either plain JSON or an SSE stream whose data lines carry the JSON-RPC message.
    text = response.text.strip()
    data_lines = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    message = json.loads(data_lines[-1] if data_lines else text)
    if "error" in message:
        raise RuntimeError(f"Wajo MCP error: {message['error']}")
    result = message.get("result") or {}
    if result.get("isError"):
        detail = " ".join(c.get("text", "") for c in result.get("content", []) if isinstance(c, dict))
        raise RuntimeError(f"Wajo tool {tool} failed: {detail[:200]}")
    return result


async def trigger_wajo_escalation(
    red_cents: int,
    green_cents: int,
    settlement_hash: str,
    intent_hash: str,
) -> dict[str, Any]:
    """Ask Fo to phone the CFO, or return a safe dry-run result."""
    to = os.getenv("CFO_ALERT_PHONE_NUMBER")
    link = settle_url(settlement_hash)
    script = (
        f"HeistBox Security Alert: an unauthorized transfer of {_usd(red_cents)} was blocked. "
        f"A genuine {_usd(green_cents)} refund is held in escrow. Open the HeistBox settle link "
        "on your phone and approve that exact amount with Face ID."
    )
    payload = {
        "to": to,
        "script": script,
        "callback_url": _callback_url(),
        "settle_url": link,
        "metadata": {"intent_hash": intent_hash, "settlement_hash": settlement_hash},
        "fo_message": (
            f"Please place a phone call now to {to} and read them this message: \"{script}\" "
            f"Then text the same number this approval link: {link} . "
            "This is only a notification: do not make any purchase or payment."
        ),
    }

    def dry_run(reason: str) -> dict[str, Any]:
        logger.warning("%s; simulating dry-run voice dispatch", reason)
        return {"dry_run": True, "reason": reason, "payload": payload}

    if not wajo_api_key():
        return dry_run("WAJO_API_KEY is not configured")
    if not to:
        return dry_run("CFO_ALERT_PHONE_NUMBER is not configured")
    if os.getenv("PYTEST_CURRENT_TEST"):
        return dry_run("running under pytest; never phones a real number")
    # Different heists have different intents, so per-intent dedupe alone could still ring the CFO in a loop.
    with _CALL_LOCK:
        now = time.monotonic()
        if _LAST_LIVE_CALL["at"] and now - _LAST_LIVE_CALL["at"] < _cooldown_s():
            return dry_run(f"a live call was placed under {_cooldown_s():.0f}s ago (WAJO_MIN_CALL_INTERVAL_S)")
        _LAST_LIVE_CALL["at"] = now

    try:
        result = await mcp_tool_call("ask_fo", {"message": payload["fo_message"], "newConversation": True})
    except Exception as exc:
        logger.exception("Wajo.ai escalation dispatch failed")
        return {"dry_run": False, "payload": payload, "error": f"dispatch_failed: {exc}"}
    status = (result.get("structuredContent") or {}).get("status", "unknown")
    logger.info("Wajo Fo accepted the CFO call request (status=%s)", status)
    return {"dry_run": False, "payload": payload, "fo_status": status}
