/* Antigravity scene bridge. The real /web/scene package can replace this file
   when it lands; the dashboard remains usable with this canvas-safe stub. */
export type SceneStore = { agents: unknown[]; area: string; weather: string };
export type SceneHandle = { dispose?: () => void };

let thiefPhoto: ImageBitmap | null = null;

/** Optional visual hand-off to the scene; the photo never leaves this tab. */
export function setThiefPhoto(bitmap: ImageBitmap) {
  thiefPhoto?.close?.();
  thiefPhoto = bitmap;
}

export function clearThiefPhoto() {
  thiefPhoto?.close?.();
  thiefPhoto = null;
}

export function mountScene(canvas: HTMLCanvasElement, _store: SceneStore): SceneHandle {
  const context = canvas.getContext("2d");
  if (context) { context.fillStyle = "#0c1820"; context.fillRect(0, 0, canvas.width, canvas.height); }
  return { dispose: () => undefined };
}
export function flyToArea(_area: string) { /* stub until Antigravity lands */ }
export function setWeather(_weather: string) { /* stub until Antigravity lands */ }
export function setTimeOfDay(_time: string) { /* stub until Antigravity lands */ }
export function onSelect(_callback: (id: string) => void) { return () => undefined; }
