"use client";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { Arena, type Phase, type RoastAudio } from "./Arena";
import { CfoAudit } from "./CfoAudit";
import { PairSplit } from "./PairSplit";
import { StatusBar } from "./StatusBar";
import { ThiefCards } from "./ThiefCards";
import { TopBar, type View } from "./TopBar";
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
  const [view, setView] = useState<View>("arena");
  const [req, setReq] = useState<HeistAttemptRequest>(createEmptyRequest);
  const [verdict, setVerdict] = useState<HeistGateVerdict>(() => instantVerdict(createEmptyRequest(), "preview"));
  const [source, setSource] = useState<DataSource>("fallback");
  const [gateLive, setGateLive] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [slam, setSlam] = useState(false);
  const [progress, setProgress] = useState(0);
  const [frozen, setFrozen] = useState(false);
  const [vault, setVault] = useState<VaultState>(INITIAL_VAULT);
  const [stars, setStars] = useState(0);
  const [rDisplay, setRDisplay] = useState(1);
  const [sparkKey, setSparkKey] = useState(0);
  const [runKey, setRunKey] = useState(0);
  const [mugshot, setMugshot] = useState<string | null>(null);
  const [posterHref, setPosterHref] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [enclaveUs, setEnclaveUs] = useState(0);
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
        setGateLive(true);
      }
    });
    // Turn the security camera on as soon as the page opens (the browser asks for permission once).
    camAsked.current = true;
    void camRef.current.start();
    return clearTimers;
  }, []);

  const run = useCallback((r: HeistAttemptRequest) => {
    clearTimers();
    // First heist arms the mugshot cam (inside the click's user gesture) so there's a frame to freeze at rollback.
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
    setRunKey((k) => k + 1);
    sfx.playSlotMachineSound();
    sfx.coinRoll(ROLL_MS);

    // The reveal waits for the kernel's verdict (live LLM proposal + gate), never less than the ROLL_MS animation.
    // Only an unreachable kernel resolves with the local twin, and the UI then shows source "fallback".
    const kernelVerdict = evaluateHeist(r, requestId);
    const minRoll = new Promise<void>((done) => later(ROLL_MS, done));
    void Promise.all([kernelVerdict, minRoll]).then(([res]) => {
      if (runSeq.current !== myRun) return; // a newer heist started
      setSource(res.source);
      if (res.source === "kernel") setGateLive(true);
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
      setPosterHref(posterPath(pid, ctx));
      savePoster(wantedLocally(pid, v, shot), "fallback");
      // The poster (Gemini alias + its own Cartesia clip) plays on the /wanted page; the arena keeps the streamed roast.
      createWantedPoster(pid, v, shot).then((p) => savePoster(p.data, p.source));

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
  const showSplit = phase === "resolved" && slam && verdict.busted;

  return (
    <div className="min-h-screen pb-16">
      <TopBar
        vault={vault}
        stars={stars}
        r={rDisplay}
        view={view}
        sparkKey={sparkKey}
        source={source}
        muted={muted}
        onToggleView={() => setView((v) => (v === "arena" ? "cfo" : "arena"))}
        onReset={reset}
        onToggleMute={() => {
          sfx.setMuted(!muted);
          setMuted(!muted);
        }}
      />
      <StatusBar
        gateLive={gateLive}
        busted={showSplit}
        challenge={verdict.heistbox_pair?.settlement_hash ?? undefined}
        cents={verdict.heistbox_pair?.green_repaired_cents}
      />

      <main className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 pt-5">
        <div className="text-center">
          <h1 className="font-display text-3xl neon-gold md:text-5xl">ROB OUR AI BANK</h1>
          <p className="text-sm text-white/50">Type any prompt injection, bribe, or exploit below. Watch the naive LLM on the Left get robbed, while HeistBox slams shut in 1.8ms, snaps your webcam mugshot, and lasers off the heist.</p>
        </div>



        <AnimatePresence mode="wait">
          {view === "arena" ? (
            <motion.div key="arena" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} className="flex flex-col gap-4">
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
              {showSplit && <PairSplit key={runKey} v={verdict} req={req} recipient={recipient} runKey={runKey} onSettled={setEnclaveUs} />}
            </motion.div>
          ) : (
            <motion.div key="cfo" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}>
              <CfoAudit v={verdict} req={req} source={source} enclaveUs={enclaveUs} recipient={recipient} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
