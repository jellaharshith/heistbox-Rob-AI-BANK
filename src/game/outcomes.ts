import type { Event, Action, Timings } from "../net/contract";
import type { Vault } from "./store";
export type Ledger = {
  actions: Action[];
  verdict?: Extract<Event, { type: "verdict" }>;
  committed: number;
  blocked: number;
  error?: string;
};
export const emptyLedgers = (): Record<Vault, Ledger> => ({
  L: { actions: [], committed: 0, blocked: 0 },
  M: { actions: [], committed: 0, blocked: 0 },
  R: { actions: [], committed: 0, blocked: 0 },
});
export function reduceEvent(ledgers: Record<Vault, Ledger>, event: Event) {
  if (!("vault" in event)) return ledgers;
  const current = { ...ledgers[event.vault] };
  if (event.type === "agent_proposal") current.actions = event.actions;
  if (event.type === "verdict") current.verdict = event;
  if (event.type === "committed") {
    current.committed = event.amountCommitted;
    current.blocked = event.amountBlocked;
  }
  if (event.type === "error") current.error = event.message;
  return { ...ledgers, [event.vault]: current };
}
export function refundStatus(ledger: Ledger) {
  const ids = ledger.actions
    .filter((a) => a.kind === "refund")
    .map((a) => a.id);
  const result = ledger.verdict?.results.filter((r) =>
    ids.includes(r.actionId),
  );
  return !result?.length
    ? "PENDING"
    : result.every((r) => r.allowed)
      ? "APPROVED"
      : "FROZEN";
}
export const pairTimings = (ledger: Ledger): Timings | undefined =>
  ledger.verdict?.timings;
export const dollars = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
