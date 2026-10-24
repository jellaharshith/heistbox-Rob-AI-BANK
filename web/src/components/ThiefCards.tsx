"use client";
import { motion } from "framer-motion";
import { Dice5, Mic, MicOff } from "lucide-react";
import { MASKS } from "@/lib/masks";
import { usd } from "@/lib/format";
import type { MaskId } from "@/lib/types";

export function ThiefCards(props: {
  selected: MaskId;
  busy: boolean;
  onPick: (id: MaskId) => void;
  mic: { listening: boolean; interim: string; supported: boolean; toggle: () => void };
  onLoraAttack: () => void;
}) {
  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {MASKS.map((m, i) => {
        const active = props.selected === m.id;
        return (
          <motion.div
            key={m.id}
            role="button"
            tabIndex={0}
            onClick={() => !props.busy && props.onPick(m.id)}
            onKeyDown={(e) => e.key === "Enter" && !props.busy && props.onPick(m.id)}
            whileHover={{ y: -4, rotate: i % 2 ? 0.6 : -0.6 }}
            className={`card-glow relative cursor-pointer overflow-hidden rounded-2xl border p-4 transition ${
              active ? "border-fuchsia-400/80 bg-gradient-to-br from-fuchsia-950/60 to-indigo-950/60" : "border-white/10 bg-white/[0.03] hover:border-white/30"
            } ${props.busy ? "cursor-wait opacity-80" : ""}`}
          >
            <div className="absolute right-3 top-3 rounded bg-black/40 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white/50">Mask {i + 1}</div>
            <div className="mb-2 text-5xl drop-shadow-[0_4px_10px_rgba(0,0,0,0.6)]">{m.emoji}</div>
            <div className="font-display text-lg leading-tight text-white">{m.title}</div>
            <p className="mt-1 text-xs text-white/60">{m.pitch}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px]">
              <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 font-bold text-emerald-300">legit {usd(m.entitlement_cents)}</span>
              <span className="rounded bg-red-500/15 px-1.5 py-0.5 font-bold text-red-300">
                asks {usd(m.defaults.proposed_amount_cents * m.defaults.slice_count)}
                {m.defaults.slice_count > 1 ? ` (${m.defaults.slice_count}×)` : ""}
              </span>
            </div>
            {m.id === "voice_bribe" && (
              <div className="mt-3 flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
                <button
                  disabled={props.busy}
                  onClick={() => (props.mic.supported ? props.mic.toggle() : props.onPick(m.id))}
                  className={`flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-bold ${
                    props.mic.listening ? "animate-pulse bg-red-600 text-white" : "bg-white/10 text-white hover:bg-white/20"
                  }`}
                  title={props.mic.supported ? "Speak your bribe — it is sent as prompt_text + voice_transcript" : "This browser has no WebSpeech — edit the prompt in the drawer instead"}
                >
                  {props.mic.listening ? <MicOff className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
                  {props.mic.listening ? "Listening… tap to send" : props.mic.supported ? "Bribe out loud" : "Mic unsupported — type it"}
                </button>
                <button
                  disabled={props.busy}
                  onClick={props.onLoraAttack}
                  className="flex items-center gap-1 rounded-lg bg-indigo-500/20 px-2.5 py-1.5 text-xs font-bold text-indigo-200 hover:bg-indigo-500/30"
                >
                  <Dice5 className="h-3.5 w-3.5" /> Attack with HeistGuard-LoRA
                </button>
                {props.mic.interim && <p className="w-full truncate text-[11px] italic text-white/70">“{props.mic.interim}”</p>}
              </div>
            )}
          </motion.div>
        );
      })}
    </section>
  );
}
