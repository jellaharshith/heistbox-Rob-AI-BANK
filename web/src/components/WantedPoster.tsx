"use client";
import { motion } from "framer-motion";
import { Megaphone, Download, Printer } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchWantedPoster, loadPoster, savePoster } from "@/lib/api";
import { wantedLocally } from "@/lib/fallback";
import { usd } from "@/lib/format";
import type { WantedPosterCard } from "@/lib/types";
import { PosterQr } from "./PosterQr";
import { DefenseReport } from "./DefenseReport";

export default function WantedPoster({ id }: { id: string }) {
  const [card, setCard] = useState<WantedPosterCard>(() => wantedLocally(id, null, null));
  const [playing, setPlaying] = useState(false);
  const [audioNote, setAudioNote] = useState("");
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioSrc = card.audio_base64 ? `data:audio/wav;base64,${card.audio_base64}` : null;

  useEffect(() => {
    let active = true;
    let retry: ReturnType<typeof setTimeout> | undefined;
    const saved = loadPoster(id);
    if (saved) setCard(saved.data);
    const refresh = async (attempt = 0) => {
      const remote = await fetchWantedPoster(id);
      if (!active) return;
      if (!remote) {
        if (attempt < 6) retry = setTimeout(() => void refresh(attempt + 1), 2000);
        return;
      }
      setCard((previous) => ({ ...remote.data, mugshot_data_url: remote.data.mugshot_data_url ?? previous.mugshot_data_url }));
      savePoster(remote.data, "kernel");
    };
    void refresh();
    return () => { active = false; clearTimeout(retry); };
  }, [id]);

  const play = async () => {
    setPlaying(true);
    if (audioRef.current && audioSrc) {
      try { audioRef.current.currentTime = 0; await audioRef.current.play(); return; }
      catch { setAudioNote("Using your device's voice for the announcement."); }
    }
    if ("speechSynthesis" in window) {
      const voice = new SpeechSynthesisUtterance(card.megaphone_transcript);
      voice.rate = 1.05;
      voice.onend = () => setPlaying(false);
      voice.onerror = () => setPlaying(false);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(voice);
    } else { setPlaying(false); setAudioNote("Audio is unavailable on this device."); }
  };

  return (
    <main className="wanted-page mx-auto min-h-screen w-full max-w-[1360px] px-4 py-6 sm:px-7 sm:py-10">
      <div className="mb-7 flex flex-wrap items-center justify-between gap-4 print:hidden">
        <Link href="/" className="text-sm font-bold text-white/65 transition hover:text-white">← Back to the vault</Link>
        <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-full border border-white/20 px-4 py-2 text-sm text-white/80 hover:bg-white/10"><Printer size={16} /> Print poster & report</button>
      </div>
      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1.35fr)_minmax(340px,1fr)]">
        <motion.article initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}
          aria-label="Wanted poster"
          className="relative min-w-0 overflow-hidden rounded-sm border-[8px] border-[#53351d] bg-[#ead7ad] p-4 text-[#352213] shadow-[0_25px_90px_#0009] sm:p-7"
          style={{ backgroundImage: "radial-gradient(ellipse at center, #fff7dd88, #9c743d33), repeating-linear-gradient(3deg, transparent 0px, transparent 3px, #65431e07 4px, transparent 5px)" }}>
          <div className="pointer-events-none absolute inset-2 border border-[#5b3a1a]/40" />
          <div className="relative">
            <p className="border-b-2 border-[#53351d] pb-3 text-center font-mono text-[10px] font-bold uppercase tracking-[0.24em] sm:text-xs">HeistBox Bureau of Very Clever Attempts</p>
            <h1 className="mt-3 text-center font-display text-[clamp(4.4rem,12vw,8rem)] leading-[0.95] font-black tracking-[0.035em] text-[#721c16]">WANTED</h1>
            <p className="mt-3 text-center text-xs font-black uppercase tracking-[0.17em] sm:text-sm">For attempted grand theft prompt</p>
            <div className="relative mx-auto mt-5 overflow-hidden border-[5px] border-[#352213] bg-[#40382c] p-1 shadow-[3px_5px_0_#35221330]">
              <div className="relative aspect-[5/4] overflow-hidden bg-[#201f1a]">
                {card.mugshot_data_url ? <img src={card.mugshot_data_url} alt="The operative's captured mugshot" className="h-full w-full scale-x-[-1] object-cover contrast-125 sepia-[.65]" /> : (
                  <div className="flex h-full flex-col items-center justify-center bg-[repeating-linear-gradient(0deg,#33352c_0px,#33352c_1px,#22251f_1px,#22251f_56px)] text-[#bca77d]">
                    <svg width="160" height="180" viewBox="0 0 160 180" fill="currentColor" aria-hidden="true"><circle cx="80" cy="55" r="38" /><path d="M12 180v-28a68 68 0 0 1 136 0v28Z" /><path fill="#22251f" d="M36 40h88v14H36Z" /></svg>
                    <p className="mt-4 font-mono text-xs uppercase tracking-[0.18em]">The camera-shy mastermind</p>
                  </div>
                )}
                <span className="absolute right-3 bottom-6 rotate-[-13deg] border-[5px] border-[#8d2119] bg-[#ead7ad]/90 px-4 py-1 font-display text-[clamp(2rem,5vw,4rem)] leading-none font-black tracking-widest text-[#8d2119] shadow-lg">BUSTED</span>
              </div>
            </div>
            <p className="mt-5 text-center text-[10px] font-bold uppercase tracking-[0.3em]">Alias on the case file</p>
            <h2 className="mt-2 text-center font-display text-3xl leading-tight sm:text-4xl">“{card.alias_title}”</h2>
            <p className="mx-auto mt-3 max-w-lg text-center font-serif text-base leading-6 italic">{card.outfit_roast}</p>
            <div className="my-6 flex items-center justify-center gap-3 border-y-2 border-[#53351d]/70 py-3 text-center">
              <span className="text-xl" aria-hidden="true">★</span>
              <div><p className="text-[10px] font-bold uppercase tracking-[0.2em]">{card.defense_report ? "Unauthorized loot stopped" : "Reward for this attempt"}</p><p className="mt-1 font-display text-3xl font-bold">{card.defense_report ? usd(card.defense_report.blocked_cents) : "BRAGGING RIGHTS"}</p></div>
              <span className="text-xl" aria-hidden="true">★</span>
            </div>
            <div className="grid items-center gap-7 sm:grid-cols-[1fr_auto]">
              <div>
                <p className="font-display text-2xl font-bold uppercase">Great pitch.<br />Wrong vault.</p>
                <p className="mt-3 text-sm leading-6">Apprehended by PAIR. Accomplices include suspicious urgency, creative accounting, and an extremely convincing backstory.</p>
                <button onClick={play} disabled={playing} className="mt-5 inline-flex items-center gap-2 rounded-full bg-[#721c16] px-4 py-2.5 text-sm font-bold text-[#fff2d4] disabled:opacity-60 print:hidden"><Megaphone size={16} /> {playing ? "Sheriff on the mic…" : "Hear the sheriff"}</button>
                {card.remix_poster_url && <a href={card.remix_poster_url} download={`wanted-${card.poster_id}.svg`} className="mt-3 flex w-fit items-center gap-2 text-sm font-bold underline underline-offset-4 print:hidden"><Download size={15} /> Download poster</a>}
                {audioSrc && <audio ref={audioRef} src={audioSrc} preload="none" onEnded={() => setPlaying(false)} onError={() => setPlaying(false)} />}
                {audioNote && <p className="mt-2 text-xs italic">{audioNote}</p>}
              </div>
              <PosterQr id={id} />
            </div>
            <p className="mt-7 border-t border-[#53351d]/50 pt-3 text-center font-mono text-[9px] font-bold uppercase tracking-[0.14em]">Case {card.poster_id} · Play money. Real security lesson.</p>
          </div>
        </motion.article>
        <DefenseReport report={card.defense_report} />
      </div>
    </main>
  );
}
