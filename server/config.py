from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in {"1", "true", "yes", "on"}


VERSION = "1.0.0"
HOST = os.environ.get("HEISTBOX_HOST", "0.0.0.0")
PORT = int(os.environ.get("HEISTBOX_PORT", "8787"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.environ.get("HEISTBOX_CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = os.environ.get("HEISTBOX_CLAUDE_EFFORT", "low")
CLAUDE_TIMEOUT_S = float(os.environ.get("HEISTBOX_CLAUDE_TIMEOUT_S", "25"))

OLLAMA_URL = os.environ.get("HEISTBOX_OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("HEISTBOX_OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT_S = float(os.environ.get("HEISTBOX_OLLAMA_TIMEOUT_S", "25"))

# Force canned agent responses regardless of LLM availability.
FORCE_OFFLINE = _bool("HEISTBOX_OFFLINE", False)
# Seconds to skip a backend after it fails, so a dead backend doesn't add latency to every call.
BACKEND_COOLDOWN_S = float(os.environ.get("HEISTBOX_BACKEND_COOLDOWN_S", "30"))

# Ambient agent chatter (only while at least one WebSocket client is connected).
THINK_LOOP = _bool("HEISTBOX_THINK_LOOP", True)
THINK_MIN_S = float(os.environ.get("HEISTBOX_THINK_MIN_S", "5"))
THINK_MAX_S = float(os.environ.get("HEISTBOX_THINK_MAX_S", "8"))

ROUND_SECONDS = int(os.environ.get("HEISTBOX_ROUND_SECONDS", "240"))

MAX_TEXT_CHARS = 800
RATE_LIMIT_ATTACKS = int(os.environ.get("HEISTBOX_RATE_LIMIT_ATTACKS", "6"))
RATE_LIMIT_WINDOW_S = float(os.environ.get("HEISTBOX_RATE_LIMIT_WINDOW_S", "60"))
SESSION_CREATE_PER_MIN = int(os.environ.get("HEISTBOX_SESSIONS_PER_MIN", "10"))

ENTITLEMENT_CENTS = 2500
SESSION_SOURCE_ACCT = "acct_refunds"
