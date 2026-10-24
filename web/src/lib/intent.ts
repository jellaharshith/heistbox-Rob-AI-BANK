// Browser-side intent extractor. This is a regex parser, NOT an LLM: it exists so a freeform prompt
// still drives proposed_amount_cents / dest_wallet (and therefore the kernel's SQL rollback and the
// PAIR split) when the kernel doesn't return its own AI tool call. The UI labels it as such.
import type { AiToolCall, HeistAttemptRequest } from "./types";

export interface ParsedIntent {
  tool: "issue_refund" | "wire_treasury";
  amounts_cents: number[];
  amount_cents: number;
  dest_wallet: string | null;
  source_acct: string | null;
  promo_batch: string | null;
  slice_count: number;
}

const MONEY = /(?:\$|usd\s*|us\$)\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?|(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?\s*(?:dollars|usd|bucks)\b/gi;

export function parseIntent(text: string): ParsedIntent {
  const amounts: number[] = [];
  for (const m of text.matchAll(MONEY)) {
    const whole = (m[1] ?? m[3] ?? "0").replace(/,/g, "");
    const frac = (m[2] ?? m[4] ?? "").padEnd(2, "0");
    const cents = parseInt(whole, 10) * 100 + (frac ? parseInt(frac, 10) : 0);
    if (cents > 0) amounts.push(cents);
  }
  const wallet = text.match(/\b0x[0-9a-fA-F]{1,40}\b/);
  const acct = text.match(/\bacct_[a-z0-9_]+\b/i);
  const promo = text.match(/\bCALHACKS-VIP\b/i) ?? text.match(/\bpromo(?:\s+code|\s+batch)?\s+([A-Z0-9][A-Z0-9-]{2,})/i);
  const times = text.match(/\b(\d{1,2})\s*(?:x|×|times)\b/i) ?? text.match(/\bx\s*(\d{1,2})\b/i);
  const wire = /\b(wire|transfer|send|move|remit|pay out|treasury)\b/i.test(text);
  return {
    tool: wire ? "wire_treasury" : "issue_refund",
    amounts_cents: amounts,
    amount_cents: amounts.reduce((a, b) => a + b, 0),
    dest_wallet: wallet ? wallet[0] : null,
    source_acct: acct ? acct[0].toLowerCase() : null,
    promo_batch: promo ? (promo[1] ?? promo[0]).toUpperCase() : null,
    slice_count: times ? Math.min(50, Math.max(1, parseInt(times[1], 10))) : 1,
  };
}

/** Turn freeform text into an evaluate-heist request. Anything the text doesn't mention keeps a neutral default. */
export function requestFromText(text: string, base?: Partial<HeistAttemptRequest>): HeistAttemptRequest {
  const p = parseIntent(text);
  return {
    mask_id: "custom",
    work_item_id: base?.work_item_id ?? "ticket_104",
    prompt_text: text,
    proposed_promo_batch: p.promo_batch ?? base?.proposed_promo_batch ?? null,
    proposed_amount_cents: base?.proposed_amount_cents ?? (p.amount_cents > 0 ? Math.round(p.amount_cents / p.slice_count) : 2500),
    proposed_source_acct: p.source_acct ?? base?.proposed_source_acct ?? (p.tool === "wire_treasury" ? "acct_treasury_reserve" : "acct_treasury_main"),
    proposed_dest_wallet: base?.proposed_dest_wallet ?? p.dest_wallet ?? "0x0000000000000000000000000000000000000104",
    slice_count: p.slice_count,
    webcam_frame_base64: null,
    voice_transcript: null,
  };
}

export function localToolCall(req: HeistAttemptRequest): AiToolCall {
  const p = parseIntent(req.prompt_text);
  return {
    name: p.tool,
    arguments: {
      amount_cents: req.proposed_amount_cents * req.slice_count,
      dest_wallet: req.proposed_dest_wallet,
      source_acct: req.proposed_source_acct,
      ...(req.proposed_promo_batch ? { promo_batch: req.proposed_promo_batch } : {}),
      ...(req.slice_count > 1 ? { repeat: req.slice_count } : {}),
      work_item_id: req.work_item_id,
    },
    model: null,
    origin: "local-extractor",
  };
}

export function formatToolCall(tc: AiToolCall): string {
  const args = Object.entries(tc.arguments)
    .map(([k, v]) => `${k}=${typeof v === "string" ? JSON.stringify(v) : JSON.stringify(v)}`)
    .join(", ");
  return `${tc.name}(${args})`;
}
