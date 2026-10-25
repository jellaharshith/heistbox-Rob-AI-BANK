"use client";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { Arena, type Phase, type RoastAudio } from "./Arena";
import { ArrowUpRight, X } from "lucide-react";
import { TopBar } from "./TopBar";
import { PosterQr } from "./PosterQr";
import {
  createWantedPoster,
  evaluateHeist,
  getVaultState,
  INITIAL_VAULT,
  instantVerdict,
  resetVault,
  rollbackRoastStreamUrl,
  savePoster,
  settleContextFrom,
  type VaultState,
} from "@/lib/api";
import { martingalePath, rollbackRoastLine, starsFromR, wantedLocally } from "@/lib/fallback";
import { LORA_ATTACKS, requestFor } from "@/lib/masks";
import { useSpeech, useWebcam } from "@/lib/media";
import { posterPath, saveSettleContext } from "@/lib/provenance";
import * as sfx from "@/lib/sound";
import type { DataSource, HeistAttemptRequest, HeistGateVerdict, MaskId, RealDisputeTicket } from "@/lib/types";

const ROLL_MS = 2000;
const SLAM_AFTER_MS = 350;
const FREEZE_AT_MS = 700;
/** Masks carry no enrolled customer wallet, so the green half goes to this labelled placeholder unless a kernel ticket supplies one. */
export const DEMO_RECIPIENT = "0x0000000000000000000000000000000000000104";

export function createEmptyRequest(): HeistAttemptRequest {
  return {
    mask_id: "custom",
    work_item_id: "ticket_104",
    prompt_text: "",
    proposed_promo_batch: null,
    proposed_amount_cents: 0,
    proposed_source_acct: "acct_treasury_main",
    proposed_dest_wallet: "0x8841000000000000000000000000000000000104",
    slice_count: 1,
    voice_transcript: null,
    webcam_frame_base64: null,
  };
}

const newId = (prefix: string) => `${prefix}-${Date.now().toString(36).toUpperCase()}${Math.floor(Math.random() * 1296).toString(36).toUpperCase()}`;

