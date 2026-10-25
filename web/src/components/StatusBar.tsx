"use client";
import { AnimatePresence, motion } from "framer-motion";
import { KeyRound, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ALLOWED_KEY_NAMES, configureKeys, getIntegrationStatus, getWajoAudit, getWajoStatus, type WajoAuditEntry, type WajoStatus } from "@/lib/api";
import type { IntegrationState } from "@/lib/types";

/** Required badges → the provider name GET /api/integrations/status actually returns (null = it doesn't report one). */
const PILLS: { label: string; provider: string | null; why?: string }[] = [
  { label: "Anthropic", provider: "anthropic" },
  { label: "Cloud Vision", provider: "cloud_vision" },
  { label: "Cartesia", provider: "cartesia" },
  { label: "CRS Sandbox", provider: "crs" },
  { label: "Base Sepolia x402", provider: "x402" },
  { label: "Fetch.ai Escrow", provider: "fetchai" },
  { label: "Wajo Voice Alert", provider: "wajo" },
  { label: "MCP Server", provider: null, why: "/api/integrations/status has no MCP entry" },
  { label: "Postgres", provider: null, why: "/api/integrations/status has no Postgres entry (kernel/db_gate.py uses sqlite3)" },
];

const ENV_PROVIDER: Record<string, string> = {
  ANTHROPIC_API_KEY: "anthropic",
  GEMINI_API_KEY: "cloud_vision",
  GOOGLE_CLOUD_VISION_API_KEY: "cloud_vision",
  CARTESIA_API_KEY: "cartesia",
  CRS_API_KEY: "crs",
  BRIGHTDATA_API_KEY: "brightdata",
  APIFY_API_TOKEN: "apify",
  X402_SIGNER_PRIVATE_KEY: "x402",
  BASE_SEPOLIA_RPC_URL: "x402",
  WAJO_API_KEY: "wajo",
  wajo_api_key: "wajo",
  FETCHAI_API_KEY: "fetchai",
};

const STYLE: Record<IntegrationState["state"], { cls: string; dot: string; text: string }> = {
  VERIFIED_LIVE: { cls: "border-emerald-400/40 bg-emerald-500/10 text-emerald-200", dot: "bg-emerald-400", text: "live" },
  MISSING_KEY: { cls: "border-amber-400/30 bg-amber-500/10 text-amber-200", dot: "bg-amber-400", text: "missing key" },
  AUTH_ERROR: { cls: "border-red-400/40 bg-red-500/10 text-red-200", dot: "bg-red-500", text: "auth error" },
  QUOTA_EXCEEDED: { cls: "border-red-400/40 bg-red-500/10 text-red-200", dot: "bg-red-500", text: "quota exceeded" },
  UNREACHABLE: { cls: "border-red-400/40 bg-red-500/10 text-red-200", dot: "bg-red-500", text: "unreachable" },
  UNVERIFIED: { cls: "border-amber-400/30 bg-amber-500/10 text-amber-200", dot: "bg-amber-400", text: "reachable, key unchecked" },
  UNKNOWN: { cls: "border-white/15 bg-white/5 text-white/50", dot: "bg-white/40", text: "not reported" },
};

function Pill({ label, st }: { label: string; st: IntegrationState }) {
  const sty = STYLE[st.state];
  return (
    <span className={`flex items-center gap-1 rounded-full border px-2 py-0.5 ${sty.cls}`} title={`${st.state}${st.latency_ms ? ` · ${st.latency_ms}ms` : ""}${st.detail ? ` — ${st.detail}` : ""}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${sty.dot}`} />
      {label} <span className="opacity-60">{sty.text}</span>
    </span>
  );
}

