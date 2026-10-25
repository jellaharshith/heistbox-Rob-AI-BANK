import { useEffect, useRef } from "react";
export function ConsentModal({ close }: { close: () => void }) {
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    button.current?.focus();
  }, []);
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
          This playable checkpoint uses an anonymous wanted poster. Camera
          capture is not connected yet; no webcam permission or image is
          requested.
        </p>
        <p>
          The later opt-in flow will ask before capture, show a camera-on
          indicator, and send one frame only.
        </p>
        <button ref={button} onClick={close}>
          Continue without camera
        </button>
      </section>
    </div>
  );
}
