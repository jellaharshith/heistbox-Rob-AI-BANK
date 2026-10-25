/**
 * HeistBox 3D Scene - Pure WebAudio Sound Synthesizer
 * Generates all SFX procedurally - Zero external audio files.
 */

let ctx = null;
let muted = false;
let activeSirenNode = null;
let activeSirenOsc = null;

function getContext() {
  if (typeof window === 'undefined') return null;
  if (!ctx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      ctx = new AudioCtx();
    }
  }
  if (ctx && ctx.state === 'suspended') {
    ctx.resume().catch(() => {});
  }
  return ctx;
}

// Auto-unlock on first user interaction
if (typeof window !== 'undefined') {
  const unlock = () => {
    if (ctx && ctx.state === 'suspended') {
      ctx.resume().catch(() => {});
    }
    window.removeEventListener('pointerdown', unlock);
    window.removeEventListener('keydown', unlock);
  };
  window.addEventListener('pointerdown', unlock, { once: true });
  window.addEventListener('keydown', unlock, { once: true });
}

export function setMuted(val) {
  muted = Boolean(val);
  if (muted && activeSirenNode) {
    stopPoliceSiren();
  }
}

export function isMuted() {
  return muted;
}

export function toggleMute() {
  setMuted(!muted);
  return muted;
}

/** Rapid mechanical click tick for slot machine rolling */
export function playReelTick(pitchOffset = 0) {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  const now = ac.currentTime;
  const osc = ac.createOscillator();
  const gain = ac.createGain();

  osc.type = 'triangle';
  osc.frequency.setValueAtTime(320 + pitchOffset * 40, now);
  osc.frequency.exponentialRampToValueAtTime(120, now + 0.04);

  gain.gain.setValueAtTime(0.12, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

  osc.connect(gain);
  gain.connect(ac.destination);

  osc.start(now);
  osc.stop(now + 0.05);
}

/** Triumphant 3-bell win sound when SAFE% hits 99% */
export function playReelWin() {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
  notes.forEach((freq, idx) => {
    const start = ac.currentTime + idx * 0.09;
    const osc = ac.createOscillator();
    const gain = ac.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, start);

    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(0.2, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, start + 0.35);

    osc.connect(gain);
    gain.connect(ac.destination);

    osc.start(start);
    osc.stop(start + 0.36);
  });
}

/** Metallic coin clinks cascading */
export function playCoinShower(count = 12) {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  for (let i = 0; i < count; i++) {
    const delay = Math.random() * 0.45;
    const start = ac.currentTime + delay;
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    const filter = ac.createBiquadFilter();

    osc.type = 'square';
    // Random coin frequencies (high metallic ring)
    const baseFreq = 2200 + Math.random() * 1800;
    osc.frequency.setValueAtTime(baseFreq, start);
    osc.frequency.exponentialRampToValueAtTime(baseFreq * 0.7, start + 0.07);

    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(baseFreq, start);
    filter.Q.setValueAtTime(8, start);

    gain.gain.setValueAtTime(0.14, start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + 0.08);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(ac.destination);

    osc.start(start);
    osc.stop(start + 0.09);
  }
}

/** Heavy vault door slam with deep sub-bass impact */
export function playDoorSlam() {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  const now = ac.currentTime;

  // Sub-bass thump
  const subOsc = ac.createOscillator();
  const subGain = ac.createGain();
  subOsc.type = 'sine';
  subOsc.frequency.setValueAtTime(110, now);
  subOsc.frequency.exponentialRampToValueAtTime(28, now + 0.32);

  subGain.gain.setValueAtTime(0.7, now);
  subGain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

  subOsc.connect(subGain);
  subGain.connect(ac.destination);

  subOsc.start(now);
  subOsc.stop(now + 0.42);

  // Metallic crunch noise
  const bufferSize = ac.sampleRate * 0.15;
  const noiseBuffer = ac.createBuffer(1, bufferSize, ac.sampleRate);
  const output = noiseBuffer.getChannelData(0);
  for (let i = 0; i < bufferSize; i++) {
    output[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.2));
  }

  const whiteNoise = ac.createBufferSource();
  whiteNoise.buffer = noiseBuffer;

  const noiseFilter = ac.createBiquadFilter();
  noiseFilter.type = 'lowpass';
  noiseFilter.frequency.setValueAtTime(600, now);
  noiseFilter.frequency.exponentialRampToValueAtTime(80, now + 0.15);

  const noiseGain = ac.createGain();
  noiseGain.gain.setValueAtTime(0.4, now);
  noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);

  whiteNoise.connect(noiseFilter);
  noiseFilter.connect(noiseGain);
  noiseGain.connect(ac.destination);

  whiteNoise.start(now);
  whiteNoise.stop(now + 0.16);
}

/** Emergency bank lockdown thud & alarm buzz */
export function playLockdownAlarm() {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  const now = ac.currentTime;

  // Heavy latch
  playDoorSlam();

  // 3 quick warning beeps
  for (let i = 0; i < 3; i++) {
    const t = now + 0.18 + i * 0.14;
    const osc = ac.createOscillator();
    const gain = ac.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(880, t); // A5 alarm tone

    gain.gain.setValueAtTime(0.2, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.08);

    osc.connect(gain);
    gain.connect(ac.destination);

    osc.start(t);
    osc.stop(t + 0.09);
  }
}

