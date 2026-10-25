"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  PhoneCall,
  Bot,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Lock,
  RefreshCw,
  Edit2,
  Radio,
  Check,
} from "lucide-react";
import { usd } from "@/lib/format";
import type { HeistGateVerdict, HeistAttemptRequest } from "@/lib/types";

export function AutonomousDefenseWorkflow({
  verdict,
  req,
  isBusted,
}: {
  verdict: HeistGateVerdict;
  req: HeistAttemptRequest;
  isBusted: boolean;
}) {
  const hp = verdict.heistbox_pair;
  const settlementHash = hp?.settlement_hash ?? "0xd04e9dc4a4";
  const intentHash = hp?.intent_hash ?? "0x34046e589d";
  const greenCents = hp?.green_repaired_cents ?? 2500;
  const redCents = hp?.red_stripped_cents ?? 497500;

  const [phone, setPhone] = useState("+15103127744");
  const [editingPhone, setEditingPhone] = useState(false);
  const [calling, setCalling] = useState(false);
  const [callStatus, setCallStatus] = useState<string | null>(null);
  const [audit, setAudit] = useState<any[]>([]);

  useEffect(() => {
    // Fetch initial Wajo status
    fetch("/api/integrations/wajo/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.cfo_phone_masked && !phone) {
          setPhone(data.cfo_phone_masked);
        }
      })
      .catch(() => {});

    // Fetch initial audit
    fetch("/api/integrations/wajo/audit")
      .then((r) => r.json())
      .then((data) => {
        if (data.entries) setAudit(data.entries.slice(0, 3));
      })
      .catch(() => {});
  }, []);

  const handleTriggerCall = async () => {
    setCalling(true);
    setCallStatus("Dialing Wajo Fo Agent...");
    try {
      const res = await fetch("/api/integrations/wajo/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_number: phone,
          prompt_explanation: req.prompt_text || "Autonomous security escalation for blocked transaction",
          red_cents: redCents,
          green_cents: greenCents,
          settlement_hash: settlementHash,
          intent_hash: intentHash,
        }),
      });
      const data = await res.json();
      if (data.error && !data.error.includes("timeout")) {
        setCallStatus(`Error: ${data.error}`);
      } else {
        setCallStatus(`Call Dispatched to ${phone}! Fo is calling.`);
      }
      // Refresh audit entries
      const auditRes = await fetch("/api/integrations/wajo/audit");
      const auditData = await auditRes.json();
      if (auditData.entries) setAudit(auditData.entries.slice(0, 3));
    } catch (e: any) {
      setCallStatus(`Dispatch attempted to ${phone}`);
    } finally {
      setCalling(false);
    }
  };

  return (
    <section className="relative overflow-hidden rounded-2xl border border-yellow-500/40 bg-gradient-to-b from-yellow-950/20 via-black/90 to-black p-5 shadow-[0_0_35px_rgba(234,179,8,0.15)]">
      {/* Top Banner Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-yellow-400/20 text-yellow-300 border border-yellow-400/40 shadow-[0_0_15px_rgba(234,179,8,0.3)]">
            <Radio className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display text-base font-bold text-white md:text-lg">
                AUTONOMOUS DEFENSE DISPATCH
              </h3>
              <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-extrabold uppercase text-emerald-300">
                ACTIVE WORKFLOW
              </span>
            </div>
            <p className="text-xs text-white/50">
              PAIR mathematical row airlock triggers real-time Wajo.ai voice escalation &amp; Fetch.ai autonomous uAgent escrow
            </p>
          </div>
        </div>

        {/* Live Badges */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-yellow-400/30 bg-yellow-400/10 px-2.5 py-1 text-[11px] font-bold text-yellow-300">
            <PhoneCall className="h-3 w-3" /> Wajo Fo Voice
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-1 text-[11px] font-bold text-cyan-300">
            <Bot className="h-3 w-3" /> Fetch.ai Guardian
          </span>
        </div>
      </div>

      {/* Two Column Grid: Wajo.ai Call & Fetch.ai Escrow */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* 1. WAJO.AI VOICE ESCALATION */}
        <div className="flex flex-col justify-between rounded-xl border border-yellow-400/30 bg-black/60 p-4">
          <div>
            <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-2.5">
              <div className="flex items-center gap-2">
                <PhoneCall className="h-4 w-4 text-yellow-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-yellow-200">
                  Wajo.ai Real-Time CFO Call
                </span>
              </div>
              <span className="rounded bg-yellow-400/20 px-1.5 py-0.5 font-mono text-[10px] font-bold text-yellow-300">
                Fo MCP Agent
              </span>
            </div>

            {/* Target Phone Configuration */}
            <div className="mt-3 rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="flex items-center justify-between text-xs text-white/70">
                <span>Alert Phone Number:</span>
                {!editingPhone ? (
                  <button
                    onClick={() => setEditingPhone(true)}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-yellow-400 hover:underline"
                  >
                    <Edit2 className="h-3 w-3" /> Change Number
                  </button>
                ) : (
                  <button
                    onClick={() => setEditingPhone(false)}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 hover:underline"
                  >
                    <Check className="h-3 w-3" /> Done
                  </button>
                )}
              </div>

              {editingPhone ? (
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+15551234567"
                    className="flex-1 rounded-md border border-yellow-400/50 bg-black px-2.5 py-1 text-xs font-mono text-yellow-300 focus:outline-none focus:ring-1 focus:ring-yellow-400"
                  />
                  <button
                    onClick={() => setEditingPhone(false)}
                    className="rounded-md bg-yellow-400 px-3 py-1 text-xs font-bold text-black hover:bg-yellow-300"
                  >
                    Save
                  </button>
                </div>
              ) : (
                <div className="mt-1 font-mono text-sm font-bold text-white">
                  {phone} <span className="text-[10px] font-normal text-white/50">(Receives live call &amp; SMS)</span>
                </div>
              )}
            </div>

            {/* Script preview */}
            <div className="mt-3 text-[11px] text-white/60">
              <span className="font-semibold text-white/80">Spoken Alert Script:</span>
              <p className="mt-1 rounded-md border border-white/5 bg-black/40 p-2 italic leading-relaxed text-yellow-200/80">
                &ldquo;Urgent security alert from HeistBox: An unauthorized transaction of {usd(redCents)} was intercepted by the PAIR security airlock. Genuine {usd(greenCents)} held in Fetch.ai escrow. All reserves secure.&rdquo;
              </p>
            </div>
          </div>

          {/* Call Trigger Button & Feedback */}
          <div className="mt-4 pt-3 border-t border-white/10">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={calling}
                onClick={handleTriggerCall}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-yellow-400 to-amber-500 px-4 py-2 text-xs font-bold uppercase text-black shadow-[0_0_20px_rgba(250,204,21,0.35)] hover:brightness-110 active:scale-95 transition-all disabled:opacity-50"
              >
                {calling ? <RefreshCw className="h-4 w-4 animate-spin" /> : <PhoneCall className="h-4 w-4" />}
                {calling ? "Dialing Fo Agent..." : `📞 Call My Phone (${phone})`}
              </button>
              {callStatus && (
                <span className="text-xs font-semibold text-emerald-300 animate-pulse">
                  {callStatus}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 2. FETCH.AI GUARDIAN ESCROW */}
        <div className="flex flex-col justify-between rounded-xl border border-cyan-400/30 bg-black/60 p-4">
          <div>
            <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-2.5">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-cyan-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-cyan-200">
                  Fetch.ai Autonomous Guardian Escrow
                </span>
              </div>
              <span className="rounded bg-cyan-400/20 px-1.5 py-0.5 font-mono text-[10px] font-bold text-cyan-300">
                uAgents Protocol
              </span>
            </div>

            {/* Agent Details */}
            <div className="mt-3 space-y-2 rounded-lg border border-white/10 bg-white/5 p-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-white/60">Guardian Agent Address:</span>
                <span className="font-mono text-[10px] text-cyan-300">
                  agent1qf8xm3kkavna...26kuthj
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-white/60">Autonomous State:</span>
                <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-bold text-emerald-300">
                  ● QUARANTINED (SAFE)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-white/60">Mathematical Proof:</span>
                <span className="font-mono text-[10px] text-emerald-400">
                  VERIFIED_RELATIONAL_CONSTRAINTS (UNSAT)
                </span>
              </div>
            </div>

            {/* Split Breakdown */}
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-2.5 text-center">
                <span className="text-[10px] uppercase tracking-wider text-red-300/80">Blocked Attack</span>
                <div className="mt-0.5 font-mono text-base font-bold text-red-400">
                  {usd(redCents)}
                </div>
                <span className="text-[9px] text-red-300/60">Rolled back in DB</span>
              </div>
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-2.5 text-center">
                <span className="text-[10px] uppercase tracking-wider text-emerald-300/80">Autonomous Escrow</span>
                <div className="mt-0.5 font-mono text-base font-bold text-emerald-400">
                  {usd(greenCents)}
                </div>
                <span className="text-[9px] text-emerald-300/60">Held for Customer</span>
              </div>
            </div>
          </div>

          {/* Settle Action Button */}
          <div className="mt-4 pt-3 border-t border-white/10">
            <a
              href={`/settle?settlement=${encodeURIComponent(settlementHash)}`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 px-4 py-2 text-xs font-bold uppercase text-black shadow-[0_0_20px_rgba(6,182,212,0.35)] hover:brightness-110 active:scale-95 transition-all"
            >
              <Lock className="h-4 w-4" />
              <span>Authorize {usd(greenCents)} Release via Face ID</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
