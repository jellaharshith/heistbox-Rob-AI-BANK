# Integration log

## 2026-10-24: Step 1 (wiring fix) blocked

- `server/round_runner.py` and `server/app.py` are not in the repo. Searched `**/round_runner.py` and `**/app.py`: only `.venv` package files matched.
- Steps 1 and 3–5 need these files, so they did not run. Step 6 (README) was not written either.
- Step 2 partial: embedded Postgres (pgserver) is up and `python -m db.migrate` reports `migrations applied: none (up to date)` at `127.0.0.1:62702`.

Next action: add `server/round_runner.py` and `server/app.py` to the repo, then re-run from step 1.

## 2026-10-24: Steps 1–2 passed, step 3 stopped

- Step 1 (wiring) passed, commit `a802d3c`. Step 2 (startup) passed, commit `f48c98e`. The server runs on port 8789 with `--reload`.
- Step 3 (`tests/contract_check.py`) did not finish: a safety check interrupted the session while the file was being written. `tests/contract_check.py` may be on disk half-written; delete it before step 3 is redone. Steps 4–6 did not run.
- Known contract drift (from reading the code, not yet checked by a test):
  - `/api/health`: only `{ok, offline}` is returned. Missing: `version`, `db`, `llm`, `offline_mode`, `ws_clients`, `uptime_s`.
  - `/api/session`: `presets` and `ws_path` are missing, and the alias is not sanitized.
  - `/api/attack`: request uses `session`/`mask` instead of `session_id`/`preset`. Bad auth returns 429 instead of 401. The per-session rate limit is not applied. The response is not `AttackResponse`.
  - `/api/leaderboard`: returns a bare list instead of `{entries, generated_at}`.
  - `/api/poster/:session_id`: route missing.
  - `round_runner.py`: `heist_step`/`agent_action` payloads don't match `HeistStep`/`AgentAction`. There are no `wanted_stars`/`ticker` events, and denied attacks return no verdicts. Not fixed because the file is limited to wiring changes.
  - `vaults.right_dry_run`: its verdict carries an extra internal `_rows` key, which is broadcast too.
- Stray processes I was not permitted to stop:
  - PID 26928: uvicorn on 127.0.0.1:8788. It shares the port with the other agent's mock (node PID 72584) and may catch its requests.
  - PID 50312: uvicorn on 8787, started before the lifespan fix, so it returns 500 on DB routes.
