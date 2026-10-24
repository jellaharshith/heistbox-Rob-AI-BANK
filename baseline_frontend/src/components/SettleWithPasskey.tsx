"use client";
import { ExternalLink, Fingerprint } from "lucide-react";
import { useEffect, useState } from "react";
import { registerPasskeyOnServer, settleGreenHalf, verifyPasskeyOnServer, type SettleContext } from "@/lib/api";
import { approveWithPasskey, forgetStoredPasskey, hasStoredPasskey, intentChallengeB64url, type PasskeyOutcome } from "@/lib/enclave";
import { usd } from "@/lib/format";
import { chime } from "@/lib/sound";
import type { X402Outcome } from "@/lib/types";

type Step = { passkey: PasskeyOutcome; server: Awaited<ReturnType<typeof verifyPasskeyOnServer>> | null; x402: X402Outcome | null; skipped?: string };

/**
 * Passkey (navigator.credentials.create once → POST /webauthn/register; then navigator.credentials.get) →
 * POST /api/integrations/webauthn/verify (py_webauthn signature check) → POST /api/integrations/x402-settle.
 * Each line shows what that step actually returned; x402 only runs after the server verifies the signature.
 */
export function SettleWithPasskey({ ctx, tone = "dark", onDone }: { ctx: SettleContext; tone?: "dark" | "paper"; onDone?: (us: number) => void }) {
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState<Step | null>(null);
  const [registered, setRegistered] = useState(false);

  useEffect(() => setRegistered(hasStoredPasskey()), []);

  const stop = (s: Step) => {
    setStep(s);
    setBusy(false);
  };

  const go = async () => {
    if (!ctx.settlement_hash) return;
    setBusy(true);
    const challenge = intentChallengeB64url(ctx.settlement_hash);
    const passkey = await approveWithPasskey(ctx.settlement_hash);
    if (!passkey.ok || !passkey.credential_id || !passkey.assertion) return stop({ passkey, server: null, x402: null });

    if (passkey.mode === "webauthn-create") {
      // A registration carries no signature over the intent, so it is not an approval.
      const reg = await registerPasskeyOnServer(challenge, passkey.credential_id, passkey.assertion);
      if (!reg.registered) {
        forgetStoredPasskey();
        setRegistered(false);
        return stop({ passkey, server: null, x402: null, skipped: `Server rejected the registration: ${reg.reason || `HTTP ${reg.status || "unreachable"}`}` });
      }
      setRegistered(true);
      return stop({ passkey, server: null, x402: null, skipped: `Passkey registered and verified by the server. Tap again to sign ${usd(ctx.green_cents)} to ${ctx.recipient.slice(0, 10)}….` });
    }

    const server = await verifyPasskeyOnServer(challenge, passkey.credential_id, passkey.assertion);
    if (!server.verified) {
      if (server.reason.startsWith("unknown_credential")) {
        forgetStoredPasskey();
        setRegistered(false);
      }
      return stop({ passkey, server, x402: null, skipped: "x402 not attempted: the server did not verify the passkey signature." });
    }
    const x402 = await settleGreenHalf(ctx);
    stop({ passkey, server, x402 });
    chime();
    onDone?.(Math.round(passkey.ms * 1000));
  };

  const paper = tone === "paper";
  const box = paper ? "border-2 border-[#2a1a08] text-[#2a1a08]" : "border border-white/10 bg-black/40 text-white/80";
  const link = paper ? "text-[#7a1010]" : "text-cyan-300";
  const dim = paper ? "opacity-70" : "text-white/50";

  return (
    <div className="space-y-2 text-xs">
      {!ctx.settlement_hash && (
        <div className={`text-[10px] ${dim}`}>No kernel-issued settlement for this verdict (local twin or nothing to refund), so there is nothing to sign.</div>
      )}
      <button
        disabled={busy || !ctx.settlement_hash}
        onClick={go}
        className={`flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-bold disabled:opacity-50 ${paper ? "bg-[#7a1010] text-[#f3e2b8]" : "bg-white/10 hover:bg-white/20"}`}
      >
        <Fingerprint className="h-4 w-4" />
        {busy ? "Waiting for Face ID…" : registered ? `Settle ${usd(ctx.green_cents)} green half with Face ID` : "Settle with Face ID (register this device)"}
      </button>
      {step && (
        <div className={`space-y-1 rounded-md p-2 text-left ${box}`}>
          <div>
            <b>1 · Passkey:</b>{" "}
            {step.passkey.ok
              ? `${step.passkey.mode === "webauthn-create" ? "registered (navigator.credentials.create)" : "signed (navigator.credentials.get)"} in ${Math.round(step.passkey.ms)}ms`
              : `${step.passkey.mode} — ${step.passkey.error ?? "no signature"}`}
          </div>
          {step.passkey.mode === "webauthn-get" && step.passkey.ok && (
            <div className={`text-[10px] ${dim}`}>
              1b · Browser pre-check: {step.passkey.browser_signature_valid === true ? "valid" : step.passkey.browser_signature_valid === false ? "INVALID" : "not checked"} — {step.passkey.browser_check_note}
            </div>
          )}
          {step.server && (
            <div>
              <b>2 · Server /webauthn/verify (py_webauthn):</b>{" "}
              {step.server.status === 200
                ? step.server.verified
                  ? `signature verified (${step.server.mode})`
                  : `rejected — ${step.server.reason || step.server.mode}`
                : `HTTP ${step.server.status || "unreachable"}`}
            </div>
          )}
          {step.skipped && <div className="font-bold">{step.skipped}</div>}
          {step.x402 && (
            <div>
              <b>3 · x402-settle {usd(ctx.green_cents + 1)} (HTTP {step.x402.status || "—"}):</b>{" "}
              {step.x402.kind === "broadcast" && "broadcast to Base Sepolia"}
              {step.x402.kind === "signed" && `EIP-3009 authorization signed, not broadcast${step.x402.reason ? ` (${step.x402.reason})` : ""}`}
              {step.x402.kind === "challenge" && "402 Payment Required challenge — the server has no X402_SIGNER_PRIVATE_KEY, so nothing was signed or paid"}
              {step.x402.kind === "error" && `failed${step.x402.reason ? ` — ${step.x402.reason}` : ""}`}
              {step.x402.kind === "unreachable" && "integrations server unreachable"}
              {step.x402.testnet_scale !== null && step.x402.testnet_scale < 1 && step.x402.onchain_usdc !== null && (
                <div className={`text-[10px] ${dim}`}>
                  Testnet scale ×{step.x402.testnet_scale}: on-chain transfer is {step.x402.onchain_usdc} test USDC for the {usd(ctx.green_cents + 1)} settlement.
                </div>
              )}
              {step.x402.nonce && <div className="break-all font-mono-tight text-[10px] opacity-80">marked-bill nonce {step.x402.nonce}</div>}
              {step.x402.tx_hash && <div className="break-all font-mono-tight text-[10px] opacity-80">receipt tx {step.x402.tx_hash}</div>}
              {step.x402.kind !== "broadcast" && <div className={`text-[10px] ${dim}`}>No BaseScan tx link: nothing was broadcast on-chain for this settlement.</div>}
              <div className="flex flex-wrap gap-3">
                {step.x402.tx_url && (
                  <a href={step.x402.tx_url} target="_blank" rel="noreferrer" className={`inline-flex items-center gap-1 font-bold underline ${link}`}>
                    BaseScan tx (chain 84532) <ExternalLink className="h-3 w-3" />
                  </a>
                )}
                {step.x402.block_url && (
                  <a href={step.x402.block_url} target="_blank" rel="noreferrer" className={`inline-flex items-center gap-1 underline ${link}`}>
                    anchor block #{step.x402.block} <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
