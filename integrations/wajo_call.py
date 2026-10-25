"""Wajo.ai voice escalation client: the ONLY module that talks to Wajo.

Wajo has no REST "dispatch a call" endpoint. Calls are placed by asking the user's Fo agent through Wajo's MCP
server: JSON-RPC `tools/call` of `ask_fo` on https://mcp.api.wajo.ai/fo, authenticated with a `wak_` key in
X-API-Key (https://wajo.ai/docs/mcp-server.md). Fo acts from the key owner's Wajo account.

Guarantees the game relies on:
- Every request is bounded by WAJO_TIMEOUT_S (default 3 s) and nothing here ever raises to the caller: a slow,
  failing or unconfigured Wajo degrades to a dry run / failure record, never to a broken heist.
- Every escalation attempt (live, dry-run, cooldown, failure, timeout) is recorded in an in-memory audit log
  (`audit_entries()`), exposed to the browser only through GET /api/integrations/wajo/audit.
- Audit and status summaries never contain the API key, and the CFO phone number is masked to its last 4 digits.
- The status probe uses Fo's read-only `list_fo_conversations`; it never calls `ask_fo` (which phones a person).
"""

import asyncio
import hashlib
import itertools
import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_WAJO_MCP_URL = "https://mcp.api.wajo.ai/fo"
DEFAULT_TIMEOUT_S = 40.0
PROBE_TIMEOUT_S = 3.0
STATUS_CACHE_S = 20.0
AUDIT_MAX = 100
_LAST_LIVE_CALL = {"at": 0.0}
_CALL_LOCK = threading.Lock()
_AUDIT: deque = deque(maxlen=AUDIT_MAX)
_AUDIT_SEQ = itertools.count(1)
_AUDIT_LOCK = threading.Lock()
# Most recent Wajo request of any kind (status probe or escalation), for GET /wajo/status.
_LAST_EVENT: dict[str, Any] = {}
_STATUS_CACHE: dict[str, Any] = {}


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


def wajo_timeout_s() -> float:
    try:
        value = float(os.getenv("WAJO_TIMEOUT_S", str(DEFAULT_TIMEOUT_S)))
    except ValueError:
        return DEFAULT_TIMEOUT_S
    return value if 0 < value <= 60 else DEFAULT_TIMEOUT_S


def _cooldown_s() -> float:
    try:
        return max(0.0, float(os.getenv("WAJO_MIN_CALL_INTERVAL_S", "30")))
    except ValueError:
        return 30.0


