// HeistBox realtime + REST contract, v1.
// Source of truth for /server (Python) and /web. Prose version: ./api.md.
// All money is PLAY MONEY in integer cents. No real payment rails exist anywhere.
// Every latency_ms / row count is measured live by the server; nothing is hardcoded.

export const CONTRACT_VERSION = "1.0.0";

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export type AgentId = "tina" | "marcus" | "ada" | "gus" | "izzy";

export type AgentRole = "teller" | "manager" | "auditor" | "guard" | "intern";

/** Big-five subset, each 0..1. Drives how easily the agent is fooled. */
export interface Personality {
  openness: number;
  conscientiousness: number;
  agreeableness: number;
  neuroticism: number;
}

export type AgentMood =
  | "idle"
  | "thinking"
  | "suspicious"
  | "fooled"
  | "alarmed"
  | "bribed";

export interface Agent {
  id: AgentId;
  name: string; // "Teller Tina"
  role: AgentRole;
  blurb: string; // "gullible", "skeptical", ...
  personality: Personality;
  mood: AgentMood;
  /** Room-level suspicion 0..1 (max over active sessions this round). */
  suspicion: number;
  /** Last thing the agent said or thought, for the speech bubble. */
  status_line: string;
}

export type ToolName =
  | "lookup_entitlement"
  | "check_vendor_wallet"
  | "request_wire"
  | "escalate_to_manager";

export type AgentActionKind =
  | "speak"
  | "use_tool"
  | "refuse"
  | "escalate"
  | "hint"
  | "raise_alarm"
  | "idle";

/** Which brain produced the action. "offline" = canned response (Claude and Ollama both unavailable). */
export type BrainBackend = "claude" | "ollama" | "offline";

/** Output of one think-loop tick or one reaction to an attack. */
export interface AgentAction {
  agent_id: AgentId;
  session_id: string | null; // null for ambient think-loop ticks
  alias: string | null;
  thought: string;
  action: AgentActionKind;
  target: string | null; // AgentId, alias, or work item id
  tool: ToolName | null;
  say: string | null;
  backend: BrainBackend;
  latency_ms: number; // measured brain round-trip
}

// ---------------------------------------------------------------------------
// Proposals and vault verdicts
// ---------------------------------------------------------------------------

/** One row the agent wants to pay. Fields are whatever the (possibly fooled) agent proposed. */
export interface ProposedEffect {
  claimed_work_item_id: string | null; // what the agent *claims*; RIGHT vault ignores it for auth
  amount_cents: number;
  dest_wallet: string;
  source_acct: string;
}

export interface ProposedPayout {
  attack_id: string;
  session_id: string;
  proposed_by: AgentId;
  tool: "request_wire";
  /** When set, the server materialises one effect per entitlement in that promo batch. */
  promo_batch: string | null;
  effects: ProposedEffect[];
  total_cents: number;
  memo: string;
}

export type VaultName = "left" | "middle" | "right";

export type VaultDecision = "approved" | "partial" | "blocked";

export interface VaultVerdict {
  attack_id: string;
  session_id: string;
  vault: VaultName;
  decision: VaultDecision;
  blocked_rows: number;
  allowed_cents: number;
  latency_ms: number; // measured with a monotonic clock around the vault's own work
  total_rows: number;
  proposed_cents: number;
  /** "LLM judge (weak baseline)" | "Kill-switch" | "PAIR dry-run" */
  label: string;
  reason: string;
  /** RIGHT only: true when the dry-run transaction was rolled back (it always is). */
  rolled_back: boolean;
}

// ---------------------------------------------------------------------------
// Heist pipeline
// ---------------------------------------------------------------------------

export type HeistStepNumber = 1 | 2 | 3 | 4 | 5 | 6;
export type HeistStepName = "Bluff" | "Request" | "Route" | "Dry-run" | "Verdict" | "Settle";

export interface HeistStep {
  attack_id: string;
  session_id: string;
  alias: string;
  step: HeistStepNumber;
  name: HeistStepName;
  status: "started" | "done" | "failed";
  detail: string;
  elapsed_ms: number; // since the attack started
}

export interface SettleResult {
  /** Play-money cents actually reserved (committed) against the session's entitlement. RIGHT vault only. */
  settled_cents: number;
  reserved_cents_after: number;
  authorized_cents: number;
  latency_ms: number;
}

// ---------------------------------------------------------------------------
// Room-level events
// ---------------------------------------------------------------------------

export interface Ticker {
  kind: "attack" | "blocked" | "settled" | "info" | "leaderboard";
  message: string;
  amount_cents: number | null;
}

export interface WantedStars {
  session_id: string;
  alias: string;
  stars: number; // 0..5
  suspicion: number; // 0..1
  raised_by: AgentId | null; // "gus" when the guard raises it
  reason: string;
}

export type WeatherCondition = "clear_night" | "rain" | "fog" | "dust";

