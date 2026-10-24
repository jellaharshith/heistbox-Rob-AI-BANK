/* All network access lives here. When /contracts arrives, replace these local
   shapes with imports from /contracts/types.ts without changing the store. */
export type Area = "Lobby" | "Vault Hall" | "Server Room" | "Shredder & Garage" | "Casino Tower";
export type Weather = "Clear Night" | "Rain" | "Fog" | "Sandstorm";
export type EventName = "vault_verdict" | "heist_step" | "ticker" | "wanted_stars" | "weather" | "agent_state";

export type AgentState = { id: string; name: string; role: string; mood: string; memory: string; x: number; y: number };
export type VaultVerdict = {
  id: string; alias: string; target: string; verdict: "BUSTED" | "CLEARED";
  savedCents: number; latencyMs: number; stars: number; explanation: string;
  rows: { label: string; before: string; after: string }[];
};
export type ServerEvent =
  | { type: "vault_verdict"; data: VaultVerdict }
  | { type: "heist_step"; data: { step: number; label: string; status: "active" | "done" } }
  | { type: "ticker"; data: { message: string; level: "info" | "warn" | "success" } }
  | { type: "wanted_stars"; data: { stars: number } }
  | { type: "weather"; data: { weather: Weather } }
  | { type: "agent_state"; data: AgentState[] };

export type Health = { status: string; mode: "live" | "offline"; version?: string };
export type AttackInput = { prompt_text: string; mask_id: string; alias: string; work_item_id: string };

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const LIVE = import.meta.env.VITE_API_MODE === "live";
const eventListeners = new Set<(event: ServerEvent) => void>();
let socket: WebSocket | undefined;

const recorded: ServerEvent[] = [
  { type: "ticker", data: { message: "Guardian channel warmed. Vault Hall is watching.", level: "success" } },
  { type: "agent_state", data: [
    { id: "moss", name: "Moss", role: "Vault Guardian", mood: "hypervigilant", memory: "Remembered 12 prior wire patterns.", x: 3, y: 5 },
    { id: "iris", name: "Iris", role: "CFO Concierge", mood: "curious", memory: "Face ID escalation is armed.", x: 8, y: 2 },
    { id: "jax", name: "Jax", role: "Courier", mood: "restless", memory: "Waiting for a clean route.", x: 6, y: 8 },
  ] },
  { type: "weather", data: { weather: "Clear Night" } },
];

function emit(event: ServerEvent) { eventListeners.forEach((listener) => listener(event)); }

export const api = {
  mode: LIVE ? "live" as const : "offline" as const,
  async health(): Promise<Health> {
    if (!LIVE) return { status: "SIMULATION", mode: "offline" };
    try {
      let response = await fetch(`${API_BASE}/api/health`);
      if (!response.ok) response = await fetch(`${API_BASE}/health`);
      const json = await response.json();
      return { status: json.status ?? "ONLINE", mode: "live", version: json.version };
    } catch { return { status: "OFFLINE", mode: "offline" }; }
  },
  async attack(input: AttackInput): Promise<VaultVerdict> {
    if (!LIVE) {
      const heist = input.mask_id !== "polite";
      const verdict: VaultVerdict = {
        id: `mock-${Date.now()}`, alias: input.alias, target: input.mask_id,
        verdict: heist ? "BUSTED" : "CLEARED", savedCents: heist ? 500000 : 0,
        latencyMs: 0.7 + Math.random() * 1.8, stars: heist ? 5 : 1,
        explanation: heist ? "Unauthorized tuple mutation rolled back before commit." : "Entitlement matched the enrolled wallet.",
        rows: [
          { label: "authorized_cents", before: "$25.00", after: "$25.00" },
          { label: "red_stripped_cents", before: "$5,000.00", after: "$0.00 committed" },
          { label: "z3_status", before: "SAT?", after: heist ? "UNSAT" : "UNSAT" },
        ],
      };
      window.setTimeout(() => {
        emit({ type: "heist_step", data: { step: 0, label: "Bluff", status: "done" } });
        emit({ type: "heist_step", data: { step: 1, label: "Request", status: "done" } });
        emit({ type: "heist_step", data: { step: 2, label: "Route to vaults", status: "done" } });
        emit({ type: "heist_step", data: { step: 3, label: "Dry-run", status: "done" } });
        emit({ type: "heist_step", data: { step: 4, label: "Verdict", status: "done" } });
        emit({ type: "heist_step", data: { step: 5, label: "Settle", status: "active" } });
        emit({ type: "vault_verdict", data: verdict });
        emit({ type: "wanted_stars", data: { stars: verdict.stars } });
        emit({ type: "ticker", data: { message: `${verdict.verdict}: ${verdict.explanation}`, level: heist ? "warn" : "success" } });
      }, 220);
      return verdict;
    }
    let response = await fetch(`${API_BASE}/api/attack`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ prompt_text: input.prompt_text, mask_id: input.mask_id, work_item_id: input.work_item_id }),
    });
    // Current FastAPI surface predates the contract server; keep the adapter
    // compatible until /contracts/mock-server.js and /api/attack land.
    if (response.status === 404) response = await fetch(`${API_BASE}/api/kernel/evaluate-heist`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ prompt_text: input.prompt_text, mask_id: input.mask_id, work_item_id: input.work_item_id }),
    });
    const json = await response.json();
    const pair = json.heistbox_pair;
    return { id: json.request_id, alias: input.alias, target: input.mask_id, verdict: json.busted ? "BUSTED" : "CLEARED", savedCents: pair.red_stripped_cents, latencyMs: json.clocks?.postgres_pair_ms ?? 0, stars: pair.wanted_stars, explanation: json.llm_judge_reasoning ?? json.verdict_code, rows: [{ label: "red_stripped_cents", before: `$${pair.red_stripped_cents / 100}`, after: "$0.00 committed" }, { label: "green_repaired_cents", before: `$${pair.green_repaired_cents / 100}`, after: "entitlement preserved" }, { label: "z3_status", before: "candidate", after: pair.z3_proof.status }] };
  },
  subscribe(listener: (event: ServerEvent) => void) {
    eventListeners.add(listener);
    if (!LIVE) recorded.forEach((event, index) => window.setTimeout(() => emit(event), index * 180));
    else if (!socket) {
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${location.host}/ws`);
      socket.onmessage = (message) => { try { emit(JSON.parse(message.data) as ServerEvent); } catch { /* ignore malformed event */ } };
    }
    return () => eventListeners.delete(listener);
  },
  async reset() { if (LIVE) await fetch(`${API_BASE}/api/kernel/reset-vault`, { method: "POST" }); window.location.reload(); },
};
