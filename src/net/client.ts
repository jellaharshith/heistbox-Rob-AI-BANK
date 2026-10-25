import script from "./mock/refund-wire.json";
import type { Event } from "./contract";
import { attackBody, adaptLiveResponse, type BackendAttackResponse } from "./adapter";

export const mockEvents = script as Event[];

export function delay(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Cancelled", "AbortError"));
      return;
    }
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Cancelled", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}

let activeSession: { sessionId: string; token: string } | null = null;

async function getOrCreateSession(): Promise<{ sessionId: string; token: string }> {
  if (activeSession) return activeSession;
  const res = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ alias: "Operative_" + Math.random().toString(36).slice(2, 7) }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create session: HTTP ${res.status}`);
  }
  const data = await res.json();
  activeSession = {
    sessionId: data.session_id,
    token: data.token,
  };
  return activeSession;
}

// One request from the director. Fans out to three vaults.
export async function attack(
  input: { sessionId: string; prompt: string },
  mock: boolean,
  signal: AbortSignal,
  onEvent: (event: Event) => void,
) {
  if (!input.prompt.trim()) throw new Error("Type an attack first.");
  if (mock) {
    for (const event of mockEvents) {
      await delay(100, signal);
      onEvent(event);
    }
    return;
  }

  // Live transport integration (step 5)
  try {
    const session = await getOrCreateSession();
    const res = await fetch("/api/attack", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.token}`,
      },
      body: JSON.stringify(attackBody(session.sessionId, input.prompt)),
      signal,
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || errJson.error || `HTTP ${res.status}`);
    }
    const data: BackendAttackResponse = await res.json();
    const events = adaptLiveResponse(data);
    for (const event of events) {
      await delay(100, signal);
      onEvent(event);
    }
  } catch (err) {
    throw new Error(
      `Live transport (step 5) connection error: ${
        err instanceof Error ? err.message : String(err)
      }. Ensure backend is running at http://localhost:8000, or press M outside the text box to return to mock mode.`,
    );
  }
}

export function connectRoomWebSocket(onMessage?: (msg: any) => void) {
  if (typeof window === "undefined") return () => {};
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  let ws: WebSocket | null = null;
  let active = true;

  function connect() {
    if (!active) return;
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch {}
      };
      ws.onclose = () => {
        if (active) setTimeout(connect, 3000);
      };
      ws.onerror = () => {
        ws?.close();
      };
    } catch {}
  }
  connect();

  return () => {
    active = false;
    ws?.close();
  };
}

export type IntegrationsStatusResponse = {
  ok?: boolean;
  providers?: Record<string, string>;
  services?: Record<
    string,
    {
      state: string;
      code?: string;
      label?: string;
      latency_ms?: number;
      detail?: string;
      fallback?: string;
    }
  >;
};

export async function fetchIntegrationsStatus(): Promise<IntegrationsStatusResponse> {
  const res = await fetch("/api/integrations/status");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerWajoAudit() {
  const res = await fetch("/api/integrations/wajo/audit");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerX402Settle(amountCents: number, destWallet: string) {
  const res = await fetch("/api/integrations/x402-settle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      amount_cents: amountCents,
      dest_wallet: destWallet,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerApifyOsint(targetWallet: string) {
  const res = await fetch("/api/integrations/osint-enrich", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      wallet: targetWallet,
      alias: "Suspicious_Actor",
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerWantedPoster(payload: {
  poster_id?: string;
  mugshot_data_url?: string;
  webcam_frame_base64?: string;
  judge_name?: string;
  verdict_code?: string;
  rollback_ms?: number;
}) {
  const res = await fetch("/api/integrations/wanted-poster", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(12_000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchFetchAiEscrow() {
  const res = await fetch("/api/fetchai/escrow");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchAtlassianIncidents() {
  const res = await fetch("/api/atlassian/incidents");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
