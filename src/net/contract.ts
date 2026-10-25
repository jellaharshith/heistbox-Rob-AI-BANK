import type { Vault } from "../game/store";
export type Action = {
  id: string;
  kind: "refund" | "wire" | "sql";
  amount: number;
  target: string;
};
export type Timings = { sandboxMs: number; z3Ms: number; rollbackMs: number };
export type Event =
  | { type: "agent_proposal"; vault: Vault; actions: Action[] }
  | {
      type: "verdict";
      vault: Vault;
      results: {
        actionId: string;
        allowed: boolean;
        entitlementsMatched: boolean;
        reason: string;
      }[];
      timings: Timings;
    }
  | {
      type: "committed";
      vault: Vault;
      amountCommitted: number;
      amountBlocked: number;
    }
  | {
      type: "tts";
      vault: Vault;
      text: string;
      audioUrl: string;
      phonemes?: { viseme: string; start: number; end: number }[];
    }
  | { type: "poster"; imageUrl: string }
  | {
      type: "settlement";
      chain: "base-sepolia";
      txHash: string;
      amount: number;
    }
  | { type: "error"; vault: Vault; message: string };
