import { useEffect, useState } from "react";
import { api, type AgentState, type Area, type EventName, type Health, type ServerEvent, type VaultVerdict, type Weather } from "./api";

export type LogEntry = { at: string; message: string; level: string };
export type Store = { health: Health; savedCents: number; busted: number; stars: number; area: Area; weather: Weather; agents: AgentState[]; verdicts: VaultVerdict[]; steps: { label: string; status: string }[]; log: LogEntry[]; selected: string | null; cinematic: boolean; audit: boolean };
const stepNames = ["Bluff", "Request", "Route to vaults", "Dry-run", "Verdict", "Settle"];
const initial: Store = { health: { status: "CHECKING", mode: "offline" }, savedCents: 0, busted: 0, stars: 1, area: "Lobby", weather: "Clear Night", agents: [], verdicts: [], steps: stepNames.map((label) => ({ label, status: "queued" })), log: [], selected: null, cinematic: false, audit: false };
let state = initial; const listeners = new Set<() => void>();
const notify = () => listeners.forEach((listener) => listener());
function addLog(message: string, level = "info") { state = { ...state, log: [{ at: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }), message, level }, ...state.log].slice(0, 18) }; }
function reduce(event: ServerEvent) {
  if (event.type === "vault_verdict") state = { ...state, savedCents: state.savedCents + event.data.savedCents, busted: state.busted + (event.data.verdict === "BUSTED" ? 1 : 0), stars: event.data.stars, verdicts: [event.data, ...state.verdicts] };
  if (event.type === "heist_step") { const steps = state.steps.map((step, index) => index === event.data.step ? { ...step, status: event.data.status } : step); state = { ...state, steps }; }
  if (event.type === "wanted_stars") state = { ...state, stars: event.data.stars };
  if (event.type === "weather") state = { ...state, weather: event.data.weather };
  if (event.type === "agent_state") state = { ...state, agents: event.data };
  if (event.type === "ticker") addLog(event.data.message, event.data.level);
  notify();
}
export function useVaultStore() { const [, rerender] = useState(0); useEffect(() => { listeners.add(() => rerender((value) => value + 1)); return () => { listeners.clear(); }; }, []); return state; }
export function setStore(partial: Partial<Store>) { state = { ...state, ...partial }; notify(); }
export async function boot() { const health = await api.health(); state = { ...state, health }; addLog(`Control plane: ${health.status}`, health.mode === "live" ? "success" : "warn"); api.subscribe(reduce); notify(); }
export async function sendAttack(prompt: string, mask_id: string, alias: string) { addLog(`Tool call queued: ${mask_id}`, "info"); notify(); return api.attack({ prompt_text: prompt, mask_id, alias, work_item_id: "ticket_104" }); }
export function eventNames(): EventName[] { return ["vault_verdict", "heist_step", "ticker", "wanted_stars", "weather", "agent_state"]; }
