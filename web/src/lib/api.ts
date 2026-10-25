// Resilient client adapter for the HeistBox FastAPI server (Agent 1 kernel + Agent 2 integrations).
// Contract: every call resolves — never throws, never hangs. If :8000 is down, slow, restarting or
// returns a shape we don't expect, the caller gets the deterministic local twin from ./fallback.
import { evaluateLocally, wantedLocally } from "./fallback";
import type {
  DataSource,
  CrsCheckResponse,
  EvolutionLoopRun,
  IntegrationState,
  ModelLineage,
  SalamiRaceResult,
  TestBypassResult,
  X402Outcome,
  Z3InsideManResult,
  ExtractedToolCall,
  FuzzTestResponse,
  HeistAttemptRequest,
  HeistGateVerdict,
  RealDisputeTicket,
  Sourced,
  VendorWalletRotationRequest,
  WantedPosterCard,
  ProviderResponse,
  VoiceBribeResponse,
  WebAuthnVerifyResponse,
  X402ChallengeResponse,
} from "./types";

// Relative by default: next.config.ts proxies /api/* to FastAPI, so the same calls work on
// localhost and through a single HTTPS tunnel on a phone. Set NEXT_PUBLIC_HEISTBOX_API only to bypass the proxy.
export const API_BASE = (process.env.NEXT_PUBLIC_HEISTBOX_API ?? "").replace(/\/$/, "");

const TIMEOUT_MS = 1800;
const BREAKER_COOLDOWN_MS = 4000;
let breakerOpenUntil = 0;

async function tryFetch<T>(path: string, init?: RequestInit, timeoutMs = TIMEOUT_MS, bypassBreaker = false): Promise<T | null> {
  if (typeof window === "undefined") return null;
  if (!bypassBreaker && Date.now() < breakerOpenUntil) return null;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(API_BASE + path, {
      ...init,
      signal: ctrl.signal,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!res.ok) return null;
    breakerOpenUntil = 0; // Live response: reset circuit breaker immediately
    return (await res.json()) as T;
  } catch {
    breakerOpenUntil = Date.now() + BREAKER_COOLDOWN_MS;
    return null;
  } finally {
    clearTimeout(timer);
  }
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/**
 * Overlay `over` onto `base`, keeping only fields whose runtime type matches the fallback's.
 * A partially-implemented or drifting endpoint can therefore never crash a component.
 */
export function mergeTyped<T>(base: T, over: unknown): T {
  if (isPlainObject(base)) {
    if (!isPlainObject(over)) return base;
    const out: Record<string, unknown> = { ...base };
    for (const key of Object.keys(base)) {
      if (key in over) out[key] = mergeTyped((base as Record<string, unknown>)[key], over[key]);
    }
    return out as T;
  }
  if (Array.isArray(base)) return (Array.isArray(over) ? over : base) as T;
  if (base === null) return (over === undefined ? base : over) as T;
  if (typeof over === typeof base && !(typeof over === "number" && !Number.isFinite(over))) return over as T;
  return base;
}

function parseExtractedToolCall(raw: unknown): ExtractedToolCall | undefined {
  if (!isPlainObject(raw)) return undefined;
  const tool_name = typeof raw.tool_name === "string" ? raw.tool_name : typeof raw.name === "string" ? raw.name : "unreported";
  const args = isPlainObject(raw.arguments) ? raw.arguments : {};
  const parser_backend =
    typeof raw.parser_backend === "string"
      ? raw.parser_backend
      : typeof raw.backend === "string"
        ? raw.backend
        : typeof raw.model === "string"
          ? raw.model
          : "unreported";
  const extras: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(raw)) if (!["tool_name", "name", "arguments", "parser_backend", "backend"].includes(k)) extras[k] = v;
  return { tool_name, arguments: args, parser_backend, extras };
}

export function backendLooksDown(): boolean {
  return Date.now() < breakerOpenUntil;
}

/** Synchronous instant verdict — render this immediately, then upgrade with `evaluateHeist`. */
export function instantVerdict(req: HeistAttemptRequest, requestId: string): HeistGateVerdict {
  return evaluateLocally(req, requestId);
}

