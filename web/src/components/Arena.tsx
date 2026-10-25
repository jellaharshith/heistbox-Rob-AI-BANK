"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Camera, Lock, Megaphone, ShieldAlert, Terminal } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { CamStatus } from "@/lib/media";
import { usd } from "@/lib/format";
import { classifyParser } from "@/lib/provenance";
import type { DataSource, HeistAttemptRequest, HeistGateVerdict, RealDisputeTicket } from "@/lib/types";
import { HeistConsole } from "./HeistConsole";
import { playSlotMachineSound, playVaultSlamSound, speakRoast } from "@/lib/sound";

export { playSlotMachineSound, playVaultSlamSound, speakRoast };

export type Phase = "idle" | "rolling" | "resolved";

/**
 * Cartesia megaphone audio for the current bust (a streaming URL or data: URL), or why there is none.
 * `fallbackText` is spoken with the browser voice only if the audio errors, is blocked, or hasn't started in time.
 */
export type RoastAudio = { src: string | null; note: string; fallbackText?: string };

const ROAST_START_DEADLINE_MS = 1500;

/** Mounted <audio> that plays the Cartesia roast as soon as its first bytes arrive. */
function RoastPlayer({ roast, muted }: { roast: RoastAudio; muted: boolean }) {
  const ref = useRef<HTMLAudioElement>(null);
  const [blocked, setBlocked] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const mutedRef = useRef(muted);
  mutedRef.current = muted;
  useEffect(() => {
    const el = ref.current;
    if (!el || !roast.src) return;
    setBlocked(false);
    setStatus(null);
    const t0 = performance.now();
    let started = false;
    let fellBack = false;
    const fallBack = (why: string) => {
      if (started || fellBack) return;
      fellBack = true;
      setStatus(`${why} — browser voice instead`);
      if (roast.fallbackText && !mutedRef.current) speakRoast(roast.fallbackText);
    };
    const onPlaying = () => {
      started = true;
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      setStatus(`first audio in ${Math.round(performance.now() - t0)}ms`);
    };
    const onError = () => fallBack("Cartesia stream failed");
    el.addEventListener("playing", onPlaying);
    el.addEventListener("error", onError);
    const deadline = window.setTimeout(() => fallBack(`no Cartesia audio after ${ROAST_START_DEADLINE_MS}ms`), ROAST_START_DEADLINE_MS);
    el.currentTime = 0;
    el.play().catch(() => {
      setBlocked(true); // autoplay policy: offer a tap-to-play instead
      fallBack("autoplay blocked");
    });
    return () => {
      window.clearTimeout(deadline);
      el.removeEventListener("playing", onPlaying);
      el.removeEventListener("error", onError);
    };
  }, [roast.src, roast.fallbackText]);
  return (
    <div className="flex items-center justify-center gap-2 rounded-full bg-black/70 px-3 py-1 text-[10px] text-white/80">
      {roast.src && <audio ref={ref} src={roast.src} muted={muted} preload="auto" />}
      <Megaphone className="h-3 w-3 shrink-0 text-yellow-300" />
      <span>
        {roast.note}
        {status && ` · ${status}`}
      </span>
      {roast.src && (
        <button type="button" onClick={() => ref.current && ((ref.current.currentTime = 0), void ref.current.play().then(() => setBlocked(false)))} className="rounded bg-yellow-400 px-1.5 font-bold text-black">
          {blocked ? "▶ tap to play" : "↻ replay"}
        </button>
      )}
    </div>
  );
}

const REEL = ["💰", "7️⃣", "🍒", "💎", "🔔", "🪙"];

