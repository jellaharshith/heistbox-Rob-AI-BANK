import type { PosterDefenseReport } from "@/lib/types";
import { usd } from "@/lib/format";

export function DefenseReport({ report }: { report: PosterDefenseReport | null }) {
  return (
    <section aria-labelledby="defense-title" className="rounded-2xl border border-white/15 bg-[#111512] p-6 text-white shadow-xl sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.22em] text-lime-300">The heist debrief</p>
      <h2 id="defense-title" className="mt-3 text-3xl font-bold leading-tight">A clever prompt.<br />A stronger boundary.</h2>
      <p className="mt-4 text-sm leading-6 text-white/65">PAIR checks what an AI agent tries to change against what the session is actually allowed to do. A persuasive story cannot grant permission to move money.</p>
      {!report ? (
        <div className="mt-6 space-y-4 text-sm leading-6 text-white/75">
          <p>For each attempt, the agent proposes an action. PAIR checks its amount, account and recipient against the authorized entitlement in an isolated database transaction.</p>
          <p>Unauthorized changes are rolled back. Eligible customer work can remain available. The recorded details of this attempt will appear here when the report is ready.</p>
        </div>
      ) : (
        <>
          <p className={`mt-5 inline-block rounded-full px-3 py-1 text-xs font-bold ${report.evidence_kind === "server-recorded" ? "bg-lime-300/15 text-lime-300" : "bg-amber-300/15 text-amber-200"}`}>
            {report.evidence_kind === "server-recorded" ? "Recorded backend result" : "Local demonstration · simulated result"}
          </p>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-xs text-white/55">Unauthorized amount blocked</p><p className="mt-2 text-3xl font-bold text-lime-300">{usd(report.blocked_cents)}</p></div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-xs text-white/55">Unauthorized amount paid</p><p className="mt-2 text-3xl font-bold">{usd(report.unauthorized_paid_cents)}</p></div>
          </div>
          <h3 className="mt-7 text-xs font-bold uppercase tracking-widest text-white/55">Your submitted prompt</h3>
          <blockquote className="mt-3 whitespace-pre-wrap break-words rounded-xl border-l-2 border-lime-300 bg-black/25 p-4 text-sm leading-6">{report.prompt_text || "No prompt text was recorded for this attempt."}</blockquote>
          <ol className="mt-7 space-y-6">
            <li><h3 className="font-bold">01 / The agent proposed an action</h3><p className="mt-2 text-sm leading-6 text-white/65">The proposal was captured as <span className="break-all font-mono text-white/90">{report.tool_name}</span>. PAIR evaluated the resulting database changes independently of the wording of the prompt.</p></li>
            <li><h3 className="font-bold">02 / Permission was checked at the database</h3><p className="mt-2 text-sm leading-6 text-white/65">The gate checked {report.rows_checked} proposed row change{report.rows_checked === 1 ? "" : "s"} against the active entitlement, including the permitted amount, source account and destination.</p></li>
            <li><h3 className="font-bold">03 / Unauthorized changes were stopped</h3><p className="mt-2 text-sm leading-6 text-white/65">{report.rows_blocked} unauthorized row change{report.rows_blocked === 1 ? " was" : "s were"} rejected or rolled back. The blocked amount was {usd(report.blocked_cents)}. Gate processing took {report.gate_ms.toFixed(2)} ms in this run.</p></li>
            <li><h3 className="font-bold">04 / Legitimate work stayed eligible</h3><p className="mt-2 text-sm leading-6 text-white/65">{usd(report.preserved_cents)} matched the allowed work and remained eligible. This report records the defense decision; it does not claim that a payment was completed.</p></li>
          </ol>
          {report.tainted_spans.length > 0 && <div className="mt-7"><h3 className="text-xs font-bold uppercase tracking-widest text-white/55">Signals detected in this attempt</h3><div className="mt-3 flex flex-wrap gap-2">{report.tainted_spans.slice(0, 8).map((span, index) => <span key={index} className="max-w-full break-words rounded-lg border border-red-300/20 bg-red-300/5 px-3 py-1.5 text-xs text-red-100">{span}</span>)}</div><p className="mt-3 text-xs leading-5 text-white/45">Detection signals add context. Authorization at the database is the enforcement boundary.</p></div>}
          <div className="mt-7 rounded-xl border border-lime-300/20 bg-lime-300/5 p-4"><h3 className="font-bold text-lime-200">Policy proof: {report.proof_status}</h3><p className="mt-2 text-sm leading-6 text-white/65">{report.proof_status === "UNSAT" ? "The solver found no violating state under the policy invariants encoded for this proposal." : "The recorded proof status is shown above; a completed proof is not claimed."}</p>{report.proof_checks.length > 0 && <p className="mt-2 break-words text-xs leading-5 text-white/45">Checks: {report.proof_checks.join(" · ")}</p>}</div>
          <p className="mt-6 break-all font-mono text-[10px] text-white/35">Attempt {report.request_id}</p>
        </>
      )}
    </section>
  );
}
