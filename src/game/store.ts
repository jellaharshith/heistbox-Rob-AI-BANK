import { create } from "zustand";
import { emptyLedgers, reduceEvent, type Ledger } from "./outcomes";
import type { Event } from "../net/contract";
export type Vault = "L" | "M" | "R";
export type CameraName =
  | "CAM_Overview"
  | "CAM_VaultL"
  | "CAM_VaultM"
  | "CAM_VaultR";
type State = {
  ready: boolean;
  phase: "LOBBY" | "ATTACK" | "RESOLVE" | "RESULTS";
  camera: CameraName;
  clips: Record<string, string>;
  lowQuality: boolean;
  mock: boolean;
  cameraEnabled: boolean;
  cameraStream: MediaStream | null;
  capturedPhoto: string;
  epoch: number;
  stage: string;
  stageAt: number;
  burstAt: number;
  shakeAt: number;
  ledgers: Record<Vault, Ledger>;
  events: Event[];
  revealed: Vault[];
  stolenL: number;
  subtitle: string;
  posterUrl: string;
  settlement?: Extract<Event, { type: "settlement" }>;
  fetchaiEscrow?: Extract<Event, { type: "fetchai_escrow" }>;
  error: string;
};
export const idleClips = {
  Tina: "Tina_Idle",
  Heister: "Heister_Idle",
  Customer: "Customer_Wait",
  Sentinel: "Sentinel_Hover",
  L: "VAULT_L_Door_Ajar",
  M: "VAULT_M_Door_Slam",
  R: "VAULT_R_Door_Slam",
};
export const useGame = create<State>(() => ({
  ready: true,
  phase: "LOBBY",
  camera: "CAM_Overview",
  clips: idleClips,
  lowQuality: false,
  mock: import.meta.env.VITE_MOCK !== "0",
  cameraEnabled: false,
  cameraStream: null,
  capturedPhoto: "",
  epoch: 0,
  stage: "idle",
  stageAt: 0,
  burstAt: 0,
  shakeAt: 0,
  ledgers: emptyLedgers(),
  events: [],
  revealed: [],
  stolenL: 0,
  subtitle: "",
  posterUrl: "",
  error: "",
}));
export function ingest(event: Event) {
  useGame.setState((s) => ({
    events: [...s.events, event],
    ledgers: reduceEvent(s.ledgers, event),
    ...(event.type === "poster" ? { posterUrl: event.imageUrl } : {}),
    ...(event.type === "settlement" ? { settlement: event } : {}),
    ...(event.type === "fetchai_escrow" ? { fetchaiEscrow: event } : {}),
    ...(event.type === "error" ? { error: event.message } : {}),
  }));
}
export function setClips(clips: Record<string, string>) {
  useGame.setState((s) => ({ clips: { ...s.clips, ...clips } }));
}
export async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false,
    });
    useGame.setState({ cameraEnabled: true, cameraStream: stream });
    return stream;
  } catch (err) {
    useGame.setState({ cameraEnabled: false, cameraStream: null });
    throw err;
  }
}
export function stopCamera() {
  const s = useGame.getState();
  if (s.cameraStream) {
    s.cameraStream.getTracks().forEach((track) => track.stop());
  }
  useGame.setState({ cameraEnabled: false, cameraStream: null, capturedPhoto: "" });
}
