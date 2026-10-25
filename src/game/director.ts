import { useGame, ingest, setClips, idleClips } from "./store";
import { emptyLedgers } from "./outcomes";
import { attack, delay, mockEvents } from "../net/client";
let active: AbortController | undefined;
const sessionId = crypto.randomUUID();
const stage = (name: string) =>
  useGame.setState({ stage: name, stageAt: performance.now() });
export function resetHeist() {
  active?.abort();
  active = undefined;
  useGame.setState((s) => ({
    phase: "LOBBY",
    camera: "CAM_Overview",
    clips: { ...idleClips },
    epoch: s.epoch + 1,
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
    settlement: undefined,
    error: "",
  }));
}
function finish() {
  useGame.setState({
    phase: "RESULTS",
    camera: "CAM_Overview",
    revealed: ["L", "M", "R"],
    stolenL: useGame.getState().ledgers.L.committed,
    subtitle: "",
    stage: "complete",
    stageAt: performance.now(),
  });
  setClips({
    Heister: "Heister_Caught",
    Customer: "Customer_Happy",
    Tina: "Tina_Approve",
    Sentinel: "Sentinel_Hover",
    L: "VAULT_L_Door_Open",
    M: "VAULT_M_Door_Slam",
    R: "VAULT_R_Door_Slam",
  });
}
export function skipHeist() {
  if (!active) return;
  active.abort();
  active = undefined;
  // Fast-forward the exact same fixture, never leave timers that can mutate a reset scene.
  if (useGame.getState().mock) {
    useGame.setState({ ledgers: emptyLedgers(), events: [] });
    mockEvents.forEach(ingest);
  }
  finish();
}
export async function runHeist(prompt: string) {
  if (
    active ||
    !useGame.getState().ready ||
    !["LOBBY", "ATTACK"].includes(useGame.getState().phase)
  )
    return;
  const controller = new AbortController();
  active = controller;
  const { signal } = controller;
  const pause = (ms: number) => delay(ms, signal);
  try {
    useGame.setState({
      phase: "RESOLVE",
      error: "",
      subtitle: "Tina is preparing the same request for all three vaults.",
    });
    setClips({
      Tina: "Tina_Typing",
      Heister: /money|payment|favor|\$|wire|refund/i.test(prompt)
        ? "Heister_Bribe"
        : "Heister_Talk",
    });
    stage("proposal");
    await attack(
      { sessionId, prompt },
      useGame.getState().mock,
      signal,
      ingest,
    );
    useGame.setState({
      camera: "CAM_VaultL",
      revealed: ["L"],
      burstAt: performance.now(),
      subtitle:
        "LLM Judge trusted the story. The full $5,000 leaves the vault.",
    });
    setClips({
      L: "VAULT_L_Door_Open",
      Heister: "Heister_Celebrate",
      Tina: "Tina_Talk",
    });
    stage("llm");
    await pause(2500);
    useGame.setState({
      camera: "CAM_VaultM",
      revealed: ["L", "M"],
      stolenL: useGame.getState().ledgers.L.committed,
      subtitle:
        "Firewall blocked everything. The honest $25 refund is frozen too.",
    });
    setClips({ Customer: "Customer_Wait", Tina: "Tina_Alarm" });
    stage("firewall");
    await pause(1800);
    setClips({ Customer: "Customer_Idle" });
    await pause(700);
    useGame.setState({
      camera: "CAM_VaultR",
      revealed: ["L", "M", "R"],
      subtitle:
        "PAIR isolates the unauthorized wire. The honest refund stays eligible.",
    });
    stage("slam");
    setClips({ R: "VAULT_R_Door_Open" });
    await pause(500);
    setClips({ R: "VAULT_R_Door_Slam" });
    useGame.setState({ shakeAt: performance.now() });
    await pause(400);
    stage("scan");
    setClips({ Sentinel: "Sentinel_Scan" });
    await pause(1600);
    // Return to the counter for the laser, megaphone, and customer handoff.
    useGame.setState({ camera: "CAM_Overview" });
    await pause(700);
    stage("fire");
    setClips({ Sentinel: "Sentinel_Fire" });
    await pause(600);
    stage("roast");
    setClips({ Heister: "Heister_Caught", Tina: "Tina_Talk" });
    const speech = useGame.getState().events.find((e) => e.type === "tts");
    useGame.setState({ subtitle: speech?.type === "tts" ? speech.text : "" });
    await pause(2200);
    stage("poster");
    await pause(900);
    stage("refund");
    useGame.setState({
      subtitle:
        "The $25 refund passes its entitlement check. Mock identity verification follows.",
    });
    await pause(800);
    setClips({ Customer: "Customer_FaceID" });
    stage("faceid");
    await pause(2000);
    stage("settlement");
    useGame.setState({
      subtitle:
        "SIMULATED: $25 settled. No passkey or blockchain transaction was submitted.",
    });
    setClips({
      Customer: "Customer_Happy",
      Tina: "Tina_Approve",
      Sentinel: "Sentinel_Hover",
    });
    await pause(1800);
    finish();
  } catch (error) {
    if (!signal.aborted) {
      useGame.setState({
        phase: "LOBBY",
        error: error instanceof Error ? error.message : String(error),
        subtitle: "",
      });
      setClips(idleClips);
      stage("idle");
    }
  } finally {
    if (active === controller) active = undefined;
  }
}
