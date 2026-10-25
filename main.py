"""Unified Entry Point for HeistBox × PAIR: Break the Vault: Agent Bank.

Serves all contract endpoints (/api/session, /api/attack, /api/leaderboard, /api/health, /ws),
plus all kernel and sponsor integrations.
"""
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

from server.app import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
