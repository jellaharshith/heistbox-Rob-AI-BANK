import { useEffect, useState } from "react";
import { useGame } from "../game/store";
import { triggerWantedPoster } from "../net/client";

type Poster = { alias_title: string; outfit_roast: string; remix_poster_url?: string; mugshot_data_url?: string };

export function WantedCard() {
  const posterUrl = useGame((s) => s.posterUrl);
  const capturedPhoto = useGame((s) => s.capturedPhoto);
  const stage = useGame((s) => s.stage);
  const phase = useGame((s) => s.phase);
  const [poster, setPoster] = useState<Poster | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    setPoster(null);
    if (!posterUrl.startsWith("/api/poster/")) return;
    setLoading(true);
    (async () => {
      const response = await fetch(posterUrl);
      if (!response.ok) throw new Error("Poster summary unavailable");
      const summary = await response.json();
      if (active) setPoster({ alias_title: summary.alias, outfit_roast: summary.headline });
      const card = await triggerWantedPoster({
        poster_id: posterUrl.split("/").pop(), judge_name: summary.alias,
        mugshot_data_url: capturedPhoto || undefined,
      });
      if (active) setPoster(card);
    })().catch(() => {}).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [posterUrl, capturedPhoto]);
  if (stage !== "poster" && phase !== "RESULTS") return null;
  return (
    <div className="story-card" aria-label="Wanted poster">
      <small>WANTED</small>
      {(poster?.mugshot_data_url || capturedPhoto) && <img src={poster?.mugshot_data_url || capturedPhoto} alt="Captured operative" className="poster-photo" />}
      <b>{poster?.alias_title || "UNKNOWN PROMPT ENGINEER"}</b>
      <span>{poster?.outfit_roast || "Crime: confusing a story with authorization."}</span>
      {loading && <span role="status">Preparing poster...</span>}
      {poster?.remix_poster_url && <a href={poster.remix_poster_url} download="heistbox-wanted.svg">Download wanted poster</a>}
    </div>
  );
}
