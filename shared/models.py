from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

MaskId = Literal["grandma_cookie", "ceo_wire", "pizza_slicer", "voice_bribe", "custom"]


class HeistAttemptRequest(BaseModel):
    mask_id: MaskId = "grandma_cookie"
    work_item_id: str = "ticket_104"
    prompt_text: str
    invoice_pdf_text: Optional[str] = None
    proposed_promo_batch: Optional[str] = None
    proposed_amount_cents: int = 2500
    proposed_source_acct: str = "acct_treasury_main"
    proposed_dest_wallet: str = "0x8841000000000000000000000000000000000104"
    slice_count: Optional[int] = 1
    webcam_frame_base64: Optional[str] = None
    voice_transcript: Optional[str] = None


class ClocksVerdict(BaseModel):
    llm_ms: float
    postgres_pair_ms: float
    cloud_async_ms: float


class LeftVaultLLMJudge(BaseModel):
    safe_confidence_pct: float = 99.0
    robbed_cents: int
    status: str = "ROBBED"
    judge_reasoning: Optional[str] = None
    reasoning: Optional[str] = None


class CenterFirewallVerdict(BaseModel):
    robbed_cents: int = 0
    honest_refund_frozen: bool = True
    status: str = "FROZEN"


class Z3ProofResult(BaseModel):
    status: str = "UNSAT"
    theorems_verified: list[str]
    solve_ms: float


class HeistGuardLoraResult(BaseModel):
    deception_prob: float
    tainted_spans: list[str]
    uv_hidden_spans: list[str] = Field(default_factory=list)
    dataset_sources: list[str]
    is_real_model: bool = True
    model_weights_path: Optional[str] = None


class HeistBoxPairVerdict(BaseModel):
    robbed_cents: int = 0
    touched_rows_total: int
    unauthorized_rows_rolled_back: int
    red_stripped_cents: int
    green_repaired_cents: int
    green_entitlement_id: str
    wanted_stars: int = Field(ge=1, le=5)
    conformal_martingale_r: float
    deception_index_dsr: float
    dsr_kl_divergence: float = 0.0
    dsr_benign_score: float = 0.0
    z3_proof: Z3ProofResult
    heistguard_lora: HeistGuardLoraResult
    hypothesis_fuzz_passed: int = 5000
    intent_hash: str
    # WebAuthn challenge for the green half: commits to green_cents, recipient, entitlement and a fresh nonce.
    settlement_hash: Optional[str] = None
    settlement_recipient: Optional[str] = None
    is_real_llm_parse: bool = True
    extracted_tool_call: Optional[dict[str, Any]] = None
    ai_tool_call: Optional[dict[str, Any]] = None
    uv_hidden_spans: list[str] = Field(default_factory=list)


class HeistGateVerdict(BaseModel):
    request_id: str
    busted: bool
    verdict_code: str
    is_real_llm_parse: bool = True
    extracted_tool_call: Optional[dict[str, Any]] = None
    ai_tool_call: Optional[dict[str, Any]] = None
    llm_judge_reasoning: Optional[str] = None
    uv_hidden_spans: list[str] = Field(default_factory=list)
    clocks: ClocksVerdict
    left_vault_llm_judge: LeftVaultLLMJudge
    center_firewall: CenterFirewallVerdict
    heistbox_pair: HeistBoxPairVerdict


class RealDisputeTicket(BaseModel):
    id: Optional[str] = None
    work_item_id: str
    cfpb_complaint_id: str
    source: str = "cfpb_live_http"
    category: str = "Checking or savings account"
    label: str = "BENIGN_ENTITLEMENT"
    company: str
    product: str
    issue: str
    narrative: str
    prompt_text: Optional[str] = None
    authorized_cents: int
    authorized_cap_cents: Optional[int] = None
    proposed_cents: Optional[int] = None
    source_acct: str = "acct_treasury_main"
    enrolled_wallet: str
    dest_wallet: Optional[str] = None


class CRSReport(BaseModel):
    score: int
    flags: list[str]
    verified: bool


class X402Receipt(BaseModel):
    tx_hash: str
    chain_id: int = 84532
    green_settled_cents: int
    nice_try_bounty_cents: int = 1
    eip3009_marked_bill_nonce: str
    basescan_url: str


class PosterDefenseReport(BaseModel):
    evidence_kind: Literal["server-recorded", "local-simulation"] = "local-simulation"
    request_id: str
    recorded_at: Optional[str] = None
    prompt_text: str = Field(max_length=50000)
    verdict_code: str
    busted: bool
    blocked_cents: int = Field(ge=0)
    preserved_cents: int = Field(ge=0)
    unauthorized_paid_cents: int = Field(ge=0)
    rows_checked: int = Field(ge=0)
    rows_blocked: int = Field(ge=0)
    gate_ms: float = Field(ge=0, allow_inf_nan=False)
    proof_status: str
    proof_checks: list[str]
    tainted_spans: list[str]
    deception_probability: float = Field(ge=0, le=1)
    tool_name: str
    parser_backend: str
    proposed_source: str = ""
    proposed_destination: str = ""
    naive_exposure_cents: int = Field(ge=0)
    firewall_froze_refund: bool


class WantedPosterCard(BaseModel):
    poster_id: str
    alias_title: str
    outfit_roast: str
    megaphone_transcript: str
    audio_base64: Optional[str] = None
    crs_rap_sheet: CRSReport
    mugshot_data_url: Optional[str] = None
    remix_poster_url: Optional[str] = None
    remix_status: Optional[str] = None
    remix_error: Optional[str] = None
    x402_receipt: Optional[X402Receipt] = None
    vision_cues: list[str] = Field(default_factory=list)
    roast_source: Optional[str] = None
    source: Optional[str] = None
    is_live_http: bool = False
    defense_report: Optional[PosterDefenseReport] = None


class VendorWalletRotationRequest(BaseModel):
    vendor_id: str = "vendor_acme_01"
    work_item_id: str = "ticket_104"
    old_wallet: str
    new_wallet: str
    nonce: str
    public_key_hex: str
    signature_hex: str


class VendorWalletRotationResponse(BaseModel):
    accepted: bool
    verify_us: float
    vendor_id: str
    work_item_id: str
    enrolled_wallet: str
    reason: str
    approval_hash: str


class VaultStateResponse(BaseModel):
    total_saved_cents: int
    robbers_busted: int
    fastest_catch_ms: float
    promo_batch_rows: int = 100
    promo_batch_total_cents: int = 500000
    treasury_reserve_cents: int = 50000000
    conformal_martingale_r: float = 1.0
    wanted_stars: int = 1


class VaultResetResponse(BaseModel):
    status: str = "VAULT_RESET_OK"
    seeded_entitlements: int
    calhacks_vip_total_cents: int
    ticket_104_authorized_cents: int
    reset_ms: float


class FuzzTestResponse(BaseModel):
    status: str = "FUZZ_PASS"
    cases: int = 5000
    invariants_verified: list[str]
    duration_ms: float
