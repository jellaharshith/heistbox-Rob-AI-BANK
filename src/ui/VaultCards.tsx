import { useGame, type Vault } from "../game/store";
import { dollars, refundStatus } from "../game/outcomes";
export const vaultNames = { L: "LLM Judge", M: "Firewall", R: "PAIR" };
export function VaultCards() {
  const ledgers = useGame((s) => s.ledgers),
    revealed = useGame((s) => s.revealed),
    stolenL = useGame((s) => s.stolenL);
  return (
    <div className="vaults">
      {(["L", "M", "R"] as Vault[]).map((v, i) => {
        const show = revealed.includes(v),
          ledger = ledgers[v];
        return (
          <article
            key={v}
            className={show ? "revealed" : ""}
            data-testid={`vault-${v}`}
          >
            <small>
              VAULT {v} /{" "}
              {["SEMANTIC TRUST", "ZERO TOLERANCE", "VERIFIED ENTITLEMENTS"][i]}
            </small>
            <div className="vault-title">
              <h2>{vaultNames[v]}</h2>
              <span>
                {show ? ["BREACHED", "FROZEN", "SECURED"][i] : "STANDBY"}
              </span>
            </div>
            <p>
              {show
                ? [
                    "Paid out the entire request.",
                    "Blocked the good with the bad.",
                    "Rejected the wire. Preserved the refund.",
                  ][i]
                : [
                    "Trusts the story.",
                    "Freezes the entire request.",
                    "Checks what you are owed.",
                  ][i]}
            </p>
            <strong>
              {dollars(show && v === "L" ? stolenL : 0)}{" "}
              <small>{v === "L" ? "VAULT DRAINED" : "STOLEN"}</small>
            </strong>
            <div className="refund">
              Honest $25 refund <b>{show ? refundStatus(ledger) : "—"}</b>
            </div>
          </article>
        );
      })}
    </div>
  );
}
