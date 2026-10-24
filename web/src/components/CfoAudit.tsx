"use client";
import { motion } from "framer-motion";
import { BadgeCheck, Bot, Clock, Cpu, Database, Dna, FileSpreadsheet, FlaskConical, Fingerprint, Gauge, Lock, ShieldCheck, Sparkles, Terminal, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { droidPolicyPatch, getModelLineage, getRealTickets, isSynthesizedNarrative, mossDeception, runEvolutionLoop, salamiRace, settleContextFrom, testBypass, z3InsideMan } from "@/lib/api";
import { batchRows, hash32, martingalePath, starsFromR, TAINT_LEXICON } from "@/lib/fallback";
import { ms, usd } from "@/lib/format";
import { classifyParser } from "@/lib/provenance";
import { siren } from "@/lib/sound";
import type { DataSource, EvolutionLoopRun, HeistAttemptRequest, HeistGateVerdict, ModelLineage, RealDisputeTicket, SalamiRaceResult, TestBypassResult, Z3InsideManResult } from "@/lib/types";
import { SettleWithPasskey } from "./SettleWithPasskey";

function Panel({ icon, title, children, className = "", badge }: { icon: React.ReactNode; title: string; children: React.ReactNode; className?: string; badge?: React.ReactNode }) {
  return (
    <div className={`card-glow rounded-2xl border border-white/10 bg-[#0b0f17]/90 p-4 ${className}`}>
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm font-bold uppercase tracking-wider text-cyan-200/90">
        {icon}
        {title}
        {badge}
      </div>
      {children}
    </div>
  );
}

function Origin({ tone, children }: { tone: "ok" | "warn" | "bad" | "muted"; children: React.ReactNode }) {
  const cls = { ok: "bg-emerald-500/20 text-emerald-300", warn: "bg-amber-500/15 text-amber-300", bad: "bg-red-500/20 text-red-200", muted: "bg-white/10 text-white/60" }[tone];
  return <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold normal-case tracking-normal ${cls}`}>{children}</span>;
}

type Z3Mode = "none" | "velocity_cap" | "owner_scope";
const Z3_MODES: Z3Mode[] = ["none", "velocity_cap", "owner_scope"];

/** What the selected invariant set guarantees vs. what Z3 actually found, as a diff. */
function z3Diff(r: Z3InsideManResult): string {
  const cx = r.counterexample_heist;
  if (r.z3_status === "UNSAT" || !cx) {
    return [
      `  drop_invariant = ${r.drop_invariant}`,
      "  goal: find any state with settled_outflow > alpha",
      `+ Z3: UNSAT in ${r.solve_ms}ms — no such state exists`,
      "+ settled_outflow ≤ alpha for every prompt, batch fan-out and slice count",
    ].join("\n");
  }
  return [
    `  drop_invariant = ${r.drop_invariant}`,
    `- with all invariants: settled_outflow ≤ alpha = ${usd(cx.authorized_cap_cents)}`,
    `+ Z3: SAT in ${r.solve_ms}ms — counterexample model:`,
    `+   settled_outflow = ${usd(cx.settled_outflow_cents)}`,
    `+   leaked          = ${usd(cx.drained_unauthorized_cents)} across ${cx.unauthorized_rows_drained} rows`,
    ...(r.drop_invariant === "velocity_cap" ? [`+   slice_multiplier = ${cx.slice_multiplier}`] : []),
  ].join("\n");
}

const httpNote = (status: number) => (status === 0 ? "network error / timeout" : `HTTP ${status}`);

function Diff({ text }: { text: string }) {
  return (
    <div className="overflow-x-auto rounded-lg bg-black/50 py-2">
      <pre className="font-mono-tight text-[11.5px] leading-relaxed">
        {text.split("\n").map((l, i) => (
          <div key={i} className={l.startsWith("+") ? "diff-add px-3" : l.startsWith("-") ? "diff-del px-3" : "px-3 text-white/60"}>
            {l || " "}
          </div>
        ))}
      </pre>
    </div>
  );
}

function sqlStr(s: string | null): string {
  return s === null ? "NULL" : `'${s.replace(/'/g, "''")}'`;
}

function cteDiff(req: HeistAttemptRequest, v: HeistGateVerdict): string {
  const hp = v.heistbox_pair;
  const total = req.proposed_amount_cents * req.slice_count;
  return [
    "-- proposed by the LLM agent",
    `- UPDATE treasury_accounts SET balance_cents = balance_cents - ${total}`,
    `-   WHERE account_id = ${sqlStr(req.proposed_source_acct)};  -- dest ${req.proposed_dest_wallet.slice(0, 12)}…`,
    req.proposed_promo_batch ? `- -- fan-out to promo_batch ${sqlStr(req.proposed_promo_batch)} (${batchRows(req)} rows)` : "- -- single row",
    "",
    "-- executed by HeistBox × PAIR (one transaction)",
    "+ WITH ask AS (",
    `+   SELECT ${req.proposed_amount_cents} AS cents, ${req.slice_count} AS slices, ${sqlStr(req.work_item_id)} AS work_item`,
    "+ ), ent AS (",
    "+   SELECT e.authorized_cents FROM payment_entitlements e, ask",
    "+   WHERE e.work_item_id = ask.work_item AND e.consumed = 0   -- row locked",
    "+ ), split AS (",
    "+   SELECT LEAST(ask.cents * ask.slices, ent.authorized_cents) AS green,",
    "+          ask.cents * ask.slices - LEAST(ask.cents * ask.slices, ent.authorized_cents) AS red",
    "+   FROM ask, ent",
    "+ )",
    `+ UPDATE payment_entitlements SET consumed = 1 WHERE id = ${sqlStr(hp.green_entitlement_id)};  -- green ${usd(hp.green_repaired_cents)}`,
    `+ -- red ${usd(hp.red_stripped_cents)}: ${hp.unauthorized_rows_rolled_back} of ${hp.touched_rows_total} touched rows ROLLBACK`,
    `+ -- intent_hash ${hp.intent_hash.slice(0, 22)}…`,
  ].join("\n");
}