export function StatusBar({
  gateLive,
  busted,
  challenge,
  cents = 2500,
}: {
  gateLive: boolean;
  busted?: boolean;
  challenge?: string;
  cents?: number;
}) {
  const [items, setItems] = useState<IntegrationState[]>([]);
  const [origin, setOrigin] = useState<string>("loading");
  const [httpStatus, setHttpStatus] = useState(0);
  const [open, setOpen] = useState(false);
  const [checking, setChecking] = useState(false);
  const [wajo, setWajo] = useState<WajoStatus | null>(null);
  const [wajoAudit, setWajoAudit] = useState<WajoAuditEntry[]>([]);

  const refresh = useCallback(async () => {
    setChecking(true);
    const [r, wajoStatus, audit] = await Promise.all([getIntegrationStatus(), getWajoStatus(busted === true), getWajoAudit()]);
    setItems(r.items);
    setOrigin(r.origin);
    setHttpStatus(r.httpStatus);
    setWajo(wajoStatus);
    setWajoAudit(audit);
    setChecking(false);
  }, []);

  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, 30000);
    return () => window.clearInterval(t);
  }, [refresh, busted]);

  const lookup = (p: (typeof PILLS)[number]): IntegrationState => {
    if (!p.provider) return { provider: p.label, state: "UNKNOWN", latency_ms: 0, detail: p.why ?? "not reported" };
    return items.find((i) => i.provider === p.provider) ?? { provider: p.provider, state: "UNKNOWN", latency_ms: 0, detail: origin === "loading" ? "checking…" : `not in /${origin}` };
  };
  const known = new Set(PILLS.map((p) => p.provider).filter(Boolean));
  const extras = items.filter((i) => !known.has(i.provider));
  const missing = items.some((i) => i.state === "MISSING_KEY");
  const wajoTone = wajo?.state === "live" ? "text-emerald-200" : wajo?.state === "dry_run" ? "text-amber-200" : "text-red-200";

  // `challenge` is the kernel's settlement hash; the settle page reads amount and recipient from the server.
  const settleHref = challenge ? `/settle?settlement=${encodeURIComponent(challenge)}` : null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-40 border-t border-white/10 bg-black/85 backdrop-blur-md shadow-[0_-4px_25px_rgba(0,0,0,0.6)]">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-1.5 px-4 py-1.5 text-[10px]">
        <span className="mr-1 font-bold uppercase tracking-wider text-white/40">sponsor status</span>
        {PILLS.map((p) => (
          <Pill key={p.label} label={p.label} st={lookup(p)} />
        ))}
        {extras.map((i) => (
          <Pill key={i.provider} label={i.provider} st={i} />
        ))}
        <Pill
          label="Kernel gate (SQLite)"
          st={{ provider: "kernel", state: gateLive ? "VERIFIED_LIVE" : "UNKNOWN", latency_ms: 0, detail: gateLive ? "GET /api/kernel/vault-state answered" : "kernel has not answered yet" }}
        />
        {wajo && (
          <span
            className={`rounded-full border border-fuchsia-400/30 bg-fuchsia-500/10 px-2 py-0.5 ${wajoTone}`}
            title={`${wajo.detail}${wajo.last_response_summary ? ` — ${wajo.last_response_summary}` : ""}`}
          >
            Wajo workflow: <b>{wajo.state}</b>{wajo.last_outcome ? ` · ${wajo.last_outcome}` : ""} · {wajoAudit.length} alert{wajoAudit.length === 1 ? "" : "s"}
          </span>
        )}
        <button onClick={refresh} disabled={checking} className="flex items-center gap-1 text-white/40 hover:text-white disabled:opacity-40" title="Re-check /api/integrations/status">
          <RefreshCw className={`h-3 w-3 ${checking ? "animate-spin" : ""}`} />
        </button>

        {/* Pulsing indicator when heist is busted (Requirement 2b) */}
        {busted && settleHref && (
          <a
            href={settleHref}
            target="_blank"
            rel="noreferrer"
            className="flex animate-pulse items-center gap-1.5 rounded-full border border-yellow-400/70 bg-yellow-400/20 px-3 py-0.5 font-bold text-yellow-300 shadow-[0_0_12px_rgba(250,204,21,0.4)] hover:bg-yellow-400/30 transition-colors"
            title="Click to open remote CFO Face ID settlement page"
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-yellow-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-yellow-500"></span>
            </span>
            <span>📞 Wajo.ai calling CFO... | 🤖 Fetch.ai holding escrow</span>
            <span className="underline ml-0.5 text-white/90">Authorize ↗</span>
          </a>
        )}

        {origin === "unreachable" && <span className="text-red-300">integrations status not available (HTTP {httpStatus || "network error"})</span>}
        {origin === "health-provenance" && <span className="text-amber-300">derived from /health-provenance (/status HTTP {httpStatus})</span>}
        {missing && (
          <button onClick={() => setOpen(true)} className="ml-auto flex animate-pulse items-center gap-1 rounded-full bg-yellow-400 px-2.5 py-0.5 font-bold text-black">
            <KeyRound className="h-3 w-3" /> 🔑 Connect Live Sponsor Keys
          </button>
        )}
      </div>
      <AnimatePresence>
        {open && (
          <KeyModal
            items={items}
            onClose={() => setOpen(false)}
            onSaved={(next) => {
              if (next) setItems(next);
              return refresh();
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function KeyModal({ items, onClose, onSaved }: { items: IntegrationState[]; onClose: () => void; onSaved: (next: IntegrationState[] | null) => Promise<void> }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string; result?: IntegrationState[] | null } | null>(null);
  const [isLocal, setIsLocal] = useState(true);

  useEffect(() => {
    setIsLocal(["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname));
  }, []);

  const save = async () => {
    const keys = Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim()));
    if (!Object.keys(keys).length) return;
    setSaving(true);
    const r = await configureKeys(keys);
    setSaving(false);
    if (r.ok) {
      setValues({});
      setMsg({ ok: true, text: `Server accepted ${Object.keys(keys).length} key(s) and re-probed providers (HTTP 200):`, result: r.items });
      await onSaved(r.items);
    } else {
      setMsg({
        ok: false,
        text:
          r.status === 403
            ? `Refused (HTTP 403): keys can only be set from the host machine, not through a tunnel. ${r.detail}`
            : r.status === 404
              ? "Not available (HTTP 404): the integrations server has no /configure-keys route."
              : `Failed (HTTP ${r.status || "network error"}). ${r.detail}`,
      });
    }
  };

  return (
    <motion.div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.div
        initial={{ scale: 0.95, y: 10 }}
        animate={{ scale: 1, y: 0 }}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/15 bg-[#0d0a14] p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-2xl neon-gold">🔑 Connect Live Sponsor Keys</h2>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="mb-3 text-xs text-white/60">
          Keys go to the HeistBox server&apos;s <code>.env</code> via POST /api/integrations/configure-keys and are never stored in the browser. Empty fields are left unchanged. Only the names the server allow-lists are offered.
        </p>
        {!isLocal && (
          <p className="mb-3 rounded-lg bg-red-500/15 p-2 text-xs text-red-200">You&apos;re on a tunnel URL. The web server refuses key writes unless the request comes from the host machine (http://localhost:3000).</p>
        )}
        <div className="space-y-2">
          {ALLOWED_KEY_NAMES.map((env) => {
            const prov = ENV_PROVIDER[env];
            const st = prov ? items.find((i) => i.provider === prov)?.state ?? "UNKNOWN" : null;
            return (
              <label key={env} className="block text-xs">
                <span className="flex items-center justify-between text-white/70">
                  <code>{env}</code>
                  {st ? (
                    <span className={`rounded px-1.5 text-[9px] font-bold ${STYLE[st].cls}`}>
                      {prov} · {STYLE[st].text}
                    </span>
                  ) : (
                    <span className="text-[9px] text-white/30">status not reported</span>
                  )}
                </span>
                <input
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  placeholder={env === "BASE_SEPOLIA_RPC_URL" ? "https://sepolia.base.org" : env === "X402_SIGNER_PRIVATE_KEY" ? "0x… (testnet key only)" : env}
                  value={values[env] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [env]: e.target.value }))}
                  className="mt-0.5 w-full rounded-md border border-white/15 bg-black/60 px-2 py-1.5 font-mono-tight text-xs text-white outline-none focus:border-yellow-400"
                />
              </label>
            );
          })}
        </div>
        {msg && (
          <div className={`mt-3 rounded-lg p-2 text-xs ${msg.ok ? "bg-emerald-500/15 text-emerald-200" : "bg-red-500/15 text-red-200"}`}>
            {msg.text}
            {msg.result && (
              <ul className="mt-1 font-mono-tight text-[10px]">
                {msg.result.map((i) => (
                  <li key={i.provider}>
                    {i.provider}: {i.state}
                    {i.detail ? ` — ${i.detail.slice(0, 120)}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-white/60 hover:text-white">
            Close
          </button>
          <button disabled={saving || !isLocal} onClick={save} className="rounded-lg bg-yellow-400 px-4 py-1.5 text-sm font-bold text-black disabled:opacity-40">
            {saving ? "Saving & re-probing…" : "Save & verify"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
