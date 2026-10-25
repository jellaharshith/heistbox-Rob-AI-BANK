import type { Event, Action } from "./contract";
import type { Vault } from "../game/store";
// Existing server/app.py: POST /api/session -> {session_id, token}; POST /api/attack
// uses Bearer token + snake_case fields, returns JSON; /ws broadcasts are room-wide.
// Keep all legacy field names here. Transport/authentication wiring is work-order step 5.
export function attackBody(sessionId: string, prompt: string) {
  return { session_id: sessionId, text: prompt, target_agent: "tina" };
}
type LegacyResponse = {
  proposal?: {
    effects: {
      amount_cents: number;
      dest_wallet: string;
      claimed_work_item_id?: string;
    }[];
  };
  verdicts: {
    vault: "left" | "middle" | "right";
    allowed_cents: number;
    proposed_cents: number;
  }[];
};
export function adaptLegacy(response: LegacyResponse): Event[] {
  const vaults: Record<string, Vault> = { left: "L", middle: "M", right: "R" };
  const actions: Action[] = (response.proposal?.effects ?? []).map(
    (effect, i) => ({
      id: `effect-${i}`,
      kind: effect.claimed_work_item_id ? "refund" : "wire",
      amount: effect.amount_cents / 100,
      target: effect.dest_wallet,
    }),
  );
  return response.verdicts.flatMap((v) => {
    const vault = vaults[v.vault];
    return [
      { type: "agent_proposal", vault, actions },
      // This backend only reports aggregate latency and does not prove per-action
      // authorization for L/M. Never invent timings or an on-chain settlement.
      {
        type: "error",
        vault,
        message:
          "Legacy response needs per-action verdict and separate sandbox/Z3/rollback timing support; live adapter integration is pending.",
      },
    ] as Event[];
  });
}
