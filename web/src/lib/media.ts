"use client";
import { useCallback, useEffect, useRef, useState } from "react";

export type CamStatus = "off" | "live" | "denied";

/** Webcam for the mugshot. `attach` is a callback ref so the <video> can remount (view toggles) without losing the stream. */
export function useWebcam() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [status, setStatus] = useState<CamStatus>("off");

  const attach = useCallback((el: HTMLVideoElement | null) => {
    videoRef.current = el;
    if (el && streamRef.current && el.srcObject !== streamRef.current) {
      el.srcObject = streamRef.current;
      el.play().catch(() => {});
    }
  }, []);

  const start = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
      streamRef.current = s;
      attach(videoRef.current);
      setStatus("live");
    } catch {
      setStatus("denied");
    }
  }, [attach]);

  /**
   * Grab the current webcam frame as a JPEG data URL, or null when the camera isn't live.
   * Never substitutes a drawing: a poster without a real frame says so instead.
   */
  const freeze = useCallback((): string | null => {
    const v = videoRef.current;
    if (!v || !streamRef.current || v.videoWidth === 0) return null;
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight || 480;
    const g = c.getContext("2d");
    if (!g) return null;
    // Colour frame: Cloud Vision reads props/clothing better in colour; the poster applies its own B&W filter.
    g.drawImage(v, 0, 0);
    return c.toDataURL("image/jpeg", 0.85);
  }, []);

  useEffect(() => () => streamRef.current?.getTracks().forEach((t) => t.stop()), []);

  return { attach, start, freeze, status };
}

interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

type SpeechCtor = new () => SpeechRecognitionLike;

/** WebSpeech mic. `supported` is false on browsers without SpeechRecognition — the UI then falls back to typing. */
export function useSpeech(onFinal: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [supported, setSupported] = useState(false);
  const recRef = useRef<SpeechRecognitionLike | null>(null);
  const cbRef = useRef(onFinal);
  cbRef.current = onFinal;

  useEffect(() => {
    const w = window as unknown as { SpeechRecognition?: SpeechCtor; webkitSpeechRecognition?: SpeechCtor };
    setSupported(Boolean(w.SpeechRecognition ?? w.webkitSpeechRecognition));
  }, []);

  const toggle = useCallback(() => {
    if (recRef.current) {
      recRef.current.stop();
      return;
    }
    const w = window as unknown as { SpeechRecognition?: SpeechCtor; webkitSpeechRecognition?: SpeechCtor };
    const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    let finalText = "";
    rec.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      finalText = text;
      setInterim(text);
    };
    rec.onerror = () => {};
    rec.onend = () => {
      recRef.current = null;
      setListening(false);
      setInterim("");
      if (finalText.trim()) cbRef.current(finalText.trim());
    };
    recRef.current = rec;
    setListening(true);
    rec.start();
  }, []);

  return { listening, interim, supported, toggle };
}
