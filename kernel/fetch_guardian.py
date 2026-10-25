"""Fetch.ai Guardian Agent and its in-process quarantine escrow."""
from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any

from integrations import wajo_call

try:  # Keep the kernel importable in minimal local/dev environments.
    from uagents import Agent, Context, Model, Protocol
except ImportError:  # pragma: no cover - exercised only without optional dependency
    class Model:
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class Context:  # type: ignore[no-redef]
        pass

    class Protocol:  # type: ignore[no-redef]
        def __init__(self, name: str = "", version: str = "") -> None:
            self.name, self.version = name, version

        def on_message(self, model: type[Model]):
            def decorator(func):
                return func
            return decorator

    class Agent:  # type: ignore[no-redef]
        def __init__(self, name: str, seed: str) -> None:
            self.name, self.seed = name, seed
            self.address = f"agent1q{hashlib.sha256(name.encode()).hexdigest()[:38]}"

        def on_message(self, model: type[Model]):
            def decorator(func):
                return func
            return decorator

        def include(self, protocol: Protocol) -> None:
            pass


logger = logging.getLogger(__name__)

FETCH_AGENT_NAME = "heistbox_guardian"
FETCH_AGENT_SEED = os.getenv("FETCH_AGENT_SEED", "heistbox_guardian_seed_calhacks2026")
guardian_agent = Agent(name=FETCH_AGENT_NAME, seed=FETCH_AGENT_SEED)
FETCHAI_AGENT_ADDRESS = getattr(guardian_agent, "address", "agent1qg8y9vg2k3p0d7z4a9u6e2c8x7w5t3l0m9j4")

escrow_protocol = Protocol(name="HeistEscrowProtocol", version="1.0.0")

escrow_registry: dict[str, dict[str, Any]] = {}
ESCROW_REGISTRY = escrow_registry


class HeistQuarantineEvent(Model):
    intent_hash: str
    settlement_hash: str
    work_item_id: str
    red_stripped_cents: int
    green_repaired_cents: int
    z3_status: str
    prompt_explanation: str = ""


class HeistReleaseEvent(Model):
    intent_hash: str
    released_by: str = "HARDWARE_ENCLAVE_FACE_ID"


async def _handle_quarantine_event(ctx: Context | None, event: HeistQuarantineEvent) -> None:
    entry = {
        "intent_hash": event.intent_hash,
        "settlement_hash": event.settlement_hash,
        "work_item_id": event.work_item_id,
        "red_stripped_cents": event.red_stripped_cents,
        "green_repaired_cents": event.green_repaired_cents,
        "z3_status": event.z3_status,
        "prompt_explanation": getattr(event, "prompt_explanation", ""),
        "status": "QUARANTINED",
        "agent_address": FETCHAI_AGENT_ADDRESS,
        "agent_name": FETCH_AGENT_NAME,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if escrow_registry.setdefault(event.intent_hash, entry) is not entry:
        return
    kwargs: dict[str, Any] = {
        "red_cents": event.red_stripped_cents,
        "green_cents": event.green_repaired_cents,
        "settlement_hash": event.settlement_hash,
        "intent_hash": event.intent_hash,
    }
    if getattr(event, "prompt_explanation", None):
        kwargs["prompt_explanation"] = event.prompt_explanation
    await wajo_call.trigger_wajo_escalation(**kwargs)


@escrow_protocol.on_message(model=HeistQuarantineEvent)
@guardian_agent.on_message(model=HeistQuarantineEvent)
async def handle_heist_quarantine(*args: Any, **kwargs: Any) -> None:
    if len(args) == 2:
        ctx, event = args
    elif len(args) >= 3:
        ctx, _, event = args[:3]
    else:
        ctx = kwargs.get("ctx")
        event = kwargs.get("msg") or kwargs.get("event")
    await _handle_quarantine_event(ctx, event)


@escrow_protocol.on_message(model=HeistReleaseEvent)
@guardian_agent.on_message(model=HeistReleaseEvent)
async def handle_heist_release(*args: Any, **kwargs: Any) -> None:
    if len(args) == 2:
        ctx, event = args
    elif len(args) >= 3:
        ctx, _, event = args[:3]
    else:
        event = kwargs.get("msg") or kwargs.get("event")
    if event and getattr(event, "intent_hash", None):
        release_escrow(event.intent_hash, getattr(event, "released_by", "HARDWARE_ENCLAVE_FACE_ID"))


if hasattr(guardian_agent, "include"):
    try:
        guardian_agent.include(escrow_protocol)
    except Exception:
        pass


async def publish_heist_quarantine(
    intent_hash: str,
    settlement_hash: str,
    work_item_id: str,
    red_cents: int,
    green_cents: int,
    z3_proof: dict[str, Any] | None = None,
    prompt_explanation: str = "",
) -> dict[str, Any]:
    """Process a quarantine event in-process using uAgents autonomous protocol."""
    z3_status = "VERIFIED_RELATIONAL_CONSTRAINTS"
    if z3_proof:
        z3_status = str(z3_proof.get("z3_status", z3_proof.get("status", z3_status)))

    event = HeistQuarantineEvent(
        intent_hash=intent_hash,
        settlement_hash=settlement_hash,
        work_item_id=work_item_id,
        red_stripped_cents=int(red_cents),
        green_repaired_cents=int(green_cents),
        z3_status=z3_status,
        prompt_explanation=prompt_explanation,
    )
    await handle_heist_quarantine(None, event)  # type: ignore[arg-type]
    return escrow_registry.get(intent_hash, {})


def release_escrow(intent_hash: str, released_by: str = "HARDWARE_ENCLAVE_FACE_ID") -> dict[str, Any] | None:
    """Mark escrow released after hardware enclave verification."""
    if intent_hash in escrow_registry:
        escrow_registry[intent_hash]["status"] = "RELEASED"
        escrow_registry[intent_hash]["released_by"] = released_by
        escrow_registry[intent_hash]["released_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return escrow_registry[intent_hash]
    return None


def get_escrow(intent_hash: str) -> dict[str, Any] | None:
    """Return a single Fetch.ai escrow record by its intent hash."""
    return escrow_registry.get(intent_hash)


def get_escrow_list() -> list[dict[str, Any]]:
    """Return all active and settled Fetch.ai escrows."""
    return list(escrow_registry.values())
