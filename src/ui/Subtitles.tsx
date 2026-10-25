import { useGame } from "../game/store";
// Text-only stage narration at step 2. WebAudio and visemes are step 4.
export function Subtitles() {
  const text = useGame((s) => s.subtitle);
  return text ? (
    <div className="subtitles" role="status">
      {text}
    </div>
  ) : null;
}
