"use client";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";

export function PosterQr({ id, size = 208 }: { id: string; size?: number }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let active = true;
    fetch("/api/poster-share", { cache: "no-store" })
      .then((response) => response.json())
      .then((share) => {
        const origin = new URL(share.origin);
        if (active && ["http:", "https:"].includes(origin.protocol)) {
          setUrl(`${origin.origin}/wanted/${encodeURIComponent(id)}`);
        }
      }).catch(() => {});
    return () => { active = false; };
  }, [id]);
  return (
    <div className="flex flex-col items-center text-center" aria-label="Scan to get your wanted poster">
      <div className="rounded-sm border-2 border-[#382714] bg-white p-2 shadow-[4px_4px_0_#38271433]">
        {url ? <QRCodeSVG value={url} size={size} level="M" marginSize={4} title="Scan to open this poster and its defense report" />
          : <div style={{ width: size, height: size }} className="flex items-center justify-center text-sm text-black" role="status">Preparing QR code…</div>}
      </div>
      <p className="mt-3 text-sm font-black uppercase tracking-[0.14em]">Scan. Get your poster.</p>
      <p className="mt-1 max-w-56 text-xs opacity-70">Your heist. Your defense breakdown. Take it with you.</p>
    </div>
  );
}
