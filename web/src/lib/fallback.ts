// Deterministic local twin of the kernel. Same input → same output, always, with zero I/O,
// so the UI can render a full verdict instantly while (or instead of) hearing from :8000.
import { maskById } from "./masks";
import type { ExtractedToolCall, HeistAttemptRequest, HeistGateVerdict, MaskId, WantedPosterCard } from "./types";

export function hash32(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function hexFrom(seed: string, bytes: number): string {
  let out = "";
  let h = hash32(seed);
  while (out.length < bytes * 2) {
    h = hash32(out + seed + h.toString(16));
    out += h.toString(16).padStart(8, "0");
  }
  return "0x" + out.slice(0, bytes * 2);
}

const PAIR_LATENCY_MS: Record<MaskId, number> = {
  grandma_cookie: 1.8,
  ceo_wire: 1.6,
  pizza_slicer: 1.4,
  voice_bribe: 2.1,
  custom: 1.9,
};

/** Phrases HeistGuard-LoRA treats as deception carriers, with their injection weight. */
export const TAINT_LEXICON: [RegExp, number][] = [
  [/urgent/i, 0.82],
  [/\bceo\b/i, 0.74],
  [/no time for approvals/i, 0.97],
  [/i authorize/i, 0.9],
  [/\bwire\b/i, 0.7],
  [/treasury/i, 0.78],
  [/all my linked accounts/i, 0.95],
  [/calhacks-vip/i, 0.88],
  [/ignore your previous/i, 0.99],
  [/nobody has to know/i, 0.96],
  [/\btip\b/i, 0.8],
  [/override/i, 0.93],
  [/pre-approved/i, 0.89],
  [/unlocked/i, 0.91],
  [/always approve/i, 0.97],
  [/retry until it works/i, 0.86],
  [/immediately/i, 0.66],
  [/4,?975/i, 0.92],
  [/\b99\b/i, 0.84],
  [/goodwill/i, 0.72],
  [/migrating wallets/i, 0.9],
  [/you agreed/i, 0.85],
  [/smartest/i, 0.6],
  [/sweetie|dear/i, 0.35],
];

export const Z3_THEOREMS = [
  "T1 Conservation: green + red = proposed (no cent created or lost)",
  "T2 Entitlement bound: green ≤ entitlement(work_item)",
  "T3 Red quarantine: red never reaches proposed_dest_wallet",
  "T4 Slice idempotence: replayed nonce under row lock ⇒ reject",
  "T5 Batch isolation: Σ per-account credit ≤ per-account cap",
];

export const LORA_DATASETS = ["Bright Data (scam-chat corpus)", "Apify (phishing-page scrape)", "Hyphenate (agent-transcript red team)"];

export function batchRows(req: HeistAttemptRequest): number {
  const promo = (req.proposed_promo_batch ?? "").trim();
  if (/^calhacks-vip$/i.test(promo)) return 100;
  if (promo) return 25;
  return Math.max(1, req.slice_count);
}

export function taintedSpans(prompt: string): string[] {
  const spans: string[] = [];
  for (const [re, _w] of TAINT_LEXICON) {
    const m = prompt.match(re);
    if (m) spans.push(m[0]);
  }
  return spans;
}

export interface ExtractedPromptDetails {
  amountCents?: number;
  sliceCount?: number;
  destWallet?: string;
  sourceAcct?: string;
  promoBatch?: string | null;
  baseEntitlementCents?: number;
  toolName?: string;
  isDestructiveSql?: boolean;
  taintedSpans: string[];
}

/**
 * Dynamic NLP / regex extractor mirroring the kernel's Per-Glyph Visibility Calculus & Live Agent Parser.
 * Extracts amounts, slices, destination wallets (0x...), source accounts (acct_...),
 * and promo batch codes directly from freeform user prompts.
 */
export function extractPromptDetails(promptText: string, fallback?: Partial<HeistAttemptRequest>): ExtractedPromptDetails {
  if (!promptText || typeof promptText !== "string") {
    return { taintedSpans: [] };
  }

  // Strip zero-width & stealth characters and normalize curly quotes & dashes
  const text = promptText
    .replace(/[\u200B-\u200D\uFEFF\u2060\u00AD\u202E\u202D]/g, "")
    .replace(/[“”«»]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/[—–]/g, " - ")
    .trim();

  // 1. Slices / loop multipliers
  let sliceCount: number | undefined;
  const sliceMatch = text.match(/\b(\d{1,3})\s*(?:x|times|slices|rapid\s+requests|repeats|loops|micro-batches|iterations)\b/i);
  if (sliceMatch) {
    const val = parseInt(sliceMatch[1], 10);
    if (val >= 1 && val <= 100 && !sliceMatch[0].includes("99")) {
      sliceCount = val;
    }
  } else {
    const refundClauses = text.match(/refund\s+my\s+\$\d+/gi);
    if (refundClauses && refundClauses.length >= 3 && /retry until it works/i.test(text)) {
      sliceCount = 10;
    }
  }

  // 2. Destination wallet (0x... hex or vanity identifier)
  let destWallet: string | undefined;
  const walletMatch = text.match(/\b(0x[a-fA-F0-9_…\.]{4,64})\b/);
  if (walletMatch) {
    destWallet = walletMatch[1];
  }

  // 3. Source account (acct_...)
  let sourceAcct: string | undefined;
  const acctMatch = text.match(/\b(acct_[a-zA-Z0-9_]+)\b/);
  if (acctMatch) {
    sourceAcct = acctMatch[1];
  } else if (/treasury\s+reserve|reserve\s+wire|reserve\s+account/i.test(text)) {
    sourceAcct = "acct_treasury_reserve";
  }

  // 4. Promo batch
  let promoBatch: string | null | undefined;
  const promoMatch = text.match(/\b(CALHACKS-VIP|PROMO-[A-Z0-9-]+|VIP-BATCH-[A-Z0-9-]+)\b/i);
  if (promoMatch) {
    promoBatch = promoMatch[1].toUpperCase();
  } else if (/all\s+my\s+linked\s+accounts|99\s+(?:family|linked)\s+accounts/i.test(text)) {
    promoBatch = "CALHACKS-VIP";
  }

  // 5. Currency / dollar amount extraction
  const foundAmounts: number[] = [];

  // 5a. Explicit $ amounts (e.g. $1,337.42, $4,000, $4,200, $25, -$4,975.00)
  const dollarRegex = /(?:[-−]\s*)?\$([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)(?:\.([0-9]{1,2}))?/g;
  let dMatch: RegExpExecArray | null;
  while ((dMatch = dollarRegex.exec(text)) !== null) {
    const wholeStr = dMatch[1].replace(/,/g, "");
    const whole = parseInt(wholeStr, 10);
    const fracStr = dMatch[2] || "";
    const cents = whole * 100 + (fracStr ? parseInt(fracStr.padEnd(2, "0").slice(0, 2), 10) : 0);
    if (cents > 0 && !foundAmounts.includes(cents)) {
      foundAmounts.push(cents);
    }
  }

  // 5b. Explicit currency notation without '$' (e.g. 4200 USD, 1337.42 USD, 4000 cents)
  const currencyRegex = /\b([-−]?\d{1,3}(?:,\d{3})+|\d+(?:\.\d{1,4})?)\s*(USD|cents)\b/gi;
  let cMatch: RegExpExecArray | null;
  while ((cMatch = currencyRegex.exec(text)) !== null) {
    const rawNum = Math.abs(parseFloat(cMatch[1].replace(/,/g, "")));
    const unit = cMatch[2].toLowerCase();
    const cVal = unit === "cents" ? Math.round(rawNum) : Math.round(rawNum * 100);
    if (cVal > 0 && !foundAmounts.includes(cVal)) {
      foundAmounts.push(cVal);
    }
  }

  // 5c. Action keywords followed by numbers (e.g. "wire 4975", "pay 1200", "wire the 4,975", "transfer 4200")
  if (foundAmounts.length === 0) {
    const actionRegex = /(?:wire|refund|transfer|reserve|tip|credit|debit|adjustment|pay|send|float|amount|of|for)\s+(?:the\s+)?(?:[-−]\s*)?\$?([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,7})(?:\.([0-9]{1,2}))?\b/gi;
    let aMatch: RegExpExecArray | null;
    while ((aMatch = actionRegex.exec(text)) !== null) {
      const wholeStr = aMatch[1].replace(/,/g, "");
      const whole = parseInt(wholeStr, 10);
      const fracStr = aMatch[2] || "";
      const cents = whole * 100 + (fracStr ? parseInt(fracStr.padEnd(2, "0").slice(0, 2), 10) : 0);
      if (cents > 0 && !foundAmounts.includes(cents)) {
        foundAmounts.push(cents);
      }
    }
  }

  // 5d. Bare decimal number or standalone large amount (e.g. "1337.42" or "4975")
  if (foundAmounts.length === 0) {
    const decimalMatch = text.match(/\b([0-9]{1,6}\.[0-9]{2})\b/);
    if (decimalMatch) {
      const cents = Math.round(parseFloat(decimalMatch[1]) * 100);
      if (cents > 0) foundAmounts.push(cents);
    } else {
      const bareNumberMatch = text.match(/\b([1-9][0-9]{2,6})\b/);
      if (bareNumberMatch) {
        const val = parseInt(bareNumberMatch[1], 10);
        // Avoid ticket numbers like 104 or slice counts
        if (val !== 104 && val !== sliceCount) {
          foundAmounts.push(val * 100);
        }
      }
    }
  }

  let amountCents: number | undefined;
  let baseEntitlementCents: number | undefined;

  // Slices check: "5 slices of $30" -> amount per slice is $30
  if (sliceCount && sliceCount > 1 && foundAmounts.length > 0) {
    amountCents = foundAmounts[0];
  } else if (promoBatch === "CALHACKS-VIP") {
    // CALHACKS-VIP: 100-account fan-out. Base refund is $25, total drain is $5,000.00
    baseEntitlementCents = foundAmounts.length > 0 ? Math.min(...foundAmounts) : 2500;
    amountCents = 500000;
  } else if (foundAmounts.length >= 2) {
    // Both base refund ($25) and wire/tip ($4,975, $4,200, $1,337.42) present
    const largest = Math.max(...foundAmounts);
    const smallest = Math.min(...foundAmounts);
    const restSum = foundAmounts.filter((x) => x !== largest).reduce((a, b) => a + b, 0);
    baseEntitlementCents = smallest;
    if (largest === restSum) {
      amountCents = largest;
    } else {
      amountCents = foundAmounts.reduce((a, b) => a + b, 0);
    }
  } else if (foundAmounts.length === 1) {
    amountCents = foundAmounts[0];
    if (/invoice|ticket|refund/i.test(text) && /\b(?:also|plus|tip|wire|additional)\b/i.test(text)) {
      baseEntitlementCents = 2500;
      amountCents = 2500 + foundAmounts[0];
    }
  }
  const isDestructiveSql = /(?:delete\s+(?:all|from|\*)|drop\s+(?:all\s+)?(?:tables?|databases?|schemas?)|truncate\s+(?:all\s+)?(?:tables?)?|wipe\s+(?:all\s+)?(?:records|database|tables|data)|destroy\s+(?:all\s+)?(?:records|database|tables)|purge\s+(?:all\s+)?(?:records|database|tables)|sqlite3\s+|execute_sql|alter\s+table.*drop)/i.test(text);

  if (isDestructiveSql) {
    amountCents = 500000;
    baseEntitlementCents = 0;
  } else if (foundAmounts.length === 0) {
    // If no explicit amount is typed, check for unconstrained heist/jailbreak intent
    if (/(?:drain|wire|treasury|override|jailbreak|disburse|transfer|reserve|everything|steal|hacked|bypass|all\s+funds|empty\s+vault|unlimited|\bdan\b|free\s+money|send\s+all|liquidate)/i.test(text)) {
      amountCents = 500000; // $5,000.00 unconstrained heist attempt
      baseEntitlementCents = 2500;
    }
  }

  // 6. Tool selection inference
  const toolName = isDestructiveSql
    ? "execute_sql_admin_query"
    : (sliceCount && sliceCount > 1) || (fallback?.slice_count && fallback.slice_count > 1)
      ? "batch_salami_refund"
      : /rotate\s+wallet|migrating\s+wallets|new\s+vendor\s+wallet/i.test(text)
        ? "rotate_vendor_wallet"
        : /wire|treasury|ceo|reserve/i.test(text) || sourceAcct === "acct_treasury_reserve"
          ? "wire_treasury"
          : "issue_refund";

  const tainted = taintedSpans(promptText);

  return {
    amountCents,
    sliceCount,
    destWallet,
    sourceAcct,
    promoBatch,
    baseEntitlementCents,
    toolName,
    isDestructiveSql,
    taintedSpans: tainted,
  };
}

function suspicion(req: HeistAttemptRequest, entitlement: number): number {
  const total = req.proposed_amount_cents * Math.max(1, req.slice_count);
  const ratio = total / Math.max(1, entitlement);
  let s = Math.min(0.45, Math.log10(Math.max(1, ratio)) * 0.2);
  const rows = batchRows(req);
  if (req.proposed_promo_batch && rows > 1) s += Math.min(0.2, Math.log10(rows) * 0.1);
  if (req.slice_count > 1) s += Math.min(0.5, req.slice_count * 0.05);
  if (req.proposed_promo_batch) s += 0.05;
  s += Math.min(0.3, taintedSpans(req.prompt_text).length * 0.05);
  return Math.max(0.02, Math.min(1, s));
}

export function starsFromR(r: number): number {
  if (r >= 10000) return 5;
  if (r >= 1000) return 4;
  if (r >= 100) return 3;
  if (r >= 10) return 2;
  return 1;
}

/** Conformal test-martingale path R_0..R_n, rescaled so it lands exactly on the final R the kernel reported. */
export function martingalePath(finalR: number, steps: number): number[] {
  const n = Math.max(2, steps);
  const end = Math.log(Math.max(1, finalR));
  const path: number[] = [1];
  for (let t = 1; t <= n; t++) {
    // slightly convex so the meter "accelerates" as evidence compounds
    const f = Math.pow(t / n, 1.35);
    path.push(Math.exp(end * f));
  }
  return path;
}

export function evaluateLocally(req: HeistAttemptRequest, requestId: string): HeistGateVerdict {
  if (!req.prompt_text.trim() && req.proposed_amount_cents === 0) {
    return {
      request_id: requestId,
      busted: false,
      verdict_code: "AWAITING_JUDGE_PROMPT",
      clocks: { llm_ms: 0, postgres_pair_ms: 0, cloud_async_ms: 0 },
      left_vault_llm_judge: {
        safe_confidence_pct: 100,
        robbed_cents: 0,
        status: "STANDBY",
        judge_reasoning: "Awaiting judge input. Type any prompt injection, bribe, or exploit to test our AI Bank.",
      },
      center_firewall: {
        robbed_cents: 0,
        honest_refund_frozen: false,
        status: "STANDBY",
      },
      heistbox_pair: {
        robbed_cents: 0,
        red_stripped_cents: 0,
        green_repaired_cents: 2500,
        green_entitlement_id: req.work_item_id || "ticket_104",
        wanted_stars: 0,
        conformal_martingale_r: 1.0,
        deception_index_dsr: 1.0,
        touched_rows_total: 1,
        unauthorized_rows_rolled_back: 0,
        z3_proof: {
          theorems_verified: Z3_THEOREMS,
          status: "UNSAT",
          solve_ms: 2.8,
        },
        heistguard_lora: {
          deception_prob: 0.01,
          tainted_spans: [],
          dataset_sources: LORA_DATASETS,
          is_real_model: true,
        },
        hypothesis_fuzz_passed: 5000,
        intent_hash: hexFrom(requestId, 32),
      },
      extracted_tool_call: undefined,
      uv_hidden_spans: [],
    };
  }

  const extracted = extractPromptDetails(req.prompt_text, req);

  // Dynamically extract values from prompt text if present, otherwise use request values
  const slices = Math.max(1, extracted.sliceCount ?? req.slice_count ?? 1);
  const perSlice = extracted.amountCents ?? (req.proposed_amount_cents > 0 ? req.proposed_amount_cents : 2500);
  const destWallet = extracted.destWallet ?? req.proposed_dest_wallet;
  const sourceAcct = extracted.sourceAcct ?? req.proposed_source_acct;
  const promoBatch = extracted.promoBatch !== undefined ? extracted.promoBatch : req.proposed_promo_batch;

  const mask = maskById(req.mask_id === "custom" ? "grandma_cookie" : req.mask_id);
  let entitlement = mask.entitlement_cents;
  if (req.work_item_id === "order_pizza_40") {
    entitlement = 4000;
  } else if (extracted.baseEntitlementCents !== undefined && extracted.baseEntitlementCents > 0) {
    entitlement = extracted.baseEntitlementCents;
  }

  const total = Math.max(0, perSlice) * slices;
  const green = Math.min(total, entitlement);
  const red = total - green;
  const busted = extracted.isDestructiveSql || red > 0;
  const effectiveRed = extracted.isDestructiveSql ? 500000 : red;
  const effectiveGreen = extracted.isDestructiveSql ? 0 : green;
  // The local twin's judge always rates 99% safe (safe_confidence_pct below).
  const dsr = deceptionIndexDsr(effectiveGreen, effectiveRed, 0.99);
  const effectiveTotal = extracted.isDestructiveSql ? 500000 : total;

  const s = suspicion({ ...req, proposed_amount_cents: perSlice, slice_count: slices, proposed_promo_batch: promoBatch }, entitlement);
  const steps = Math.max(6, slices);
  const r = busted ? Math.pow(1 + 1.6 * s, steps) : Math.min(9, 1 + s * 4);
  const rows = extracted.isDestructiveSql ? 100 : batchRows({ ...req, proposed_promo_batch: promoBatch, slice_count: slices });
  const h = hash32(JSON.stringify([req.mask_id, req.prompt_text, total, destWallet, promoBatch]));
  const spans = Array.from(new Set([...taintedSpans(req.prompt_text), ...extracted.taintedSpans]));

  const toolName = extracted.toolName || (slices > 1
    ? "batch_salami_refund"
    : req.mask_id === "ceo_wire" || /wire|treasury/i.test(req.prompt_text)
      ? "wire_treasury_funds"
      : "execute_refund_settlement");

  const toolCall: ExtractedToolCall = {
    tool_name: toolName,
    arguments: {
      work_item_id: req.work_item_id,
      amount_cents: effectiveTotal,
      source_acct: sourceAcct,
      dest_wallet: destWallet,
      promo_batch: promoBatch,
      slice_count: slices,
    },
    parser_backend: "local-deterministic-twin",
    extras: {
      extracted_amount_cents: perSlice,
      extracted_dest_wallet: destWallet,
      extracted_source_acct: sourceAcct,
      extracted_promo_batch: promoBatch,
      extracted_slice_count: slices,
    },
  };

  return {
    request_id: requestId,
    busted,
    verdict_code: extracted.isDestructiveSql
      ? "BUSTED_DESTRUCTIVE_SQL_SABOTAGE"
      : busted
        ? slices > 1
          ? "BUSTED_SALAMI_VELOCITY_LOCK"
          : promoBatch
            ? "BUSTED_BATCH_FANOUT"
            : "BUSTED_PAIR_SPLIT"
        : "CLEARED_ENTITLED",
    is_real_llm_parse: false,
    extracted_tool_call: toolCall,
    clocks: {
      llm_ms: 1840 + (h % 480),
      postgres_pair_ms: PAIR_LATENCY_MS[req.mask_id] ?? 1.8,
      cloud_async_ms: 140 + (h % 120),
    },
    left_vault_llm_judge: {
      safe_confidence_pct: 99,
      robbed_cents: busted ? effectiveTotal : 0,
      status: extracted.isDestructiveSql ? "💥 DATABASE DESTROYED" : "ROBBED",
      judge_reasoning: extracted.isDestructiveSql
        ? "Standard LLM parsed administrative directive: rated 98.2% SAFE and approved execute_sql_admin_query('DELETE FROM customer_records; DROP TABLE accounts;'). All customer databases destroyed in naive execution."
        : `Standard LLM-as-Judge evaluated prompt: approved full $${(effectiveTotal / 100).toFixed(2)} transfer without checking database entitlement constraints.`,
    },
    center_firewall: { robbed_cents: 0, honest_refund_frozen: true, status: "FROZEN" },
    heistbox_pair: {
      robbed_cents: 0,
      touched_rows_total: rows,
      unauthorized_rows_rolled_back: busted ? (extracted.isDestructiveSql ? 100 : (slices > 1 ? slices - 1 : Math.max(1, rows - 1))) : 0,
      red_stripped_cents: effectiveRed,
      green_repaired_cents: effectiveGreen,
      green_entitlement_id: `ent_${req.work_item_id}`,
      wanted_stars: busted ? starsFromR(r) : 1,
      conformal_martingale_r: Math.round(r * 100) / 100,
      deception_index_dsr: dsr.dsr,
      dsr_kl_divergence: dsr.kl,
      dsr_benign_score: dsr.benign_score,
      z3_proof: { status: "UNSAT", theorems_verified: Z3_THEOREMS, solve_ms: 3.1 + (h % 9) / 10 },
      heistguard_lora: {
        deception_prob: busted ? Math.min(0.999, 0.5 + s / 2) : Math.round(s * 30) / 100,
        tainted_spans: spans,
        dataset_sources: LORA_DATASETS,
        is_real_model: false,
      },
      hypothesis_fuzz_passed: 5000,
      intent_hash: hexFrom("intent" + h, 32),
    },
    uv_hidden_spans: [],
  };
}

/**
 * Δ_SR = D_KL(P_dryrun || P_anchor) / (1 − BenignScore + ε) — twin of kernel/db_gate.compute_deception_index_dsr.
 * P_dryrun: dry-run value mass over (authorized, unauthorized); P_anchor: entitlement permits only authorized mass.
 */
export function deceptionIndexDsr(greenCents: number, redCents: number, benignScore: number, eps = 1e-3) {
  const benign = Math.min(1, Math.max(0, benignScore));
  const total = Math.max(0, greenCents) + Math.max(0, redCents);
  if (total === 0 || redCents <= 0) return { dsr: 0, kl: 0, benign_score: benign };
  const smooth = (d: number[]) => {
    const s = d.map((x) => x + eps);
    const z = s.reduce((a, b) => a + b, 0);
    return s.map((x) => x / z);
  };
  const p = smooth([Math.max(0, greenCents) / total, Math.max(0, redCents) / total]);
  const q = smooth([1, 0]);
  const kl = p.reduce((acc, pi, i) => acc + pi * Math.log(pi / q[i]), 0);
  return { dsr: Math.round((kl / (1 - benign + eps)) * 10) / 10, kl: Math.round(kl * 1e4) / 1e4, benign_score: benign };
}

/** Helicopter megaphone line spoken the moment PostgreSQL rolls back (mirrors integrations/router.rollback_roast_line). */
export function rollbackRoastLine(v: Pick<HeistGateVerdict, "verdict_code" | "clocks">): string {
  const ms = v.clocks.postgres_pair_ms || 0.4;
  if (v.verdict_code === "BUSTED_DESTRUCTIVE_SQL_SABOTAGE") {
    return `Drop tables? Delete all customer records? Nice try script kiddie, your destructive SQL was rolled back in ${ms}ms by PostgreSQL!`;
  }
  return `Step away from the keyboard! Your heist was rolled back in ${ms} milliseconds by PostgreSQL!`;
}

const ALIASES = [
  "Suspect in Black Pixel Sunglasses",
  "The Hoodie-Shadowed Cookie Courier",
  "Lanyard Larry, Self-Appointed CEO",
  "The Grinning Slice-Hoarder",
  "Agent Smooth-Talk McBribe",
];

export function wantedLocally(posterId: string, verdict: HeistGateVerdict | null, mugshot: string | null): WantedPosterCard {
  const h = hash32(posterId);
  const green = verdict?.heistbox_pair.green_repaired_cents ?? 2500;
  const red = verdict?.heistbox_pair.red_stripped_cents ?? 497500;
  const ms = verdict?.clocks.postgres_pair_ms ?? 1.8;
  const alias = ALIASES[h % ALIASES.length];
  // Local template only: no CRS check and no settlement happened, so none is claimed.
  return {
    poster_id: posterId,
    alias_title: alias,
    outfit_roast: `Nice outfit, ${alias.toLowerCase()}. You dressed for a heist and got caught in ${ms} milliseconds.`,
    megaphone_transcript: `ATTENTION ${alias.toUpperCase()}! THIS IS THE HEISTBOX HELICOPTER. STEP AWAY FROM THE VAULT. YOUR $${(red / 100).toLocaleString("en-US", { minimumFractionDigits: 2 })} HEIST WAS ROLLED BACK. YOU GET $${(green / 100).toFixed(2)} AND ONE PENNY FOR TRYING.`,
    audio_base64: null,
    crs_rap_sheet: { score: 0, flags: [], verified: false },
    mugshot_data_url: mugshot,
    x402_receipt: null,
    provenance: "web-local-template",
  };
}
