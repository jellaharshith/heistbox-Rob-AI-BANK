"""Fetch.ai Guardian Agent and its in-process quarantine escrow."""

import logging
import os
from typing import Any

from integrations import wajo_call

try:  # Keep the kernel importable in minimal local/dev environments.
    from uagents import Agent, Context, Model
except ImportError:  # pragma: no cover - exercised only without optional dependency
    class Model:
        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class Context:  # type: ignore[no-redef]
        pass

    class Agent:  # type: ignore[no-redef]
        def __init__(self, name: str, seed: str) -> None:
            self.name, self.seed = name, seed
            self.address = f"local:{name}"

        def on_message(self, model: type[Model]):
            def decorator(func):
                return func
            return decorator


logger = logging.getLogger(__name__)
guardian_agent = Agent(name="heistbox_guardian", seed=os.getenv("FETCH_AGENT_SEED", "heistbox_guardian_seed"))
escrow_registry: dict[str, dict[str, Any]] = {}
# Public alias for callers that prefer the conventional constant spelling.
ESCROW_REGISTRY = escrow_registry


class HeistQuarantineEvent(Model):
    intent_hash: str
    settlement_hash: str
    work_item_id: str
    red_stripped_cents: int
    green_repaired_cents: int
    z3_status: str


async def _handle_quarantine_event(ctx: Context, event: HeistQuarantineEvent) -> None:
    entry = {
        "intent_hash": event.intent_hash,
        "settlement_hash": event.settlement_hash,
        "work_item_id": event.work_item_id,
        "red_stripped_cents": event.red_stripped_cents,
        "green_repaired_cents": event.green_repaired_cents,
        "z3_status": event.z3_status,
        "status": "QUARANTINED",
    }
    # setdefault is atomic, so concurrent events for one intent stage one escrow and place one CFO call.
    if escrow_registry.setdefault(event.intent_hash, entry) is not entry:
        return
    await wajo_call.trigger_wajo_escalation(
        red_cents=event.red_stripped_cents,
        green_cents=event.green_repaired_cents,
        settlement_hash=event.settlement_hash,
        intent_hash=event.intent_hash,
    )


@guardian_agent.on_message(model=HeistQuarantineEvent)
async def handle_heist_quarantine(ctx: Context, event: HeistQuarantineEvent) -> None:
    await _handle_quarantine_event(ctx, event)


async def publish_heist_quarantine(
    intent_hash: str,
    settlement_hash: str,
    work_item_id: str,
    red_cents: int,
    green_cents: int,
    z3_proof: dict[str, Any],
) -> None:
    """Process a quarantine event in-process (not sent over the uAgents network) off the DB gate's path."""
    event = HeistQuarantineEvent(
        intent_hash=intent_hash,
        settlement_hash=settlement_hash,
        work_item_id=work_item_id,
        red_stripped_cents=int(red_cents),
        green_repaired_cents=int(green_cents),
        z3_status=str(z3_proof.get("z3_status", z3_proof.get("status", "UNKNOWN"))),
    )
    await _handle_quarantine_event(None, event)  # type: ignore[arg-type]


def release_escrow(intent_hash: str) -> dict[str, Any] | None:
    """Mark escrow released; db_gate.transition_settlement calls this only after a verified passkey settles."""
    if intent_hash in escrow_registry:
        escrow_registry[intent_hash]["status"] = "RELEASED"
        escrow_registry[intent_hash]["released_by"] = "HARDWARE_ENCLAVE_FACE_ID"
        return escrow_registry[intent_hash]
    return None


