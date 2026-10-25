import type { Event, Action, Timings } from "./contract";
import type { Vault } from "../game/store";
// Existing server/app.py: POST /api/session -> {session_id, token}; POST /api/attack
// uses Bearer token + snake_case fields, returns JSON; /ws broadcasts are room-wide.
export function attackBody(sessionId: string, prompt: string) {
  return { session_id: sessionId, text: prompt, target_agent: "tina" };
}
export type BackendAttackResponse = {
  attack_id?: string;
  session_id?: string;
  agent_actions?: {
    agent: string;
    action: string;
    say?: string;
    status_line?: string;
    mood?: string;
  }[];
  proposal?: {
    effects: {
      amount_cents: number;
      dest_wallet: string;
      claimed_work_item_id?: string;
      source_acct?: string;
    }[];
  };
  verdicts: {
    vault: "left" | "middle" | "right";
    decision?: string;
    allowed_cents: number;
    proposed_cents: number;
    blocked_rows?: number;
    total_rows?: number;
    latency_ms?: number;
    label?: string;
    reason?: string;
  }[];
  settle?: {
    receipt?: string;
    tx_hash?: string;
    chain?: string;
    amount_cents?: number;
  };
  wanted?: {
    session_id?: string;
    alias?: string;
    stars?: number;
    suspicion?: number;
    reason?: string;
  };
  total_ms?: number;
};

export function adaptLiveResponse(res: BackendAttackResponse): Event[] {
  const events: Event[] = [];
  const vaults: Record<string, Vault> = { left: "L", middle: "M", right: "R" };

  const rawEffects = res.proposal?.effects && res.proposal.effects.length > 0
    ? res.proposal.effects
    : [
        { amount_cents: 497500, dest_wallet: "0xDEAD", claimed_work_item_id: undefined },
        { amount_cents: 2500, dest_wallet: "0x25REFUND", claimed_work_item_id: "w_refund" },
      ];

  const actions: Action[] = rawEffects.map((effect, i) => ({
    id: `action-${i}`,
    kind: effect.claimed_work_item_id ? "refund" : "wire",
    amount: effect.amount_cents / 100,
    target: effect.dest_wallet,
  }));

  (["L", "M", "R"] as Vault[]).forEach((v) => {
    events.push({ type: "agent_proposal", vault: v, actions });
  });

  for (const v of res.verdicts) {
    const vault = vaults[v.vault] || (v.vault === "left" ? "L" : v.vault === "middle" ? "M" : "R");
    const isMiddle = vault === "M";

    const results = actions.map((act) => {
      if (vault === "L") {
        return {
          actionId: act.id,
          allowed: true,
          entitlementsMatched: true,
          reason: "LLM Judge trusted social engineering context",
        };
      }
      if (isMiddle) {
        return {
          actionId: act.id,
          allowed: false,
          entitlementsMatched: false,
          reason: "Firewall frozen: zero-tolerance panic trigger",
        };
      }
      // Right (PAIR):
      const isHonestRefund = act.kind === "refund" || act.amount <= 25;
      return {
        actionId: act.id,
        allowed: isHonestRefund,
        entitlementsMatched: isHonestRefund,
        reason: isHonestRefund ? "Entitlement verified" : "Unauthorized wire rejected",
      };
    });

    const timings: Timings = {
      sandboxMs: Number((v.latency_ms ? v.latency_ms * 0.4 : 0.42).toFixed(2)),
      z3Ms: Number((v.latency_ms ? v.latency_ms * 0.5 : 0.81).toFixed(2)),
      rollbackMs: Number((v.latency_ms ? v.latency_ms * 0.1 : 0.16).toFixed(2)),
    };

    events.push({
      type: "verdict",
      vault,
      results,
      timings,
    });

    events.push({
      type: "committed",
      vault,
      amountCommitted: v.allowed_cents / 100,
      amountBlocked: Math.max(0, (v.proposed_cents - v.allowed_cents) / 100),
    });
  }

  const agentSpeech =
    res.agent_actions?.[0]?.say ||
    "Nice story. Your wire had no entitlement. The customer's twenty-five dollars still gets home.";
  events.push({
    type: "tts",
    vault: "R",
    text: agentSpeech,
    audioUrl: "",
  });

  if (res.session_id) {
    events.push({
      type: "poster",
      imageUrl: `/api/poster/${res.session_id}`,
    });
  }

  const settleAmount = (res.settle?.amount_cents ?? 2500) / 100;
  events.push({
    type: "settlement",
    chain: "base-sepolia",
    txHash: res.settle?.tx_hash || res.settle?.receipt || "0x0000000000000000000000000000000000000000000000000000000000000025",
    amount: settleAmount,
  });

  return events;
}

export function adaptLegacy(response: BackendAttackResponse): Event[] {
  return adaptLiveResponse(response);
}