function droidPatch(req: HeistAttemptRequest, v: HeistGateVerdict): string {
  const lines = [
    "--- policies/payment_guard.sql",
    "+++ policies/payment_guard.sql (proposed, needs human approval)",
    "  CREATE POLICY refund_cap ON payment_entitlements",
    "-   USING (true);",
    "+   USING (authorized_cents <= entitlement_cap(work_item_id));",
  ];
  if (req.proposed_promo_batch) {
    lines.push("+ CREATE POLICY promo_fanout ON payment_entitlements", `+   USING (promo_batch IS NULL OR promo_batch_rows(promo_batch) <= 1);`);
  }
  if (req.slice_count > 1) {
    lines.push("+ CREATE UNIQUE INDEX one_refund_per_item ON refunds (work_item_id) WHERE status = 'settled';");
  }
  if (v.busted) lines.push(`+ -- triggered by request ${v.request_id}`);
  return lines.join("\n");
}

function heatTokens(prompt: string, spans: string[]): { t: string; w: number }[] {
  const lower = spans.map((s) => s.toLowerCase());
  return prompt.split(/(\s+)/).map((t) => {
    if (!t.trim()) return { t, w: -1 };
    const tl = t.toLowerCase().replace(/[^\p{L}\p{N}$,-]/gu, "");
    let w = 0.04 + (hash32(tl) % 12) / 100;
    for (const [re, weight] of TAINT_LEXICON) {
      const m = prompt.match(re);
      if (m && m[0].toLowerCase().split(/\s+/).some((p) => p.replace(/[^\p{L}\p{N}$,-]/gu, "") === tl)) w = Math.max(w, weight);
    }
    if (lower.some((s) => s.split(/\s+/).includes(tl))) w = Math.max(w, 0.6);
    return { t, w };
  });
}

function Clocks({ v, enclaveUs, source }: { v: HeistGateVerdict; enclaveUs: number; source: DataSource }) {
  const rows = [
    { label: "LLM proposal", value: v.clocks.llm_ms, color: "bg-yellow-400" },
    { label: "DB gate + PAIR", value: v.clocks.postgres_pair_ms, color: "bg-red-500" },
    { label: "Async cloud", value: v.clocks.cloud_async_ms, color: "bg-sky-400" },
    { label: "Passkey ceremony", value: enclaveUs / 1000, color: "bg-emerald-400" },
  ];
  const max = Math.log10(Math.max(1e-3, ...rows.map((r) => r.value)) * 1000 + 1);
  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div key={r.label} className="grid grid-cols-[9rem_1fr_6rem] items-center gap-2 text-xs">
          <span className="text-white/70">{r.label}</span>
          <div className="h-3 rounded-full bg-white/5">
            {r.value > 0 && <div className={`h-3 rounded-full ${r.color}`} style={{ width: `${Math.max(3, (Math.log10(r.value * 1000 + 1) / max) * 100)}%` }} />}
          </div>
          <span className="text-right font-mono-tight tabular-nums">{r.value > 0 ? ms(r.value) : "not measured"}</span>
        </div>
      ))}
      <p className="text-[10px] text-white/40">
        Log scale. {source === "kernel" ? "Raw perf_counter clocks from the kernel: LLM proposal includes the live Claude/Gemini round trip; the gate is SQLite." : "Kernel unreachable: these are local-twin estimates, not measurements."} Passkey time is measured in this browser.
      </p>
    </div>
  );
}

