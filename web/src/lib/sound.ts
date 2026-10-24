// Tiny WebAudio synth — every sound is generated, no audio files to load.
let ctx: AudioContext | null = null;
let muted = false;

export function setMuted(m: boolean) {
  muted = m;
}

function ac(): AudioContext | null {
  if (typeof window === "undefined" || muted) return null;
  try {
    if (!ctx) {
      const C = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      ctx = new C();
    }
    if (ctx.state === "suspended") void ctx.resume();
    return ctx;
  } catch {
    return null;
  }
}

/** Speak out loud with the browser's built-in voice (SpeechSynthesis). Returns false if unavailable or muted. */
export function speak(text: string): boolean {
  if (typeof window === "undefined" || muted || !("speechSynthesis" in window)) return false;
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 1.05;
  u.pitch = 0.75;
  u.volume = 1;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
  return true;
}

function tone(a: AudioContext, freq: number, at: number, dur: number, type: OscillatorType, gain: number, endFreq?: number) {
  const o = a.createOscillator();
  const g = a.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, at);
  if (endFreq) o.frequency.exponentialRampToValueAtTime(endFreq, at + dur);
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(gain, at + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
  o.connect(g).connect(a.destination);
  o.start(at);
  o.stop(at + dur + 0.05);
}

function noise(a: AudioContext, at: number, dur: number, gain: number, filterHz: number, q = 0.8) {
  const len = Math.floor(a.sampleRate * dur);
  const buf = a.createBuffer(1, len, a.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
  const src = a.createBufferSource();
  src.buffer = buf;
  const f = a.createBiquadFilter();
  f.type = "bandpass";
  f.frequency.value = filterHz;
  f.Q.value = q;
  const g = a.createGain();
  g.gain.value = gain;
  src.connect(f).connect(g).connect(a.destination);
  src.start(at);
}

/** Real synthesized Web Audio slot machine sound */
export function playSlotMachineSound() {
  if (typeof window === "undefined") return;
  const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sawtooth";
  osc.frequency.setValueAtTime(440, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 1.8);
  gain.gain.setValueAtTime(0.15, ctx.currentTime);
  gain.gain.linearRampToValueAtTime(0.01, ctx.currentTime + 1.8);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 1.8);
}

/** Real synthesized Web Audio vault slam sound */
export function playVaultSlamSound() {
  if (typeof window === "undefined") return;
  const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(150, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(30, ctx.currentTime + 0.6);
  gain.gain.setValueAtTime(0.4, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.6);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 0.6);
}

/** Real browser Text-to-Speech voice roast */
export function speakRoast(text: string) {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 0.9;
    window.speechSynthesis.speak(utterance);
  }
}

/** Slot-machine reel ticks that speed up and climb in pitch for `ms`. */
export function coinRoll(ms = 2000) {
  const a = ac();
  if (!a) return;
  const t0 = a.currentTime;
  let t = 0;
  let i = 0;
  while (t < ms / 1000) {
    const p = t / (ms / 1000);
    tone(a, 520 + p * 900 + (i % 2) * 60, t0 + t, 0.04, "square", 0.035);
    t += 0.085 - p * 0.05;
    i++;
  }
}

/** Jackpot payout — a shower of high pings. */
export function coinBurst() {
  const a = ac();
  if (!a) return;
  const t0 = a.currentTime;
  for (let i = 0; i < 14; i++) tone(a, 1800 + ((i * 337) % 900), t0 + i * 0.045, 0.18, "triangle", 0.05);
}

/** Heavy steel vault door: metallic clang + sub-bass drop. */
export function clangBoom() {
  const a = ac();
  if (!a) return;
  const t0 = a.currentTime;
  noise(a, t0, 0.35, 0.9, 900, 1.2);
  for (const f of [211, 587, 1043, 1611]) tone(a, f, t0, 0.9, "sine", 0.08);
  tone(a, 120, t0 + 0.02, 1.4, "sine", 0.6, 32);
  tone(a, 60, t0 + 0.02, 1.6, "triangle", 0.35, 28);
}

/** Ice crackle for the frozen firewall. */
export function freezeZap() {
  const a = ac();
  if (!a) return;
  const t0 = a.currentTime;
  tone(a, 2400, t0, 0.35, "sawtooth", 0.03, 300);
  noise(a, t0, 0.25, 0.25, 5000, 2);
}

export function laserZap() {
  const a = ac();
  if (!a) return;
  const t0 = a.currentTime;
  tone(a, 3200, t0, 0.5, "sawtooth", 0.04, 180);
}

export function siren(cycles = 2) {
  const a = ac();
  if (!a) return;
  const t0 = a.currentTime;
  for (let i = 0; i < cycles; i++) {
    tone(a, 650, t0 + i * 0.6, 0.3, "square", 0.03, 950);
    tone(a, 950, t0 + i * 0.6 + 0.3, 0.3, "square", 0.03, 650);
  }
}

export function chime() {
  const a = ac();
  if (!a) return;
  const t0 = a.currentTime;
  tone(a, 880, t0, 0.25, "sine", 0.08);
  tone(a, 1320, t0 + 0.12, 0.4, "sine", 0.08);
}