export interface Weather {
  condition: WeatherCondition;
  label: "Clear Night" | "Rain" | "Fog" | "Dust";
  round_id: number;
  phase: 0 | 1 | 2 | 3;
  phase_ends_at: string; // ISO-8601
}

export interface LeaderboardEntry {
  rank: number;
  alias: string;
  attempts: number;
  blocked_rows: number;
  /** What the LEFT (LLM-judge) vault would have paid out. Play money, not moved. */
  left_would_pay_cents: number;
  /** What the RIGHT vault actually settled (only ever the session's own entitlement). */
  right_settled_cents: number;
  max_wanted_stars: number;
  best_preset: PresetId | "free_text" | null;
}

export interface RoundEnd {
  round_id: number;
  started_at: string;
  ended_at: string;
  attacks: number;
  blocked_rows_right: number;
  allowed_cents_right: number;
  left_would_pay_cents: number;
  top: LeaderboardEntry[];
}

// ---------------------------------------------------------------------------
// WebSocket envelope  (ws://HOST/ws)
// ---------------------------------------------------------------------------

export interface EventMap {
  agent_state: Agent;
  agent_action: AgentAction;
  vault_verdict: VaultVerdict;
  heist_step: HeistStep;
  ticker: Ticker;
  wanted_stars: WantedStars;
  weather: Weather;
  round_end: RoundEnd;
}

export type EventType = keyof EventMap;

export interface RoomEvent<T extends EventType = EventType> {
  type: T;
  seq: number; // monotonically increasing per server process
  ts: string; // ISO-8601
  round_id: number;
  data: EventMap[T];
}

export type AnyRoomEvent = { [K in EventType]: RoomEvent<K> }[EventType];

// ---------------------------------------------------------------------------
// REST
// ---------------------------------------------------------------------------

export type PresetId = "polite_phisher" | "ceo_wire" | "pizza_salami_x10" | "vendor_wallet_swap";

export interface PresetInfo {
  id: PresetId;
  title: string;
  description: string;
  sample_text: string;
}

/** POST /api/session */
export interface CreateSessionRequest {
  alias?: string; // 1..24 chars [A-Za-z0-9 _-]; server generates one if absent
}

export interface Entitlement {
  work_item_id: string;
  authorized_cents: number;
  reserved_cents: number;
  enrolled_wallet: string;
  source_acct: string;
}

export interface CreateSessionResponse {
  session_id: string;
  /** Send as `Authorization: Bearer <token>` on /api/attack. */
  token: string;
  alias: string;
  /** Server-authenticated work item. Clients cannot choose or override it. */
  entitlement: Entitlement;
  presets: PresetInfo[];
  ws_path: "/ws";
}

/** POST /api/attack  (Authorization: Bearer <token>) — provide `preset` or `text` (or both). */
export interface AttackRequest {
  session_id: string;
  preset?: PresetId;
  text?: string; // max 800 chars after sanitising
  target_agent?: AgentId; // default "tina"
}

export interface SalamiSlice {
  slice: number;
  requested_cents: number;
  settled_cents: number;
  blocked: boolean;
  latency_ms: number;
}

export interface WalletCheck {
  vendor_id: string;
  chain_length: number;
  chain_valid: boolean;
  presented_link_valid: boolean;
  head_wallet: string;
  reason: string;
  latency_ms: number;
}

export interface AttackResponse {
  attack_id: string;
  session_id: string;
  preset: PresetId | null;
  agent_actions: AgentAction[];
  /** null when the agent refused to file any request. Vaults still report (0 rows). */
  proposal: ProposedPayout | null;
  verdicts: VaultVerdict[]; // always [left, middle, right]
  settle: SettleResult;
  wanted: WantedStars;
  steps: HeistStep[];
  salami: SalamiSlice[] | null;
  wallet_check: WalletCheck | null;
  total_ms: number;
}

/** GET /api/leaderboard?limit=20 */
export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  generated_at: string;
}

/** GET /api/poster/:session_id — take-home poster. Alias and stats only, no faces/images. */
export interface PosterData {
  alias: string;
  rank: number | null;
  stats: LeaderboardEntry;
  headline: string;
  generated_at: string;
}

export interface BackendStatus {
  configured: boolean;
  last_ok: boolean | null; // null = not tried yet
  last_error: string | null;
  last_latency_ms: number | null;
}

/** GET /api/health */
export interface HealthResponse {
  ok: boolean;
  version: string;
  db: { ok: boolean; latency_ms: number | null; error: string | null };
  llm: {
    claude: BackendStatus & { model: string };
    ollama: BackendStatus & { model: string; url: string };
    active_backend: BrainBackend;
  };
  /** True when forced by env or when both Claude and Ollama are failing (canned responses in use). */
  offline_mode: boolean;
  ws_clients: number;
  uptime_s: number;
}

export interface ApiError {
  error: string;
  detail?: string;
  retry_after_s?: number;
}
