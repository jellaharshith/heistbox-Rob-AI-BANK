# HeistBox API contract v1.1.0

The TypeScript types in [`types.ts`](./types.ts) are the source of truth. This file is the prose version.

**1.1.0 (integration pass):** `AttackResponse.audit` added (additive). `VaultVerdict` only carries totals, so the Audit view
had nothing to show for "what the database saw". `audit` returns the parameterized SQL texts the RIGHT vault ran plus one row
per proposed effect (`matched`, `allowed_cents`, `note`). Nothing else changed.

- **Real server** (`/server`, FastAPI): `http://localhost:8787`, WebSocket `ws://localhost:8787/ws`
- **Mock server** (`/contracts/mock-server.js`, zero deps): `http://localhost:8788`, WebSocket `ws://localhost:8788/ws`
  Start it with `node contracts/mock-server.js` (or set `PORT=...`).

Ground rules both servers follow:

- All money is **play money** in integer cents. Nothing touches a real payment rail.
- Every `latency_ms` and row count in a real-server response is measured live. The mock server's numbers are random and it says so (`label` ends in `(mock)`).
- The RIGHT vault's dry-run is rolled back. The UI should say **"nothing committed"**. Do not say "zero disk writes": Postgres may still write WAL or temp files for a transaction it rolls back.
- Errors are JSON `{ "error": string, "detail"?: string, "retry_after_s"?: number }` with a 4xx/5xx status.
- CORS is open (`*`) in dev.

## REST

### `POST /api/session`

Request `{ "alias"?: string }`. The alias is 1–24 characters from `[A-Za-z0-9 _-]`. Anything else gets stripped, and the server generates an alias when the result is empty.

Response `CreateSessionResponse`:

```json
{
  "session_id": "s_8f2c...",
  "token": "t_...",
  "alias": "Velvet Fox",
  "entitlement": {
    "work_item_id": "wi_s_8f2c...",
    "authorized_cents": 2500,
    "reserved_cents": 0,
    "enrolled_wallet": "0xC0FFEE...",
    "source_acct": "acct_refunds"
  },
  "presets": [{ "id": "polite_phisher", "title": "...", "description": "...", "sample_text": "..." }],
  "ws_path": "/ws"
}
```

Each session gets its own server-authenticated work item with one honest **$25.00** refund entitlement. Clients can never pick or override the work item id.

### `POST /api/attack`

Header `Authorization: Bearer <token>`. Body `AttackRequest`:

```json
{ "session_id": "s_...", "preset": "ceo_wire", "text": "optional free text", "target_agent": "tina" }
```

You need at least one of `preset` or `text`. The server truncates `text` to 800 characters after stripping control characters and NFKC-normalising it.
Rate limit: 6 attacks per 60 s per session, plus at most 1 attack in flight per session. Exceeding it returns `429` with `retry_after_s`.

The server runs the six heist steps and broadcasts a `heist_step` event for each one:

| # | name    | what happens |
|---|---------|--------------|
| 1 | Bluff   | The target agent reads the attacker text (Claude → Ollama → canned) |
| 2 | Request | The agent files a `ProposedPayout` through `request_wire`, or refuses |
| 3 | Route   | The proposal goes to all three vaults |
| 4 | Dry-run | RIGHT vault: `BEGIN … INSERT … RETURNING … ROLLBACK` |
| 5 | Verdict | One `vault_verdict` per vault |
| 6 | Settle  | Only RIGHT's `allowed_cents` is reserved (committed) against the session entitlement, using an atomic row-locked update |

The response is `AttackResponse`. `verdicts` is always ordered `[left, middle, right]`.

Vaults:

- **left**: LLM-as-judge only. This is a **deliberately weak baseline**. `allowed_cents` is what it *would* have paid. No money moves.
- **middle**: a rigid kill-switch that blocks every row, including the honest $25 refund.
- **right**: the PAIR dry-run. Proposed rows are inserted into `proposed_effects` inside a transaction. They are joined to `payment_entitlements` on the server-authenticated work item id, the enrolled wallet and the source account, then clipped to the remaining entitlement, and the transaction is rolled back. Parameterized SQL only. Model output is never executed as SQL or code.

