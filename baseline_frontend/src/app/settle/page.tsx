"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, ArrowRight, Bot, Lock, PhoneCall, ShieldAlert, Sparkles } from "lucide-react";
import Link from "next/link";
import { SettleWithPasskey } from "@/components/SettleWithPasskey";
import { fetchSettlement, type SettleContext } from "@/lib/api";
import { usd } from "@/lib/format";

// Opened from the Wajo.ai call: /settle?settlement=<settlement_hash>. Everything shown and signed comes from
// the kernel's settlement record, so editing the URL cannot change the amount or recipient.
type Loaded = { ctx: SettleContext; state: string } | { error: string } | null;

function SettleContent() {
  const settlementHash = (useSearchParams().get("settlement") ?? "").trim();
  const [loaded, setLoaded] = useState<Loaded>(null);

  useEffect(() => {
    if (!/^0x[0-9a-fA-F]{64}$/.test(settlementHash)) {
      setLoaded({ error: "This link has no valid settlement hash." });
      return;
    }
    fetchSettlement(settlementHash).then((r) => setLoaded(r.ctx ? { ctx: r.ctx, state: r.state } : { error: `Kernel did not return this settlement (${r.error}).` }));
  }, [settlementHash]);

  return (
    <div className="mx-auto flex min-h-[100dvh] max-w-md flex-col justify-between p-4 font-sans text-white sm:p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-white/10 pb-3 font-mono-tight text-[11px] text-white/60">
          <span className="font-bold uppercase tracking-wider text-emerald-300">Remote Enclave Settle</span>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-white/70">WebAuthn · ES256</span>
        </div>

        <div className="rounded-2xl border border-red-500/40 bg-gradient-to-b from-red-950/60 via-red-900/20 to-black p-4">
          <div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-red-400">
            <PhoneCall className="h-3.5 w-3.5" />
            <span>Wajo.ai voice escalation</span>
          </div>
          <h1 className="font-display text-2xl font-extrabold leading-tight tracking-tight text-white sm:text-3xl">HeistBox CFO approval</h1>
          <p className="mt-1 text-xs text-white/70">Approve the honest half with this device&apos;s passkey (Face ID / Touch ID).</p>
        </div>

        {loaded === null && <div className="text-sm text-white/60">Loading settlement from the kernel…</div>}

        {loaded && "error" in loaded && (
          <div className="flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-950/40 p-3 text-xs text-amber-200">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
            <span>{loaded.error}</span>
          </div>
        )}

        {loaded && "ctx" in loaded && (
          <>
            <div className="space-y-2.5">
              <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-black/60 p-3.5">
                <div className="mt-0.5 shrink-0 rounded-lg bg-red-500/10 p-2 text-red-400">
                  <ShieldAlert className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-red-300">Blocked by the PAIR airlock</div>
                  <div className="text-sm font-semibold leading-snug text-white/90">{usd(loaded.ctx.red_cents)} unauthorized transfer stripped.</div>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-black/60 p-3.5">
                <div className="mt-0.5 shrink-0 rounded-lg bg-emerald-500/10 p-2 text-emerald-400">
                  <Bot className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-300">Held by the Guardian escrow</div>
                  <div className="text-sm font-semibold leading-snug text-white/90">
                    {usd(loaded.ctx.green_cents)} refund to <span className="font-mono-tight">{loaded.ctx.recipient}</span>
                  </div>
                  <div className="mt-0.5 font-mono text-[10px] text-white/50">status {loaded.state}</div>
                </div>
              </div>
            </div>

            <div className="space-y-1.5 rounded-xl border border-white/10 bg-white/[0.03] p-3 font-mono-tight text-xs">
              <div className="text-[10px] text-white/50">SETTLEMENT CHALLENGE (signed by the passkey)</div>
              <div className="break-all rounded border border-white/5 bg-black/40 px-2 py-1 text-[11px] text-cyan-200">{loaded.ctx.settlement_hash}</div>
              <div className="text-[10px] text-white/40">commits to amount, recipient, entitlement {loaded.ctx.entitlement_id} and a one-time nonce</div>
            </div>

            {loaded.state === "PENDING" ? (
              <SettleWithPasskey ctx={loaded.ctx} />
            ) : (
              <div className="rounded-xl border border-white/10 p-3 text-xs text-white/70">This settlement is {loaded.state}; each approval can be used once.</div>
            )}
            <div className="flex items-center justify-center gap-1.5 text-center text-[11px] text-white/50">
              <Lock className="h-3 w-3 text-emerald-400" />
              <span>The server verifies the signature before any payout.</span>
            </div>
          </>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4 text-xs text-white/50">
        <Link href="/" className="flex items-center gap-1 text-white/70 transition-colors hover:text-white">
          <ArrowRight className="h-3.5 w-3.5 rotate-180" />
          <span>Back to Arena</span>
        </Link>
        <div className="flex items-center gap-1.5 text-[10px] text-white/40">
          <Sparkles className="h-3 w-3 text-yellow-400" />
          <span>HeistBox</span>
        </div>
      </div>
    </div>
  );
}

export default function SettlePage() {
  return (
    <main className="min-h-[100dvh] bg-[#07090e]">
      <Suspense fallback={<div className="flex min-h-[100dvh] items-center justify-center font-mono text-sm text-white/60">Loading…</div>}>
        <SettleContent />
      </Suspense>
    </main>
  );
}
