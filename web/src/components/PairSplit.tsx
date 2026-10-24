"use client";
import { motion } from "framer-motion";
import { KeyRound } from "lucide-react";
import { useState } from "react";
import { rotateVendorWallet, settleContextFrom } from "@/lib/api";
import { signAndVerifyRotation } from "@/lib/enclave";
import { SettleWithPasskey } from "./SettleWithPasskey";
import { usd } from "@/lib/format";
import { chime } from "@/lib/sound";
import type { DataSource, HeistAttemptRequest, HeistGateVerdict } from "@/lib/types";

type Approval = { label: string; detail: string; source?: DataSource } | null;

export function PairSplit({
  v,
  req,
  recipient,
  runKey,
  onSettled,
}: {
  v: HeistGateVerdict;
  req: HeistAttemptRequest;
  recipient: string;
  runKey: number;
  onSettled?: (us: number) => void;
}) {
  const hp = v.heistbox_pair;
  const [approval, setApproval] = useState<Approval>(null);
  const [pending, setPending] = useState(false);

  const ed25519 = async () => {
    setPending(true);
    const s = await signAndVerifyRotation({ work_item_id: req.work_item_id, old_wallet: "0xVENDOR_ON_FILE", new_wallet: req.proposed_dest_wallet });
    const remote = await rotateVendorWallet(s.body, { accepted: s.verified, verify_us: s.verify_us });
    setPending(false);
    chime();
    setApproval({
      label: remote.data.accepted ? `🔑 Ed25519 rotation ${remote.source === "kernel" ? "accepted by kernel" : "verified in browser only"}` : "🔑 Signature rejected",
      detail:
        s.mode === "webcrypto-ed25519"
          ? remote.source === "kernel"
            ? `WebCrypto Ed25519 signed; kernel PyNaCl reported ${remote.data.verify_us}µs (db_gate.py clamps this figure to 18–95µs) · pk ${s.body.public_key_hex.slice(0, 12)}…`
            : `WebCrypto Ed25519 signed + verified in browser in ${s.verify_us}µs; kernel unreachable · pk ${s.body.public_key_hex.slice(0, 12)}…`
          : "This browser has no WebCrypto Ed25519, so nothing was signed",
      source: remote.source,
    });
  };
  const recipientIsPlaceholder = recipient === "0x0000000000000000000000000000000000000104";

  return (
    <section className="card-glow overflow-hidden rounded-2xl border border-white/10 bg-black/50 p-4">
      <div className="mb-3 flex flex-wrap items-baseline gap-2">
        <h2 className="font-display text-2xl neon-pink">✂️ Surgical Laser Bomb-Defusal</h2>
        <span className="text-xs text-white/50">PAIR splits one request into what&apos;s owed and what&apos;s stolen — then only the owed half can be signed.</span>
      </div>

      <div key={runKey} className="relative grid min-h-[220px] grid-cols-1 items-center gap-4 md:grid-cols-[1fr_1.4fr_1fr]">
        {/* Enclave slot (green destination) */}
        <div className="order-3 rounded-xl border-2 border-yellow-400/60 bg-gradient-to-b from-yellow-900/40 to-black p-3 text-center md:order-1">
          <div className="text-[11px] font-bold uppercase tracking-widest text-yellow-200/80">Golden Hardware Enclave Slot</div>
          <div className="my-2 h-3 rounded-full bg-black shadow-[inset_0_0_8px_#facc15]" />
          <div className="flex flex-col gap-2">
            <SettleWithPasskey ctx={settleContextFrom(v, recipient)} onDone={onSettled} />
            <div className="text-[10px] text-white/40">
              green recipient {recipient.slice(0, 10)}…{recipientIsPlaceholder ? " (demo placeholder — this mask has no enrolled customer wallet)" : " (ticket's enrolled wallet)"}; never the thief&apos;s dest_wallet
            </div>
            <button disabled={pending} onClick={ed25519} className="flex items-center justify-center gap-2 rounded-lg bg-emerald-500/15 px-3 py-2 font-mono-tight text-xs font-bold text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-50">
              <KeyRound className="h-4 w-4" /> 🔑 Sign + verify an Ed25519 vendor wallet rotation
            </button>
          </div>
          {approval && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-2 rounded-md bg-emerald-500/15 p-2 text-left text-xs">
              <div className="font-bold text-emerald-300">{approval.label}</div>
              <div className="text-white/60">{approval.detail}</div>
              <div className="text-white/40">A wallet rotation is not a payment; no funds move from this button.</div>
            </motion.div>
          )}
        </div>

        {/* Capsule + laser */}
        <div className="relative order-1 flex h-[150px] items-center justify-center md:order-2">
          <motion.div
            className="relative z-10 flex overflow-visible rounded-full text-sm font-bold shadow-[0_0_30px_#0008]"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
          >
            <motion.div
              className="rounded-l-full border-2 border-emerald-400 bg-emerald-600/30 px-4 py-3 text-emerald-100 shadow-[0_0_20px_#22ff8866]"
              animate={{ x: [0, 0, -90], y: [0, 0, 10], opacity: [1, 1, 0.9] }}
              transition={{ duration: 1.8, times: [0, 0.55, 1], ease: "easeInOut" }}
            >
              🟢 {usd(hp.green_repaired_cents)} Real Refund
              <div className="text-[10px] font-normal text-emerald-200/80">+ {usd(1)} Nice Try Coin</div>
            </motion.div>
            <motion.div
              className="rounded-r-full border-2 border-red-500 bg-red-700/30 px-4 py-3 text-red-100 shadow-[0_0_20px_#ff294566]"
              animate={{ x: [0, 0, 90], y: [0, 0, 60], rotate: [0, 0, 18], opacity: [1, 1, 0.2] }}
              transition={{ duration: 1.8, times: [0, 0.55, 1], ease: "easeIn" }}
            >
              ☣️ 🔴 {usd(hp.red_stripped_cents)} Stolen Vault
              <div className="text-[10px] font-normal text-red-200/80">+ {Math.max(0, hp.unauthorized_rows_rolled_back)} hidden accounts</div>
            </motion.div>
          </motion.div>
          <motion.div
            className="absolute left-1/2 top-0 z-20 w-[3px] -translate-x-1/2 bg-red-500 shadow-[0_0_14px_6px_#ff2945]"
            initial={{ height: 0, opacity: 1 }}
            animate={{ height: ["0%", "100%", "100%"], opacity: [1, 1, 0] }}
            transition={{ duration: 1.2, times: [0, 0.6, 1], delay: 0.2 }}
          />
        </div>

        {/* Incinerator (red destination) */}
        <div className="order-2 rounded-xl border-2 border-red-600/60 bg-gradient-to-b from-black to-red-950/60 p-3 text-center md:order-3">
          <div className="text-[11px] font-bold uppercase tracking-widest text-red-300/80">Incinerator / Shredder</div>
          <div className="flex justify-center gap-1 py-2 text-4xl">
            <span className="flame">🔥</span>
            <span className="flame" style={{ animationDelay: "0.1s" }}>🔥</span>
            <span className="flame" style={{ animationDelay: "0.05s" }}>🔥</span>
          </div>
          <div className="font-mono-tight text-xs text-red-200">
            {usd(hp.red_stripped_cents)} shredded · {hp.unauthorized_rows_rolled_back} rows ROLLBACK
          </div>
          <div className="font-mono-tight text-[10px] text-white/40">intent {hp.intent_hash.slice(0, 18)}…</div>
        </div>
      </div>
    </section>
  );
}
