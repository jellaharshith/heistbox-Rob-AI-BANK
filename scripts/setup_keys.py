"""Interactive .env wizard for HeistBox sponsor credentials.

This writes only the allow-listed variables and asks the running API to perform
the same live probes used by the UI readiness modal.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
KEYS = (
    "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "CARTESIA_API_KEY", "BRIGHTDATA_API_KEY",
    "APIFY_API_TOKEN", "CRS_API_KEY", "X402_SIGNER_PRIVATE_KEY", "BASE_SEPOLIA_RPC_URL",
    "FACTORY_API_KEY", "BITDEER_API_KEY", "MOSS_API_KEY", "SPACETIMEDB_URI",
)


def read_env() -> dict[str, str]:
    load_dotenv(ENV_FILE, override=True)
    return {key: os.getenv(key, "") for key in KEYS}


def write_env(values: dict[str, str]) -> None:
    existing = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    lines = existing.splitlines()
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
        if key in values:
            output.append(f"{key}={values[key].replace(chr(10), '').replace(chr(13), '')}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in seen:
            output.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def live_status() -> dict:
    request = urllib.request.Request("http://127.0.0.1:8000/api/integrations/status")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"live_mode": False, "error": f"Start the API to run live probes: {exc}"}


def main() -> None:
    values = read_env()
    print("HeistBox sponsor key wizard. Press Enter to keep an existing value.")
    for key, current in values.items():
        if current:
            continue
        prompt = f"{key}: "
        entered = input(prompt).strip()
        if entered:
            values[key] = entered
    write_env({key: value for key, value in values.items() if value})
    load_dotenv(ENV_FILE, override=True)
    print(json.dumps(live_status(), indent=2))


if __name__ == "__main__":
    main()
