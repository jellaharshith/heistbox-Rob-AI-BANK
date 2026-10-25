import React, { useEffect, useState } from "react";
import {
  fetchIntegrationsStatus,
  triggerWajoAudit,
  triggerX402Settle,
  triggerApifyOsint,
  fetchFetchAiEscrow,
  fetchAtlassianIncidents,
  type IntegrationsStatusResponse,
} from "../net/client";

export function IntegrationsHub() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<IntegrationsStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionOutput, setActionOutput] = useState<string>("");
  const [actionRunning, setActionRunning] = useState<boolean>(false);

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

  const runTest = async (name: string, fn: () => Promise<any>) => {
    setActionRunning(true);
    setActionOutput(`Testing live connection to ${name}…`);
    try {
      const res = await fn();
      setActionOutput(`✓ ${name} responded successfully:\n` + JSON.stringify(res, null, 2));
    } catch (err) {
      setActionOutput(`✕ ${name} response: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setActionRunning(false);
    }
  };

  const providers = data?.providers || {};
  const services = data?.services || {};

  const keySponsors = [
    { key: "wajo", name: "Wajo AI", role: "CFO Voice Escalation" },
    { key: "x402", name: "Coinbase CDP / x402", role: "Base Sepolia Escrow" },
    { key: "apify", name: "Apify", role: "OSINT Fraud Recon" },
    { key: "cartesia", name: "Cartesia", role: "Sonic Neural TTS" },
    { key: "claude", name: "Anthropic Claude", role: "Adversarial Reasoning & Roast" },
    { key: "cloud_vision", name: "Google Cloud Vision", role: "Mugshot OCR & Disguise" },
    { key: "fetchai", name: "Fetch.ai", role: "Autonomous Escrow Guardian" },
    { key: "atlassian", name: "Atlassian", role: "Jira / Confluence Incident Bridge" },
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
              ? `${Object.keys(providers).filter((k) => providers[k] === "LIVE" || providers[k] === "LOCAL" || services[k]?.code === "LOCAL" || services[k]?.state === "local").length}/${Object.keys(providers).length} LIVE`
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
              Probes are read-only and audited live across all endpoints.
            </p>

            <div className="sponsor-grid">
              {keySponsors.map(({ key, name, role }) => {
                const prov = providers[key] || "FALLBACK_READY";
                const svc = services[key];
                const isLive = prov === "LIVE" || prov === "LOCAL" || svc?.code === "LOCAL" || svc?.state === "local";
                const displayState = svc?.code === "LOCAL" ? "LOCAL" : prov;
                return (
                  <div key={key} className={`sponsor-card ${isLive ? "live" : "fallback"}`}>
                    <div className="card-top">
                      <b>{name}</b>
                      <span className={`status-badge ${displayState.toLowerCase()}`}>
                        {displayState}
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

            <div className="interactive-tests">
              <span className="eyebrow">INTERACTIVE SPONSOR TEST HARNESS</span>
              <div className="test-buttons">
                <button
                  type="button"
                  className="test-btn"
                  disabled={actionRunning}
                  onClick={() => runTest("Wajo CFO Audit", triggerWajoAudit)}
                >
                  ⚡ Wajo Voice Audit
                </button>
                <button
                  type="button"
                  className="test-btn"
                  disabled={actionRunning}
                  onClick={() =>
                    runTest("Coinbase x402 Escrow", () =>
                      triggerX402Settle(2500, "0x0000000000000000000000000000000000000000")
                    )
                  }
                >
                  ⚡ Coinbase / x402 Base Escrow
                </button>
                <button
                  type="button"
                  className="test-btn"
                  disabled={actionRunning}
                  onClick={() =>
                    runTest("Apify OSINT", () =>
                      triggerApifyOsint("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
                    )
                  }
                >
                  ⚡ Apify OSINT Recon
                </button>
                <button
                  type="button"
                  className="test-btn"
                  disabled={actionRunning}
                  onClick={() => runTest("Fetch.ai Escrow Guardian", fetchFetchAiEscrow)}
                >
                  ⚡ Fetch.ai Guardian
                </button>
                <button
                  type="button"
                  className="test-btn"
                  disabled={actionRunning}
                  onClick={() => runTest("Atlassian Incidents", fetchAtlassianIncidents)}
                >
                  ⚡ Atlassian Jira / Confluence
                </button>
              </div>

              {actionOutput && (
                <pre className="test-console">{actionOutput}</pre>
              )}
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
