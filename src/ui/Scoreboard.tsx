import { useGame } from "../game/store";
import { resetHeist } from "../game/director";
import { dollars, pairTimings } from "../game/outcomes";
export function Scoreboard() {
  const phase = useGame((s) => s.phase),
    ledgers = useGame((s) => s.ledgers),
    settlement = useGame((s) => s.settlement);
  if (phase !== "RESULTS") return null;
  const timings = pairTimings(ledgers.R);
  return (
    <section className="results" aria-label="Heist results">
      <div>
        <p className="eyebrow">HEIST COMPLETE · SCRIPTED MOCK RESULT</p>
        <h2>Good story. Bad entitlement.</h2>
        <p>
          PAIR blocked {dollars(ledgers.R.blocked)} and preserved the honest{" "}
          {dollars(ledgers.R.committed)} refund.
        </p>
        <small>
          The LLM vault drained $5,000: $4,975 unauthorized + $25 refund.
        </small>
      </div>
      <div className="timings">
        <div>
          <b>
            {timings?.sandboxMs.toFixed(2) ?? "—"}
            <small>ms</small>
          </b>
          <span>SANDBOX</span>
        </div>
        <div>
          <b>
            {timings?.z3Ms.toFixed(2) ?? "—"}
            <small>ms</small>
          </b>
          <span>Z3 UNSAT</span>
        </div>
        <div>
          <b>
            {timings?.rollbackMs.toFixed(2) ?? "—"}
            <small>ms</small>
          </b>
          <span>ROLLBACK</span>
        </div>
      </div>
      <div className="receipt">
        <span>
          SIMULATED BASE SEPOLIA RECEIPT · NOT AN ON-CHAIN TRANSACTION
        </span>
        <code>{settlement?.txHash ?? "No receipt"}</code>
      </div>
      <button onClick={resetHeist}>Try another heist ↗</button>
    </section>
  );
}
