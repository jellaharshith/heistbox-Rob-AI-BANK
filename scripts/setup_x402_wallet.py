#!/usr/bin/env python3
"""
scripts/setup_x402_wallet.py — Base Sepolia TESTNET signer for POST /api/integrations/x402-settle.

1. If X402_SIGNER_PRIVATE_KEY is empty in .env, generates a fresh EVM key and writes it there (the key is never
   printed). An existing key is never overwritten.
2. Requests free Base Sepolia faucet funds (ETH for gas, USDC for the settlement) to that address through the
   Coinbase Developer Platform faucet, using the CDP API key in .env (testnet_coinbase_base_api_key / _secret,
   or CDP_API_KEY_ID / CDP_API_KEY_SECRET).

Testnet only: Base Sepolia tokens have no monetary value.

Usage:  uv run python scripts/setup_x402_wallet.py [--no-faucet]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
sys.path.insert(0, str(ROOT))
load_dotenv(ENV_FILE, override=True)


def ensure_signer() -> str:
    from eth_account import Account

    existing = os.getenv("X402_SIGNER_PRIVATE_KEY", "").strip()
    if existing:
        address = Account.from_key(existing).address
        print(f"Using existing X402 signer {address}")
        return address
    import importlib

    router = importlib.import_module("integrations.router")
    account = Account.create()
    router._write_env({"X402_SIGNER_PRIVATE_KEY": "0x" + account.key.hex().removeprefix("0x")})
    print(f"Generated new Base Sepolia testnet signer {account.address} (private key written to .env, not shown)")
    return account.address


CDP_KEY_PAIRS = (
    ("CDP_API_KEY_ID", "CDP_API_KEY_SECRET"),
    ("CDP_API_KEY_NAME", "CDP_API_KEY_PRIVATE_KEY"),
    ("testnet_coinbase_base_api_key", "testnet_coinbase_base_api_secret"),
)


async def fund(address: str, tokens: tuple[str, ...]) -> None:
    from cdp import CdpClient

    pairs = [(i, s) for i, s in CDP_KEY_PAIRS if os.getenv(i) and os.getenv(s)]
    if not pairs:
        print("No CDP API key in .env; fund the address from a Base Sepolia faucet manually.")
        return
    for token in tokens:
        for id_env, secret_env in pairs:  # first key pair the CDP API accepts wins
            try:
                async with CdpClient(api_key_id=os.environ[id_env].strip(), api_key_secret=os.environ[secret_env].strip()) as cdp:
                    tx = await cdp.evm.request_faucet(address=address, network="base-sepolia", token=token)
                print(f"Faucet {token.upper()} via {id_env}: https://sepolia.basescan.org/tx/{tx}")
                break
            except Exception as exc:
                print(f"Faucet {token.upper()} via {id_env} failed: {str(exc).splitlines()[0][:140]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-faucet", action="store_true")
    parser.add_argument("--tokens", default="eth,usdc", help="comma-separated faucet tokens (eth, usdc)")
    args = parser.parse_args()
    addr = ensure_signer()
    if not args.no_faucet:
        asyncio.run(fund(addr, tuple(t.strip() for t in args.tokens.split(",") if t.strip())))
