import { useEffect, useRef, useState } from "react";
import { useGame, startCamera, stopCamera } from "../game/store";

export function ConsentModal({ close }: { close: () => void }) {
  const button = useRef<HTMLButtonElement>(null);
  const cameraEnabled = useGame((s) => s.cameraEnabled);
  const [error, setError] = useState("");

  useEffect(() => {
    button.current?.focus();
  }, []);

  const handleToggle = async () => {
    setError("");
    if (cameraEnabled) {
      stopCamera();
    } else {
      try {
        await startCamera();
        close();
      } catch (err) {
        setError("Webcam permission denied or no camera device found.");
      }
    }
  };

  return (
    <div
      className="modal-backdrop"
      onKeyDown={(e) => {
        if (e.key === "Escape") close();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="consent-title"
        className="consent"
      >
        <p className="eyebrow">YOUR FACE. YOUR CHOICE.</p>
        <h2 id="consent-title">A heist without a camera.</h2>
        <p>
          You have full control over camera capture. By default, no webcam
          permission or image is requested, preserving complete privacy with
          an anonymous wanted poster.
        </p>
        <p>
          Opting in enables live video monitoring inside the bank arena and
          captures your operator snapshot for the wanted poster.
        </p>
        {error && <p className="camera-err">{error}</p>}
        <div className="consent-actions">
          <button ref={button} onClick={close}>
            Continue without camera
          </button>
          <button className="camera-toggle-btn" onClick={handleToggle}>
            {cameraEnabled ? "Turn camera off" : "● Turn camera on (Live Video)"}
          </button>
        </div>
      </section>
    </div>
  );
}
