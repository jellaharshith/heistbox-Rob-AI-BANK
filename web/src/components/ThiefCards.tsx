"use client";
import React from "react";
import { motion } from "framer-motion";
import { Dice5, Mic, MicOff, CheckCircle2, AlertOctagon, UserCheck } from "lucide-react";
import { MASKS } from "@/lib/masks";
import { usd } from "@/lib/format";
import type { MaskId } from "@/lib/types";

const TARGET_AGENTS: Record<string, { label: string; agent: string; color: string }> = {
  grandma_cookie: { label: "Target: Teller Tina", agent: "tina", color: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10" },
  ceo_wire: { label: "Target: Manager Marcus", agent: "marcus", color: "text-amber-300 border-amber-500/30 bg-amber-500/10" },
  pizza_slicer: { label: "Target: Auditor Ada", agent: "ada", color: "text-cyan-300 border-cyan-500/30 bg-cyan-500/10" },
  voice_bribe: { label: "Target: Intern Izzy / Guard", agent: "izzy", color: "text-fuchsia-300 border-fuchsia-500/30 bg-fuchsia-500/10" },
};

export function ThiefCards(props: {
  selected: MaskId;
  busy: boolean;
  onPick: (id: MaskId) => void;
  mic: { listening: boolean; interim: string; supported: boolean; toggle: () => void };
  onLoraAttack: () => void;
}) {
  return (
    <section className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
      {MASKS.map((m, i) => {
        const active = props.selected === m.id;
        const targetMeta = TARGET_AGENTS[m.id] || {
          label: "Target: Bank Agent",
          agent: "tina",
          color: "text-yellow-300 border-yellow-500/30 bg-yellow-500/10",
        };

        return (
          <motion.div
            key={m.id}
            role="button"
            tabIndex={0}
            onClick={() => !props.busy && props.onPick(m.id)}
            onKeyDown={(e) => e.key === "Enter" && !props.busy && props.onPick(m.id)}
            whileHover={{ y: -4 }}
            className={`pixel-card group relative flex flex-col justify-between p-4 cursor-pointer overflow-hidden transition-all duration-200 select-none ${
              active
                ? "border-cyan-400 bg-gradient-to-b from-cyan-950/40 via-[#0a0f24] to-[#070a18] shadow-[0_0_25px_rgba(34,243,255,0.25)] ring-1 ring-cyan-400/50"
                : "border-white/12 bg-gradient-to-b from-[#10142b]/80 via-[#0a0e20]/90 to-[#060814] hover:border-white/30 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)]"
            } ${props.busy ? "cursor-wait opacity-80" : ""}`}
          >
            {/* Top Tag Row */}
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <span className="font-mono text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-white/60">
                  MASK {i + 1}
                </span>
                <span
                  className={`font-mono text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${targetMeta.color}`}
                >
                  {targetMeta.label}
                </span>
              </div>

              {/* Avatar + Title Container */}
              <div className="flex items-start gap-3 mb-2.5">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-black/60 border border-white/15 text-3xl shadow-inner group-hover:scale-105 transition-transform">
                  {m.emoji}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-display text-base leading-tight text-white group-hover:text-cyan-200 transition-colors line-clamp-2">
                    {m.title}
                  </h3>
                </div>
              </div>

              {/* Pitch */}
              <p className="text-xs text-white/65 leading-relaxed line-clamp-3 mb-3">
                {m.pitch}
              </p>
            </div>

            {/* Bottom Actions & Stats Strip */}
            <div className="mt-auto pt-2 border-t border-white/8 flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                {/* Legit Anchor Pill */}
                <span className="flex items-center gap-1 font-mono text-[10px] font-bold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-1 rounded-md">
                  <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                  <span>LEGIT {usd(m.entitlement_cents)}</span>
                </span>

                {/* Drain Amount Pill */}
                <span className="flex items-center gap-1 font-mono text-[10px] font-bold text-red-300 bg-red-500/15 border border-red-500/30 px-2 py-1 rounded-md">
                  <AlertOctagon className="h-3 w-3 text-red-400" />
                  <span>
                    ASKS {usd(m.defaults.proposed_amount_cents * m.defaults.slice_count)}
                    {m.defaults.slice_count > 1 ? ` (${m.defaults.slice_count}×)` : ""}
                  </span>
                </span>
              </div>

              {/* Mask 4 Special Actions (Audio Mic & LoRA) */}
              {m.id === "voice_bribe" && (
                <div
                  className="mt-1 flex flex-wrap gap-1.5"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    type="button"
                    disabled={props.busy}
                    onClick={() =>
                      props.mic.supported ? props.mic.toggle() : props.onPick(m.id)
                    }
                    className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1 text-[11px] font-bold transition-all ${
                      props.mic.listening
                        ? "animate-pulse bg-red-600 text-white shadow-[0_0_15px_#ef4444]"
                        : "bg-white/10 text-white hover:bg-white/20 border border-white/15"
                    }`}
                    title={
                      props.mic.supported
                        ? "Speak your bribe — sent as prompt_text"
                        : "Microphone unsupported — type in terminal"
                    }
                  >
                    {props.mic.listening ? (
                      <MicOff className="h-3 w-3" />
                    ) : (
                      <Mic className="h-3 w-3 text-fuchsia-300" />
                    )}
                    <span>{props.mic.listening ? "Stop Mic" : "🎙️ Bribe Mic"}</span>
                  </button>

                  <button
                    type="button"
                    disabled={props.busy}
                    onClick={props.onLoraAttack}
                    className="flex flex-1 items-center justify-center gap-1 rounded-lg bg-indigo-500/20 px-2 py-1 text-[11px] font-bold text-indigo-200 hover:bg-indigo-500/30 border border-indigo-400/30 transition-all"
                    title="Fire one of 250 fine-tuned RTX 4060 adversarial attacks"
                  >
                    <Dice5 className="h-3 w-3" />
                    <span>🎲 LoRA Attack</span>
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        );
      })}
    </section>
  );
}