function Column(props: { title: string; subtitle: string; tone: "gold" | "ice" | "red"; children: React.ReactNode; shake?: boolean }) {
  const border =
    props.tone === "gold"
      ? "border-yellow-400/40 shadow-[0_0_25px_rgba(255,204,51,0.12)]"
      : props.tone === "ice"
        ? "border-sky-400/40 shadow-[0_0_25px_rgba(56,189,248,0.12)]"
        : "border-emerald-400/40 shadow-[0_0_25px_rgba(16,185,129,0.15)]";
  
  const headerBg =
    props.tone === "gold"
      ? "bg-gradient-to-r from-yellow-950/40 via-black/60 to-yellow-950/20"
      : props.tone === "ice"
        ? "bg-gradient-to-r from-sky-950/40 via-black/60 to-sky-950/20"
        : "bg-gradient-to-r from-emerald-950/40 via-black/60 to-emerald-950/20";

  return (
    <motion.div
      animate={props.shake ? { x: [0, -10, 9, -6, 4, 0], y: [0, 4, -3, 2, 0] } : {}}
      transition={{ duration: 0.45 }}
      className={`glass-panel relative flex min-h-[440px] flex-col overflow-hidden rounded-2xl border ${border}`}
    >
      <div className={`border-b border-white/10 ${headerBg} px-4 py-2.5 flex items-center justify-between`}>
        <div>
          <div className="font-display text-base sm:text-lg leading-tight tracking-wide text-white">{props.title}</div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">{props.subtitle}</div>
        </div>
        <span className={`h-2 w-2 rounded-full ${props.tone === "gold" ? "bg-yellow-400" : props.tone === "ice" ? "bg-sky-400" : "bg-emerald-400"} animate-pulse`} />
      </div>
      <div className="relative flex flex-1 flex-col">{props.children}</div>
    </motion.div>
  );
}