export default function HeistApp() {
  const [req, setReq] = useState<HeistAttemptRequest>(createEmptyRequest);
  const [verdict, setVerdict] = useState<HeistGateVerdict>(() => instantVerdict(createEmptyRequest(), "preview"));
  const [source, setSource] = useState<DataSource>("fallback");
  const [phase, setPhase] = useState<Phase>("idle");
  const [slam, setSlam] = useState(false);
  const [progress, setProgress] = useState(0);
  const [frozen, setFrozen] = useState(false);
  const [vault, setVault] = useState<VaultState>(INITIAL_VAULT);
  const [stars, setStars] = useState(0);
  const [rDisplay, setRDisplay] = useState(1);
  const [sparkKey, setSparkKey] = useState(0);
  const [mugshot, setMugshot] = useState<string | null>(null);
  const [posterHref, setPosterHref] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const enclaveUs = 0;
  const [briefingOpen, setBriefingOpen] = useState(false);
  const briefingRef = useRef<HTMLElement>(null);
  const [recipient, setRecipient] = useState(DEMO_RECIPIENT);
  const [roast, setRoast] = useState<RoastAudio | null>(null);

  const timers = useRef<number[]>([]);
  const verdictRef = useRef(verdict);
  verdictRef.current = verdict;
  const sourceRef = useRef(source);
  sourceRef.current = source;
  const recipientRef = useRef(recipient);
  recipientRef.current = recipient;
  const reqRef = useRef(req);
  reqRef.current = req;
  const camAsked = useRef(false);
  const loraIdx = useRef(0);
  const posterIdRef = useRef<string | null>(null);
  const runSeq = useRef(0);
  const cam = useWebcam();
  const camRef = useRef(cam);
  camRef.current = cam;

  useEffect(() => {
    if (!briefingOpen) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setBriefingOpen(false);
      if (e.key !== "Tab") return;
      const buttons = briefingRef.current?.querySelectorAll<HTMLButtonElement>("button");
      if (!buttons?.length) return;
      const first = buttons[0], last = buttons[buttons.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); previous?.focus(); };
  }, [briefingOpen]);

  const clearTimers = () => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  };
  const later = (ms: number, fn: () => void) => timers.current.push(window.setTimeout(fn, ms));

  useEffect(() => {
    getVaultState().then((s) => {
      if (s.source === "kernel") {
        setVault(s.data);
        setSource("kernel");
      }
    });
    camAsked.current = true;
    void camRef.current.start();
    return clearTimers;
  }, []);

  const run = useCallback((r: HeistAttemptRequest) => {
    clearTimers();
    if (!camAsked.current && camRef.current.status === "off") {
      camAsked.current = true;
      void camRef.current.start();
    }
    if (!r.prompt_text.trim()) {
      return;
    }
    const myRun = ++runSeq.current;
    const requestId = newId("REQ");
    const instant = instantVerdict(r, requestId);
    setReq(r);
    setVerdict(instant);
    setSource("fallback");
    setPhase("rolling");
    setSlam(false);
    setProgress(0);
    setFrozen(false);
    setStars(0);
    setRDisplay(1);
    setMugshot(null);
    setPosterHref(null);
    setRoast(null);
    posterIdRef.current = null;
    sfx.playSlotMachineSound();
    sfx.coinRoll(ROLL_MS);

    // The reveal waits for the kernel's verdict (live LLM proposal + gate), never less than the ROLL_MS animation.
    // Only an unreachable kernel resolves with the local twin, and the UI then shows source "fallback".
    const kernelVerdict = evaluateHeist(r, requestId);
    const minRoll = new Promise<void>((done) => later(ROLL_MS, done));
    void Promise.all([kernelVerdict, minRoll]).then(([res]) => {
      if (runSeq.current !== myRun) return; // a newer heist started
      setSource(res.source);
      setVerdict(res.data);
      verdictRef.current = res.data;
      reveal(res.data);
      later(SLAM_AFTER_MS, () => slamDown(res.data));
    });

    const t0 = performance.now();
    const tick = () => {
      const p = Math.min(99, Math.round(((performance.now() - t0) / ROLL_MS) * 99));
      setProgress(p);
      if (p < 99) later(40, tick);
    };
    tick();

    // Wanted meter climbs with the martingale as each slice lands.
    const steps = Math.max(5, r.slice_count);
    later(0, () => {
      const v = verdictRef.current;
      const path = martingalePath(v.heistbox_pair.conformal_martingale_r, steps);
      path.slice(1).forEach((rv, i) =>
        later(((i + 1) / steps) * (ROLL_MS - 150), () => {
          const cur = verdictRef.current;
          setRDisplay(rv);
          setStars(Math.min(cur.heistbox_pair.wanted_stars, starsFromR(rv)));
        }),
      );
    });

    later(FREEZE_AT_MS, () => {
      setFrozen(true);
      sfx.freezeZap();
    });

    // ≥2s, once the kernel answers: the LLM judge's slot machine lands on 99% and the coins fly.
    const reveal = (v: HeistGateVerdict) => {
      setPhase("resolved");
      setProgress(99);
      setStars(v.heistbox_pair.wanted_stars);
      setRDisplay(v.heistbox_pair.conformal_martingale_r);
      if (!v.busted) {
        sfx.chime();
        return;
      }
      sfx.coinBurst();
    };

    // +350ms: steel vault door slams, BUSTED stamp, webcam freezes into the mugshot.
    const slamDown = (v: HeistGateVerdict) => {
      if (!v.busted) return;
      setSlam(true);
      sfx.playVaultSlamSound();
      sfx.clangBoom();
      // Cartesia Sonic streams the roast straight into <audio>; the browser voice only covers a failed/late stream.
      const pid = newId("WP");
      posterIdRef.current = pid;
      setRoast({ src: rollbackRoastStreamUrl(v), note: "🔊 Cartesia Sonic (streaming /api/integrations/rollback-roast/stream)", fallbackText: rollbackRoastLine(v) });
      later(380, sfx.laserZap);
      later(900, () => sfx.siren(2));
      setSparkKey((k) => k + 1);

      const shot = camRef.current.freeze();
      setMugshot(shot);
      const ctx = settleContextFrom(v, recipientRef.current);
      saveSettleContext(pid, ctx);
      setPosterHref(posterPath(pid, null));
      savePoster(wantedLocally(pid, v, shot), "fallback");
      // The poster (Gemini alias + its own Cartesia clip) plays on the /wanted page; the arena keeps the streamed roast.
      createWantedPoster(pid, v, shot, "Judge", reqRef.current).then((p) => savePoster(p.data, p.source));

      if (sourceRef.current === "kernel") {
        getVaultState().then((s) => s.source === "kernel" && setVault(s.data));
      } else {
        setVault((s) => ({
          total_saved_cents: s.total_saved_cents + v.heistbox_pair.red_stripped_cents,
          robbers_busted: s.robbers_busted + 1,
          fastest_catch_ms: s.fastest_catch_ms > 0 ? Math.min(s.fastest_catch_ms, v.clocks.postgres_pair_ms) : v.clocks.postgres_pair_ms,
        }));
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pick = (id: MaskId) => {
    const r = requestFor(id);
    setReq(r);
    setRecipient(DEMO_RECIPIENT);
    if (phase !== "rolling") {
      setPhase("idle");
      setSlam(false);
      setVerdict(instantVerdict(r, "preview"));
      setStars(0);
      setFrozen(false);
    }
  };

  const onTicket = (t: RealDisputeTicket | null) => {
    setRecipient(t && /^0x[0-9a-fA-F]{40}$/.test(t.enrolled_wallet) ? t.enrolled_wallet : DEMO_RECIPIENT);
  };

  const mic = useSpeech((text) => {
    const updated: HeistAttemptRequest = {
      ...reqRef.current,
      prompt_text: text,
      voice_transcript: text,
      mask_id: "custom",
    };
    setReq(updated);
    if (phase !== "rolling") {
      setVerdict(instantVerdict(updated, "preview"));
    }
  });

  const loraAttack = () => {
    const prompt = LORA_ATTACKS[loraIdx.current++ % LORA_ATTACKS.length];
    const updated: HeistAttemptRequest = {
      ...reqRef.current,
      prompt_text: prompt,
      mask_id: "custom",
    };
    setReq(updated);
    if (phase !== "rolling") {
      setVerdict(instantVerdict(updated, "preview"));
    }
  };

  const reset = () => {
    clearTimers();
    setPhase("idle");
    setSlam(false);
    setProgress(0);
    setFrozen(false);
    setStars(0);
    setRDisplay(1);
    setMugshot(null);
    setPosterHref(null);
    setRoast(null);
    posterIdRef.current = null;
    setVault(INITIAL_VAULT);
    const empty = createEmptyRequest();
    setReq(empty);
    setVerdict(instantVerdict(empty, "preview"));
    resetVault().then(() => getVaultState()).then((s) => s.source === "kernel" && setVault(s.data));
  };

  const busy = phase === "rolling";

  return (
    <div className="heist-app min-h-screen pb-16">
      <TopBar
        vault={vault}
        stars={stars}
        r={rDisplay}
        sparkKey={sparkKey}
        source={source}
        muted={muted}
        onReset={reset}
        onToggleMute={() => {
          sfx.setMuted(!muted);
          setMuted(!muted);
        }}
      />

      <main className="heist-main mx-auto flex max-w-[1500px] flex-col gap-6 px-4 pt-5">

        <div className="flex flex-col gap-4">
              <div className="arena-section-label" id="heist-arena">
                <div>
                  <span className="mission-eyebrow">01 / THE PLAYGROUND</span>
                  <h2>Make your move.</h2>
                </div>
                <div className="flex items-center gap-3">
                  <span className="arena-instruction hidden sm:inline">Choose an attack below or write your own.</span>
                  <button
                    onClick={() => setBriefingOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white/80 hover:bg-white/10 hover:text-white transition"
                  >
                    Briefing <ArrowUpRight size={14} />
                  </button>
                </div>
              </div>
              <Arena
                phase={phase}
                progress={progress}
                slam={slam}
                firewallFrozen={frozen}
                verdict={verdict}
                req={req}
                source={source}
                cam={cam}
                mugshot={mugshot}
                posterHref={posterHref}
                roast={roast}
                muted={muted}
                console={{
                  busy,
                  onChange: (r) => {
                    setReq(r);
                    if (phase !== "rolling") {
                      setVerdict(instantVerdict(r, "preview"));
                    }
                  },
                  onRun: () => run(reqRef.current),
                  onTicket,
                  mic,
                  onLoraAttack: loraAttack,
                }}
              />
              {posterHref && posterIdRef.current && (
                <section className="flex flex-col items-center gap-6 rounded-2xl border border-[#cbb78a]/40 bg-[#ead7ad] p-6 text-[#352213] sm:flex-row sm:justify-between sm:p-8" aria-label="Take your wanted poster">
                  <div><p className="text-xs font-bold uppercase tracking-[0.2em]">Your souvenir from the vault</p><h2 className="mt-3 text-3xl font-bold">You brought the heist.<br />We kept the receipts.</h2><p className="mt-3 max-w-lg text-sm leading-6 opacity-75">Scan to take home your Wanted poster and a personal breakdown of how PAIR handled your prompt.</p></div>
                  <PosterQr id={posterIdRef.current} size={192} />
                </section>
              )}
        </div>
        <footer className="mission-footer"><span>HEISTBOX <span className="text-white/30">×</span> PAIR</span><span>Curiosity is encouraged. Real money is not involved.</span><span>CAL HACKS / 2026 ↗</span></footer>
      </main>
      <AnimatePresence>
        {briefingOpen && <motion.div className="briefing-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setBriefingOpen(false)}>
          <section ref={briefingRef} className="briefing-panel" role="dialog" aria-modal="true" aria-labelledby="briefing-title" onClick={(e) => e.stopPropagation()}>
            <button autoFocus className="briefing-close" aria-label="Close mission briefing" onClick={() => setBriefingOpen(false)}><X size={20} /></button>
            <p className="mission-eyebrow">CLASSIFIED / YOUR FIRST HEIST</p><h2 id="briefing-title">Three steps to trouble.</h2>
            <ol><li><b>Enter the arena.</b><span>Explore the three vaults and choose which defense to test.</span></li><li><b>Make your pitch.</b><span>Choose a preset attack or type a creative prompt. Hit the heist button to run it.</span></li><li><b>Watch the vaults.</b><span>Compare the naive agent, rigid firewall, and PAIR airlock. Inspect the verdict, row locking, and airlock defense.</span></li></ol>
            <button className="mission-primary" onClick={() => setBriefingOpen(false)}>Got it. Let&apos;s play. <ArrowUpRight size={17} /></button>
          </section>
        </motion.div>}
      </AnimatePresence>
    </div>
  );
}