/** High-tech laser shredder zaps & incinerating sparks */
export function playLaserShredder() {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  const now = ac.currentTime;

  // Modulated electric saw buzz
  const osc = ac.createOscillator();
  const lfo = ac.createOscillator();
  const lfoGain = ac.createGain();
  const gain = ac.createGain();
  const filter = ac.createBiquadFilter();

  osc.type = 'sawtooth';
  osc.frequency.setValueAtTime(240, now);

  lfo.type = 'sine';
  lfo.frequency.setValueAtTime(35, now); // 35Hz modulation

  lfoGain.gain.setValueAtTime(120, now);
  lfo.connect(lfoGain);
  lfoGain.connect(osc.frequency);

  filter.type = 'bandpass';
  filter.frequency.setValueAtTime(1400, now);
  filter.Q.setValueAtTime(3, now);

  gain.gain.setValueAtTime(0.22, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);

  osc.connect(filter);
  filter.connect(gain);
  gain.connect(ac.destination);

  osc.start(now);
  lfo.start(now);
  osc.stop(now + 0.48);
  lfo.stop(now + 0.48);
}

/** Celestial golden chime for honest $25 drop / Apple Secure Enclave Face ID */
export function playGoldenChime() {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  // Pentatonic sparkle: E5, G#5, B5, E6
  const freqs = [659.25, 830.61, 987.77, 1318.51];
  freqs.forEach((freq, idx) => {
    const start = ac.currentTime + idx * 0.07;
    const osc = ac.createOscillator();
    const gain = ac.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, start);

    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(0.22, start + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0005, start + 0.65);

    osc.connect(gain);
    gain.connect(ac.destination);

    osc.start(start);
    osc.stop(start + 0.68);
  });
}

/** Crystalline ice freeze sound */
export function playFreezeSound() {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  const now = ac.currentTime;
  const osc = ac.createOscillator();
  const gain = ac.createGain();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(1800, now);
  osc.frequency.exponentialRampToValueAtTime(3200, now + 0.25);

  gain.gain.setValueAtTime(0.15, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

  osc.connect(gain);
  gain.connect(ac.destination);

  osc.start(now);
  osc.stop(now + 0.32);
}

/** Continuous or timed dual-tone Police Siren */
export function startPoliceSiren(durationSec = 4.0) {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  stopPoliceSiren();

  const now = ac.currentTime;
  const osc = ac.createOscillator();
  const lfo = ac.createOscillator();
  const lfoGain = ac.createGain();
  const masterGain = ac.createGain();

  osc.type = 'sawtooth';
  osc.frequency.setValueAtTime(800, now); // Center frequency

  // LFO wails between ~650Hz and 1150Hz at 1.8Hz
  lfo.type = 'sine';
  lfo.frequency.setValueAtTime(1.8, now);

  lfoGain.gain.setValueAtTime(300, now);
  lfo.connect(lfoGain);
  lfoGain.connect(osc.frequency);

  masterGain.gain.setValueAtTime(0, now);
  masterGain.gain.linearRampToValueAtTime(0.18, now + 0.2);
  masterGain.gain.setValueAtTime(0.18, now + durationSec - 0.4);
  masterGain.gain.exponentialRampToValueAtTime(0.001, now + durationSec);

  osc.connect(masterGain);
  masterGain.connect(ac.destination);

  osc.start(now);
  lfo.start(now);
  osc.stop(now + durationSec);
  lfo.stop(now + durationSec);

  activeSirenOsc = osc;
  activeSirenNode = masterGain;

  setTimeout(() => {
    if (activeSirenOsc === osc) {
      activeSirenOsc = null;
      activeSirenNode = null;
    }
  }, durationSec * 1000);
}

export function stopPoliceSiren() {
  if (activeSirenOsc) {
    try {
      activeSirenOsc.stop();
    } catch {}
    activeSirenOsc = null;
    activeSirenNode = null;
  }
}

/** Mechanical camera shutter sound with realistic dual-action click-clack */
export function playCameraShutter() {
  if (muted) return;
  const ac = getContext();
  if (!ac) return;

  const now = ac.currentTime;

  // Stage 1: Quick crisp mechanical shutter click
  const osc1 = ac.createOscillator();
  const gain1 = ac.createGain();
  const filter1 = ac.createBiquadFilter();

  osc1.type = 'triangle';
  osc1.frequency.setValueAtTime(1800, now);
  osc1.frequency.exponentialRampToValueAtTime(320, now + 0.022);

  filter1.type = 'bandpass';
  filter1.frequency.setValueAtTime(2200, now);
  filter1.Q.setValueAtTime(5, now);

  gain1.gain.setValueAtTime(0.28, now);
  gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.028);

  osc1.connect(filter1);
  filter1.connect(gain1);
  gain1.connect(ac.destination);
  osc1.start(now);
  osc1.stop(now + 0.032);

  // Stage 2: Shutter curtain latch release (~42ms later)
  const t2 = now + 0.042;
  const osc2 = ac.createOscillator();
  const gain2 = ac.createGain();

  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(950, t2);
  osc2.frequency.exponentialRampToValueAtTime(140, t2 + 0.038);

  gain2.gain.setValueAtTime(0.22, t2);
  gain2.gain.exponentialRampToValueAtTime(0.001, t2 + 0.045);

  osc2.connect(gain2);
  gain2.connect(ac.destination);
  osc2.start(t2);
  osc2.stop(t2 + 0.05);
}
