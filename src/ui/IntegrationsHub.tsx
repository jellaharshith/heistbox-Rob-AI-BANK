import React, { useEffect, useState } from "react";
import {
  fetchIntegrationsStatus,
  type IntegrationsStatusResponse,
} from "../net/client";

export function IntegrationsHub() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<IntegrationsStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetchIntegrationsStatus();
      setData(res);
    } catch (e) {
      console.warn("Integrations status offline", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadStatus();
    }
  }, [open]);

  const providers = data?.providers || {};
  const services = data?.services || {};

  const keySponsors = [
    { key: "wajo", name: "Wajo AI", role: "CFO Voice Escalation" },
    { key: "x402", name: "Coinbase / x402", role: "Base Sepolia Escrow" },
    { key: "apify", name: "Apify", role: "OSINT Fraud Recon" },
    { key: "cartesia", name: "Cartesia", role: "Neural Voice TTS" },
    { key: "claude", name: "Anthropic Claude", role: "Reasoning & Roast" },
    { key: "cloud_vision", name: "Google Cloud Vision", role: "Mugshot OCR" },
  ];

  return (
    <>
      <div className="integrations-pill-bar">
        <button
          className="integrations-hub-btn"
          onClick={() => {
            setOpen(true);
            loadStatus();
          }}
          title="Open Live Sponsor Integrations Hub"
        >
          <span className="hub-dot" />
          <b>INTEGRATIONS</b>
          <span className="hub-count">
            {Object.keys(providers).length > 0
              ? `${Object.values(providers).filter((v) => v === "LIVE" || v === "LOCAL").length}/${Object.keys(providers).length} LIVE`
              : "WAJO · COINBASE · APIFY · FASTAPI"}
          </span>
        </button>
      </div>

      {open && (
        <div className="modal-backdrop" onClick={() => setOpen(false)}>
          <div
            className="integrations-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="integrations-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="eyebrow">AUTHENTICATED SECOPS ARCHITECTURE</span>
                <h2 id="integrations-title">Live Sponsor & API Registry</h2>
              </div>
              <button className="close-btn" onClick={() => setOpen(false)}>
                ✕
              </button>
            </div>

            <p className="modal-intro">
              HeistBox integrates live sponsor APIs with strict deterministic fallbacks.
              Probes are read-only and audited live across all 18 endpoints.
            </p>

            <div className="sponsor-grid">
              {keySponsors.map(({ key, name, role }) => {
                const prov = providers[key] || "FALLBACK_READY";
                const svc = services[key];
                const isLive = prov === "LIVE" || prov === "LOCAL";
                return (
                  <div key={key} className={`sponsor-card ${isLive ? "live" : "fallback"}`}>
                    <div className="card-top">
                      <b>{name}</b>
                      <span className={`status-badge ${prov.toLowerCase()}`}>
                        {prov}
                      </span>
                    </div>
                    <small className="card-role">{role}</small>
                    <div className="card-meta">
                      <span>Latency: {svc?.latency_ms ? `${svc.latency_ms.toFixed(0)} ms` : "in-process"}</span>
                      <span className="card-fallback">Fallback: {svc?.fallback || "local rule"}</span>
                    </div>
                    {svc?.detail && <p className="card-detail">{svc.detail}</p>}
                  </div>
                );
              })}
            </div>

            <div className="modal-footer">
              <button className="btn-refresh" onClick={loadStatus} disabled={loading}>
                {loading ? "Probing APIs…" : "↻ Refresh Live Probes"}
              </button>
              <button className="btn-close" onClick={() => setOpen(false)}>
                Close Hub
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
