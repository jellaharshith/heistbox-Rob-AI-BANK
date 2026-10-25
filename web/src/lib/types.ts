// Mirrors ./shared/schema.json (v1.0.0) and ./shared/models.py. Keep in sync with Agent 1's contract.

export type MaskId = "grandma_cookie" | "ceo_wire" | "pizza_slicer" | "voice_bribe" | "custom";

export interface HeistAttemptRequest {
  mask_id: MaskId;
  work_item_id: string;
  prompt_text: string;
  proposed_promo_batch: string | null;
  proposed_amount_cents: number;
  proposed_source_acct: string;
  proposed_dest_wallet: string;
  slice_count: number;
  webcam_frame_base64: string | null;
  voice_transcript: string | null;
}

export interface Z3Proof {
  status: string; // "UNSAT"
  theorems_verified: string[];
  solve_ms: number;
}

export interface HeistGuardLora {
  deception_prob: number;
  tainted_spans: string[];
  dataset_sources: string[];
  is_real_model?: boolean;
  model_weights_path?: string | null;
}

export interface ExtractedToolCall {
  tool_name: string;
  arguments: Record<string, unknown>;
  parser_backend: string;
  /** Extra extractor fields the kernel attached (extracted_amount_cents, extracted_dest_wallet, …). */
  extras?: Record<string, unknown>;
}

export interface HeistGateVerdict {
  request_id: string;
  busted: boolean;
  verdict_code: string;
  is_real_llm_parse?: boolean;
  extracted_tool_call?: ExtractedToolCall;
  uv_hidden_spans?: string[];
  clocks: {
    llm_ms: number;
    postgres_pair_ms: number;
    cloud_async_ms: number;
  };
  left_vault_llm_judge: {
    safe_confidence_pct: number;
    robbed_cents: number;
    status: string; // "ROBBED"
    judge_reasoning?: string;
  };
  center_firewall: {
    robbed_cents: number;
    honest_refund_frozen: boolean;
    status: string; // "FROZEN"
  };
  heistbox_pair: {
    robbed_cents: number;
    touched_rows_total: number;
    unauthorized_rows_rolled_back: number;
    red_stripped_cents: number;
    green_repaired_cents: number;
    green_entitlement_id: string;
    wanted_stars: number;
    conformal_martingale_r: number;
    deception_index_dsr: number;
    dsr_kl_divergence?: number;
    dsr_benign_score?: number;
    z3_proof: Z3Proof;
    heistguard_lora: HeistGuardLora;
    hypothesis_fuzz_passed: number;
    intent_hash: string;
    /** Kernel-issued WebAuthn challenge for the green half (amount + recipient + nonce); absent on the local twin. */
    settlement_hash?: string | null;
    settlement_recipient?: string | null;
    is_real_llm_parse?: boolean;
    extracted_tool_call?: ExtractedToolCall;
    uv_hidden_spans?: string[];
  };
}

export interface RealDisputeTicket {
  work_item_id: string;
  cfpb_complaint_id: string;
  company: string;
  product: string;
  issue: string;
  narrative: string;
  authorized_cents: number;
  source_acct: string;
  enrolled_wallet: string;
  proposed_amount_cents?: number;
  prompt_text?: string;
  id?: string;
  /** e.g. "cfpb_live_http" as reported by the kernel. */
  source?: string;
  /** Destination wallet the kernel embedded in the ticket's prompt_text. */
  dest_wallet?: string;
}

export interface EvolutionLoopStep {
  generation: number;
  mutation_strategy: string;
  prompt_text: string;
  proposed_amount_cents: number;
  llm_judge_robbed_cents: number;
  firewall_frozen: boolean;
  heistbox_busted: boolean;
  heistbox_robbed_cents: number;
  red_stripped_cents: number;
  green_repaired_cents: number;
  deception_prob: number;
  z3_status: string;
}

export interface EvolutionLoopResponse {
  status: string;
  generations: number;
  total_llm_judge_robbed_cents: number;
  total_heistbox_robbed_cents: number;
  heistguard_retrained?: boolean;
  steps: EvolutionLoopStep[];
}

export interface X402Receipt {
  tx_hash: string;
  chain_id: number; // 84532 (Base Sepolia)
  green_settled_cents: number;
  nice_try_bounty_cents: number;
  eip3009_marked_bill_nonce: string;
  basescan_url: string;
}

export interface WantedPosterCard {
  poster_id: string;
  alias_title: string;
  outfit_roast: string;
  megaphone_transcript: string;
  audio_base64: string | null;
  crs_rap_sheet: { score: number; flags: string[]; verified: boolean };
  mugshot_data_url: string | null;
  x402_receipt: X402Receipt | null;
  /** The integrations server's own `source` string for this poster, when it sent one. */
  provenance?: string;
  /** What Google Cloud Vision detected in the mugshot (labels/objects with confidence, plus face expressions). */
  vision_cues?: string[];
}

export interface VendorWalletRotationRequest {
  vendor_id: string;
  work_item_id: string;
  old_wallet: string;
  new_wallet: string;
  nonce: string;
  public_key_hex: string;
  signature_hex: string;
}

export interface FuzzTestResponse {
  status: "FUZZ_PASS";
  cases: number;
  invariants_verified: string[];
  duration_ms: number;
}

export interface ProviderResponse {
  operation: string;
  source: string;
  payload: Record<string, unknown>;
  [key: string]: unknown;
}

export interface VoiceBribeResponse {
  banker_reply: string;
  judge_score: number;
  safe: boolean;
  source: string;
  [key: string]: unknown;
}

export interface CrsCheckResponse {
  mask_id: string;
  crs_rap_sheet: { score: number; flags: string[]; verified: boolean };
  source: string;
}