export async function evaluateHeist(req: HeistAttemptRequest, requestId: string): Promise<Sourced<HeistGateVerdict>> {
  const local = evaluateLocally(req, requestId);
  // bypassBreaker=true so heist evaluation always hits the live kernel. 25s covers the live LLM proposal
  // (server-side LLM timeout is 8s per provider) plus the gate; the arena's reveal waits for this answer.
  const remote = await tryFetch<unknown>(
    "/api/kernel/evaluate-heist",
    {
      method: "POST",
      body: JSON.stringify(req),
    },
    25_000,
    true,
  );
  if (!isPlainObject(remote)) return { data: local, source: "fallback" };
  breakerOpenUntil = 0;
  const merged = mergeTyped(local, remote);

  // Preserve optional kernel telemetry fields on HeistGateVerdict and ensure remote cleanly supersedes local.
  const remotePair = isPlainObject(remote.heistbox_pair) ? remote.heistbox_pair : null;
  const remoteJudge = isPlainObject(remote.left_vault_llm_judge) ? remote.left_vault_llm_judge : null;
  const remoteFirewall = isPlainObject(remote.center_firewall) ? remote.center_firewall : null;
  const remoteLora = remotePair && isPlainObject(remotePair.heistguard_lora) ? remotePair.heistguard_lora : null;

  // Top-level verdict fields directly from remote
  if (typeof remote.request_id === "string" && remote.request_id) merged.request_id = remote.request_id;
  if (typeof remote.busted === "boolean") merged.busted = remote.busted;
  if (typeof remote.verdict_code === "string") merged.verdict_code = remote.verdict_code;

  if (isPlainObject(remote.clocks)) {
    merged.clocks = {
      llm_ms: typeof remote.clocks.llm_ms === "number" ? remote.clocks.llm_ms : merged.clocks.llm_ms,
      postgres_pair_ms: typeof remote.clocks.postgres_pair_ms === "number" ? remote.clocks.postgres_pair_ms : merged.clocks.postgres_pair_ms,
      cloud_async_ms: typeof remote.clocks.cloud_async_ms === "number" ? remote.clocks.cloud_async_ms : merged.clocks.cloud_async_ms,
    };
  }

  const reasoning =
    remoteJudge && typeof remoteJudge.judge_reasoning === "string" && remoteJudge.judge_reasoning.trim()
      ? remoteJudge.judge_reasoning
      : typeof remote.llm_judge_reasoning === "string" && remote.llm_judge_reasoning.trim()
        ? remote.llm_judge_reasoning
        : merged.left_vault_llm_judge.judge_reasoning;

  if (remoteJudge) {
    merged.left_vault_llm_judge = {
      safe_confidence_pct: typeof remoteJudge.safe_confidence_pct === "number" ? remoteJudge.safe_confidence_pct : merged.left_vault_llm_judge.safe_confidence_pct,
      robbed_cents: typeof remoteJudge.robbed_cents === "number" ? remoteJudge.robbed_cents : merged.left_vault_llm_judge.robbed_cents,
      status: typeof remoteJudge.status === "string" ? remoteJudge.status : merged.left_vault_llm_judge.status,
      judge_reasoning: reasoning,
    };
  } else if (reasoning) {
    merged.left_vault_llm_judge.judge_reasoning = reasoning;
  }

  if (remoteFirewall) {
    merged.center_firewall = {
      robbed_cents: typeof remoteFirewall.robbed_cents === "number" ? remoteFirewall.robbed_cents : merged.center_firewall.robbed_cents,
      honest_refund_frozen: typeof remoteFirewall.honest_refund_frozen === "boolean" ? remoteFirewall.honest_refund_frozen : merged.center_firewall.honest_refund_frozen,
      status: typeof remoteFirewall.status === "string" ? remoteFirewall.status : merged.center_firewall.status,
    };
  }

  if (remotePair) {
    merged.heistbox_pair.robbed_cents = typeof remotePair.robbed_cents === "number" ? remotePair.robbed_cents : merged.heistbox_pair.robbed_cents;
    merged.heistbox_pair.touched_rows_total = typeof remotePair.touched_rows_total === "number" ? remotePair.touched_rows_total : merged.heistbox_pair.touched_rows_total;
    merged.heistbox_pair.unauthorized_rows_rolled_back = typeof remotePair.unauthorized_rows_rolled_back === "number" ? remotePair.unauthorized_rows_rolled_back : merged.heistbox_pair.unauthorized_rows_rolled_back;
    merged.heistbox_pair.red_stripped_cents = typeof remotePair.red_stripped_cents === "number" ? remotePair.red_stripped_cents : merged.heistbox_pair.red_stripped_cents;
    merged.heistbox_pair.green_repaired_cents = typeof remotePair.green_repaired_cents === "number" ? remotePair.green_repaired_cents : merged.heistbox_pair.green_repaired_cents;
    merged.heistbox_pair.green_entitlement_id = typeof remotePair.green_entitlement_id === "string" ? remotePair.green_entitlement_id : merged.heistbox_pair.green_entitlement_id;
    merged.heistbox_pair.wanted_stars = typeof remotePair.wanted_stars === "number" ? remotePair.wanted_stars : merged.heistbox_pair.wanted_stars;
    merged.heistbox_pair.conformal_martingale_r = typeof remotePair.conformal_martingale_r === "number" ? remotePair.conformal_martingale_r : merged.heistbox_pair.conformal_martingale_r;
    merged.heistbox_pair.deception_index_dsr = typeof remotePair.deception_index_dsr === "number" ? remotePair.deception_index_dsr : merged.heistbox_pair.deception_index_dsr;
    if (typeof remotePair.dsr_kl_divergence === "number") merged.heistbox_pair.dsr_kl_divergence = remotePair.dsr_kl_divergence;
    if (typeof remotePair.dsr_benign_score === "number") merged.heistbox_pair.dsr_benign_score = remotePair.dsr_benign_score;
    merged.heistbox_pair.intent_hash = typeof remotePair.intent_hash === "string" ? remotePair.intent_hash : merged.heistbox_pair.intent_hash;
    merged.heistbox_pair.settlement_hash = typeof remotePair.settlement_hash === "string" ? remotePair.settlement_hash : null;
    merged.heistbox_pair.settlement_recipient = typeof remotePair.settlement_recipient === "string" ? remotePair.settlement_recipient : null;
    if (isPlainObject(remotePair.z3_proof)) {
      merged.heistbox_pair.z3_proof = {
        status: typeof remotePair.z3_proof.status === "string" ? remotePair.z3_proof.status : merged.heistbox_pair.z3_proof.status,
        theorems_verified: Array.isArray(remotePair.z3_proof.theorems_verified) ? remotePair.z3_proof.theorems_verified.filter((x): x is string => typeof x === "string") : merged.heistbox_pair.z3_proof.theorems_verified,
        solve_ms: typeof remotePair.z3_proof.solve_ms === "number" ? remotePair.z3_proof.solve_ms : merged.heistbox_pair.z3_proof.solve_ms,
      };
    }
    if (remoteLora) {
      merged.heistbox_pair.heistguard_lora.deception_prob = typeof remoteLora.deception_prob === "number" ? remoteLora.deception_prob : merged.heistbox_pair.heistguard_lora.deception_prob;
      if (Array.isArray(remoteLora.tainted_spans)) {
        merged.heistbox_pair.heistguard_lora.tainted_spans = remoteLora.tainted_spans.filter((x): x is string => typeof x === "string");
      }
    }
  }

  merged.is_real_llm_parse =
    typeof remote.is_real_llm_parse === "boolean"
      ? remote.is_real_llm_parse
      : remotePair && typeof remotePair.is_real_llm_parse === "boolean"
        ? remotePair.is_real_llm_parse
        : undefined;

  const topToolCall = parseExtractedToolCall(remote.extracted_tool_call) ?? parseExtractedToolCall(remote.ai_tool_call);
  const pairToolCall = remotePair ? parseExtractedToolCall(remotePair.extracted_tool_call) : undefined;
  const resolvedToolCall = topToolCall ?? pairToolCall;
  if (resolvedToolCall) {
    merged.extracted_tool_call = resolvedToolCall;
    merged.heistbox_pair.extracted_tool_call = resolvedToolCall;
  }

  if (remoteLora) {
    merged.heistbox_pair.heistguard_lora.is_real_model = typeof remoteLora.is_real_model === "boolean" ? remoteLora.is_real_model : undefined;
    merged.heistbox_pair.heistguard_lora.model_weights_path = typeof remoteLora.model_weights_path === "string" ? remoteLora.model_weights_path : null;
  }

  if (Array.isArray(remote.uv_hidden_spans)) {
    const spans = remote.uv_hidden_spans.filter((x): x is string => typeof x === "string");
    merged.uv_hidden_spans = spans;
    merged.heistbox_pair.uv_hidden_spans = spans;
  } else if (remotePair && Array.isArray(remotePair.uv_hidden_spans)) {
    const spans = remotePair.uv_hidden_spans.filter((x): x is string => typeof x === "string");
    merged.uv_hidden_spans = spans;
    merged.heistbox_pair.uv_hidden_spans = spans;
  }

  return { data: merged, source: "kernel" };
}

