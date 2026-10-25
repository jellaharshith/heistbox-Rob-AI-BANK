"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Landmark, RotateCcw, Siren, Volume2, VolumeX, Zap } from "lucide-react";
import type { VaultState } from "@/lib/api";
import { usd, useTween } from "@/lib/format";
import type { DataSource } from "@/lib/types";

export type View = "arena" | "cfo";

function GoldSparks({ burstKey }: { burstKey: number }) {
  return <AnimatePresence>{burstKey > 0 && <motion.div key={burstKey} className="pointer-events-none absolute inset-0" initial={{ opacity: 1 }} animate={{ opacity: 0 }} transition={{ duration: 1.4 }}>{Array.from({ length: 18 }, (_, i) => { const a = (i / 18) * Math.PI * 2; const d = 50 + ((i * 37) % 60); return <motion.span key={i} className="absolute left-1/2 top-1/2 text-lg" initial={{ x: 0, y: 0, scale: 0.4 }} animate={{ x: Math.cos(a) * d * 2.2, y: Math.sin(a) * d, scale: 1, rotate: i * 40 }} transition={{ duration: 0.9, ease: "easeOut" }}>{i % 3 === 0 ? "🪙" : "✨"}</motion.span>; })}</motion.div>}</AnimatePresence>;
}

export function WantedMeter({ stars }: { stars: number }) {
  const hot = stars >= 4;
  return <div className="flex items-center gap-2" aria-label={`Wanted level ${stars} of 5`}><span className="text-[10px] font-bold uppercase tracking-widest text-white/50">Wanted</span><div className="flex gap-0.5 text-2xl leading-none">{Array.from({ length: 5 }, (_, i) => <motion.span key={i} animate={i < stars ? { scale: [1.6, 1], rotate: [-20, 0] } : { scale: 1 }} transition={{ duration: 0.35 }} className={i < stars ? (hot ? "cop-flash" : "neon-gold") : "text-white/20"}>{i < stars ? "★" : "☆"}</motion.span>)}</div></div>;
}

export function TopBar(props: {
  vault: VaultState; stars: number; r: number; sparkKey: number;
  source: DataSource; muted: boolean;
  onReset: () => void; onToggleMute: () => void;
}) {
  const saved = useTween(props.vault.total_saved_cents, 1100);
  const busted = useTween(props.vault.robbers_busted, 600);
  return (
    <header className="heist-topbar sticky top-0 z-40 border-b border-white/10 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3">
        <div className="heist-scoreboard relative flex flex-1 flex-wrap items-center justify-center gap-x-6 gap-y-1 rounded-xl border border-white/10 px-4 py-2">
          <GoldSparks burstKey={props.sparkKey} />
          <div className="flex items-center gap-2"><Landmark className="h-5 w-5 text-yellow-300" /><span className="text-[11px] font-bold uppercase tracking-wider text-yellow-200/70">Total vault money saved today</span><span className="font-display text-2xl tabular-nums neon-gold md:text-3xl">{usd(Math.round(saved))}</span></div>
          <div className="flex items-center gap-2"><Siren className="h-5 w-5 text-red-400" /><span className="text-[11px] font-bold uppercase tracking-wider text-white/60">Robbers busted</span><span className="font-display text-2xl tabular-nums neon-red">{Math.round(busted)}</span></div>
          <div className="flex items-center gap-2"><Zap className="h-5 w-5 text-cyan-300" /><span className="text-[11px] font-bold uppercase tracking-wider text-white/60">Fastest catch</span><span className="font-display text-2xl tabular-nums neon-cyan">{props.vault.fastest_catch_ms > 0 ? `${props.vault.fastest_catch_ms.toFixed(2)}ms` : "—"}</span></div>
        </div>
        <div className="heist-controls flex max-w-full min-w-0 flex-wrap items-center gap-3">
          <div className="flex flex-col items-end"><WantedMeter stars={props.stars} /><span className="font-mono-tight text-[10px] text-white/50">conformal martingale R<sub>t</sub> = {props.r.toLocaleString("en-US", { maximumFractionDigits: 1 })}</span></div>
          <button onClick={props.onReset} className="flex items-center gap-1 rounded-lg border border-white/20 bg-white/5 px-3 py-2 text-sm font-bold hover:bg-white/10" title="1-Click Reset Vault"><RotateCcw className="h-4 w-4" /> Reset Vault</button>
          <button onClick={props.onToggleMute} className="rounded-lg border border-white/10 p-2 text-white/60 hover:text-white" title={props.muted ? "Unmute" : "Mute"}>{props.muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}</button>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${props.source === "kernel" ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`} title={props.source === "kernel" ? "Live data from :8000" : "Kernel unreachable — deterministic local twin"}>● {props.source === "kernel" ? "kernel live" : "local twin"}</span>
        </div>
      </div>
    </header>
  );
}
