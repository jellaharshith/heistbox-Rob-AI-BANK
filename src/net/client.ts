import script from "./mock/refund-wire.json";
import type { Event } from "./contract";
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
// One request from the director. The fixture itself fans out to three vaults.
export async function attack(
  input: { sessionId: string; prompt: string },
  mock: boolean,
  signal: AbortSignal,
  onEvent: (event: Event) => void,
) {
  if (!input.prompt.trim()) throw new Error("Type an attack first.");
  if (!mock)
    throw new Error(
      "Live transport is scheduled for step 5. Press M outside the text box to return to mock mode.",
    );
  for (const event of mockEvents) {
    await delay(100, signal);
    onEvent(event);
  }
}