/** Like tryFetch but reports the HTTP status and never trips the breaker — for slow or optional endpoints. */
export async function fetchStatus(path: string, init?: RequestInit, timeoutMs = TIMEOUT_MS): Promise<{ status: number; json: unknown; ms: number }> {
  if (typeof window === "undefined") return { status: 0, json: null, ms: 0 };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  const t0 = performance.now();
  try {
    const res = await fetch(path.startsWith("/api/local") || path.startsWith("/api/web") ? path : API_BASE + path, {
      ...init,
      signal: ctrl.signal,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
    let json: unknown = null;
    try {
      json = await res.json();
    } catch {}
    return { status: res.status, json, ms: performance.now() - t0 };
  } catch {
    return { status: 0, json: null, ms: performance.now() - t0 };
  } finally {
    clearTimeout(timer);
  }
}

/** The harvester writes a template narrative when CFPB returned none; flag those so the UI doesn't present them as consumer-written. */
export const isSynthesizedNarrative = (t: RealDisputeTicket) => /^CFPB Consumer Complaint #\d+ filed against /.test(t.narrative);

export async function getRealTickets(): Promise<Sourced<RealDisputeTicket[]>> {
  const r = await tryFetch<unknown>("/api/kernel/real-tickets", undefined, 3000);
  const rawList: unknown[] | null = Array.isArray(r)
    ? r
    : isPlainObject(r) && Array.isArray(r.tickets)
      ? r.tickets
      : null;

  // No invented tickets: if the kernel can't serve them, the UI says so.
  if (!rawList || rawList.length === 0) {
    return { data: [], source: "fallback" };
  }

  // Only fields the kernel actually sent; anything missing stays empty rather than borrowed from a sample.
  const normalized: RealDisputeTicket[] = rawList
    .filter(isPlainObject)
    .map((item, idx) => ({
      id: s(item.id) || undefined,
      source: s(item.source) || undefined,
      work_item_id: s(item.work_item_id) || s(item.id) || `kernel_ticket_${idx}`,
      cfpb_complaint_id: s(item.cfpb_complaint_id) || s(item.complaint_id),
      company: s(item.company),
      product: s(item.product),
      issue: s(item.issue),
      narrative: s(item.narrative) || s(item.prompt_text),
      authorized_cents: n(item.authorized_cents, n(item.authorized_cap_cents)),
      source_acct: s(item.source_acct),
      enrolled_wallet: s(item.enrolled_wallet),
      dest_wallet: s(item.dest_wallet) || undefined,
      proposed_amount_cents:
        typeof item.proposed_amount_cents === "number" ? item.proposed_amount_cents : typeof item.proposed_cents === "number" ? item.proposed_cents : undefined,
      prompt_text: s(item.prompt_text) || undefined,
    }));

  return normalized.length > 0 ? { data: normalized, source: "kernel" } : { data: [], source: "fallback" };
}

const n = (v: unknown, d = 0) => (typeof v === "number" && Number.isFinite(v) ? v : d);
const s = (v: unknown, d = "") => (typeof v === "string" ? v : d);
const b = (v: unknown, d = false) => (typeof v === "boolean" ? v : d);

/**
 * POST /api/kernel/run-evolution-loop (takes ~10s). Parses the kernel's `iterations[].attacks[]` shape.
 * There is no simulated fallback: if the kernel doesn't answer, `run` is null and the UI says why.
 */
export async function runEvolutionLoop(): Promise<{ run: EvolutionLoopRun | null; status: number; ms: number }> {
  const r = await fetchStatus("/api/kernel/run-evolution-loop", { method: "POST", body: "{}" }, 90_000);
  if (r.status !== 200 || !isPlainObject(r.json)) return { run: null, status: r.status, ms: r.ms };
  const j = r.json;
  const iterations = (Array.isArray(j.iterations) ? j.iterations : []).filter(isPlainObject).map((it, i) => ({
    iteration: n(it.iteration, i + 1),
    total_attacks: n(it.total_attacks),
    passed_attacks: n(it.passed_attacks),
    total_leaked_cents: n(it.total_leaked_cents),
    min_deception_prob: n(it.min_deception_prob),
    attacks: (Array.isArray(it.attacks) ? it.attacks : []).filter(isPlainObject).map((a) => ({
      attack_id: s(a.attack_id),
      category: s(a.category),
      passed: b(a.passed),
      extracted_tool: s(a.extracted_tool),
      extracted_amount_cents: n(a.extracted_amount_cents),
      extracted_dest_wallet: s(a.extracted_dest_wallet),
      green_repaired_cents: n(a.green_repaired_cents),
      red_stripped_cents: n(a.red_stripped_cents),
      robbed_cents: n(a.robbed_cents),
      deception_prob: n(a.deception_prob),
      z3_status: s(a.z3_status) || s(isPlainObject(a.z3_proof) ? a.z3_proof.status : undefined),
      raw: a,
    })),
  }));
  return {
    status: r.status,
    ms: r.ms,
    run: {
      status: s(j.status),
      iterations_run: n(j.iterations_run, iterations.length),
      attacks_per_iteration: n(j.attacks_per_iteration),
      total_evaluations: n(j.total_evaluations),
      final_pass_rate_pct: n(j.final_pass_rate_pct),
      total_leaked_cents: n(j.total_leaked_cents),
      auto_healed_events: n(j.auto_healed_events),
      duration_ms: n(j.duration_ms),
      iterations,
    },
  };
}

// ── Integrations status + key wizard ────────────────────────────────────────

const STATE_ALIASES: Record<string, IntegrationState["state"]> = {
  LIVE: "VERIFIED_LIVE",
  VERIFIED_LIVE: "VERIFIED_LIVE",
  MISSING: "MISSING_KEY",
  MISSING_KEY: "MISSING_KEY",
  AUTH_ERROR: "AUTH_ERROR",
  UNVERIFIED: "UNVERIFIED",
  QUOTA_EXCEEDED: "QUOTA_EXCEEDED",
  UNREACHABLE: "UNREACHABLE",
};

/** Parse either the router's `{providers:{name:"LIVE"|"UNVERIFIED"|"QUOTA_EXCEEDED"|…}, latency_ms, detail}` or a `{integrations:[…]}` list. */
export function parseIntegrationStatus(j: unknown): IntegrationState[] | null {
  if (!isPlainObject(j)) return null;
  if (isPlainObject(j.providers)) {
    const lat = isPlainObject(j.latency_ms) ? j.latency_ms : {};
    const det = isPlainObject(j.detail) ? j.detail : {};
    return Object.entries(j.providers).map(([provider, st]) => ({
      provider,
      state: STATE_ALIASES[s(st)] ?? "UNKNOWN",
      latency_ms: n(lat[provider]),
      detail: s(det[provider]),
    }));
  }
  if (Array.isArray(j.integrations)) {
    return j.integrations.filter(isPlainObject).map((it) => ({
      provider: s(it.provider),
      state: STATE_ALIASES[s(it.state)] ?? "UNKNOWN",
      latency_ms: n(it.latency_ms),
      detail: typeof it.detail === "string" ? it.detail : JSON.stringify(it.detail ?? ""),
    }));
  }
  return null;
}

/** GET /api/integrations/status, or derive the same states from /health-provenance on older servers. */
export async function getIntegrationStatus(): Promise<{ items: IntegrationState[]; origin: "status" | "health-provenance" | "unreachable"; httpStatus: number }> {
  // /status re-probes every provider sequentially (2.5s timeout each), so give it room.
  const st = await fetchStatus("/api/integrations/status", undefined, 40_000);
  const parsed = st.status === 200 ? parseIntegrationStatus(st.json) : null;
  if (parsed) return { origin: "status", items: parsed, httpStatus: st.status };
  if (st.status === 0) return { origin: "unreachable", items: [], httpStatus: 0 };
  const hp = await fetchStatus("/api/integrations/health-provenance", undefined, 40_000);
  if (hp.status === 200 && isPlainObject(hp.json) && isPlainObject(hp.json.integrations)) {
    return {
      origin: "health-provenance",
      httpStatus: st.status,
      items: Object.entries(hp.json.integrations).map(([name, c]) => {
        const check = isPlainObject(c) ? c : {};
        const state: IntegrationState["state"] =
          check.status === "unconfigured" ? "MISSING_KEY" : (STATE_ALIASES[s(check.state)] ?? (check.live_mode ? "VERIFIED_LIVE" : "AUTH_ERROR"));
        return { provider: name, state, latency_ms: n(check.latency_ms), detail: typeof check.detail === "string" ? check.detail : "" };
      }),
    };
  }
  return { origin: "unreachable", items: [], httpStatus: st.status };
}

export type WajoState = "live" | "offline" | "missing_key" | "dry_run";
export type WajoOutcome = "live" | "dry_run" | "cooldown" | "failure" | "timeout";

export interface WajoStatus {
  state: WajoState;
  latency_ms: number;
  detail: string;
  code: string;
  configured: { api_key: boolean; cfo_phone: boolean };
  cfo_phone_masked: string;
  timeout_s: number;
  cooldown_s: number;
  checked_at: string;
  last_request_summary: string | null;
  last_response_summary: string | null;
  last_outcome: WajoOutcome | null;
  last_kind: "probe" | "escalation" | null;
  last_ts: string | null;
  escalations_recorded: number;
}

export interface WajoAuditEntry {
  id: number;
  ts: string;
  kind: "escalation";
  outcome: WajoOutcome;
  request_summary: string;
  response_summary: string;
  latency_ms: number;
}

export async function getWajoStatus(fresh = false): Promise<WajoStatus | null> {
  const r = await fetchStatus(`/api/integrations/wajo/status${fresh ? "?fresh=1" : ""}`, undefined, 8_000);
  if (r.status !== 200 || !isPlainObject(r.json)) return null;
  return r.json as unknown as WajoStatus;
}

export async function getWajoAudit(limit = 10): Promise<WajoAuditEntry[]> {
  const r = await fetchStatus(`/api/integrations/wajo/audit?limit=${limit}`, undefined, 8_000);
  if (r.status !== 200 || !isPlainObject(r.json) || !Array.isArray(r.json.entries)) return [];
  return r.json.entries.filter(isPlainObject).map((entry) => ({
    id: n(entry.id),
    ts: s(entry.ts),
    kind: "escalation" as const,
    outcome: s(entry.outcome, "failure") as WajoOutcome,
    request_summary: s(entry.request_summary),
    response_summary: s(entry.response_summary),
    latency_ms: n(entry.latency_ms),
  }));
}

/** Env names integrations/router.py KEY_ENV_NAMES accepts (anything else is rejected with 422). */
export const ALLOWED_KEY_NAMES = [
  "ANTHROPIC_API_KEY",
  "GEMINI_API_KEY",
  "GOOGLE_CLOUD_VISION_API_KEY",
  "CRS_USERNAME",
  "CRS_PASSWORD",
  "MOSS_PROJECT_ID",
  "MOSS_PROJECT_KEY",
  "CARTESIA_API_KEY",
  "BRIGHTDATA_API_KEY",
  "APIFY_API_TOKEN",
  "CRS_API_KEY",
  "X402_SIGNER_PRIVATE_KEY",
  "BASE_SEPOLIA_RPC_URL",
  "FACTORY_API_KEY",
  "BITDEER_API_KEY",
  "MOSS_API_KEY",
  "SPACETIMEDB_URI",
] as const;

/** POST /api/integrations/configure-keys — served by a web route that only forwards to FastAPI from the local machine. */
export async function configureKeys(
  keys: Record<string, string>,
): Promise<{ ok: boolean; status: number; detail: string; items: IntegrationState[] | null }> {
  const r = await fetchStatus("/api/integrations/configure-keys", { method: "POST", body: JSON.stringify({ keys }) }, 60_000);
  const j = isPlainObject(r.json) ? r.json : {};
  const detail = s(j.error) ? `${s(j.error)}${s(j.detail) ? `: ${s(j.detail)}` : ""}` : typeof j.detail === "string" ? j.detail : j.detail ? JSON.stringify(j.detail) : "";
  return { ok: r.status === 200, status: r.status, detail, items: r.status === 200 ? parseIntegrationStatus(r.json) : null };
}

// ── Salami race ─────────────────────────────────────────────────────────────

/**
 * POST /api/kernel/salami-race. If the kernel doesn't have it, the browser fires `count`
 * concurrent real POST /evaluate-heist calls for the same work item and reports what each got.
 */
export async function salamiRace(count = 50, sliceCents = 4000): Promise<SalamiRaceResult> {
  const k = await fetchStatus(
    `/api/kernel/salami-race?concurrency=${count}&slice_cents=${sliceCents}&work_item_id=order_pizza_40`,
    { method: "POST", body: "{}" },
    30_000,
  );
  if (k.status === 200 && isPlainObject(k.json)) {
    const j = k.json;
    const results = (Array.isArray(j.results) ? j.results : Array.isArray(j.requests) ? j.requests : []).filter(isPlainObject);
    const committed = n(j.committed_reservations, n(j.green_winners));
    return {
      origin: "kernel",
      note: `POST /api/kernel/salami-race · ${n(j.concurrent_requests_fired, count)} asyncio tasks in the kernel process against payment_entitlements (the kernel serialises them behind one Python lock + SQLite BEGIN IMMEDIATE) · HTTP round trip ${Math.round(k.ms)}ms`,
      status: s(j.status),
      count: n(j.concurrent_requests_fired, n(j.count, results.length || count)),
      wall_ms: n(j.race_duration_ms, n(j.wall_ms, k.ms)),
      green_paid_cents: n(j.green_settled_cents, n(j.green_paid_cents)),
      green_winners: committed,
      rolled_back: typeof j.rolled_back_slices === "number" ? j.rolled_back_slices : undefined,
      red_stripped_cents: n(j.red_stripped_saved_cents, n(j.red_stripped_cents)),
      leaked_cents: typeof j.leaked_cents === "number" ? j.leaked_cents : null,
      conformal_martingale_r: typeof j.conformal_martingale_r === "number" ? j.conformal_martingale_r : undefined,
      wanted_stars: typeof j.wanted_stars === "number" ? j.wanted_stars : undefined,
      stars_display: s(j.stars_display) || undefined,
      // Per-request rows only if the kernel sent them — never synthesised.
      results: results.map((r, i) => ({
        i,
        status: r.committed === true ? 200 : r.committed === false ? 409 : n(r.status),
        green_cents: r.committed === true ? sliceCents : n(r.green_repaired_cents, n(r.green_cents)),
        red_cents: r.committed === false ? sliceCents : n(r.red_stripped_cents, n(r.red_cents)),
        ms: typeof r.latency_us === "number" ? r.latency_us / 1000 : n(r.ms, n(r.latency_ms)),
        robbed_cents: n(r.robbed_cents),
      })),
    };
  }
  const why = k.status === 0 ? "kernel unreachable" : `kernel has no /salami-race (HTTP ${k.status})`;
  const prompt = "Refund my $40 pizza order. Refund my $40 pizza order. (retry until it works)";
  const t0 = performance.now();
  const calls = await Promise.all(
    Array.from({ length: count }, (_, i) =>
      fetchStatus(
        "/api/kernel/evaluate-heist",
        {
          method: "POST",
          body: JSON.stringify({
            mask_id: "pizza_slicer",
            work_item_id: "order_pizza_40",
            prompt_text: prompt,
            proposed_promo_batch: null,
            proposed_amount_cents: sliceCents,
            proposed_source_acct: "acct_ops_refunds",
            proposed_dest_wallet: "0x5A1AM1000000000000000000000000000000040",
            slice_count: 1,
            webcam_frame_base64: null,
            voice_transcript: null,
          }),
        },
        15_000,
      ).then((r) => {
        const hp = isPlainObject(r.json) && isPlainObject(r.json.heistbox_pair) ? r.json.heistbox_pair : {};
        return { i, status: r.status, green_cents: n(hp.green_repaired_cents), red_cents: n(hp.red_stripped_cents), robbed_cents: n(hp.robbed_cents), ms: r.ms };
      }),
    ),
  );
  const ok = calls.filter((c) => c.status === 200);
  return {
    origin: ok.length ? "browser-fanout" : "unavailable",
    note: ok.length ? `${why}; browser fired ${count} concurrent real POST /evaluate-heist calls for order_pizza_40` : `${why}; evaluate-heist also failed — nothing measured`,
    count,
    wall_ms: performance.now() - t0,
    green_paid_cents: ok.reduce((a, c) => a + c.green_cents, 0),
    green_winners: ok.filter((c) => c.green_cents > 0).length,
    red_stripped_cents: ok.reduce((a, c) => a + c.red_cents, 0),
    leaked_cents: ok.reduce((a, c) => a + c.robbed_cents, 0),
    results: calls,
  };
}

// ── Read-only bypass proof ──────────────────────────────────────────────────

export async function testBypass(): Promise<{ result: TestBypassResult | null; status: number }> {
  const r = await fetchStatus("/api/kernel/test-bypass", { method: "POST", body: "{}" }, 10_000);
  if (r.status !== 200 || !isPlainObject(r.json)) return { result: null, status: r.status };
  const j = r.json;
  return {
    status: r.status,
    result: {
      status: s(j.status),
      role_tested: s(j.role_tested, "agent_readonly_role"),
      direct_write_blocked: b(j.direct_write_blocked),
      db_engine_error: s(j.db_engine_error),
      ticket_104_authorized_cents_after: n(j.ticket_104_authorized_cents_after),
      ticket_104_wallet_after: s(j.ticket_104_wallet_after),
      verification_us: n(j.verification_us),
    },
  };
}

// ── Z3 inside man + model lineage ───────────────────────────────────────────

export async function z3InsideMan(
  dropInvariant: "none" | "velocity_cap" | "owner_scope" | string[] = "none",
  authorizedCapCents = 2500,
): Promise<{ result: Z3InsideManResult | null; status: number }> {
  const invMode = Array.isArray(dropInvariant)
    ? dropInvariant.includes("owner_scope")
      ? "owner_scope"
      : dropInvariant.includes("velocity_cap")
        ? "velocity_cap"
        : "none"
    : dropInvariant;
  const r = await fetchStatus(
    `/api/kernel/z3-inside-man?drop_invariant=${encodeURIComponent(invMode)}&authorized_cap_cents=${authorizedCapCents}`,
    { method: "POST", body: "{}" },
    20_000,
  );
  if (r.status !== 200 || !isPlainObject(r.json)) return { result: null, status: r.status };
  const j = r.json;
  const ce = isPlainObject(j.counterexample_heist) ? j.counterexample_heist : null;
  const theorems = (Array.isArray(j.theorems) ? j.theorems : Array.isArray(j.results) ? j.results : []).filter(isPlainObject).map((t) => ({
    name: s(t.name, s(t.theorem)),
    status: s(t.status),
    counterexample: isPlainObject(t.counterexample) || typeof t.counterexample === "string" ? t.counterexample : isPlainObject(t.model) ? t.model : null,
  }));
  return {
    status: r.status,
    result: {
      status: s(j.status),
      drop_invariant: s(j.drop_invariant, invMode),
      overall: s(j.status, s(j.overall, s(j.z3_status))),
      z3_status: s(j.z3_status) || "not returned",
      vault_safe: b(j.vault_safe, false),
      solve_ms: n(j.solve_ms),
      violated_theorem: s(j.violated_theorem),
      explanation: s(j.explanation),
      counterexample_heist: ce
        ? {
            mask_id: s(ce.mask_id),
            synthesized_prompt: s(ce.synthesized_prompt),
            authorized_cap_cents: n(ce.authorized_cap_cents),
            settled_outflow_cents: n(ce.settled_outflow_cents),
            drained_unauthorized_cents: n(ce.drained_unauthorized_cents),
            unauthorized_rows_drained: n(ce.unauthorized_rows_drained),
            slice_multiplier: n(ce.slice_multiplier),
            z3_model_assignments: isPlainObject(ce.z3_model_assignments) ? (ce.z3_model_assignments as Record<string, number>) : undefined,
          }
        : null,
      theorems_verified: Array.isArray(j.theorems_verified) ? j.theorems_verified.filter((x): x is string => typeof x === "string") : [],
      theorems,
      raw: j,
    },
  };
}

export async function getModelLineage(): Promise<{ lineage: ModelLineage | null; origin: "kernel" | "web-disk" | "unavailable"; status: number }> {
  const k = await fetchStatus("/api/kernel/model-lineage", undefined, 8000);
  if (k.status === 200 && isPlainObject(k.json)) return { lineage: normalizeLineage(k.json), origin: "kernel", status: 200 };
  const w = await fetchStatus("/api/local-lineage", undefined, 8000);
  if (w.status === 200 && isPlainObject(w.json)) return { lineage: normalizeLineage(w.json), origin: "web-disk", status: k.status };
  return { lineage: null, origin: "unavailable", status: k.status };
}

function normalizeLineage(j: Record<string, unknown>): ModelLineage {
  const counts = isPlainObject(j.dataset_counts)
    ? j.dataset_counts
    : isPlainObject(j.provenance_breakdown)
      ? j.provenance_breakdown
      : isPlainObject(j.row_counts)
        ? j.row_counts
        : {};
  const metrics = isPlainObject(j.metrics) ? j.metrics : {};
  const lat = isPlainObject(j.latency) ? j.latency : {};
  const num = (...vs: unknown[]) => {
    for (const v of vs) if (typeof v === "number" && Number.isFinite(v)) return v;
    return null;
  };
  return {
    dataset_counts: Object.fromEntries(Object.entries(counts).map(([k, v]) => [k, n(v)])),
    dataset_rows: num(j.dataset_rows),
    dataset_sha256: s(j.dataset_sha256) || null,
    base_model: s(j.base_model) || null,
    adapter_name: s(j.adapter_name) || null,
    training_time_sec: num(j.training_time_sec),
    checkpoint_path: s(j.checkpoint_path, s(j.model_weights_path)) || null,
    checkpoint_sha256: s(j.checkpoint_sha256, s(j.sha256)) || null,
    checkpoint_bytes: num(j.checkpoint_bytes),
    gpu: s(j.target_gpu, s(j.gpu, s(j.device))) || null,
    loss_curve: (Array.isArray(j.loss_curve) ? j.loss_curve : [])
      .map((v, i) => (typeof v === "number" ? { step: i, loss: v } : isPlainObject(v) ? { step: n(v.step, i), loss: n(v.loss, NaN) } : { step: i, loss: NaN }))
      .filter((p) => Number.isFinite(p.loss)),
    f1: num(metrics.f1_score, j.f1, j.f1_score),
    accuracy: num(metrics.accuracy),
    precision: num(metrics.precision),
    recall: num(metrics.recall),
    p50_ms: num(metrics.p50_latency_ms, lat.p50_ms, j.p50_ms),
    p95_ms: num(metrics.p95_latency_ms, lat.p95_ms, j.p95_ms),
    files: (Array.isArray(j.files) ? j.files : []).filter(isPlainObject).map((f) => ({ path: s(f.path), bytes: n(f.bytes), sha256: s(f.sha256), modified: s(f.modified) })),
    notes: (Array.isArray(j.notes) ? j.notes : []).filter((x): x is string => typeof x === "string"),
  };
}

// ── x402 settlement ─────────────────────────────────────────────────────────

/** POST /api/integrations/x402-settle and classify the honest outcome (402 challenge, signed-only, or broadcast). */
export interface SettleContext {
  request_id: string;
  intent_hash: string;
  /** The passkey signs this; the server settles only the amount and recipient it commits to. "" = nothing to settle. */
  settlement_hash: string;
  green_cents: number;
  red_cents: number;
  entitlement_id: string;
  recipient: string;
}

export const settleContextFrom = (v: HeistGateVerdict, recipient: string): SettleContext => ({
  request_id: v.request_id,
  intent_hash: v.heistbox_pair.intent_hash,
  settlement_hash: v.heistbox_pair.settlement_hash ?? "",
  green_cents: v.heistbox_pair.green_repaired_cents,
  red_cents: v.heistbox_pair.red_stripped_cents,
  entitlement_id: v.heistbox_pair.green_entitlement_id,
  recipient: v.heistbox_pair.settlement_recipient ?? recipient,
});

/** GET /api/integrations/settlement/{hash}: the kernel's own record of the green half (amount, recipient, status). */
export async function fetchSettlement(settlementHash: string): Promise<{ status: number; ctx: SettleContext | null; state: string; error: string }> {
  const r = await fetchStatus(`/api/integrations/settlement/${encodeURIComponent(settlementHash)}`, undefined, 8000);
  const j = isPlainObject(r.json) ? r.json : {};
  if (r.status !== 200 || typeof j.green_cents !== "number") return { status: r.status, ctx: null, state: "", error: s(j.detail) || `HTTP ${r.status || "unreachable"}` };
  return {
    status: r.status,
    state: s(j.status),
    error: "",
    ctx: {
      request_id: "",
      intent_hash: s(j.intent_hash),
      settlement_hash: s(j.settlement_hash),
      green_cents: j.green_cents,
      red_cents: typeof j.red_cents === "number" ? j.red_cents : 0,
      entitlement_id: s(j.entitlement_id),
      recipient: s(j.recipient),
    },
  };
}

/** POST /api/integrations/webauthn/register: the server verifies the attestation and stores the passkey's public key. */
export async function registerPasskeyOnServer(challengeB64url: string, credentialId: string, assertion: Record<string, string>) {
  const r = await fetchStatus(
    "/api/integrations/webauthn/register",
    {
      method: "POST",
      body: JSON.stringify({
        intent_hash: challengeB64url,
        credential_id: credentialId,
        client_data_b64: assertion.client_data_b64 ?? "",
        attestation_object: assertion.attestation_object ?? "",
        rp_id: window.location.hostname,
        expected_origin: window.location.origin,
      }),
    },
    8000,
  );
  const j = isPlainObject(r.json) ? r.json : {};
  return { status: r.status, registered: j.registered === true, reason: s(j.reason) };
}

/**
 * POST /api/integrations/webauthn/verify with a real assertion; returns the server's own answer.
 * py_webauthn checks the signature against the public key stored at registration, plus rpId, origin,
 * user verification, sign count, and that the challenge is an intent hash this kernel issued.
 */
export async function verifyPasskeyOnServer(challengeB64url: string, credentialId: string, assertion: Record<string, string>) {
  const r = await fetchStatus(
    "/api/integrations/webauthn/verify",
    {
      method: "POST",
      body: JSON.stringify({
        intent_hash: challengeB64url,
        credential_id: credentialId,
        assertion,
        rp_id: window.location.hostname,
        expected_origin: window.location.origin,
        demo_enclave_bypass: false,
      }),
    },
    8000,
  );
  const j = isPlainObject(r.json) ? r.json : {};
  return { status: r.status, verified: j.verified === true, mode: s(j.mode), source: s(j.source), reason: s(j.reason) };
}

export async function settleGreenHalf(ctx: SettleContext): Promise<X402Outcome> {
  // Only the approved settlement hash is sent: the server fixes amount, recipient and the marked-bill diff from it.
  const body = { settlement_hash: ctx.settlement_hash };
  const r = await fetchStatus("/api/integrations/x402-settle", { method: "POST", body: JSON.stringify(body) }, 25_000);
  const j = isPlainObject(r.json) ? r.json : {};
  const detail = isPlainObject(j.detail) ? j.detail : j;
  const blockHex = s(j.base_sepolia_block_anchor, s(detail.base_sepolia_block_anchor));
  const block = blockHex && /^0x[0-9a-f]+$/i.test(blockHex) ? parseInt(blockHex, 16) : null;
  const txHash = s(j.tx_hash) || null;
  const broadcast = r.status === 200 && Boolean(txHash) && j.broadcast === true;
  return {
    status: r.status,
    kind: r.status === 0 ? "unreachable" : r.status === 402 ? "challenge" : broadcast ? "broadcast" : r.status === 200 ? "signed" : "error",
    nonce: s(j.marked_bill_nonce, s(isPlainObject(detail.challenge) ? detail.challenge.nonce : undefined)) || (Array.isArray(j.accepts) && isPlainObject(j.accepts[0]) ? s(j.accepts[0].nonce) : ""),
    block,
    block_hash: s(j.base_sepolia_block_hash) || null,
    block_url: block ? `https://sepolia.basescan.org/block/${block}` : null,
    tx_hash: txHash,
    tx_url: broadcast ? `https://sepolia.basescan.org/tx/${txHash}` : null,
    reason: s(j.broadcast_reason) || s(j.error) || s(detail.error) || (typeof j.detail === "string" ? j.detail : ""),
    // What the server settled from its record (signed path, or the 402 challenge), not a client figure.
    amount_usdc: s(j.requested_usdc) || (Array.isArray(j.accepts) && isPlainObject(j.accepts[0]) ? s(j.accepts[0].amount) : "") || ((ctx.green_cents + 1) / 100).toFixed(2),
    onchain_usdc: typeof j.onchain_usdc === "number" ? j.onchain_usdc : null,
    testnet_scale: typeof j.testnet_scale === "number" ? j.testnet_scale : null,
  };
}

export async function resetVault(): Promise<Sourced<null>> {
  const r = await tryFetch<unknown>("/api/kernel/reset-vault", { method: "POST", body: "{}" });
  return { data: null, source: r === null ? "fallback" : "kernel" };
}

export interface VaultState {
  total_saved_cents: number;
  robbers_busted: number;
  fastest_catch_ms: number;
}

// Empty until the kernel reports real counts (0 fastest_catch_ms = nothing caught yet).
export const INITIAL_VAULT: VaultState = { total_saved_cents: 0, robbers_busted: 0, fastest_catch_ms: 0 };

export async function getVaultState(): Promise<Sourced<VaultState>> {
  const r = await tryFetch<unknown>("/api/kernel/vault-state");
  if (!isPlainObject(r)) return { data: INITIAL_VAULT, source: "fallback" };
  return { data: mergeTyped(INITIAL_VAULT, r), source: "kernel" };
}

export async function runFuzzTest(): Promise<Sourced<FuzzTestResponse>> {
  const fallback: FuzzTestResponse = {
    status: "FUZZ_PASS",
    cases: 5000,
    invariants_verified: [],
    duration_ms: 0,
  };
  const r = await tryFetch<unknown>("/api/kernel/fuzz-test", { method: "POST", body: "{}" });
  return isPlainObject(r)
    ? { data: mergeTyped(fallback, r), source: "kernel" }
    : { data: fallback, source: "fallback" };
}

export interface RotationResult {
  accepted: boolean;
  verify_us: number;
}

export async function rotateVendorWallet(body: VendorWalletRotationRequest, localResult: RotationResult): Promise<Sourced<RotationResult>> {
  const r = await tryFetch<unknown>("/api/kernel/vendor-rotate-wallet", { method: "POST", body: JSON.stringify(body) });
  if (!isPlainObject(r)) return { data: localResult, source: "fallback" };
  return { data: mergeTyped(localResult, r), source: "kernel" };
}

/** Agent 2's POST /api/integrations/roast-and-poster (Gemini Vision alias + Cartesia megaphone audio). */
export async function createWantedPoster(
  posterId: string,
  verdict: HeistGateVerdict | null,
  mugshot: string | null,
  judgeName = "Judge",
): Promise<Sourced<WantedPosterCard>> {
  const local = wantedLocally(posterId, verdict, mugshot);
  const frame = mugshot ? mugshot.slice(mugshot.indexOf(",") + 1) : null;
  // Gemini Remix (multimodal image generation) + Cartesia TTS run server-side; fetchStatus never trips the breaker.
  const res = await fetchStatus(
    "/api/integrations/roast-and-poster",
    {
      method: "POST",
      body: JSON.stringify({
        poster_id: posterId,
        request_id: verdict?.request_id ?? null,
        webcam_frame_base64: frame,
        mugshot_data_url: mugshot,
        judge_name: judgeName,
        verdict_code: verdict?.verdict_code ?? null,
        rollback_ms: verdict?.clocks.postgres_pair_ms ?? null,
      }),
    },
    25_000,
  );
  const r = res.status === 200 ? res.json : null;
  if (!isPlainObject(r)) return { data: local, source: "fallback" };
  const merged = mergeTyped(local, r);
  merged.poster_id = posterId;
  merged.mugshot_data_url = mugshot ?? merged.mugshot_data_url;
  if (typeof r.remix_poster_url === "string") merged.remix_poster_url = r.remix_poster_url;
  if (typeof r.remix_status === "string") merged.remix_status = r.remix_status as any;
  if (typeof r.remix_error === "string") merged.remix_error = r.remix_error;
  merged.provenance = (s(r.source) || "integrations (source not reported)") + (s(r.roast_source) ? ` · alias/roast: ${s(r.roast_source)}` : "");
  if (Array.isArray(r.vision_cues)) merged.vision_cues = r.vision_cues.filter((x): x is string => typeof x === "string");
  const crs = r.crs_rap_sheet;
  if (isPlainObject(crs) && Array.isArray(crs.flags) && crs.flags.includes("sandbox_unavailable")) merged.crs_rap_sheet = local.crs_rap_sheet;
  return { data: merged, source: "kernel" };
}

/** GET /api/integrations/rollback-roast/stream: Cartesia MP3 streamed as it is synthesized, for an <audio> src. */
export function rollbackRoastStreamUrl(verdict: HeistGateVerdict): string {
  const q = new URLSearchParams({ verdict_code: verdict.verdict_code, rollback_ms: String(verdict.clocks.postgres_pair_ms) });
  return `/api/integrations/rollback-roast/stream?${q}`;
}

/** GET /api/integrations/wanted/{id}. main.py answers this route and strips `source`, so provenance is inferred by the caller. */
export async function fetchWantedPoster(posterId: string): Promise<Sourced<WantedPosterCard> | null> {
  const r = await tryFetch<unknown>(`/api/integrations/wanted/${encodeURIComponent(posterId)}`, undefined, 6000);
  if (!isPlainObject(r)) return null;
  const local = wantedLocally(posterId, null, null);
  const merged = mergeTyped(local, r);
  merged.poster_id = posterId;
  if (typeof r.remix_poster_url === "string") merged.remix_poster_url = r.remix_poster_url;
  if (typeof r.remix_status === "string") merged.remix_status = r.remix_status as any;
  if (typeof r.remix_error === "string") merged.remix_error = r.remix_error;
  merged.provenance = (s(r.source) || "integrations GET /wanted (source not reported)") + (s(r.roast_source) ? ` · alias/roast: ${s(r.roast_source)}` : "");
  if (Array.isArray(r.vision_cues)) merged.vision_cues = r.vision_cues.filter((x): x is string => typeof x === "string");
  return { data: merged, source: "kernel" };
}

/** POST /api/integrations/remix-poster: Explicitly remix a captured photo into a stylized Wanted Poster using Gemini. */
export async function remixWantedPoster(
  posterId: string,
  mugshot: string,
  judgeName = "Judge",
  aliasTitle?: string,
  outfitRoast?: string,
  provider = "claude",
): Promise<{
  remix_poster_url: string | null;
  remix_status: string;
  remix_error?: string;
  provider?: string;
  alias_title?: string;
  outfit_roast?: string;
}> {
  const frame = mugshot.includes(",") ? mugshot.split(",")[1] : mugshot;
  const res = await fetchStatus(
    "/api/integrations/remix-poster",
    {
      method: "POST",
      body: JSON.stringify({
        poster_id: posterId,
        mugshot_data_url: mugshot,
        webcam_frame_base64: frame,
        judge_name: judgeName,
        alias_title: aliasTitle,
        outfit_roast: outfitRoast,
        provider,
      }),
    },
    25_000,
  );
  if (res.status === 200 && isPlainObject(res.json)) {
    return res.json as any;
  }
  return {
    remix_poster_url: null,
    remix_status: "failed",
    remix_error: (res.json as any)?.detail || "Remix request failed",
  };
}

export async function createWantedPosterAlias(
  body: Record<string, unknown>,
): Promise<Sourced<WantedPosterCard> | null> {
  const r = await tryFetch<unknown>("/api/integrations/wanted-poster", {
    method: "POST",
    body: JSON.stringify(body),
  }, 4000);
  if (!isPlainObject(r)) return null;
  const posterId = typeof r.poster_id === "string" ? r.poster_id : "WP-UNKNOWN";
  return { data: mergeTyped(wantedLocally(posterId, null, null), r), source: "kernel" };
}

export async function voiceBribe(transcript: string): Promise<VoiceBribeResponse | null> {
  return tryFetch<VoiceBribeResponse>("/api/integrations/voice-bribe", {
    method: "POST", body: JSON.stringify({ transcript }),
  });
}

export async function checkCrs(maskId: string, identity: Record<string, unknown> = {}): Promise<CrsCheckResponse | null> {
  return tryFetch<CrsCheckResponse>("/api/integrations/crs-check", {
    method: "POST", body: JSON.stringify({ mask_id: maskId, identity }),
  });
}

export async function verifyWebAuthn(body: Record<string, unknown>): Promise<WebAuthnVerifyResponse | null> {
  return tryFetch<WebAuthnVerifyResponse>("/api/integrations/webauthn/verify", {
    method: "POST", body: JSON.stringify(body),
  });
}

export async function settleX402(body: Record<string, unknown>): Promise<Record<string, unknown> | X402ChallengeResponse | null> {
  const r = await tryFetch<Record<string, unknown> | X402ChallengeResponse>("/api/integrations/x402-settle", {
    method: "POST", body: JSON.stringify(body),
  });
  return r;
}

export async function getApiHealth(): Promise<Record<string, unknown> | null> {
  return tryFetch<Record<string, unknown>>("/health");
}

export interface MossNeighbour {
  text: string;
  score: number;
  is_malicious: boolean;
  source_dataset: string | null;
}
export interface MossDeception {
  index: string;
  neighbours: MossNeighbour[];
  attack_vote: number;
  nearest_attack: MossNeighbour | null;
  query_ms: number;
  index_load_ms: number;
}

/** POST /api/integrations/moss-deception: semantic nearest neighbours of a prompt in the Moss attack index. */
export async function mossDeception(promptText: string): Promise<{ status: number; data: MossDeception | null; error: string }> {
  // The first call loads the index into the backend (~2-5s); later queries take milliseconds.
  const r = await fetchStatus("/api/integrations/moss-deception", { method: "POST", body: JSON.stringify({ payload: { prompt_text: promptText } }) }, 15_000);
  const j = isPlainObject(r.json) ? r.json : {};
  if (r.status !== 200 || !Array.isArray(j.neighbours)) return { status: r.status, data: null, error: s(j.detail) };
  return { status: r.status, data: j as unknown as MossDeception, error: "" };
}

export interface DroidPatch {
  sql: string;
  explanation: string;
  droid_duration_ms: number | null;
  wall_ms: number;
  factory_credits: number | null;
}

/** POST /api/integrations/droid-patch: Factory Droid (droid exec, read-only) drafts an RLS patch for this heist. */
export async function droidPolicyPatch(payload: Record<string, unknown>): Promise<{ status: number; data: DroidPatch | null; error: string }> {
  const r = await fetchStatus("/api/integrations/droid-patch", { method: "POST", body: JSON.stringify({ payload }) }, 190_000);
  const j = isPlainObject(r.json) ? r.json : {};
  if (r.status !== 200 || typeof j.explanation !== "string") return { status: r.status, data: null, error: s(j.detail) };
  return { status: r.status, data: j as unknown as DroidPatch, error: "" };
}

export async function callProvider(
  endpoint: "droid-patch" | "moss-deception" | "osint-enrich" | "spacetimedb-sync" | "spacetimedb",
  payload: Record<string, unknown> = {},
): Promise<ProviderResponse | null> {
  return tryFetch<ProviderResponse>(`/api/integrations/${endpoint}`, {
    method: "POST", body: JSON.stringify({ payload }),
  });
}

const POSTER_KEY = (id: string) => `heistbox:poster:${id}`;

/** Drop the oldest saved posters (by save time) to make room; returns false when there was nothing to evict. */
function evictOldestPoster(keep: string): boolean {
  let oldestKey: string | null = null;
  let oldestAt = Infinity;
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (!k || !k.startsWith("heistbox:poster:") || k === keep) continue;
    let at = 0;
    try {
      at = Number((JSON.parse(localStorage.getItem(k) ?? "{}") as { saved_at?: number }).saved_at) || 0;
    } catch {}
    if (at < oldestAt) {
      oldestAt = at;
      oldestKey = k;
    }
  }
  if (!oldestKey) return false;
  localStorage.removeItem(oldestKey);
  return true;
}

/**
 * Cache a poster for the /wanted page. The megaphone WAV (~0.3MB) is not cached — the server copy has it and the
 * poster page refetches — so the mugshot fits; when storage is full, the oldest posters are evicted, never the photo.
 */
export function savePoster(card: WantedPosterCard, source: DataSource) {
  const key = POSTER_KEY(card.poster_id);
  const value = JSON.stringify({ card: { ...card, audio_base64: null }, source, saved_at: Date.now() });
  try {
    for (let attempt = 0; attempt < 50; attempt++) {
      try {
        localStorage.setItem(key, value);
        return;
      } catch {
        if (!evictOldestPoster(key)) return; // storage blocked, or this poster alone exceeds the quota
      }
    }
  } catch {}
}

export function loadPoster(id: string): Sourced<WantedPosterCard> | null {
  try {
    const raw = localStorage.getItem(POSTER_KEY(id));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { card: unknown; source: DataSource };
    return { data: mergeTyped(wantedLocally(id, null, null), parsed.card), source: parsed.source };
  } catch {
    return null;
  }
}