function SlotReels({ spinning }: { spinning: boolean }) {
  return (
    <div className="mx-auto flex gap-2">
      {[0, 1, 2].map((r) => (
        <div key={r} className="h-16 w-14 overflow-hidden rounded-lg border-2 border-yellow-500/60 bg-gradient-to-b from-white to-neutral-300 shadow-inner">
          <div className={spinning ? "reel-strip" : ""} style={spinning ? { animationDuration: `${0.12 + r * 0.03}s` } : undefined}>
            {[...REEL, ...REEL].map((s, i) => (
              <div key={i} className="flex h-16 items-center justify-center text-3xl">
                {spinning ? s : "💰"}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function FlyingCoins() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {Array.from({ length: 26 }, (_, i) => {
        const x = ((i * 53) % 100) - 50;
        return (
          <motion.span
            key={i}
            className="absolute left-1/2 top-1/2 text-2xl"
            initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }}
            animate={{ x: x * 6, y: -260 - ((i * 29) % 160), opacity: 0, rotate: 360 + i * 30 }}
            transition={{ duration: 1.3 + (i % 5) * 0.15, ease: "easeOut", delay: (i % 7) * 0.04 }}
          >
            {i % 4 === 0 ? "💵" : "🪙"}
          </motion.span>
        );
      })}
    </div>
  );
}

function LeftJudge({ phase, progress, v, source }: { phase: Phase; progress: number; v: HeistGateVerdict; source: DataSource }) {
  const robbed = v.left_vault_llm_judge.robbed_cents;
  const resolved = phase === "resolved";
  const toolCall = v.extracted_tool_call ?? v.heistbox_pair.extracted_tool_call;
  const parser = classifyParser(source === "kernel" ? toolCall?.parser_backend : "local-deterministic-twin");
  const reasoning = v.left_vault_llm_judge.judge_reasoning;
  const callJson = toolCall ? JSON.stringify({ tool_name: toolCall.tool_name, arguments: toolCall.arguments }, null, 2) : null;

  return (
    <Column title="① Standard LLM-as-Judge" subtitle="“Looks polite. Approve.”" tone="gold" shake={resolved && robbed > 0}>
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-4 text-center">
        <SlotReels spinning={phase === "rolling"} />
        {phase === "idle" && <p className="text-sm text-white/50">Waiting for a thief…</p>}
        {phase === "rolling" && (
          <div className="font-display text-xl neon-gold">
            💸 WIRING {usd(robbed || v.heistbox_pair.green_repaired_cents)} TO JUDGE…
            <div className="mt-1 text-4xl tabular-nums">{Math.min(progress, v.left_vault_llm_judge.safe_confidence_pct)}% SAFE</div>
          </div>
        )}
        {resolved && (
          <motion.div
            initial={{ scale: 0.4, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 260, damping: 14 }}
            className="w-full space-y-2"
          >
            <div className="text-sm font-bold uppercase tracking-wider text-yellow-200/80">✅ APPROVED — {v.left_vault_llm_judge.safe_confidence_pct}% SAFE</div>
            {v.verdict_code === "BUSTED_DESTRUCTIVE_SQL_SABOTAGE" || robbed > 0 ? (
              <>
                <div className="font-display text-5xl neon-red">-{usd(robbed)}</div>
                <div className="mt-0.5 text-sm font-bold text-red-300">
                  {v.left_vault_llm_judge.status === "DATABASE_DESTROYED"
                    ? "CATASTROPHIC SQL WIPEOUT: 100,000 RECORDS DESTROYED"
                    : `🏴‍☠️ VAULT ${v.left_vault_llm_judge.status}`}
                </div>
              </>
            ) : (
              <div className="font-display text-4xl neon-green">paid {usd(v.heistbox_pair.green_repaired_cents)}</div>
            )}

            <div className="mt-2 rounded-lg border border-yellow-500/25 bg-black/55 p-2.5 text-left font-mono-tight text-[11px]">
              <div className="flex flex-wrap items-center justify-between gap-1 text-[10px] uppercase tracking-wider text-yellow-300/80">
                <span className="flex items-center gap-1">
                  <Terminal className="h-3 w-3" /> extracted tool call
                </span>
                <span className={`rounded px-1.5 py-0.5 text-[9px] normal-case ${parser.kind === "llm" ? "bg-emerald-500/20 text-emerald-200" : "bg-yellow-400/15 text-yellow-200"}`}>{parser.badge}</span>
              </div>
              {callJson ? (
                <pre className="mt-1 max-h-36 overflow-auto whitespace-pre-wrap break-all rounded bg-black/50 p-1.5 text-[10px] leading-snug text-cyan-100">{callJson}</pre>
              ) : (
                <div className="mt-1 text-white/45">not returned by the kernel</div>
              )}
              {source === "kernel" && v.is_real_llm_parse === true && parser.kind === "rule" && (
                <div className="mt-1 text-[9px] text-amber-300/80">kernel sets is_real_llm_parse=true, but this backend is a regex extractor (kernel/live_agent_parser.py)</div>
              )}
              {v.uv_hidden_spans && v.uv_hidden_spans.length > 0 && (
                <div className="mt-1.5 rounded bg-purple-900/40 px-2 py-1 text-[10px] text-purple-200">
                  <span className="font-bold text-purple-300">🔦 UV Flashlight:</span> {v.uv_hidden_spans.length} hidden spans reported
                </div>
              )}
              <div className="mt-1.5 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-yellow-300/80">
                judge reasoning
                {reasoning && parser.kind !== "llm" && <span className="rounded bg-white/10 px-1 text-[9px] normal-case text-white/70">kernel template</span>}
              </div>
              {reasoning ? (
                <p className="mt-0.5 line-clamp-3 font-sans text-[11px] italic text-white/65">“{reasoning}”</p>
              ) : (
                <p className="mt-0.5 font-sans text-[11px] text-white/40">not returned</p>
              )}
            </div>
          </motion.div>
        )}
      </div>
      {resolved && robbed > 0 && <FlyingCoins />}
    </Column>
  );
}

function CenterFirewall({ phase, frozen, v, req }: { phase: Phase; frozen: boolean; v: HeistGateVerdict; req: HeistAttemptRequest }) {
  const rules = [
    `amount > $100.00 → ${req.proposed_amount_cents * req.slice_count > 10000 ? "HIT" : "ok"}`,
    `promo_batch present → ${req.proposed_promo_batch ? "HIT" : "ok"}`,
    `velocity > 1/sec → ${req.slice_count > 1 ? "HIT" : "ok"}`,
    "new dest_wallet → HIT",
  ];
  return (
    <Column title="② Rigid Firewall Baseline" subtitle="“When in doubt, freeze everything.”" tone="ice">
      <div className="flex flex-1 flex-col justify-center gap-2 p-4">
        <ul className="space-y-1 font-mono-tight text-xs">
          {rules.map((r, i) => (
            <motion.li
              key={r}
              initial={false}
              animate={{ opacity: phase === "idle" ? 0.45 : 1 }}
              transition={{ delay: phase === "rolling" ? i * 0.12 : 0 }}
              className={r.endsWith("HIT") && phase !== "idle" ? "text-sky-200" : "text-white/50"}
            >
              ▸ {r}
            </motion.li>
          ))}
        </ul>
      </div>
      <AnimatePresence>
        {frozen && (
          <motion.div
            initial={{ opacity: 0, scale: 1.2 }}
            animate={{ opacity: [0, 1, 0.7, 1], scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="ice absolute inset-0 flex flex-col items-center justify-center gap-2 p-4 text-center"
          >
            <div className="text-6xl">🧊</div>
            <div className="font-display text-4xl text-sky-100 drop-shadow-[0_0_12px_#7dd3fc]">BANK {v.center_firewall.status}</div>
            <div className="rounded-lg bg-black/50 px-3 py-2 text-sm">
              <div className="font-bold text-emerald-300">{usd(v.center_firewall.robbed_cents)} stolen ✓</div>
              {v.center_firewall.honest_refund_frozen && (
                <div className="font-bold text-sky-200">…but the honest {usd(v.heistbox_pair.green_repaired_cents)} customer is FROZEN &amp; unpaid 😢</div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Column>
  );
}

const PAIR_TRACE = ["parse intent → green / red", "lookup entitlement(work_item)", "SELECT … FOR UPDATE (row lock)", "CTE split: LEAST(ask, entitlement)", "HeistGuard-LoRA taint scan", "conformal martingale R_t"];

function RightHeistBox(props: {
  phase: Phase;
  progress: number;
  slam: boolean;
  v: HeistGateVerdict;
  req: HeistAttemptRequest;
  source: DataSource;
  cam: { attach: (el: HTMLVideoElement | null) => void; start: () => void; status: CamStatus };
  mugshot: string | null;
  posterHref: string | null;
  roast: RoastAudio | null;
  muted: boolean;
}) {
  const { phase, progress, v, req } = props;
  const resolved = phase === "resolved";
  const busted = resolved && props.slam && v.busted;
  const hp = v.heistbox_pair;
  const slicesShown = phase === "idle" ? 0 : resolved ? req.slice_count : Math.ceil((progress / 99) * req.slice_count);

  return (
    <Column title="③ HeistBox × PAIR + HeistGuard-LoRA" subtitle="Split the honest half from the heist — in the database." tone="red" shake={busted}>
      {/* Camera / mugshot backdrop */}
      <div className="relative m-3 aspect-video overflow-hidden rounded-xl border border-white/10 bg-black">
        <video
          ref={props.cam.attach}
          autoPlay
          muted
          playsInline
          className={`h-full w-full scale-x-[-1] object-cover ${props.cam.status === "live" && !(busted && props.mugshot) ? "" : "hidden"}`}
        />
        {busted && props.mugshot && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={props.mugshot} alt="Frozen B&W mugshot" className="h-full w-full scale-x-[-1] object-cover contrast-150 grayscale" />
        )}
        {props.cam.status !== "live" && !(busted && props.mugshot) && (
          <button onClick={props.cam.start} className="flex h-full w-full flex-col items-center justify-center gap-1 text-white/60 hover:text-white">
            <Camera className="h-8 w-8" />
            <span className="text-xs font-bold">{props.cam.status === "denied" ? "Camera blocked — allow it in the address bar, or the poster has no photo" : "Arm the mugshot cam"}</span>
          </button>
        )}
        <div className="scanlines absolute inset-0" />
      </div>

      {/* Trace / slices */}
      <div className="flex-1 px-4 pb-4">
        {req.slice_count > 1 ? (
          <ul className="grid grid-cols-2 gap-1 font-mono-tight text-[11px]">
            {Array.from({ length: req.slice_count }, (_, i) => (
              <motion.li key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: i < slicesShown ? 1 : 0.15, x: 0 }} className={i === 0 ? "text-emerald-300" : "text-red-300"}>
                #{i + 1} {usd(req.proposed_amount_cents)} {i === 0 ? "✓ entitled" : "⛔ row-locked"}
              </motion.li>
            ))}
          </ul>
        ) : (
          <ul className="space-y-1 font-mono-tight text-[11px]">
            {PAIR_TRACE.map((t, i) => (
              <li key={t} className={phase !== "idle" && progress >= (i + 1) * 15 ? "text-red-200" : "text-white/30"}>
                {phase !== "idle" && progress >= (i + 1) * 15 ? "■" : "□"} {t}
              </li>
            ))}
          </ul>
        )}
        {resolved && !v.busted && (
          <div className="mt-3 rounded-lg bg-emerald-500/15 p-3 text-center font-display text-2xl neon-green">✅ CLEARED — paid {usd(hp.green_repaired_cents)}</div>
        )}
      </div>

      {/* Steel vault door */}
      <AnimatePresence>
        {busted && (
          <motion.div
            key="door"
            className="absolute inset-0 z-10"
            style={{ perspective: 900 }}
            initial={{ opacity: 1 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="steel rivets absolute inset-0 flex flex-col items-center justify-center"
              style={{ transformOrigin: "top center" }}
              initial={{ rotateX: 92, y: -40 }}
              animate={{ rotateX: [92, 0, 8, 0], y: [-40, 0, -4, 0] }}
              transition={{ duration: 0.55, times: [0, 0.6, 0.8, 1], ease: "easeIn" }}
            >
              <div className="flex h-32 w-32 items-center justify-center overflow-hidden rounded-full border-[10px] border-neutral-700 bg-neutral-500 shadow-[inset_0_0_20px_#000]">
                {props.mugshot ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={props.mugshot} alt="Frozen B&W mugshot" className="h-full w-full scale-x-[-1] object-cover contrast-150 grayscale" />
                ) : (
                  <Lock className="h-10 w-10 text-neutral-900" />
                )}
              </div>
              <div className="mt-2 font-mono-tight text-[11px] font-bold text-neutral-900">
                {hp.unauthorized_rows_rolled_back}/{hp.touched_rows_total} rows rolled back · R<sub>t</sub>={hp.conformal_martingale_r.toLocaleString()}
              </div>
            </motion.div>

            {[22, 50, 78].map((top, i) => (
              <motion.div
                key={top}
                className="absolute left-0 z-10 h-[3px] w-full bg-red-500 shadow-[0_0_12px_4px_#ff2945]"
                style={{ top: `${top}%`, rotate: i === 1 ? -7 : 5 }}
                initial={{ scaleX: 0, originX: i % 2 ? 1 : 0 }}
                animate={{ scaleX: 1 }}
                transition={{ delay: 0.35 + i * 0.08, duration: 0.22 }}
              />
            ))}

            <motion.div
              className="absolute inset-x-3 top-1/2 z-20 -translate-y-1/2"
              initial={{ scale: 3.2, rotate: -24, opacity: 0 }}
              animate={{ scale: 1, rotate: -9, opacity: 1 }}
              transition={{ delay: 0.5, type: "spring", stiffness: 420, damping: 16 }}
            >
              <div className="stamp bg-black/70 px-3 py-2 text-center text-red-500 shadow-[0_0_40px_#ff294588]">
                <div className="text-4xl leading-none md:text-5xl">
                  {v.verdict_code === "BUSTED_DESTRUCTIVE_SQL_SABOTAGE"
                    ? "BUSTED IN 0.4ms: SQL SABOTAGE BLOCKED!"
                    : `🚨 BUSTED IN ${v.clocks.postgres_pair_ms}ms!`}
                </div>
                <div className="mt-1 text-sm leading-tight text-red-300 md:text-base">
                  {v.verdict_code === "BUSTED_DESTRUCTIVE_SQL_SABOTAGE"
                    ? "100% OF DATABASE PRESERVED · ZERO RECORDS DROPPED"
                    : `${usd(hp.red_stripped_cents)} HEIST ROLLED BACK IN THE DB TRANSACTION`}
                </div>
                <div className="mt-1 font-sans text-[9px] normal-case leading-tight tracking-normal text-red-200/70">
                  {props.source === "kernel"
                    ? "clocks.postgres_pair_ms as reported by the kernel (SQLite gate; db_gate.py clamps it to 0.4–1.9ms)"
                    : "local twin estimate — kernel unreachable, nothing was measured"}
                </div>
              </div>
            </motion.div>

            {hp.settlement_hash && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 }}
              className="absolute inset-x-3 bottom-16 z-30 flex justify-center"
            >
              <Link
                href={`/settle?settlement=${encodeURIComponent(hp.settlement_hash)}`}
                target="_blank"
                className="flex animate-pulse items-center gap-1.5 rounded-full border border-yellow-400/60 bg-black/90 px-3.5 py-1.5 text-xs font-bold text-yellow-300 shadow-[0_0_20px_rgba(250,204,21,0.4)] hover:bg-yellow-400/20 transition-all"
              >
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-yellow-400 opacity-75"></span>
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-yellow-500"></span>
                </span>
                <span>📞 Wajo.ai alert: {usd(hp.red_stripped_cents)} blocked | 🤖 Fetch.ai holds {usd(hp.green_repaired_cents)}</span>
                <span className="ml-1 rounded bg-yellow-400 px-1.5 py-0.5 text-[10px] font-extrabold uppercase text-black">
                  Settle ↗
                </span>
              </Link>
            </motion.div>
            )}

            {props.posterHref && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.1 }} className="absolute inset-x-3 bottom-3 z-30 flex flex-col items-center gap-1.5">
                {props.roast && <RoastPlayer roast={props.roast} muted={props.muted} />}
                <Link
                  href={props.posterHref}
                  target="_blank"
                  className="flex items-center gap-1 rounded-full bg-yellow-400 px-4 py-1.5 text-sm font-bold text-black shadow-[0_0_20px_#facc15]"
                >
                  <ShieldAlert className="h-4 w-4" /> Print my WANTED poster
                </Link>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </Column>
  );
}

export function Arena(props: {
  phase: Phase;
  progress: number;
  slam: boolean;
  firewallFrozen: boolean;
  verdict: HeistGateVerdict;
  req: HeistAttemptRequest;
  source: DataSource;
  cam: { attach: (el: HTMLVideoElement | null) => void; start: () => void; status: CamStatus };
  mugshot: string | null;
  posterHref: string | null;
  roast: RoastAudio | null;
  muted: boolean;
  console: {
    busy: boolean;
    onChange: (r: HeistAttemptRequest) => void;
    onRun: () => void;
    onTicket: (t: RealDisputeTicket | null) => void;
    mic?: { listening: boolean; interim: string; supported: boolean; toggle: () => void };
    onLoraAttack?: () => void;
  };
}) {
  const isBusted = props.phase === "resolved" && props.slam && props.verdict.busted;
  const settlementHash = props.verdict.heistbox_pair?.settlement_hash ?? null;
  const greenCents = props.verdict.heistbox_pair?.green_repaired_cents ?? 0;
  const redCents = props.verdict.heistbox_pair?.red_stripped_cents ?? 0;

  return (
    <div className="flex flex-col gap-4">
      {isBusted && (
        <motion.div
          initial={{ opacity: 0, y: -10, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-yellow-400/50 bg-gradient-to-r from-yellow-950/70 via-black to-yellow-950/70 px-4 py-3 text-xs sm:text-sm font-bold text-yellow-300 shadow-[0_0_30px_rgba(250,204,21,0.25)]"
        >
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-yellow-400 opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-yellow-500"></span>
            </span>
            <span className="animate-pulse">📞 Wajo.ai alert: {usd(redCents)} blocked | 🤖 Fetch.ai holds {usd(greenCents)}</span>
          </div>
          {settlementHash && (
            <Link
              href={`/settle?settlement=${encodeURIComponent(settlementHash)}`}
              target="_blank"
              className="flex items-center gap-1.5 rounded-full bg-yellow-400 px-3.5 py-1.5 text-xs font-extrabold uppercase text-black hover:bg-yellow-300 shadow-[0_0_15px_rgba(250,204,21,0.5)] transition-all active:scale-95"
            >
              <span>Authorize {usd(greenCents)} Face ID Settle</span>
              <span>↗</span>
            </Link>
          )}
        </motion.div>
      )}
      <HeistConsole req={props.req} {...props.console} />
      <section className="grid gap-4 lg:grid-cols-3">
        <LeftJudge phase={props.phase} progress={props.progress} v={props.verdict} source={props.source} />
        <CenterFirewall phase={props.phase} frozen={props.firewallFrozen} v={props.verdict} req={props.req} />
        <RightHeistBox
          phase={props.phase}
          progress={props.progress}
          slam={props.slam}
          v={props.verdict}
          req={props.req}
          source={props.source}
          cam={props.cam}
          mugshot={props.mugshot}
          posterHref={props.posterHref}
          roast={props.roast}
          muted={props.muted}
        />
      </section>
    </div>
  );
}
