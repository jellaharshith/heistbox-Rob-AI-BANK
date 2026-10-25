# External Integrations Status and Registry

This document lists every external service and integration touched by HeistBox,
where it is used in the codebase, its timeouts and fallbacks, its current live status,
and read-only probe evidence.

Status legend:
- **works**: Configured, reachable, and verified via read-only probe / local check.
- **fallback only**: Not configured or upstream unreachable; fallback cleanly activates.
- **dead**: Defunct client with no working fallback (none in current build).
- **not used**: Configured or unconfigured, but not invoked by any active game path.

| service | where used (file:line) | env var(s) | timeout | fallback | status (works / fallback only / dead / not used) | evidence (probe result + latency_ms, no secrets) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `claude` | integrations/router.py:441, integrations/router.py:908, kernel/live_agent_parser.py:279 | `ANTHROPIC_API_KEY, ANTHROPIC_MODEL` | 8s (probe 3s) | Ollama, then canned agent lines / regex extractor | **works** | HTTP 200; key accepted; 14 models; claude-haiku-5-5 listed, claude-opus-5-5 listed (1596.2ms) |
| `ollama` | kernel/heistguard_infer.py:288, kernel/live_agent_parser.py:324, server/config.py:28 | `HEISTBOX_OLLAMA_URL, OLLAMA_HOST, HEISTBOX_OLLAMA_MODEL` | 1.5s (probe), 5s (infer) | canned offline agent lines / local sklearn classifier | **fallback only** | http://localhost:11434 not answering (unreachable: ConnectTimeout) (1941.3ms) |
| `wajo` | integrations/wajo_call.py:180, integrations/router.py:736, kernel/fetch_guardian.py:60 | `WAJO_API_KEY, WAJO_MCP_URL, CFO_ALERT_PHONE_NUMBER, WAJO_TIMEOUT_S` | 3s | escalation recorded as a dry run in the Wajo audit log | **works** | key accepted by https://mcp.api.wajo.ai/fo (read-only probe) (1279.0ms) |
| `cartesia` | integrations/router.py:72, integrations/router.py:437 | `CARTESIA_API_KEY, CARTESIA_VOICE_ID` | 8s (probe 3s) | browser speech synthesis | **works** | HTTP 200; key accepted; 1049 voices (2339.4ms) |
| `gemini` | integrations/status.py:172, kernel/live_agent_parser.py:302 | `GEMINI_API_KEY, GEMINI_TEXT_MODEL` | 3s | regex extractor (after Claude) | **fallback only** | HTTP 403 Requests to this API generativelanguage.googleapis.com method google.ai.generativelanguage.v1beta.ModelService.ListModels are blocked. (749.6ms) |
| `cloud_vision` | integrations/router.py:428, integrations/router.py:852 | `GOOGLE_CLOUD_VISION_API_KEY, GEMINI_API_KEY` | 8s (probe 3s) | template roast without vision cues | **works** | HTTP 200; images:annotate on a 1x1 PNG succeeded (1697.2ms) |
| `openai` | integrations/status.py:186 | `OPENAI_API_KEY` | 3s | not used by any code path | **not used** | key accepted (127 models) but no HeistBox code path calls OpenAI (1828.7ms) |
| `moss` | integrations/router.py:461, integrations/router.py:1837 | `MOSS_API_KEY, MOSS_PROJECT_ID, MOSS_PROJECT_KEY` | 8s (probe 3s) | Moss panel hidden; local HeistGuard classifier still runs | **works** | HTTP 200; project key accepted; 2 index(es) (2196.1ms) |
| `bitdeer` | integrations/router.py:453, integrations/router.py:1166 | `BITDEER_API_KEY, BITDEER_BASE_URL` | 8s (probe 3s) | voice bribe uses Claude only | **fallback only** | BITDEER_API_KEY is not set |
| `crs` | integrations/router.py:488, integrations/router.py:1263 | `CRS_API_KEY, CRS_USERNAME, CRS_PASSWORD` | 8s (probe 3s) | local persona file shared/crs_personas.json | **works** | HTTP 200; sandbox login accepted; GET /users ok (696.1ms) |
| `x402` | integrations/router.py:1335, integrations/status.py:204 | `X402_SIGNER_PRIVATE_KEY, X402_TESTNET_SCALE, BASE_SEPOLIA_RPC_URL` | 8s (probe 3s) | HTTP 402 challenge only; nothing is signed or broadcast | **works** | RPC ok (chain 84532); signer 0xA7AA...486B holds 0.00010 test ETH, 0.50 test USDC (1417.1ms) |
| `cdp` | integrations/status.py:238, scripts/setup_x402_wallet.py:19 | `CDP_API_KEY_NAME, CDP_API_KEY_PRIVATE_KEY` | 3s | fund the testnet signer manually (scripts only) | **works** | CDP_API_KEY_NAME pair accepted (list_accounts: 0 account(s)) (1026.5ms) |
| `basescan` | integrations/router.py:815, integrations/status.py:195 | `BASESCAN_API_KEY` | 3s | plain sepolia.basescan.org links (no API needed) | **fallback only** | BASESCAN_API_KEY not set; explorer links need no key |
| `factory` | integrations/router.py:564, integrations/router.py:1764 | `FACTORY_API_KEY` | 12s (probe 0.5s) | no RLS patch draft | **works** | droid CLI at C:\Users\Shaik\AppData\Roaming\npm\droid.CMD; key is checked by the first droid exec |
| `apify` | integrations/router.py:447, integrations/router.py:2000 | `APIFY_API_TOKEN` | 8s (probe 3s) | OSINT runs without the Apify scrape | **works** | HTTP 200; token accepted (users/me) (1665.9ms) |
| `brightdata` | integrations/router.py:477, integrations/router.py:1926 | `BRIGHTDATA_API_KEY, BRIGHTDATA_SERP_ZONE` | 8s (probe 3s) | OSINT runs without the web fraud search | **works** | HTTP 200; key accepted; 1 active zone(s), types: serp (1484.5ms) |
| `fetchai` | kernel/fetch_guardian.py:20, integrations/router.py:620 | `None` | In-process (0ms) | in-process escrow (same behaviour) | **works** | in-process escrow guardian (uagents SDK installed); not registered on Agentverse; 0 held, 0 released |
| `spacetimedb` | integrations/router.py:469, integrations/router.py:2032 | `SPACETIMEDB_URI, SPACETIMEDB_id, SPACETIMEDB_TOKEN` | 8s (probe 3s) | telemetry sync reports a local fallback | **works** | HTTP 200; database metadata reachable (public) (1429.0ms) |
| `webauthn` | integrations/router.py:1545, integrations/status.py:299 | `None` | In-process (0ms) | settlement cannot be approved | **works** | py_webauthn 3.0.1 loaded; 2 registered passkey(s) (878.4ms) |
| `z3` | kernel/pair_z3.py:7, integrations/status.py:288 | `None` | In-process (100ms) | proof panel shows 'unavailable' | **works** | z3 5.3.1 loaded; sanity UNSAT check ok (179.6ms) |
| `heistguard` | kernel/heistguard_infer.py:99, kernel/db_gate.py:25 | `HEISTBOX_MODEL_CACHE` | In-process (100ms) | lexical taint rules only | **works** | sklearn classifier loaded (2204 KB); p(attack)=1.00 vs benign 0.79 (8578.9ms) |
| `osint_public` | integrations/router.py:1977, integrations/status.py:264 | `OSINT_USER_AGENT` | 3s | OSINT fields left empty | **works** | CFPB ok, RDAP ok (no keys) (974.0ms) |
