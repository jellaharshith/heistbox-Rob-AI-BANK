#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
"$root/.venv/Scripts/python.exe" -m uvicorn server.app:app --host 127.0.0.1 --port 8788 & server=$!
(cd "$root" && npm --prefix web run dev) & web=$!
trap 'kill "$server" "$web" 2>/dev/null || true' INT TERM EXIT
wait -n "$server" "$web"
