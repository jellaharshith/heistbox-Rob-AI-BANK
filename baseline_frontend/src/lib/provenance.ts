// Honest labelling helpers shared by Arena, CFO Audit and the poster page.
import type { SettleContext } from "./api";

export type ParserKind = "llm" | "rule" | "local" | "none";

/**
 * Classify a kernel `parser_backend` by what it actually is, not by the kernel's `is_real_llm_parse` flag.
 * kernel/live_agent_parser.py reports `heistbox-nl-tool-extractor-v2` (a regex extractor) with
 * is_real_llm_parse=true, so the flag alone can't be trusted.
 */
export function classifyParser(backend: string | null | undefined): { kind: ParserKind; badge: string } {
  const b = (backend ?? "").trim();
  if (!b || b === "unreported") return { kind: "none", badge: "parser not reported" };
  if (b === "local-deterministic-twin") return { kind: "local", badge: "local twin · kernel unreachable" };
  if (/^ollama/i.test(b) || /anthropic|claude|gemini|mcp/i.test(b)) return { kind: "llm", badge: `LLM · ${b}` };
  return { kind: "rule", badge: `rule-based parser · ${b}` };
}

// ── Poster links carry the settle context so a phone can settle without the desktop's localStorage ──

const ORIGIN_KEY = "heistbox:public-origin";
const SETTLE_KEY = (id: string) => `heistbox:settle:${id}`;

export function loadPublicOrigin(): string {
  try {
    return localStorage.getItem(ORIGIN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function savePublicOrigin(v: string) {
  try {
    if (v.trim()) localStorage.setItem(ORIGIN_KEY, v.trim().replace(/\/$/, ""));
    else localStorage.removeItem(ORIGIN_KEY);
  } catch {}
}

export function saveSettleContext(posterId: string, ctx: SettleContext) {
  try {
    localStorage.setItem(SETTLE_KEY(posterId), JSON.stringify(ctx));
  } catch {}
}

export function loadSettleContext(posterId: string): SettleContext | null {
  try {
    const raw = localStorage.getItem(SETTLE_KEY(posterId));
    return raw ? (JSON.parse(raw) as SettleContext) : null;
  } catch {
    return null;
  }
}

export function settleQuery(ctx: SettleContext): string {
  const q = new URLSearchParams({
    rid: ctx.request_id,
    ih: ctx.intent_hash,
    sh: ctx.settlement_hash,
    g: String(ctx.green_cents),
    r: String(ctx.red_cents),
    ent: ctx.entitlement_id,
    to: ctx.recipient,
  });
  return q.toString();
}

export function settleFromQuery(search: string): SettleContext | null {
  const q = new URLSearchParams(search);
  const ih = q.get("ih");
  const g = Number(q.get("g"));
  if (!ih || !/^0x[0-9a-fA-F]{8,}$/.test(ih) || !Number.isFinite(g)) return null;
  return {
    request_id: q.get("rid") ?? "",
    intent_hash: ih,
    // Amount/recipient here are display-only; the server settles what this hash commits to.
    settlement_hash: q.get("sh") ?? "",
    green_cents: g,
    red_cents: Number(q.get("r")) || 0,
    entitlement_id: q.get("ent") ?? "",
    recipient: q.get("to") ?? "",
  };
}

export function posterPath(posterId: string, ctx: SettleContext | null): string {
  return `/wanted/${encodeURIComponent(posterId)}${ctx ? `?${settleQuery(ctx)}` : ""}`;
}

/**
 * Both integrations/router.py `_poster_fallback` and main.py `_build_wanted_poster_card` derive the poster's
 * tx_hash as sha256("tx:{poster_id}") — a placeholder, not a broadcast transaction.
 */
export async function isPlaceholderTxHash(posterId: string, txHash: string | null | undefined): Promise<boolean> {
  if (!txHash) return true;
  try {
    const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`tx:${posterId}`));
    const hex = "0x" + Array.from(new Uint8Array(d), (x) => x.toString(16).padStart(2, "0")).join("");
    return hex.toLowerCase() === txHash.toLowerCase();
  } catch {
    // Can't check (no SubtleCrypto on plain-HTTP LAN origins) — treat as unverified.
    return true;
  }
}

/** main.py's GET /wanted/{id} invents a card (with crs verified=true) for any unknown id; spot it so it isn't shown as real. */
export function looksLikeServerPlaceholderPoster(card: { outfit_roast: string; crs_rap_sheet: { flags: string[] } }): boolean {
  return card.outfit_roast.startsWith("Nice disguise,") && card.outfit_roast.includes("Gemini Vision flagged the hoodie + lanyard combo");
}