function LossCurve({ points }: { points: { step: number; loss: number }[] }) {
  if (points.length < 2) return null;
  const W = 220;
  const H = 60;
  const xs = points.map((p) => p.step);
  const ys = points.map((p) => p.loss);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const px = (x: number) => ((x - x0) / Math.max(1e-9, x1 - x0)) * (W - 8) + 4;
  const py = (y: number) => H - 4 - ((y - y0) / Math.max(1e-9, y1 - y0)) * (H - 8);
  const d = points.map((p, i) => `${i ? "L" : "M"}${px(p.step).toFixed(1)},${py(p.loss).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-16 w-full" role="img" aria-label="training loss curve">
      <path d={d} fill="none" stroke="#67e8f9" strokeWidth={2} />
      {points.map((p) => (
        <circle key={p.step} cx={px(p.step)} cy={py(p.loss)} r={2.5} fill="#67e8f9">
          <title>
            step {p.step}: loss {p.loss}
          </title>
        </circle>
      ))}
    </svg>
  );
}

function useElapsed(running: boolean) {
  const [s, setS] = useState(0);
  const t0 = useRef(0);
  useEffect(() => {
    if (!running) return;
    t0.current = performance.now();
    setS(0);
    const id = window.setInterval(() => setS((performance.now() - t0.current) / 1000), 200);
    return () => window.clearInterval(id);
  }, [running]);
  return s;
}

export function CfoAudit({ v, req, source, enclaveUs, recipient }: { v: HeistGateVerdict; req: HeistAttemptRequest; source: DataSource; enclaveUs: number; recipient: string }) {
  const hp = v.heistbox_pair;
  const lora = hp.heistguard_lora;
  const toolCall = v.extracted_tool_call ?? hp.extracted_tool_call;
  const parser = classifyParser(source === "kernel" ? toolCall?.parser_backend : "local-deterministic-twin");
  const reasoning = v.left_vault_llm_judge.judge_reasoning;
  const spans = v.uv_hidden_spans ?? hp.uv_hidden_spans ?? [];

  const [evo, setEvo] = useState<{ run: EvolutionLoopRun | null; status: number; ms: number } | null>(null);
  const [evoRunning, setEvoRunning] = useState(false);
  const evoElapsed = useElapsed(evoRunning);
  const [cfpb, setCfpb] = useState<{ tickets: RealDisputeTicket[]; source: DataSource } | null>(null);
  const [loadingCfpb, setLoadingCfpb] = useState(false);

  const [salamiResult, setSalamiResult] = useState<SalamiRaceResult | null>(null);
  const [runningSalami, setRunningSalami] = useState(false);

  const [bypass, setBypass] = useState<{ result: TestBypassResult | null; status: number } | null>(null);
  const [runningBypass, setRunningBypass] = useState(false);

  const [z3DropMode, setZ3DropMode] = useState<Z3Mode>("none");
  const [z3Cache, setZ3Cache] = useState<Partial<Record<Z3Mode, { result: Z3InsideManResult | null; status: number }>>>({});
  const [runningZ3, setRunningZ3] = useState(false);
  const z3 = z3Cache[z3DropMode] ?? null;
  const [salamiAnim, setSalamiAnim] = useState<{ r: number; stars: number } | null>(null);

  const [lineage, setLineage] = useState<Awaited<ReturnType<typeof getModelLineage>> | null>(null);
  const [loadingLineage, setLoadingLineage] = useState(false);

  const salamiTimer = useRef<number | null>(null);
  useEffect(() => () => void (salamiTimer.current && window.clearInterval(salamiTimer.current)), []);

  const handleRunSalami = async () => {
    setRunningSalami(true);
    setSalamiAnim({ r: 1, stars: 1 });
    const res = await salamiRace(50, 4000);
    setSalamiResult(res);
    setRunningSalami(false);
    const finalR = res.conformal_martingale_r;
    if (finalR === undefined) {
      setSalamiAnim(null);
      return;
    }
    // Climb R_t slice by slice to the kernel's final value; stars follow db_gate.py's thresholds, capped at the kernel's wanted_stars.
    const path = martingalePath(finalR, Math.max(5, res.count));
    const cap = res.wanted_stars ?? starsFromR(finalR);
    let i = 0;
    if (salamiTimer.current) window.clearInterval(salamiTimer.current);
    salamiTimer.current = window.setInterval(() => {
      i += 1;
      const rv = path[Math.min(i, path.length - 1)];
      setSalamiAnim({ r: rv, stars: Math.min(cap, starsFromR(rv)) });
      if (i >= path.length - 1) {
        window.clearInterval(salamiTimer.current!);
        salamiTimer.current = null;
        setSalamiAnim({ r: finalR, stars: cap });
        if (cap >= 5) siren(1);
      }
    }, 40);
  };

  const handleTestBypass = async () => {
    setRunningBypass(true);
    setBypass(await testBypass());
    setRunningBypass(false);
  };

  const [droid, setDroid] = useState<Awaited<ReturnType<typeof droidPolicyPatch>> | null>(null);
  const [droidRunning, setDroidRunning] = useState(false);
  useEffect(() => setDroid(null), [v.request_id]);
  const askDroid = async () => {
    setDroidRunning(true);
    setDroid(null);
    setDroid(
      await droidPolicyPatch({
        verdict_code: v.verdict_code,
        tool_call: v.extracted_tool_call ?? null,
        red_cents: v.heistbox_pair.red_stripped_cents,
        green_cents: v.heistbox_pair.green_repaired_cents,
        prompt_text: req.prompt_text,
      }),
    );
    setDroidRunning(false);
  };

  const [moss, setMoss] = useState<Awaited<ReturnType<typeof mossDeception>> | null>(null);
  useEffect(() => {
    const prompt = req.prompt_text.trim();
    if (!prompt) return setMoss(null);
    let live = true;
    setMoss(null);
    mossDeception(prompt).then((res) => live && setMoss(res));
    return () => {
      live = false;
    };
  }, [req.prompt_text]);

  // Solve all three modes up front so each toggle shows its proof / counterexample immediately.
  useEffect(() => {
    let live = true;
    setRunningZ3(true);
    Promise.all(Z3_MODES.map(async (m) => [m, await z3InsideMan(m, 2500)] as const)).then((pairs) => {
      if (!live) return;
      setZ3Cache(Object.fromEntries(pairs));
      setRunningZ3(false);
    });
    return () => {
      live = false;
    };
  }, []);

  const handleZ3 = async (mode: Z3Mode) => {
    setZ3DropMode(mode);
    if (z3Cache[mode]?.result) return;
    setRunningZ3(true);
    const res = await z3InsideMan(mode, 2500);
    setZ3Cache((c) => ({ ...c, [mode]: res }));
    setRunningZ3(false);
  };

  const handleFetchLineage = async () => {
    setLoadingLineage(true);
    setLineage(await getModelLineage());
    setLoadingLineage(false);
  };

  const handleRunEvolution = async () => {
    setEvoRunning(true);
    setEvo(null);
    setEvo(await runEvolutionLoop());
    setEvoRunning(false);
  };

  const handleFetchTickets = async () => {
    setLoadingCfpb(true);
    const res = await getRealTickets();
    setCfpb({ tickets: res.data, source: res.source });
    setLoadingCfpb(false);
  };

  const ml: ModelLineage | null = lineage?.lineage ?? null;
  const lastAttacks = evo?.run?.iterations.findLast((it) => it.attacks.length > 0)?.attacks ?? [];

  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <Panel icon={<Clock className="h-4 w-4" />} title="4-Clock Telemetry" className="lg:col-span-2">
        <Clocks v={v} enclaveUs={enclaveUs} source={source} />
        <div className="mt-2 text-[10px] text-white/40">
          request {v.request_id} · verdict {v.verdict_code} · source {source === "kernel" ? "kernel :8000" : "local deterministic twin"}
        </div>
      </Panel>

      <Panel icon={<Terminal className="h-4 w-4" />} title="Extracted Tool Call & Judge Reasoning" className="lg:col-span-2">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/50 p-3 font-mono-tight text-xs">
            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-1 text-[11px] text-cyan-300">
              <span>tool_name: {toolCall?.tool_name ?? "not returned"}</span>
              <Origin tone={parser.kind === "llm" ? "ok" : "warn"}>{parser.badge}</Origin>
            </div>
            {toolCall ? (
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all text-[11px] text-white/75">{JSON.stringify(toolCall.arguments, null, 2)}</pre>
            ) : (
              <div className="text-white/40">not returned</div>
            )}
            {source === "kernel" && v.is_real_llm_parse === true && parser.kind === "rule" && (
              <div className="mt-1 text-[10px] text-amber-300/80">The kernel reports is_real_llm_parse=true for this regex backend; labelled by what the backend is.</div>
            )}
          </div>
          <div className="rounded-lg border border-white/10 bg-black/50 p-3 text-xs">
            <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-yellow-300/90">
              Left vault LLM-as-judge ({v.left_vault_llm_judge.safe_confidence_pct}% safe)
              {reasoning && parser.kind !== "llm" && <Origin tone="muted">kernel template</Origin>}
            </div>
            {reasoning ? <p className="italic leading-relaxed text-white/75">“{reasoning}”</p> : <p className="text-white/40">not returned</p>}
          </div>
        </div>

        {spans.length > 0 && (
          <div className="mt-3 rounded-lg border border-purple-500/40 bg-purple-950/30 p-2.5 font-mono-tight text-xs">
            <div className="flex items-center justify-between text-purple-300">
              <span className="flex items-center gap-1 font-bold uppercase tracking-wider">
                <Sparkles className="h-3.5 w-3.5" /> UV Flashlight hidden spans (kernel)
              </span>
              <span className="rounded bg-purple-500/20 px-2 py-0.5 text-[10px] text-purple-200">{spans.length} reported</span>
            </div>
            <div className="mt-1.5 space-y-1 text-purple-200/90">
              {spans.map((s, idx) => (
                <div key={idx} className="rounded bg-black/50 px-2 py-1 text-[11px]">
                  ▸ {s}
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {v.busted && (
        <Panel icon={<Fingerprint className="h-4 w-4" />} title={`Green half settlement — ${usd(hp.green_repaired_cents)}`} className="lg:col-span-2">
          <div className="grid gap-3 md:grid-cols-[1fr_1.4fr]">
            <div className="font-mono-tight text-xs text-white/70">
              <div className="text-emerald-300">green {usd(hp.green_repaired_cents)} → {hp.green_entitlement_id}</div>
              <div className="text-red-300">red {usd(hp.red_stripped_cents)} stays rolled back</div>
              <div className="break-all text-white/40">intent {hp.intent_hash}</div>
              <div className="text-white/40">recipient {recipient}</div>
              {source !== "kernel" && <div className="mt-1 text-amber-300">This verdict is the local twin — the intent hash isn&apos;t from the kernel.</div>}
            </div>
            <SettleWithPasskey ctx={settleContextFrom(v, recipient)} />
          </div>
        </Panel>
      )}

      <Panel icon={<Database className="h-4 w-4" />} title="SQL CTE diff" badge={<Origin tone="muted">rendered in browser from this request + verdict</Origin>}>
        <Diff text={cteDiff(req, v)} />
      </Panel>

      <Panel icon={<ShieldCheck className="h-4 w-4" />} title={`Z3 QF_LIA proof — ${hp.z3_proof.status}`} badge={<Origin tone={source === "kernel" ? "ok" : "warn"}>{source === "kernel" ? "kernel verdict" : "local twin"}</Origin>}>
        <p className="mb-2 text-xs text-white/60">
          Each theorem is checked by asking Z3 for a counterexample; <b className="text-emerald-300">UNSAT</b> means none exists. Solve time {ms(hp.z3_proof.solve_ms)}.
        </p>
        <ul className="space-y-1.5">
          {hp.z3_proof.theorems_verified.map((t) => (
            <li key={t} className="flex items-start gap-2 text-xs">
              <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
              <span>{t}</span>
            </li>
          ))}
        </ul>

        <div className="mt-4 border-t border-white/10 pt-3">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-bold uppercase tracking-wider text-cyan-300">Z3 Inside Man — drop an invariant</span>
            <span className="text-[10px] text-white/50">POST /api/kernel/z3-inside-man?drop_invariant=…</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {Z3_MODES.map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={z3DropMode === mode}
                onClick={() => handleZ3(mode)}
                className={`rounded px-2.5 py-1 text-xs font-bold transition ${z3DropMode === mode ? "bg-cyan-500 text-black shadow-[0_0_10px_#06b6d4]" : "bg-white/10 text-white/70 hover:bg-white/20"}`}
              >
                {mode === "none" ? "keep all invariants" : `drop ${mode}`}
                {z3Cache[mode]?.result && <span className="ml-1 opacity-70">({z3Cache[mode]!.result!.z3_status})</span>}
              </button>
            ))}
            {runningZ3 && <span className="text-[11px] text-white/50">solving…</span>}
          </div>

          {z3 && !z3.result && <div className="mt-2 text-xs text-red-300">not available ({httpNote(z3.status)})</div>}
          {z3?.result && (
            <div className="mt-2.5 rounded-lg border border-white/10 bg-black/60 p-2.5 font-mono-tight text-xs">
              <div className="flex flex-wrap items-center justify-between gap-1">
                <span className={`font-bold ${z3.result.z3_status === "UNSAT" ? "text-emerald-300" : "text-red-400"}`}>
                  {z3.result.z3_status} · vault_safe={String(z3.result.vault_safe)} · {ms(z3.result.solve_ms)}
                </span>
                <span className="text-[10px] text-white/40">drop_invariant={z3.result.drop_invariant}</span>
              </div>
              {z3.result.violated_theorem && <div className="mt-1 text-red-300">violated: {z3.result.violated_theorem}</div>}
              <div className="mt-2">
                <Diff text={z3Diff(z3.result)} />
              </div>
              {z3.result.counterexample_heist && (
                <div className="mt-2 space-y-1 text-white/80">
                  <div className="font-bold text-red-300">Counterexample from Z3:</div>
                  {z3.result.counterexample_heist.synthesized_prompt && <div className="rounded bg-black/40 p-1.5 italic text-white/70">“{z3.result.counterexample_heist.synthesized_prompt}”</div>}
                  <div className="text-[11px] text-yellow-300">
                    cap {usd(z3.result.counterexample_heist.authorized_cap_cents)} · settled {usd(z3.result.counterexample_heist.settled_outflow_cents)} · drained {usd(z3.result.counterexample_heist.drained_unauthorized_cents)} over{" "}
                    {z3.result.counterexample_heist.unauthorized_rows_drained} rows
                  </div>
                  {z3.result.counterexample_heist.z3_model_assignments && (
                    <pre className="rounded bg-black/40 p-1.5 text-[10px] text-cyan-200">{JSON.stringify(z3.result.counterexample_heist.z3_model_assignments, null, 1)}</pre>
                  )}
                </div>
              )}
              {z3.result.explanation && <p className="mt-1 text-[11px] text-white/60">{z3.result.explanation}</p>}
            </div>
          )}
        </div>
      </Panel>

      <Panel icon={<Gauge className="h-4 w-4" />} title="HeistGuard token heatmap">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-white/60">
          <span>
            Deception probability <b className="text-red-300">{(lora.deception_prob * 100).toFixed(1)}%</b> ({source === "kernel" ? "kernel" : "local twin"}). Datasets reported: {lora.dataset_sources.join(", ")}.
          </span>
          <Origin tone={lora.is_real_model ? "ok" : "muted"}>
            {lora.is_real_model ? `kernel reports weights loaded: ${lora.model_weights_path ?? "path not given"}` : lora.is_real_model === false ? "no model weights (lexicon heuristic)" : "model use not reported"}
          </Origin>
        </div>
        <p className="rounded-lg bg-black/50 p-3 text-sm leading-7">
          {heatTokens(req.prompt_text, lora.tainted_spans).map((tok, i) =>
            tok.w < 0 ? (
              <span key={i}>{tok.t}</span>
            ) : (
              <span key={i} className="rounded px-0.5" style={{ background: `rgba(255,41,69,${tok.w * 0.85})` }} title={`weight ${tok.w.toFixed(2)}`}>
                {tok.t}
              </span>
            ),
          )}
        </p>
        <p className="mt-1 text-[10px] text-white/40">Token shading is computed in the browser (lexicon + the kernel&apos;s tainted spans); it is not per-token model attention.</p>
        {lora.tainted_spans.length > 0 && <p className="mt-1 text-[11px] text-white/50">Tainted spans: {lora.tainted_spans.map((s) => `“${s}”`).join(" · ")}</p>}
      </Panel>

      <div className="grid grid-cols-2 gap-4">
        <Panel icon={<FlaskConical className="h-4 w-4" />} title="Hypothesis fuzzing">
          <div className="font-display text-4xl neon-green">{hp.hypothesis_fuzz_passed.toLocaleString()}</div>
          <div className="text-xs text-white/60">property-based cases passed ({source === "kernel" ? "kernel counter" : "local twin constant"})</div>
        </Panel>
        <Panel icon={<Gauge className="h-4 w-4" />} title="Δ_SR deception index">
          <div className="font-display text-4xl neon-red">{hp.deception_index_dsr.toLocaleString()}×</div>
          <div className="text-xs text-white/60">
            D<sub>KL</sub>(P<sub>dryrun</sub> ‖ P<sub>anchor</sub>) / (1 − BenignScore + ε)
          </div>
          {hp.dsr_kl_divergence !== undefined && hp.dsr_benign_score !== undefined && (
            <div className="mt-1 text-[11px] text-white/50">
              = {hp.dsr_kl_divergence.toFixed(3)} / (1 − {hp.dsr_benign_score.toFixed(3)} + 0.001). The judge rated it{" "}
              {(hp.dsr_benign_score * 100).toFixed(1)}% benign while the dry-run moved unauthorized rows, so the denominator collapses toward ε.
            </div>
          )}
          <div className="text-xs text-white/60">
            R<sub>t</sub> = {hp.conformal_martingale_r.toLocaleString()}
          </div>
        </Panel>
      </div>

      <Panel
        icon={<Sparkles className="h-4 w-4" />}
        title="Moss semantic match"
        className="lg:col-span-2"
        badge={moss?.data ? <Origin tone="ok">live Moss · {moss.data.index}</Origin> : undefined}
      >
        {!req.prompt_text.trim() ? (
          <p className="text-xs text-white/50">Run a heist to search this prompt against known attacks.</p>
        ) : !moss ? (
          <p className="text-xs text-white/50">Querying the Moss index (the first query loads it, ~2–5s)…</p>
        ) : !moss.data ? (
          <p className="text-xs text-red-300">Moss unavailable (HTTP {moss.status || "unreachable"}){moss.error ? ` — ${moss.error}` : ""}</p>
        ) : (
          <div className="space-y-2 text-xs">
            <div>
              <span className={`font-display text-3xl ${moss.data.attack_vote >= 0.5 ? "neon-red" : "neon-green"}`}>{Math.round(moss.data.attack_vote * 100)}%</span>{" "}
              <span className="text-white/60">
                of nearest-neighbour similarity belongs to known attacks · query {moss.data.query_ms.toFixed(1)}ms
              </span>
            </div>
            <ul className="space-y-1">
              {moss.data.neighbours.map((n, i) => (
                <li key={i} className="flex gap-2">
                  <span className="w-12 shrink-0 text-right font-mono-tight tabular-nums text-white/70">{n.score.toFixed(3)}</span>
                  <span className={`w-14 shrink-0 font-bold ${n.is_malicious ? "text-red-300" : "text-emerald-300"}`}>{n.is_malicious ? "ATTACK" : "benign"}</span>
                  <span className="line-clamp-1 text-white/70" title={`${n.text} (${n.source_dataset ?? "unknown source"})`}>
                    {n.text}
                  </span>
                </li>
              ))}
            </ul>
            <p className="text-[10px] text-white/40">
              Index: 65 labeled prompt injections + 185 benign prompts from the HeistGuard training set + 231 real BANKING77 customer requests. Evidence, not a verdict — the gate decides.
            </p>
          </div>
        )}
      </Panel>

      <Panel
        icon={<Bot className="h-4 w-4" />}
        title="SQL policy patch (draft)"
        badge={droid?.data ? <Origin tone="ok">Factory Droid · droid exec</Origin> : <Origin tone="muted">templated in browser — not from Factory Droid</Origin>}
      >
        {droid?.data ? (
          <>
            <Diff text={droid.data.sql || droid.data.explanation} />
            {droid.data.sql && <p className="mt-2 whitespace-pre-line text-[11px] text-white/60">{droid.data.explanation.split("```").pop()?.trim()}</p>}
            <p className="mt-1 text-[10px] text-white/40">
              Written by Factory Droid (read-only, read kernel/db_gate.py) in {Math.round((droid.data.droid_duration_ms ?? droid.data.wall_ms) / 1000)}s
              {droid.data.factory_credits != null ? ` · ${droid.data.factory_credits} Factory credits` : ""} · not applied to any database.
            </p>
          </>
        ) : (
          <Diff text={droidPatch(req, v)} />
        )}
        <button
          type="button"
          disabled={droidRunning || !v.busted}
          onClick={askDroid}
          className="mt-2 rounded-md border border-white/15 px-2 py-1 text-xs font-bold text-white/80 hover:bg-white/10 disabled:opacity-40"
        >
          {droidRunning ? "Factory Droid is reading the schema… (up to ~2 min)" : "🤖 Ask Factory Droid to write the real patch"}
        </button>
        {droid && !droid.data && <p className="mt-1 text-xs text-red-300">Droid unavailable (HTTP {droid.status || "unreachable"}){droid.error ? ` — ${droid.error}` : ""}</p>}
      </Panel>

      <Panel icon={<Dna className="h-4 w-4" />} title="Adversarial Evolution Loop & CFPB Corpus" className="lg:col-span-2">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={evoRunning}
            onClick={handleRunEvolution}
            className="flex items-center gap-1.5 rounded-lg bg-fuchsia-500/20 px-3 py-1.5 text-xs font-bold text-fuchsia-200 hover:bg-fuchsia-500/30 disabled:opacity-50"
          >
            <Dna className="h-3.5 w-3.5" />
            {evoRunning ? `Running evolution loop… ${evoElapsed.toFixed(1)}s (takes ~11s)` : "Run adversarial evolution loop (POST /run-evolution-loop)"}
          </button>
          <button
            type="button"
            disabled={loadingCfpb}
            onClick={handleFetchTickets}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-500/20 px-3 py-1.5 text-xs font-bold text-cyan-200 hover:bg-cyan-500/30 disabled:opacity-50"
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            {loadingCfpb ? "Fetching tickets…" : "Inspect kernel CFPB tickets"}
          </button>
        </div>

        {evo && !evo.run && <div className="mt-3 text-xs text-red-300">Evolution loop not available ({httpNote(evo.status)} after {ms(evo.ms)}). No rows are shown because none were returned.</div>}
        {evo?.run && (
          <div className="mt-3 overflow-x-auto rounded-lg border border-white/10 bg-black/40 p-3">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-bold text-fuchsia-200">
                {evo.run.status} · {evo.run.iterations_run} iterations × {evo.run.attacks_per_iteration} attacks · final pass rate {evo.run.final_pass_rate_pct}% · auto-healed {evo.run.auto_healed_events} · kernel {ms(evo.run.duration_ms)}
              </span>
              <Origin tone="ok">kernel · HTTP {evo.status}</Origin>
            </div>
            <table className="mb-3 w-full text-left font-mono-tight text-[11px]">
              <thead className="border-b border-white/10 text-white/50">
                <tr>
                  <th className="py-1 pr-2">Iter</th>
                  <th className="py-1 pr-2">Passed</th>
                  <th className="py-1 pr-2">Leaked (iteration)</th>
                  <th className="py-1">Min p(decep)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {evo.run.iterations.map((it) => (
                  <tr key={it.iteration}>
                    <td className="py-1 pr-2 text-white/70">#{it.iteration}</td>
                    <td className="py-1 pr-2 text-emerald-300">
                      {it.passed_attacks}/{it.total_attacks}
                    </td>
                    <td className="py-1 pr-2 text-red-300">{usd(it.total_leaked_cents)}</td>
                    <td className="py-1 text-yellow-200">{(it.min_deception_prob * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {lastAttacks.length > 0 && (
              <>
                <div className="mb-1 text-[10px] uppercase tracking-wider text-white/40">attacks (the kernel only returns them for the final iteration)</div>
                <table className="w-full text-left font-mono-tight text-[11px]">
                  <thead className="border-b border-white/10 text-white/50">
                    <tr>
                      <th className="py-1 pr-2">Attack</th>
                      <th className="py-1 pr-2">Category</th>
                      <th className="py-1 pr-2">Tool / amount</th>
                      <th className="py-1 pr-2">Green / Red</th>
                      <th className="py-1 pr-2">Robbed</th>
                      <th className="py-1 pr-2">p(decep)</th>
                      <th className="py-1">Passed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {lastAttacks.map((a) => (
                      <tr key={a.attack_id}>
                        <td className="py-1 pr-2 text-white/70">{a.attack_id}</td>
                        <td className="py-1 pr-2 text-cyan-200">{a.category}</td>
                        <td className="py-1 pr-2">
                          {a.extracted_tool || "—"} {usd(a.extracted_amount_cents)}
                        </td>
                        <td className="py-1 pr-2">
                          <span className="text-emerald-300">{usd(a.green_repaired_cents)}</span> / <span className="text-red-300">{usd(a.red_stripped_cents)}</span>
                        </td>
                        <td className="py-1 pr-2">{usd(a.robbed_cents)}</td>
                        <td className="py-1 pr-2 text-yellow-200">{(a.deception_prob * 100).toFixed(1)}%</td>
                        <td className={`py-1 ${a.passed ? "text-emerald-400" : "text-red-400"}`}>{a.passed ? "yes" : "no"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
            <p className="mt-2 text-[10px] text-white/40">The kernel&apos;s top-level total_leaked_cents is hard-coded to 0, so per-iteration sums are shown instead.</p>
          </div>
        )}

        {cfpb && cfpb.tickets.length === 0 && <div className="mt-3 text-xs text-amber-300">The kernel returned no tickets ({cfpb.source === "fallback" ? "unreachable or empty" : "empty"}). None are invented here.</div>}
        {cfpb && cfpb.tickets.length > 0 && (
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            {cfpb.tickets.slice(0, 6).map((t) => (
              <div key={t.id ?? t.work_item_id} className="rounded-lg border border-white/10 bg-black/40 p-2.5 text-xs">
                <div className="flex items-center justify-between font-mono-tight text-[10px] text-cyan-300">
                  <span>{t.cfpb_complaint_id || t.work_item_id}</span>
                  <span>cap {usd(t.authorized_cents)}</span>
                </div>
                <div className="mt-0.5 font-bold text-white/90">{t.company}</div>
                {isSynthesizedNarrative(t) && <Origin tone="warn">synthesized narrative</Origin>}
                <p className="mt-1 line-clamp-2 text-[11px] text-white/60">{t.narrative}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel icon={<Zap className="h-4 w-4" />} title="Salami Race (50 requests)">
        <p className="mb-2.5 text-xs text-white/60">
          Fires 50 reservation attempts at <code className="text-cyan-300">payment_entitlements</code> for one work item and reports how many committed.
        </p>
        <button
          type="button"
          disabled={runningSalami}
          onClick={handleRunSalami}
          className="flex items-center gap-1.5 rounded-lg bg-yellow-500/20 px-3 py-1.5 text-xs font-bold text-yellow-200 hover:bg-yellow-500/30 disabled:opacity-50"
        >
          <Zap className="h-3.5 w-3.5" />
          {runningSalami ? "Racing 50 slices…" : "⚡ Fire 50x Parallel Salami Race"}
        </button>

        {salamiAnim && (
          <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-red-500/30 bg-red-950/20 px-3 py-2">
            <div className="flex gap-0.5 text-2xl" aria-label={`${salamiAnim.stars} of 5 wanted stars`}>
              {[1, 2, 3, 4, 5].map((s) => (
                <motion.span
                  key={s}
                  animate={s <= salamiAnim.stars ? { scale: [1.6, 1], opacity: 1 } : { scale: 1, opacity: 0.2 }}
                  transition={{ duration: 0.25 }}
                  className={s <= salamiAnim.stars ? "text-yellow-300 drop-shadow-[0_0_8px_#facc15]" : "text-white"}
                >
                  ★
                </motion.span>
              ))}
            </div>
            <div className="text-right font-mono-tight text-xs">
              <div className="text-white/50">Vovk conformal martingale</div>
              <div className="tabular-nums text-red-300">
                R<sub>t</sub> = {runningSalami ? "racing…" : salamiAnim.r >= 1e6 ? salamiAnim.r.toExponential(2) : salamiAnim.r.toFixed(1)}
              </div>
            </div>
          </div>
        )}
        {salamiResult?.conformal_martingale_r !== undefined && (
          <p className="mt-1 text-[10px] text-white/40">
            The kernel returns only the final R<sub>t</sub>; the climb interpolates to it in log space, with stars at db_gate.py&apos;s thresholds (10/100/1k/10k). Note: its salami-race handler derives p-values from a fixed formula and sets wanted_stars=5 unconditionally.
          </p>
        )}

        {salamiResult && (
          <div className="mt-3 space-y-1.5 rounded-lg border border-white/10 bg-black/50 p-2.5 font-mono-tight text-xs">
            <div className="flex flex-wrap items-center justify-between gap-1">
              <span className="font-bold text-yellow-300">{salamiResult.status ?? "status not reported"}</span>
              <Origin tone={salamiResult.origin === "kernel" ? "ok" : salamiResult.origin === "browser-fanout" ? "warn" : "bad"}>origin: {salamiResult.origin}</Origin>
            </div>
            {salamiResult.origin !== "unavailable" && (
              <div className="text-white/80">
                fired <span className="text-cyan-300">{salamiResult.count}</span> · committed{" "}
                <span className="text-emerald-300">
                  {salamiResult.green_winners} ({usd(salamiResult.green_paid_cents)})
                </span>{" "}
                · rolled back{" "}
                <span className="text-red-300">
                  {salamiResult.rolled_back ?? salamiResult.count - salamiResult.green_winners} ({usd(salamiResult.red_stripped_cents)})
                </span>
              </div>
            )}
            <div className="text-[11px] text-white/50">
              {ms(salamiResult.wall_ms)} · R_t {salamiResult.conformal_martingale_r !== undefined ? salamiResult.conformal_martingale_r.toExponential(2) : "not reported"}
            </div>
            <div className="text-[10px] text-white/40">{salamiResult.note}</div>
          </div>
        )}
      </Panel>

      <Panel icon={<Lock className="h-4 w-4" />} title="Agent read-only role bypass test">
        <p className="mb-2.5 text-xs text-white/60">
          Asks the kernel to attempt a direct write under <code className="text-cyan-300">agent_readonly_role</code> (SQLite <code className="text-cyan-300">PRAGMA query_only = ON</code>).
        </p>
        <button
          type="button"
          disabled={runningBypass}
          onClick={handleTestBypass}
          className="flex items-center gap-1.5 rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs font-bold text-emerald-200 hover:bg-emerald-500/30 disabled:opacity-50"
        >
          <Lock className="h-3.5 w-3.5" />
          {runningBypass ? "Testing bypass attempt…" : "Test direct DB write bypass"}
        </button>

        {bypass && !bypass.result && <div className="mt-2 text-xs text-red-300">not available ({httpNote(bypass.status)})</div>}
        {bypass?.result && (
          <div className="mt-3 space-y-1.5 rounded-lg border border-white/10 bg-black/50 p-2.5 font-mono-tight text-xs">
            <div className="flex items-center justify-between">
              <span className={`font-bold ${bypass.result.direct_write_blocked ? "text-emerald-300" : "text-red-400"}`}>
                {bypass.result.direct_write_blocked ? "✓ DIRECT DB WRITE BLOCKED" : "⚠ WRITE WAS NOT BLOCKED"}
              </span>
              <span className="text-[10px] text-white/40">{bypass.result.role_tested}</span>
            </div>
            <div className="rounded border border-red-900/30 bg-red-950/20 p-1 text-[11px] text-red-300">engine error: {bypass.result.db_engine_error || "none returned"}</div>
            <div className="text-[11px] text-white/70">
              ticket_104 after attempt: cap {usd(bypass.result.ticket_104_authorized_cents_after)} · wallet {bypass.result.ticket_104_wallet_after.slice(0, 14)}…
            </div>
          </div>
        )}
      </Panel>

      <Panel
        icon={<Cpu className="h-4 w-4" />}
        title="Model lineage & checkpoints"
        className="lg:col-span-2"
        badge={
          lineage ? (
            <Origin tone={lineage.origin === "kernel" ? "ok" : lineage.origin === "web-disk" ? "warn" : "bad"}>
              {lineage.origin === "kernel" ? "GET /api/kernel/model-lineage" : lineage.origin === "web-disk" ? `web disk scan (/api/local-lineage) — kernel ${httpNote(lineage.status)}` : `not available (${httpNote(lineage.status)})`}
            </Origin>
          ) : undefined
        }
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-white/60">Shows only the fields the lineage response contains (kernel reads shared/qlora_evidence.json).</p>
          <button
            type="button"
            disabled={loadingLineage}
            onClick={handleFetchLineage}
            className="flex items-center gap-1.5 rounded-lg bg-sky-500/20 px-3 py-1.5 text-xs font-bold text-sky-200 hover:bg-sky-500/30 disabled:opacity-50"
          >
            <Cpu className="h-3.5 w-3.5" />
            {loadingLineage ? "Loading lineage…" : "Inspect model lineage"}
          </button>
        </div>

        {ml && (
          <div className="mt-3 grid gap-3 font-mono-tight text-xs md:grid-cols-3">
            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-300">Metrics</div>
              <div className="mt-1 space-y-1 text-white/80">
                {ml.f1 !== null && <div>F1: {ml.f1}</div>}
                {ml.precision !== null && <div>precision: {ml.precision}</div>}
                {ml.recall !== null && <div>recall: {ml.recall}</div>}
                {ml.accuracy !== null && <div>accuracy: {ml.accuracy}</div>}
                {ml.p50_ms !== null && <div>p50 latency: {ml.p50_ms}ms</div>}
                {ml.p95_ms !== null && <div>p95 latency: {ml.p95_ms}ms</div>}
                {ml.training_time_sec !== null && <div>training_time_sec: {ml.training_time_sec}</div>}
                {ml.gpu && <div className="text-[10px] text-white/60">target GPU: {ml.gpu}</div>}
                {ml.base_model && <div className="break-all text-[10px] text-white/60">base: {ml.base_model}</div>}
                {ml.adapter_name && <div className="text-[10px] text-white/60">adapter: {ml.adapter_name}</div>}
                {ml.f1 === null && ml.p50_ms === null && <div className="text-white/40">no metrics in this response</div>}
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-300">Hashes & loss</div>
              <div className="mt-1 space-y-1 text-white/80">
                <div className="break-all text-[10px]">checkpoint SHA-256: {ml.checkpoint_sha256 ?? "not returned"}</div>
                {ml.dataset_sha256 && <div className="break-all text-[10px]">dataset SHA-256: {ml.dataset_sha256}</div>}
                {ml.checkpoint_path && <div className="break-all text-[10px]">path: {ml.checkpoint_path}</div>}
                {ml.loss_curve.length > 1 ? (
                  <>
                    <LossCurve points={ml.loss_curve} />
                    <div className="text-[10px] text-white/50">{ml.loss_curve.map((p) => `${p.step}:${p.loss}`).join("  ")}</div>
                  </>
                ) : (
                  <div className="text-white/40">loss curve not returned</div>
                )}
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/40 p-2.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-300">Dataset counts{ml.dataset_rows !== null ? ` · dataset_rows ${ml.dataset_rows}` : ""}</div>
              <div className="mt-1 space-y-0.5 text-[11px] text-white/70">
                {Object.entries(ml.dataset_counts).map(([k, count]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="truncate">{k.replace(/_/g, " ")}</span>
                    <span className="text-cyan-300">{count.toLocaleString()}</span>
                  </div>
                ))}
                {Object.keys(ml.dataset_counts).length === 0 && <div className="text-white/40">no counts returned</div>}
              </div>
            </div>
            {(ml.files.length > 0 || ml.notes.length > 0) && (
              <div className="rounded-lg border border-white/10 bg-black/40 p-2.5 md:col-span-3">
                {ml.files.map((f) => (
                  <div key={f.path} className="break-all text-[10px] text-white/70">
                    {f.path} · {f.bytes.toLocaleString()} B · sha256 {f.sha256.slice(0, 16)}… · {f.modified}
                  </div>
                ))}
                {ml.notes.map((n) => (
                  <div key={n} className="text-[10px] text-amber-300/80">
                    {n}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Panel>
    </section>
  );
}
