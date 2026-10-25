import React, { Suspense, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Canvas } from "@react-three/fiber";
import { useProgress } from "@react-three/drei";
import { ACESFilmicToneMapping } from "three";
import { Bank } from "./scene/Bank";
import { useGame } from "./game/store";
import { skipHeist } from "./game/director";
import { connectRoomWebSocket } from "./net/client";
import { ChatBox } from "./ui/ChatBox";
import { VaultCards } from "./ui/VaultCards";
import { Scoreboard } from "./ui/Scoreboard";
import { Subtitles } from "./ui/Subtitles";
import { ConsentModal } from "./ui/ConsentModal";
import { WantedCard } from "./ui/WantedCard";
import "./style.css";

function CameraFeed() {
  const stream = useGame((s) => s.cameraStream);
  const videoRef = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(() => {});
    }
  }, [stream]);

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 320;
    canvas.height = videoRef.current.videoHeight || 240;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
      useGame.setState({ capturedPhoto: dataUrl, posterUrl: dataUrl });
    }
  };

  return (
    <div className="camera-feed-pip">
      <div className="camera-feed-header">
        <span><span className="live-dot" /> LIVE CAM 01 // OPERATOR</span>
        <button className="snap-btn" onClick={capturePhoto} title="Capture Wanted Photo">
          📸 SNAP
        </button>
      </div>
      <video ref={videoRef} autoPlay playsInline muted />
    </div>
  );
}
class Boundary extends React.Component<
  React.PropsWithChildren,
  { error: string }
> {
  state = { error: "" };
  static getDerivedStateFromError(error: Error) {
    return { error: error.message };
  }
  render() {
    return this.state.error ? (
      <div className="fatal">
        Asset contract failure: {this.state.error}
        <p>Check the console and assets3d load test.</p>
      </div>
    ) : (
      this.props.children
    );
  }
}
function App() {
  const ready = useGame((s) => s.ready),
    mock = useGame((s) => s.mock),
    camera = useGame((s) => s.camera),
    stage = useGame((s) => s.stage),
    error = useGame((s) => s.error),
    cameraEnabled = useGame((s) => s.cameraEnabled);
  const phase = useGame((s) => s.phase);
  const [consent, setConsent] = useState(false);
  const { progress } = useProgress();

  useEffect(() => {
    if (mock) return;
    const disconnect = connectRoomWebSocket();
    return () => disconnect();
  }, [mock]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        e.key.toLowerCase() !== "m" ||
        e.repeat ||
        e.ctrlKey ||
        e.metaKey ||
        e.altKey ||
        (e.target instanceof HTMLElement &&
          (e.target.matches("input,textarea") || e.target.isContentEditable))
      )
        return;
      if (useGame.getState().phase === "RESOLVE") return;
      useGame.setState((s) => ({ mock: !s.mock, error: "" }));
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  return (
    <Boundary>
      <main>
        <header>
          <a className="brand" href="/" aria-label="HeistBox home">
            H<span>×</span>P
          </a>
          <div>
            <b>
              HEISTBOX <span>× PAIR</span>
            </b>
            <small>THE ADVERSARIAL BANKING EXPERIMENT</small>
          </div>
          <div className="status">
            ● {mock ? "MOCK · OFFLINE READY" : "LIVE · CONNECTED"}
          </div>
        </header>
        <section className="intro">
          <div>
            <p className="eyebrow">ONE PROMPT. THREE LINES OF DEFENSE.</p>
            <h1>Rob our AI bank.</h1>
            <p>Talk your way past Tina. See which vault holds.</p>
          </div>
          <button
            className={`privacy ${cameraEnabled ? "active" : ""}`}
            onClick={() => setConsent(true)}
          >
            {cameraEnabled ? "● Camera on · Live active" : "◎ Camera off · your choice"}
          </button>
        </section>
        <div className="arena">
          <Canvas
            dpr={[1, 1.5]}
            camera={{ position: [0, 3.2, 5.6], fov: 50, near: 0.05, far: 100 }}
            gl={{
              antialias: true,
              toneMapping: ACESFilmicToneMapping,
              toneMappingExposure: 1.15,
            }}
          >
            <Suspense fallback={null}>
              <Bank />
            </Suspense>
          </Canvas>
          {cameraEnabled && <CameraFeed />}
          <div className="scene-label">
            LIVE BANK FLOOR{" "}
            <span>
              {camera.replace("CAM_", "").toUpperCase()} / {stage.toUpperCase()}
            </span>
          </div>
          <Subtitles />
          <WantedCard />
          {phase === "RESOLVE" && (
            <button className="scene-skip" onClick={skipHeist}>
              Skip sequence →
            </button>
          )}
          {["refund", "faceid", "settlement"].includes(stage) && (
            <div className="story-card">
                  <small>HONEST CUSTOMER / $25 REFUND</small>
                  <b>
                    {stage === "faceid"
                      ? "◎ Verifying identity…"
                      : stage === "settlement"
                        ? "✓ Refund approved"
                        : "Entitlement matched"}
                  </b>
                  <span>SIMULATED · no passkey or payment submitted</span>
            </div>
          )}
        </div>
        <VaultCards />
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        <Scoreboard />
        <ChatBox />
        <footer>
          <span>HEISTBOX × PAIR / CAL HACKS</span>
          <span>
            MOCK CHECKPOINT · All amounts and timings are scripted. No funds
            move.
          </span>
        </footer>
        {!ready && (
          <div className="loading">
            <b>Opening the bank</b>
            <progress value={progress} max={100} />
            <span>{Math.round(progress)}% · decoding six GLBs</span>
          </div>
        )}
        {consent && <ConsentModal close={() => setConsent(false)} />}
      </main>
    </Boundary>
  );
}
document.title = "HeistBox × PAIR — Rob Our AI Bank";
createRoot(document.getElementById("root")!).render(<App />);
