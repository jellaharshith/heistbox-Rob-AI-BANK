"use client";
import { motion } from "framer-motion";
import { ExternalLink, Megaphone, Sparkles } from "lucide-react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useRef, useState } from "react";
import { fetchWantedPoster, loadPoster, remixWantedPoster, savePoster, type SettleContext } from "@/lib/api";
import { wantedLocally } from "@/lib/fallback";
import { usd } from "@/lib/format";
import {
  isPlaceholderTxHash,
  loadPublicOrigin,
  loadSettleContext,
  looksLikeServerPlaceholderPoster,
  posterPath,
  savePublicOrigin,
  saveSettleContext,
  settleFromQuery,
} from "@/lib/provenance";
import { siren } from "@/lib/sound";
import type { DataSource, WantedPosterCard } from "@/lib/types";
import { SettleWithPasskey } from "./SettleWithPasskey";

export default function WantedPoster({ id }: { id: string }) {
  const [card, setCard] = useState<WantedPosterCard>(() => wantedLocally(id, null, null));
  const [source, setSource] = useState<DataSource>("fallback");
  const [ctx, setCtx] = useState<SettleContext | null>(null);
  const [qrUrl, setQrUrl] = useState("");
  const [origin, setOrigin] = useState("");
  const [originOverride, setOriginOverride] = useState("");
  const [playing, setPlaying] = useState(false);
  const [audioNote, setAudioNote] = useState("");
  const [txPlaceholder, setTxPlaceholder] = useState(true);
  const [remixing, setRemixing] = useState(false);
  const [remixError, setRemixError] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);

  const handleRemix = async (provider: "claude" | "openai" = "claude") => {
    if (!card.mugshot_data_url) return;
    setRemixing(true);
    setRemixError(null);
    try {
      const res = await remixWantedPoster(
        id,
        card.mugshot_data_url,
        "Judge",
        card.alias_title,
        card.outfit_roast,
        provider,
      );
      if (res.remix_poster_url) {
        const updated = {
          ...card,
          remix_poster_url: res.remix_poster_url,
          alias_title: res.alias_title || card.alias_title,
          outfit_roast: res.outfit_roast || card.outfit_roast,
          remix_status: "success" as const,
          remix_error: null,
        };
        setCard(updated);
        savePoster(updated, "kernel");
        setShowOriginal(false);
      } else {
        setRemixError(res.remix_error || "Poster remix generation failed");
      }
    } catch (err: any) {
      setRemixError(err?.message || "Failed to remix poster");
    } finally {
      setRemixing(false);
    }
  };

  useEffect(() => {
    setOrigin(window.location.origin);
    setOriginOverride(loadPublicOrigin());
    // Settle context: from the QR link's query (phone) or what the desktop saved when the heist was busted.
    const fromQuery = settleFromQuery(window.location.search);
    const c = fromQuery ?? loadSettleContext(id);
    if (fromQuery) saveSettleContext(id, fromQuery);
    setCtx(c);

    const saved = loadPoster(id);
    if (saved) {
      setCard(saved.data);
      setSource(saved.source);
    }
    // The server copy carries the Cloud Vision/Claude roast, the Cartesia audio (never cached locally) and the
    // mugshot, so refetch whenever the local copy is a fallback or is missing either.
    if (!saved || saved.source === "fallback" || !saved.data.mugshot_data_url || !saved.data.audio_base64) {
      fetchWantedPoster(id).then((remote) => {
        if (!remote) return;
        const placeholder = looksLikeServerPlaceholderPoster(remote.data);
        if (placeholder && saved) return; // keep our honest local template over the server's invented card
        const data = placeholder ? { ...remote.data, provenance: "server placeholder (main.py _build_wanted_poster_card / router fallback)" } : remote.data;
        setCard((prev) => ({ ...data, mugshot_data_url: data.mugshot_data_url ?? prev.mugshot_data_url }));
        setSource(placeholder ? "fallback" : "kernel");
        if (!placeholder) savePoster(data, "kernel");
      });
    }
  }, [id]);

  const effectiveOrigin = (originOverride.trim() || origin).replace(/\/$/, "");

  useEffect(() => {
    if (!effectiveOrigin) return;
    // The QR is this page's live URL (window.location.href). With a tunnel override, keep the same path +
    // query on the public origin; if the page was opened without settle params, add them so the phone can settle.
    const here = new URL(window.location.href);
    const pathAndQuery = here.search ? here.pathname + here.search : posterPath(id, ctx);
    setQrUrl(originOverride.trim() ? effectiveOrigin + pathAndQuery : here.search ? here.href : effectiveOrigin + pathAndQuery);
  }, [effectiveOrigin, originOverride, id, ctx]);

  const receipt = card.x402_receipt;
  useEffect(() => {
    let live = true;
    isPlaceholderTxHash(id, receipt?.tx_hash).then((p) => live && setTxPlaceholder(p));
    return () => {
      live = false;
    };
  }, [id, receipt?.tx_hash]);

  const audioRef = useRef<HTMLAudioElement>(null);
  const audioSrc = card.audio_base64 ? `data:audio/wav;base64,${card.audio_base64}` : null;

  // Play the Cartesia roast as soon as the poster carries it (browsers may block this until a tap).
  useEffect(() => {
    const el = audioRef.current;
    if (!el || !audioSrc) return;
    el.play()
      .then(() => {
        setPlaying(true);
        setAudioNote("playing Cartesia audio returned by the integrations server");
      })
      .catch(() => setAudioNote("Cartesia audio is ready — tap the button to play (browser blocked autoplay)"));
  }, [audioSrc]);

  const play = async () => {
    setPlaying(true);
    siren(1);
    if (audioSrc && audioRef.current) {
      try {
        audioRef.current.currentTime = 0;
        await audioRef.current.play();
        setAudioNote("playing Cartesia audio returned by the integrations server");
        return;
      } catch {
        setAudioNote("Cartesia audio failed to play; using the browser voice instead");
      }
    } else {
      setAudioNote("no Cartesia audio on this poster (key missing or call failed) — browser speech synthesis");
    }
    if ("speechSynthesis" in window) {
      const u = new SpeechSynthesisUtterance(card.megaphone_transcript);
      u.rate = 1.05;
      u.pitch = 0.8;
      u.onend = () => setPlaying(false);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } else {
      setPlaying(false);
    }
  };

  const prov = card.provenance ?? (source === "kernel" ? "integrations" : "web-local-template");
  const serverPlaceholder = prov.startsWith("server placeholder");
  const crsReal = card.crs_rap_sheet.verified && !serverPlaceholder && /crs/i.test(prov);
  // Only a non-fallback poster whose tx hash isn't the sha256("tx:{id}") placeholder may link to BaseScan.
  const showBaseScan = Boolean(receipt?.basescan_url) && source === "kernel" && !/fallback|placeholder|local/i.test(prov) && !txPlaceholder;

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-4 py-8">
      <motion.div
        initial={{ rotate: -4, scale: 0.9, opacity: 0 }}
        animate={{ rotate: -1.5, scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 160, damping: 14 }}
        className="w-full rounded-md border-[6px] border-[#5b3a1a] bg-[#f3e2b8] p-5 text-[#2a1a08] shadow-[0_30px_80px_#000c]"
        style={{ backgroundImage: "radial-gradient(circle at 30% 20%, #fff6 0, transparent 40%), radial-gradient(circle at 80% 90%, #a0703033 0, transparent 50%)" }}
      >
        <div className="text-center font-display text-6xl tracking-widest text-[#7a1010]">WANTED</div>
        <div className="-mt-1 text-center text-xs font-bold uppercase tracking-[0.3em]">for attempted vault robbery</div>

        <div className="relative mx-auto mt-3 aspect-[4/3] w-full overflow-hidden border-4 border-[#2a1a08] bg-neutral-800">
          {card.remix_poster_url && !showOriginal ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={card.remix_poster_url} alt="Gemini Remixed Wanted Poster" className="h-full w-full object-cover" />
          ) : card.mugshot_data_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={card.mugshot_data_url} alt="B&W mugshot" className="h-full w-full scale-x-[-1] object-cover contrast-150 grayscale" />
          ) : (
            <div className="flex h-full flex-col items-center justify-center text-8xl grayscale">
              🕶️<span className="mt-1 text-[10px] text-white/60 grayscale-0">no webcam frame on this device</span>
            </div>
          )}
          {card.remix_poster_url && !showOriginal && (
            <div className="absolute top-2 right-2 rounded bg-amber-600/90 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white shadow">
              ✨ Claude AI Remix
            </div>
          )}
        </div>

        {card.mugshot_data_url && (
          <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
            <button
              onClick={() => handleRemix("claude")}
              disabled={remixing}
              className="flex items-center gap-1.5 rounded-full border border-[#5b3a1a] bg-[#e6ce9e] px-3 py-1 text-xs font-semibold text-[#2a1a08] shadow-sm hover:bg-[#dbc08c] disabled:opacity-50 transition"
            >
              <Sparkles className="h-3.5 w-3.5 text-[#7a1010]" />
              {remixing ? "Remixing with Claude…" : card.remix_poster_url ? "Re-Remix (Claude)" : "✨ Remix Poster (Claude)"}
            </button>
            {card.remix_poster_url && (
              <button
                onClick={() => setShowOriginal(!showOriginal)}
                className="rounded-full border border-[#5b3a1a]/50 px-2.5 py-1 text-[11px] font-medium text-[#2a1a08]/80 hover:bg-[#5b3a1a]/10 transition"
              >
                {showOriginal ? "View AI Remix" : "View Raw Mugshot"}
              </button>
            )}
          </div>
        )}
        {(remixError || card.remix_error) && !card.remix_poster_url && (
          <p className="mt-1 text-center text-[10px] italic text-[#7a1010]/80">
            Remix note: {remixError || card.remix_error}
          </p>
        )}

        <div className="mt-3 text-center font-display text-2xl leading-tight">“{card.alias_title}”</div>
        <p className="mt-1 text-center text-sm italic">{card.outfit_roast}</p>
        {card.vision_cues && card.vision_cues.length > 0 && (
          <p className="mt-1 text-center text-[10px] uppercase tracking-wider opacity-70">Cloud Vision saw: {card.vision_cues.join(" · ")}</p>
        )}

        <button onClick={play} disabled={playing} className="mx-auto mt-3 flex items-center gap-2 rounded-full bg-[#7a1010] px-4 py-2 text-sm font-bold text-[#f3e2b8] disabled:opacity-60">
          <Megaphone className="h-4 w-4" /> {playing ? "Helicopter on the mic…" : "▶ Replay helicopter megaphone roast"}
        </button>
        {audioSrc && <audio ref={audioRef} src={audioSrc} preload="auto" onEnded={() => setPlaying(false)} />}
        {audioNote && <p className="mt-1 text-center text-[10px] italic">{audioNote}</p>}

        <div className="mt-4 grid grid-cols-[1fr_auto] gap-3">
          <div className="space-y-2 text-xs">
            <div className="rounded border-2 border-[#2a1a08] p-2">
              <div className="font-bold uppercase">CRS sandbox rap sheet</div>
              {crsReal ? (
                <>
                  <div className="font-display text-2xl">
                    {card.crs_rap_sheet.score} <span className="font-sans text-xs">✔ from CRS sandbox</span>
                  </div>
                  <ul className="list-inside list-disc">
                    {card.crs_rap_sheet.flags.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <div className="text-[11px] italic">Not checked — no CRS sandbox result on this poster{serverPlaceholder ? " (the server's placeholder card claims verified=true, but it was never sent to CRS)" : ""}.</div>
              )}
            </div>
            <div className="rounded border-2 border-[#2a1a08] p-2">
              <div className="font-bold uppercase">x402 marked bill</div>
              {receipt ? (
                <>
                  <div className="break-all font-mono-tight text-[10px]">nonce {receipt.eip3009_marked_bill_nonce}</div>
                  {showBaseScan ? (
                    <a href={receipt.basescan_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-bold text-[#7a1010] underline">
                      View on BaseScan <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <div className="text-[10px] italic">The poster&apos;s tx hash is a placeholder from the integrations fallback, not an on-chain transaction — no BaseScan link. Settle below for a real outcome.</div>
                  )}
                </>
              ) : (
                <div className="text-[10px] italic">No receipt on this poster. Settle below for a real outcome.</div>
              )}
            </div>
          </div>
          <div className="flex flex-col items-center">
            <div className="border-2 border-[#2a1a08] bg-white p-1 shadow-md">
              <QRCodeSVG
                value={qrUrl || (typeof window !== "undefined" ? `${window.location.origin}/wanted/${card.poster_id || id}` : "http://localhost:3000")}
                size={180}
                bgColor={"#ffffff"}
                fgColor={"#000000"}
                level={"Q"}
                includeMargin={true}
                title="QR code for this poster"
              />
            </div>
            <span className="mt-1 text-[10px] font-bold uppercase tracking-wider text-[#2a1a08]">scan to settle on phone</span>
          </div>
        </div>

        <div className="mt-3 rounded border-2 border-[#2a1a08] p-2">
          <div className="mb-1 text-xs font-bold uppercase">Settle the green half</div>
          {ctx ? (
            <>
              <div className="mb-1 font-mono-tight text-[10px]">
                {usd(ctx.green_cents)} green · {usd(ctx.red_cents)} red · intent {ctx.intent_hash.slice(0, 14)}… · to {ctx.recipient.slice(0, 10)}…
              </div>
              <SettleWithPasskey ctx={ctx} tone="paper" />
            </>
          ) : (
            <div className="text-[11px] italic">No settle context for this poster. Open it from the arena&apos;s “Print my WANTED poster” link, or scan that poster&apos;s QR.</div>
          )}
        </div>

        <div className="mt-3 flex items-center justify-between gap-2 text-[10px] uppercase tracking-wider">
          <span>#{card.poster_id}</span>
          <span className="text-right normal-case">poster source: {prov}</span>
        </div>
      </motion.div>

      <div className="mt-4 w-full rounded-lg border border-white/10 bg-black/50 p-3 text-xs text-white/70">
        <label className="block">
          QR origin (paste your public tunnel URL so phones can reach it)
          <input
            value={originOverride}
            placeholder={origin || "https://….trycloudflare.com"}
            onChange={(e) => {
              setOriginOverride(e.target.value);
              savePublicOrigin(e.target.value);
            }}
            className="mt-1 w-full rounded-md border border-white/15 bg-black/60 px-2 py-1.5 font-mono-tight text-xs text-white outline-none focus:border-yellow-400"
          />
        </label>
        <div className="mt-1 break-all font-mono-tight text-[10px] text-white/40">QR → {qrUrl}</div>
      </div>

      <Link href="/" className="mt-6 text-sm text-white/60 underline hover:text-white">
        ← back to the vault
      </Link>
    </main>
  );
}
