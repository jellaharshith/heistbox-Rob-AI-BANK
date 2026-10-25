"use client";

import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Landmark,
  RotateCcw,
  Siren,
  Volume2,
  VolumeX,
  Zap,
  Box,
  Terminal,
  FileSpreadsheet,
  Trophy,
  Camera,
} from "lucide-react";
import type { VaultState } from "@/lib/api";
import { usd, useTween } from "@/lib/format";
import type { DataSource } from "@/lib/types";

export type View = "office" | "arena" | "cfo";

function GoldSparks({ burstKey }: { burstKey: number }) {
  return (
    <AnimatePresence>
      {burstKey > 0 && (
        <motion.div
          key={burstKey}
          className="pointer-events-none absolute inset-0 overflow-hidden"
          initial={{ opacity: 1 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 1.4 }}
        >
          {Array.from({ length: 18 }, (_, i) => {
            const a = (i / 18) * Math.PI * 2;
            const d = 50 + ((i * 37) % 60);
            return (
              <motion.span
                key={i}
                className="absolute left-1/2 top-1/2 text-lg pointer-events-none"
                initial={{ x: 0, y: 0, scale: 0.4 }}
                animate={{
                  x: Math.cos(a) * d * 2.2,
                  y: Math.sin(a) * d,
                  scale: 1,
                  rotate: i * 40,
                }}
                transition={{ duration: 0.9, ease: "easeOut" }}
              >
                {i % 3 === 0 ? "🪙" : "✨"}
              </motion.span>
            );
          })}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function WantedMeter({ stars }: { stars: number }) {
  const hot = stars >= 4;
  return (
    <div className="flex items-center gap-1.5" aria-label={`Wanted level ${stars} of 5`}>
      <span className="text-[10px] font-bold uppercase tracking-widest text-white/50 font-mono">
        WANTED
      </span>
      <div className="flex gap-0.5 text-lg leading-none">
        {Array.from({ length: 5 }, (_, i) => (
          <motion.span
            key={i}
            animate={i < stars ? { scale: [1.3, 1], rotate: [-10, 0] } : { scale: 1 }}
            transition={{ duration: 0.35 }}
            className={i < stars ? (hot ? "cop-flash" : "neon-gold") : "text-white/20"}
          >
            {i < stars ? "★" : "☆"}
          </motion.span>
        ))}
      </div>
    </div>
  );
}

export function TopBar(props: {
  vault: VaultState;
  stars: number;
  r?: number;
  view: View;
  sparkKey: number;
  source: DataSource;
  muted: boolean;
  timeLeft?: number;
  lowQuality?: boolean;
  onToggleQuality?: () => void;
  onSelectView?: (view: View) => void;
  onToggleView?: () => void;
  onOpenLeaderboard?: () => void;
  onReset: () => void;
  onToggleMute: () => void;
  onArmCam?: () => void;
  camLive?: boolean;
}) {
  const saved = useTween(props.vault.total_saved_cents, 800);
  const busted = useTween(props.vault.robbers_busted, 500);

  const handleViewClick = (v: View) => {
    if (props.onSelectView) {
      props.onSelectView(v);
    } else if (props.onToggleView) {
      props.onToggleView();
    }
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#070a14]/95 backdrop-blur-xl">
      {/* Vegas bulb border strip */}
      <div className="bulbs h-1.5 w-full opacity-80" />

      <div className="mx-auto flex max-w-[1700px] flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-2">
        {/* 1. Brand Logo */}
        <div className="flex items-center gap-2">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-fuchsia-600/40 via-purple-900/50 to-indigo-950/80 border border-fuchsia-400/40 shadow-[0_0_15px_rgba(255,43,214,0.3)] shrink-0">
            <span className="text-lg">🎰</span>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-display text-xl sm:text-2xl tracking-wider neon-pink">
                HEISTBOX
              </span>
              <span className="rounded bg-fuchsia-500/20 px-1 py-0.2 text-[8px] font-mono font-bold uppercase text-fuchsia-300 border border-fuchsia-400/30">
                LIVE
              </span>
            </div>
            <div className="text-[9px] font-mono font-bold uppercase tracking-[0.18em] text-white/50">
              Agent-Office 3D × PAIR Airlock
            </div>
          </div>
        </div>

        {/* 2. Center Vegas Marquee Box (Measured 100% Live from Database) */}
        <div className="relative flex flex-1 max-w-xl flex-wrap items-center justify-around gap-x-4 gap-y-1 rounded-xl border border-yellow-400/35 bg-gradient-to-r from-yellow-950/40 via-black/85 to-yellow-950/40 px-4 py-1.5 shadow-[0_0_20px_rgba(255,204,51,0.12)]">
          <GoldSparks burstKey={props.sparkKey} />

          {/* Metric 1: Saved Today */}
          <div className="flex items-center gap-1.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-yellow-400/10 border border-yellow-400/30">
              <Landmark className="h-3.5 w-3.5 text-yellow-300" />
            </div>
            <div className="flex flex-col">
              <span className="text-[8px] font-mono font-bold uppercase tracking-wider text-yellow-200/70">
                Total Saved Today
              </span>
              <span className="font-display text-lg sm:text-xl tabular-nums neon-gold leading-none">
                {usd(Math.round(saved))}
              </span>
            </div>
          </div>

          {/* Metric 2: Robbers Busted */}
          <div className="flex items-center gap-1.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-red-500/10 border border-red-500/30">
              <Siren className="h-3.5 w-3.5 text-red-400" />
            </div>
            <div className="flex flex-col">
              <span className="text-[8px] font-mono font-bold uppercase tracking-wider text-red-200/70">
                Robbers Busted
              </span>
              <span className="font-display text-lg sm:text-xl tabular-nums neon-red leading-none">
                {Math.round(busted)}
              </span>
            </div>
          </div>

          {/* Metric 3: Fastest Catch */}
          <div className="flex items-center gap-1.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-cyan-400/10 border border-cyan-400/30">
              <Zap className="h-3.5 w-3.5 text-cyan-300" />
            </div>
            <div className="flex flex-col">
              <span className="text-[8px] font-mono font-bold uppercase tracking-wider text-cyan-200/70">
                Fastest Catch
              </span>
              <span className="font-display text-lg sm:text-xl tabular-nums neon-cyan leading-none">
                {props.vault.fastest_catch_ms > 0
                  ? `${props.vault.fastest_catch_ms.toFixed(2)}ms`
                  : "--"}
              </span>
            </div>
          </div>
        </div>

        {/* 3. Primary Mode Switcher Tabs */}
        <div className="flex items-center rounded-xl bg-black/70 p-1 border border-white/15 shadow-inner">
          <button
            type="button"
            onClick={() => handleViewClick("office")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              props.view === "office"
                ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.6)] border border-purple-400/50"
                : "text-white/60 hover:text-white hover:bg-white/5"
            }`}
            title="3D Bank Office Simulation (Three.js + Autonomous AI Agents) [Hotkey: 1]"
          >
            <Box className="h-4 w-4" />
            <span>3D Office</span>
          </button>

          <button
            type="button"
            onClick={() => handleViewClick("arena")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              props.view === "arena"
                ? "bg-gradient-to-r from-amber-500 to-yellow-500 text-black shadow-[0_0_15px_rgba(245,158,11,0.6)] border border-yellow-300"
                : "text-white/60 hover:text-white hover:bg-white/5"
            }`}
            title="Heist Terminal Arena & 3-Vault Display [Hotkey: 2]"
          >
            <Terminal className="h-4 w-4" />
            <span>Arena</span>
          </button>

          <button
            type="button"
            onClick={() => handleViewClick("cfo")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              props.view === "cfo"
                ? "bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-[0_0_15px_rgba(6,182,212,0.6)] border border-cyan-400/50"
                : "text-white/60 hover:text-white hover:bg-white/5"
            }`}
            title="Relational CFO Audit & Postgres Dry-Run Log [Hotkey: 3]"
          >
            <FileSpreadsheet className="h-4 w-4" />
            <span>CFO Audit</span>
          </button>

          {props.onOpenLeaderboard && (
            <button
              type="button"
              onClick={props.onOpenLeaderboard}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-yellow-300 hover:text-yellow-200 hover:bg-yellow-500/10 transition-all cursor-pointer"
              title="Hall of Fame Leaderboard & QR Wanted Poster [Hotkey: 4]"
            >
              <Trophy className="h-4 w-4 text-yellow-400" />
              <span>Leaderboard</span>
            </button>
          )}
        </div>

        {/* 4. Controls & HUD (Timer, Wanted Stars, Quality, Reset, Audio, Status) */}
        <div className="flex items-center gap-2">
          {/* 90-Second Round Timer */}
          {props.timeLeft !== undefined && (
            <div className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-black/80 border border-yellow-500/40 shadow-inner">
              <span className="text-[9px] uppercase font-bold text-white/50 font-mono">Timer:</span>
              <span
                className={`font-mono text-sm font-bold tabular-nums ${
                  props.timeLeft < 20 ? "text-red-400 animate-pulse" : "text-yellow-400"
                }`}
              >
                {Math.floor(props.timeLeft / 60)}:{(props.timeLeft % 60).toString().padStart(2, "0")}
              </span>
            </div>
          )}

          {/* Wanted Stars */}
          <WantedMeter stars={props.stars} />

          {/* Optional Webcam Mugshot */}
          {props.onArmCam && (
            <button
              type="button"
              onClick={props.onArmCam}
              title="Opt-in Webcam Mugshot"
              className={`p-1.5 rounded-lg border text-xs font-semibold transition cursor-pointer ${
                props.camLive
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                  : "bg-white/5 text-white/70 border-white/10 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Camera className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Quality Toggle (60fps vs High) */}
          {props.onToggleQuality && (
            <button
              type="button"
              onClick={props.onToggleQuality}
              title="Toggle Graphic Quality"
              className={`px-2 py-1 rounded-lg border text-[10px] font-mono font-bold transition cursor-pointer ${
                props.lowQuality
                  ? "bg-amber-500/20 text-amber-300 border-amber-400"
                  : "bg-white/5 text-white/70 border-white/10 hover:bg-white/10"
              }`}
            >
              {props.lowQuality ? "⚡ 60fps" : "✨ High"}
            </button>
          )}

          {/* Reset Vault Button */}
          <button
            type="button"
            onClick={props.onReset}
            className="flex items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs font-bold text-red-300 hover:bg-red-500/20 transition cursor-pointer"
            title="Reset Game Round (Hotkey: R)"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset</span>
          </button>

          {/* Audio Mute/Unmute */}
          <button
            type="button"
            onClick={props.onToggleMute}
            className="rounded-lg border border-white/10 bg-white/5 p-1.5 text-white/70 hover:bg-white/10 hover:text-white transition cursor-pointer"
            title={props.muted ? "Unmute Audio (Hotkey: M)" : "Mute Audio (Hotkey: M)"}
          >
            {props.muted ? (
              <VolumeX className="h-3.5 w-3.5 text-red-400" />
            ) : (
              <Volume2 className="h-3.5 w-3.5 text-emerald-400" />
            )}
          </button>

          {/* Kernel Live Status Badge */}
          <span
            className={`flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider border shrink-0 ${
              props.source === "kernel"
                ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]"
                : "bg-amber-500/15 text-amber-300 border-amber-500/30"
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span>{props.source === "kernel" ? "KERNEL LIVE (:8000)" : "LOCAL TWIN"}</span>
          </span>
        </div>
      </div>
    </header>
  );
}