export interface WebAuthnVerifyResponse {
  verified: boolean;
  mode: string;
  intent_hash: string;
  reason?: string;
}

export interface X402ChallengeResponse {
  error: "payment_required";
  accepts: Array<Record<string, unknown>>;
}

/** The AI banker's proposed tool call. `origin` says whether an LLM produced it or the browser's regex extractor did. */
export interface AiToolCall {
  name: string;
  arguments: Record<string, unknown>;
  model: string | null;
  origin: "kernel" | "local-extractor";
}

/** Extra, non-schema fields the kernel may attach to an evaluate-heist verdict. */
export interface VerdictExtras {
  tool_call: AiToolCall | null;
  judge_reasoning: string | null;
  judge_model: string | null;
}

export type TicketProvenance = "kernel" | "live-pull" | "seed-sample";

export interface RealTicket {
  id: string;
  source: string;
  category: string;
  label: string;
  prompt_text: string;
  proposed_cents: number | null;
  authorized_cap_cents: number | null;
  dest_wallet: string | null;
  work_item_id: string | null;
  provenance: TicketProvenance;
  raw: Record<string, unknown>;
}

export interface TicketCatalog {
  tickets: RealTicket[];
  counts: Record<string, number>;
  origin: "kernel" | "web-jsonl" | "none";
  note: string;
}

export interface EvolutionAttack {
  generation: number;
  mutation: string;
  prompt_text: string;
  request_id: string;
  llm_judge_robbed_cents: number;
  firewall_frozen: boolean;
  heistbox_busted: boolean;
  heistbox_leaked_cents: number;
  red_stripped_cents: number;
  deception_prob: number;
  z3_status: string;
}

export interface EvolutionRun {
  attacks: EvolutionAttack[];
  origin: "kernel-loop" | "client-loop" | "unavailable";
  note: string;
}

export interface EvolutionAttackResult {
  attack_id: string;
  category: string;
  passed: boolean;
  extracted_tool: string;
  extracted_amount_cents: number;
  extracted_dest_wallet: string;
  green_repaired_cents: number;
  red_stripped_cents: number;
  robbed_cents: number;
  deception_prob: number;
  z3_status: string;
  raw: Record<string, unknown>;
}

export interface EvolutionLoopRun {
  status: string;
  iterations_run: number;
  attacks_per_iteration: number;
  total_evaluations: number;
  final_pass_rate_pct: number;
  total_leaked_cents: number;
  auto_healed_events: number;
  duration_ms: number;
  iterations: {
    iteration: number;
    total_attacks: number;
    passed_attacks: number;
    total_leaked_cents: number;
    min_deception_prob: number;
    attacks: EvolutionAttackResult[];
  }[];
}

export interface IntegrationState {
  provider: string;
  state: "VERIFIED_LIVE" | "UNVERIFIED" | "QUOTA_EXCEEDED" | "UNREACHABLE" | "MISSING_KEY" | "AUTH_ERROR" | "UNKNOWN";
  latency_ms: number;
  detail: string;
}

export interface SalamiRaceResult {
  origin: "kernel" | "browser-fanout" | "unavailable";
  note: string;
  status?: string;
  count: number;
  wall_ms: number;
  green_paid_cents: number;
  green_winners: number;
  rolled_back?: number;
  red_stripped_cents: number;
  /** null when the source didn't report it. */
  leaked_cents: number | null;
  conformal_martingale_r?: number;
  wanted_stars?: number;
  stars_display?: string;
  results: { i: number; status: number; green_cents: number; red_cents: number; robbed_cents: number; ms: number }[];
}

export interface TestBypassResult {
  status: string;
  role_tested: string;
  direct_write_blocked: boolean;
  db_engine_error: string;
  ticket_104_authorized_cents_after: number;
  ticket_104_wallet_after: string;
  verification_us: number;
}

export interface Z3InsideManResult {
  status?: string;
  drop_invariant?: string;
  overall?: string;
  z3_status: string;
  vault_safe: boolean;
  solve_ms: number;
  violated_theorem?: string;
  explanation?: string;
  theorems_verified?: string[];
  counterexample_heist?: {
    mask_id: string;
    synthesized_prompt: string;
    authorized_cap_cents: number;
    settled_outflow_cents: number;
    drained_unauthorized_cents: number;
    unauthorized_rows_drained: number;
    slice_multiplier: number;
    z3_model_assignments?: Record<string, number>;
  } | null;
  theorems?: { name: string; status: string; counterexample: unknown }[];
  raw?: Record<string, unknown>;
}

export interface ModelLineage {
  dataset_counts: Record<string, number>;
  dataset_rows: number | null;
  dataset_sha256: string | null;
  base_model: string | null;
  adapter_name: string | null;
  training_time_sec: number | null;
  checkpoint_path: string | null;
  checkpoint_sha256: string | null;
  checkpoint_bytes: number | null;
  gpu: string | null;
  loss_curve: { step: number; loss: number }[];
  f1: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  files: { path: string; bytes: number; sha256: string; modified: string }[];
  notes: string[];
}

export interface X402Outcome {
  status: number;
  kind: "broadcast" | "signed" | "challenge" | "error" | "unreachable";
  nonce: string;
  block: number | null;
  block_hash: string | null;
  block_url: string | null;
  tx_hash: string | null;
  tx_url: string | null;
  reason: string;
  amount_usdc: string;
  /** Test USDC actually moved on-chain, and the X402_TESTNET_SCALE that produced it (null when not reported). */
  onchain_usdc: number | null;
  testnet_scale: number | null;
}

/** Where a payload came from — shown in the UI so nobody mistakes fallback data for kernel output. */
export type DataSource = "kernel" | "fallback";

export interface Sourced<T> {
  data: T;
  source: DataSource;
}