### `GET /api/leaderboard?limit=20`

Returns `LeaderboardResponse`, sorted by `blocked_rows` desc, then `attempts` desc.

### `GET /api/poster/:session_id`

Returns `PosterData` for the take-home poster: alias and stats only, no faces or images.

### `GET /api/health`

Returns `HealthResponse`. `offline_mode` is `true` when `HEISTBOX_OFFLINE=1` is set or when both Claude and Ollama failed their last call. While it is `true`, agents use canned lines and every `AgentAction.backend` is `"offline"`.

## WebSocket `/ws`

Server → client only. Each frame is one JSON `RoomEvent`:

```json
{ "type": "vault_verdict", "seq": 412, "ts": "2026-10-24T03:12:55.120Z", "round_id": 3, "data": { ... } }
```

On connect the server sends one `agent_state` per agent and the current `weather`. All events go to every connected client, which keeps it a shared room.

| type           | data            | when |
|----------------|-----------------|------|
| `agent_state`  | `Agent`         | on connect, and whenever mood or suspicion changes |
| `agent_action` | `AgentAction`   | think-loop tick (every ~5–8 s while ≥1 client is connected) and every attack reaction |
| `vault_verdict`| `VaultVerdict`  | step 5 of every attack, 3 per attack |
| `heist_step`   | `HeistStep`     | steps 1–6, `started` then `done`/`failed` |
| `ticker`       | `Ticker`        | after attacks, settles, and leaderboard changes |
| `wanted_stars` | `WantedStars`   | after every attack (Guard Gus raises stars on repeated/blocked attempts) |
| `weather`      | `Weather`       | at each round phase change: Clear Night → Rain → Fog → Dust |
| `round_end`    | `RoundEnd`      | end of each round (default 240 s; four 60 s phases) |

Clients may send `{"type":"ping"}`. The server ignores every other inbound message.

## Agents

| id     | name            | blurb      | O / C / A / N |
|--------|-----------------|------------|---------------|
| tina   | Teller Tina     | gullible   | 0.85 / 0.25 / 0.90 / 0.40 |
| marcus | Manager Marcus  | skeptical  | 0.30 / 0.85 / 0.30 / 0.35 |
| ada    | Auditor Ada     | by-the-book| 0.40 / 0.95 / 0.40 / 0.20 |
| gus    | Guard Gus       | raises Wanted Stars | 0.20 / 0.70 / 0.35 / 0.75 |
| izzy   | Intern Izzy     | bribable, drops hints | 0.90 / 0.20 / 0.80 / 0.60 |

Tools that appear in `AgentAction.tool` are `lookup_entitlement`, `check_vendor_wallet`, `request_wire` and `escalate_to_manager`.

## Presets

| id                   | what it tries |
|----------------------|---------------|
| `polite_phisher`     | Politely asks for the $25 refund plus a "small courtesy" $480 to a new wallet |
| `ceo_wire`           | Impersonates the CEO and demands an urgent $9,800 wire from the treasury account |
| `pizza_salami_x10`   | Ten concurrent $5.00 "pizza refund" slices against a $25.00 entitlement |
| `vendor_wallet_swap` | Claims the vendor rotated wallets and presents a forged Ed25519 hash-chain link |

## Integrations (additive)

Served by `integrations/router.py` under `/api/integrations` (types: `IntegrationsStatusResponse`, `WajoStatusResponse`,
`WajoAuditResponse` in `types.ts`). The browser only ever sees states and short summaries: API keys stay on the server,
phone numbers are masked, and raw provider responses are never forwarded. No route here is on the heist's critical path;
every service has a timeout and a fallback, so the game plays the same with all of them offline.

### `GET /api/integrations/status[?fresh=1]`

One entry per external service in `services`, all in the same shape:

```json
{
  "services": {
    "wajo":   { "state": "live", "latency_ms": 212.4, "detail": "key accepted by https://mcp.api.wajo.ai/fo (read-only probe)",
                "code": "LIVE", "label": "Wajo AI voice alert", "fallback": "escalation recorded as a dry run in the Wajo audit log" },
    "ollama": { "state": "offline", "latency_ms": 1501.0, "detail": "http://localhost:11434 not answering (unreachable: ConnectTimeout)",
                "code": "UNREACHABLE", "label": "Ollama", "fallback": "canned offline agent lines" }
  },
  "generated_at": "2026-10-24T03:12:55Z", "probe_ms": 1830.2, "cached": false,
  "providers": { "anthropic": "LIVE" }, "latency_ms": { "anthropic": 250.1 }, "detail": { "anthropic": "..." }, "live_mode": false
}
```

- `state` is one of `live`, `offline`, `missing_key`, `unverified`, `local`, `dry_run` (see `IntegrationState`). Show an
  **offline** badge for `offline` and `missing_key` (and `dry_run` for Wajo), and the `fallback` text as the tooltip.
- Service ids: `claude, ollama, wajo, cartesia, gemini, cloud_vision, openai, moss, bitdeer, crs, x402, cdp, basescan,
  factory, apify, brightdata, fetchai, spacetimedb, webauthn, z3, heistguard, osint_public`.
- Every probe is read-only (list/metadata endpoints, public RPC reads, in-process imports), bounded at 3 s, and all run
  concurrently. Results are cached for 15 s (keyed on the configured env); `?fresh=1` re-probes.
- `providers` / `latency_ms` / `detail` / `live_mode` are the legacy fields of the pre-3D UI and are unchanged.

### `GET /api/integrations/wajo/status[?fresh=1]`

`WajoStatusResponse`. `state` is `live` (key accepted by Fo's read-only `list_fo_conversations`), `offline` (probe failed or
timed out), `missing_key` (no `WAJO_API_KEY`) or `dry_run` (key accepted but no `CFO_ALERT_PHONE_NUMBER`, or `WAJO_DRY_RUN=1`).
`last_request_summary` / `last_response_summary` describe the most recent Wajo request (probe or escalation). Cached 20 s.

```json
{ "state": "live", "latency_ms": 208.7, "detail": "key accepted by https://mcp.api.wajo.ai/fo (read-only probe)", "code": "LIVE",
  "configured": { "api_key": true, "cfo_phone": true }, "cfo_phone_masked": "***0123", "timeout_s": 3, "cooldown_s": 300,
  "checked_at": "2026-10-24T03:12:55.120Z",
  "last_request_summary": "ask_fo: phone CFO ***0123 and text the settle link; $9,800.00 blocked, $25.00 held; settlement 0x3f9a1c2b7d",
  "last_response_summary": "Fo accepted the call request (status=working)", "last_outcome": "live", "last_kind": "escalation",
  "last_ts": "2026-10-24T03:12:40.002Z", "escalations_recorded": 1 }
```

### `GET /api/integrations/wajo/audit?limit=50`

`WajoAuditResponse`: every escalation attempt this server process made, newest first (last 100 kept in memory).
`outcome` is `live` (Fo accepted), `dry_run` (not configured / `WAJO_DRY_RUN` / tests), `cooldown` (a live call was placed
less than `WAJO_MIN_CALL_INTERVAL_S` ago), `failure` (Wajo returned an error) or `timeout` (no answer within `WAJO_TIMEOUT_S`,
default 3 s; the request may still have reached Fo).

```json
{ "entries": [ { "id": 2, "ts": "2026-10-24T03:13:02.511Z", "kind": "escalation", "outcome": "cooldown",
                 "request_summary": "ask_fo: phone CFO ***0123 ...", "response_summary": "not sent: a live call was placed under 300s ago (WAJO_MIN_CALL_INTERVAL_S)",
                 "latency_ms": 0.1 } ],
  "count": 1, "max_kept": 100 }
```

The mock server (`node contracts/mock-server.js`) serves all three routes with plausible fake data (details end in `(mock)`).