def _forced_dry_run() -> bool:
    return os.getenv("WAJO_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}


def mask_phone(number: str | None) -> str:
    digits = "".join(ch for ch in str(number or "") if ch.isdigit())
    return f"***{digits[-4:]}" if len(digits) >= 4 else "(unset)"


def _redact(text: Any) -> str:
    """Strip the API key and the CFO phone number from anything that may reach logs or the browser."""
    out = str(text)
    for secret in (wajo_api_key(), os.getenv("CFO_ALERT_PHONE_NUMBER")):
        if secret and len(secret) >= 4:
            out = out.replace(secret, "***")
    return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _record(kind: str, outcome: str, request_summary: str, response_summary: str, latency_ms: float) -> dict[str, Any]:
    entry = {
        "ts": _now_iso(),
        "kind": kind,
        "outcome": outcome,
        "request_summary": _redact(request_summary)[:300],
        "response_summary": _redact(response_summary)[:300],
        "latency_ms": round(float(latency_ms), 1),
    }
    with _AUDIT_LOCK:
        if kind == "escalation":
            entry = {"id": next(_AUDIT_SEQ), **entry}
            _AUDIT.append(entry)
        _LAST_EVENT.clear()
        _LAST_EVENT.update(entry)
    return entry


def audit_entries(limit: int = AUDIT_MAX) -> list[dict[str, Any]]:
    """Escalation audit log, newest first."""
    with _AUDIT_LOCK:
        items = list(_AUDIT)
    return list(reversed(items))[: max(0, int(limit))]


def clear_audit() -> None:
    with _AUDIT_LOCK:
        _AUDIT.clear()
        _LAST_EVENT.clear()
    _STATUS_CACHE.clear()


async def mcp_tool_call(tool: str, arguments: dict[str, Any], *, timeout: float | None = None) -> dict[str, Any]:
    """One stateless MCP tools/call; returns the JSON-RPC `result` or raises with the server's error."""
    api_key = wajo_api_key()
    if not api_key:
        raise RuntimeError("WAJO_API_KEY is not configured")
    t = timeout if timeout is not None else wajo_timeout_s()
    body = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    async with httpx.AsyncClient(timeout=httpx.Timeout(t)) as client:
        response = await asyncio.wait_for(
            client.post(
                wajo_mcp_url(),
                json=body,
                headers={"X-API-Key": api_key, "Accept": "application/json, text/event-stream"},
            ),
            timeout=t + 0.5,
        )
    if response.status_code != 200:
        raise RuntimeError(f"Wajo MCP HTTP {response.status_code}: {_redact(response.text[:200])}")
    # Streamable HTTP answers with either plain JSON or an SSE stream whose data lines carry the JSON-RPC message.
    text = response.text.strip()
    data_lines = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    messages = [json.loads(line) for line in data_lines] if data_lines else [json.loads(text)]
    # SSE streams may end with a notification; use the response to our own request.
    message = next((item for item in messages if item.get("id") == body["id"]), None)
    if message is None:
        raise RuntimeError("Wajo MCP returned no matching JSON-RPC response")
    if "error" in message:
        raise RuntimeError(f"Wajo MCP error: {_redact(message['error'])}")
    result = message.get("result") or {}
    if result.get("isError"):
        detail = " ".join(c.get("text", "") for c in result.get("content", []) if isinstance(c, dict))
        raise RuntimeError(f"Wajo tool {tool} failed: {_redact(detail[:200])}")
    return result


def _error_text(exc: BaseException) -> str:
    if isinstance(exc, (asyncio.TimeoutError, httpx.TimeoutException)):
        return f"timeout after {wajo_timeout_s():g}s"
    return _redact(f"{type(exc).__name__}: {exc}")[:200]


def summarize_prompt_injection(prompt_text: str = "", judge_reason: str = "", mask_id: str = "") -> str:
    """Summarize the attacker's prompt injection or exploit strategy into a clear, concise sentence for the CFO phone call."""
    p_lower = (prompt_text or "").lower()
    m_lower = (mask_id or "").lower()

    if any(k in p_lower for k in ["drop ", "delete ", "union ", "select ", "truncate", "--", "/*"]) or "sql" in m_lower:
        return "The attacker attempted a SQL injection attack to tamper with database records and ledger balance constraints"
    if any(k in p_lower for k in ["ignore previous", "system prompt", "developer mode", "jailbreak", "unlocked", "override all rules"]):
        return "The attacker attempted a direct prompt injection jailbreak, instructing the banking agent to disregard core security policies"
    if any(k in p_lower for k in ["ceo", "cfo", "board", "executive", "urgent", "wire immediately", "controller"]) or "ceo" in m_lower or "phisher" in m_lower:
        return "The attacker used an executive impersonation attack, claiming urgent C-level authority to pressure staff into bypassing wire controls"
    if any(k in p_lower for k in ["pizza", "bribe", "donut", "tip", "for yourself", "goodwill"]) or "bribe" in m_lower:
        return "The attacker used social engineering and bribery manipulation against the branch teller to solicit an unauthorized wire"
    if any(k in p_lower for k in ["salami", "batch", "slice", "micro", "10x", "promo_batch"]) or "salami" in m_lower:
        return "The attacker attempted a salami-slicing exploit, subdividing unauthorized treasury drain requests across micro-batches"
    if any(k in p_lower for k in ["rotate wallet", "vendor", "swap wallet", "new wallet"]) or "vendor" in m_lower:
        return "The attacker attempted an unauthorized vendor wallet substitution attack to reroute honest settlement payouts"

    if judge_reason:
        clean = re.sub(r"^\[.*?\]\s*", "", judge_reason).strip()
        first_sent = clean.split(".")[0].strip()
        if len(first_sent) > 20:
            return f"Attack detected: {first_sent}"

    return "The attacker used social engineering prompt injection to manipulate payout authorizations"


async def trigger_wajo_escalation(
    red_cents: int,
    green_cents: int,
    settlement_hash: str,
    intent_hash: str,
    prompt_explanation: str | None = None,
) -> dict[str, Any]:
    """Ask Fo to phone the CFO, or return a safe dry-run result. Never raises; every attempt is audited."""
    started = time.perf_counter()
    to = os.getenv("CFO_ALERT_PHONE_NUMBER")
    link = settle_url(settlement_hash)
    explanation_clause = f" Attack analysis: {prompt_explanation.strip()}." if prompt_explanation and prompt_explanation.strip() else ""
    script = (
        f"This is an urgent security alert from the HeistBox banking defense system: "
        f"An unauthorized transaction of {_usd(red_cents)} was intercepted and blocked by the PAIR security airlock."
        f"{explanation_clause} "
        f"A genuine {_usd(green_cents)} refund is held in escrow. "
        "All vault reserves are secure. No action is needed and no money has moved."
    )
    metadata = {"intent_hash": intent_hash, "settlement_hash": settlement_hash}
    if prompt_explanation:
        metadata["prompt_explanation"] = prompt_explanation
    payload = {
        "to": to,
        "script": script,
        "callback_url": _callback_url(),
        "settle_url": link,
        "metadata": metadata,
        "fo_message": (
            f"Please place a phone call now to {to} and read them this message: \"{script}\" "
            f"Then text the same number this security dashboard link: {link} . "
            "This is only an authorized security notification: do not make any purchase or payment, and do not send anything else."
        ),
    }
    request_summary = (
        f"ask_fo: phone CFO {mask_phone(to)} and text the settle link; {_usd(red_cents)} blocked, "
        f"{_usd(green_cents)} held; settlement {str(settlement_hash)[:12]}"
    )

    def elapsed() -> float:
        return (time.perf_counter() - started) * 1000

    def dry_run(reason: str, outcome: str = "dry_run") -> dict[str, Any]:
        logger.warning("%s; simulating dry-run voice dispatch", reason)
        _record("escalation", outcome, request_summary, f"not sent: {reason}", elapsed())
        return {"dry_run": True, "reason": reason, "payload": payload}

    if not wajo_api_key():
        return dry_run("WAJO_API_KEY is not configured")
    if not to:
        return dry_run("CFO_ALERT_PHONE_NUMBER is not configured")
    if _forced_dry_run():
        return dry_run("WAJO_DRY_RUN is set")
    if os.getenv("PYTEST_CURRENT_TEST"):
        return dry_run("running under pytest; never phones a real number")
    # Different heists have different intents, so per-intent dedupe alone could still ring the CFO in a loop.
    with _CALL_LOCK:
        now = time.monotonic()
        if _LAST_LIVE_CALL["at"] and now - _LAST_LIVE_CALL["at"] < _cooldown_s():
            return dry_run(f"a live call was placed under {_cooldown_s():.0f}s ago (WAJO_MIN_CALL_INTERVAL_S)", "cooldown")
        _LAST_LIVE_CALL["at"] = now

    try:
        result = await mcp_tool_call("ask_fo", {"message": payload["fo_message"], "newConversation": True})
    except Exception as exc:  # noqa: BLE001 - Wajo must never break the heist
        timed_out = isinstance(exc, (asyncio.TimeoutError, httpx.TimeoutException))
        if not timed_out:
            # A definitive rejection did not place a call. Allow a corrected request.
            with _CALL_LOCK:
                if _LAST_LIVE_CALL["at"] == now:
                    _LAST_LIVE_CALL["at"] = 0.0
        error = _error_text(exc)
        logger.warning("Wajo.ai escalation dispatch failed: %s", error)
        note = " (the request may still have reached Fo)" if timed_out else ""
        _record("escalation", "timeout" if timed_out else "failure", request_summary, f"{error}{note}", elapsed())
        return {"dry_run": False, "payload": payload, "error": f"dispatch_failed: {error}"}
    status = (result.get("structuredContent") or {}).get("status", "unknown")
    logger.info("Wajo Fo accepted the CFO call request (status=%s)", status)
    _record("escalation", "live", request_summary, f"Fo accepted the call request (status={status})", elapsed())
    return {"dry_run": False, "payload": payload, "fo_status": status}


def _fingerprint() -> str:
    raw = "|".join([wajo_api_key() or "", os.getenv("CFO_ALERT_PHONE_NUMBER") or "", wajo_mcp_url(), str(_forced_dry_run())])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def probe(timeout: float | None = None) -> dict[str, Any]:
    """Read-only key check via Fo's list_fo_conversations. Returns {ok, code, latency_ms, detail}; never raises."""
    if not wajo_api_key():
        return {"ok": False, "code": "MISSING_KEY", "latency_ms": 0.0, "detail": "WAJO_API_KEY not set"}
    started = time.perf_counter()
    request_summary = "list_fo_conversations (read-only status probe)"
    try:
        await mcp_tool_call("list_fo_conversations", {}, timeout=timeout if timeout is not None else PROBE_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001
        text = _error_text(exc)
        code = "AUTH_ERROR" if ("401" in text or "invalid api key" in text.lower()) else "UNREACHABLE"
        latency = round((time.perf_counter() - started) * 1000, 1)
        _record("probe", "failure", request_summary, text, latency)
        return {"ok": False, "code": code, "latency_ms": latency, "detail": f"{wajo_mcp_url()}: {text}"}
    latency = round((time.perf_counter() - started) * 1000, 1)
    _record("probe", "live", request_summary, "key accepted", latency)
    return {"ok": True, "code": "LIVE", "latency_ms": latency, "detail": f"key accepted by {wajo_mcp_url()} (read-only probe)"}


_STATUS_LOCKS: dict[int, asyncio.Lock] = {}


async def status(*, fresh: bool = False) -> dict[str, Any]:
    """Browser-safe Wajo status: state live | offline | missing_key | dry_run, plus the last request/response."""
    loop_id = id(asyncio.get_running_loop())
    lock = _STATUS_LOCKS.setdefault(loop_id, asyncio.Lock())
    async with lock:  # concurrent callers (e.g. /status) share one probe
        return await _status(fresh=fresh)


async def _status(*, fresh: bool) -> dict[str, Any]:
    fp = _fingerprint()
    cached = _STATUS_CACHE.get("value")
    if not fresh and cached and _STATUS_CACHE.get("fp") == fp and time.monotonic() - _STATUS_CACHE.get("at", 0) < STATUS_CACHE_S:
        result = dict(cached)
    else:
        has_key = bool(wajo_api_key())
        has_phone = bool(os.getenv("CFO_ALERT_PHONE_NUMBER"))
        result_probe = await probe()
        if not has_key:
            state, detail = "missing_key", "WAJO_API_KEY not set; escalations are dry runs"
        elif not result_probe["ok"]:
            state, detail = "offline", f"{result_probe['code']}: {result_probe['detail']}; escalations fall back to dry-run records"
        elif not has_phone:
            state, detail = "dry_run", "key accepted, but CFO_ALERT_PHONE_NUMBER is not set; escalations are dry runs"
        elif _forced_dry_run():
            state, detail = "dry_run", "key accepted, WAJO_DRY_RUN is set; escalations are dry runs"
        else:
            state, detail = "live", result_probe["detail"]
        result = {
            "state": state,
            "latency_ms": result_probe["latency_ms"],
            "detail": _redact(detail)[:300],
            "code": result_probe["code"],
            "configured": {"api_key": has_key, "cfo_phone": has_phone},
            "cfo_phone_masked": mask_phone(os.getenv("CFO_ALERT_PHONE_NUMBER")),
            "timeout_s": wajo_timeout_s(),
            "cooldown_s": _cooldown_s(),
            "checked_at": _now_iso(),
        }
        _STATUS_CACHE.update(value=dict(result), fp=fp, at=time.monotonic())
    with _AUDIT_LOCK:
        last = dict(_LAST_EVENT)
        escalations = len(_AUDIT)
    result.update(
        {
            "last_request_summary": last.get("request_summary"),
            "last_response_summary": last.get("response_summary"),
            "last_outcome": last.get("outcome"),
            "last_kind": last.get("kind"),
            "last_ts": last.get("ts"),
            "escalations_recorded": escalations,
        }
    )
    return result
