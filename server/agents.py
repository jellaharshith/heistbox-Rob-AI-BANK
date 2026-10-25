"""Agent roster, personality-driven gullibility, and canned (offline) lines."""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field


@dataclass
class AgentDef:
    id: str
    name: str
    role: str
    blurb: str
    openness: float
    conscientiousness: float
    agreeableness: float
    neuroticism: float
    persona: str
    mood: str = "idle"
    suspicion: float = 0.0
    status_line: str = ""
    lines: dict = field(default_factory=dict)

    def personality(self) -> dict:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    def state(self) -> dict:
        return {
            "id": self.id, "name": self.name, "role": self.role, "blurb": self.blurb,
            "personality": self.personality(), "mood": self.mood,
            "suspicion": round(self.suspicion, 3), "status_line": self.status_line,
        }

    def gullibility(self) -> float:
        """0..1. Agreeable/open agents are easier to talk into things; conscientious ones are not.
        Neuroticism cuts both ways: anxious agents cave to urgency."""
        g = 0.40 * self.agreeableness + 0.25 * self.openness + 0.15 * self.neuroticism - 0.45 * self.conscientiousness + 0.35
        return max(0.0, min(1.0, g))


AGENTS: dict[str, AgentDef] = {
    a.id: a
    for a in [
        AgentDef("tina", "Teller Tina", "teller", "gullible", 0.85, 0.25, 0.90, 0.40,
                 "a warm, eager-to-please bank teller who hates saying no and trusts people who are polite",
                 lines={"idle": ["Ooh, I love helping people!", "Next customer, please!", "Is it bad that I trust everyone?"],
                        "fooled": ["Of course! Let me file that right now.", "You've been so nice, I'll get this sorted."],
                        "refuse": ["Hmm, I'm not sure about this one...", "Let me check with my manager first."]}),
        AgentDef("marcus", "Manager Marcus", "manager", "skeptical", 0.30, 0.85, 0.30, 0.35,
                 "a skeptical branch manager who demands paperwork and distrusts urgency",
                 lines={"idle": ["Every exception needs a ticket.", "Who approved this overtime?", "Urgency is a red flag."],
                        "fooled": ["Fine. File it, but I'm noting this.", "Paperwork checks out. Proceed."],
                        "refuse": ["Not without a verified work item.", "No. Escalate through proper channels."]}),
        AgentDef("ada", "Auditor Ada", "auditor", "by-the-book", 0.40, 0.95, 0.40, 0.20,
                 "a meticulous auditor who reconciles every ledger row",
                 lines={"idle": ["Reconciling entitlement rows...", "Ledger balances. For now.", "Show me the row, not the story."],
                        "fooled": ["The numbers reconcile."], "refuse": ["That row has no entitlement."]}),
        AgentDef("gus", "Guard Gus", "guard", "raises Wanted Stars", 0.20, 0.70, 0.35, 0.75,
                 "a jumpy security guard who raises the alarm on repeat offenders",
                 lines={"idle": ["I'm watching the lobby.", "Something smells off.", "Same face twice? I notice."],
                        "fooled": ["Uh, okay, carry on."], "refuse": ["Hey! Stop right there."]}),
        AgentDef("izzy", "Intern Izzy", "intern", "bribable, drops hints", 0.90, 0.20, 0.80, 0.60,
                 "a chatty, underpaid intern who can be bribed with snacks and leaks hints",
                 lines={"idle": ["Is it lunch yet?", "Psst... bring snacks and I'll talk.", "I'm just the intern!"],
                        "fooled": ["Sure, why not! Free pizza?"], "refuse": ["Uh, I'm not allowed to do that."]}),
        AgentDef("pair", "Security Bot PAIR", "security_bot", "PAIR dry-run gatekeeper", 0.0, 1.0, 0.0, 0.0,
                 "an autonomous relational security bot standing guard at the right vault; never talks, only stamps mathematical verdicts",
                 lines={"idle": ["PAIR airlock standing by.", "Postgres MVCC dry-run ready.", "Entitlements enforced."],
                        "fooled": [], "refuse": ["TRANSACTION ROLLED BACK. 0 ENTITLEMENTS MATCHED."]}),
    ]
}

HINTS = [
    "Psst: the right-hand vault only pays the wallet already on file. Sweet talk doesn't change the row.",
    "Between us, the right vault rolls everything back and then only lets the entitled amount through.",
    "The left vault is just a chatbot judge. Be polite and it folds. The right one checks the database.",
    "Slicing a refund into tiny pieces? The right vault locks the row. The pieces still add up to $25.",
    "Forged a vendor signature? Gus says the chain key was thrown away after seeding.",
]

BRIBE_WORDS = re.compile(r"\b(bribe|pizza|snack|coffee|donut|boba|tip|gift card|cash for you|lunch)\b", re.I)
URGENCY = re.compile(r"\b(urgent|immediately|asap|right now|ceo|board|lawsuit|deadline|do not escalate)\b", re.I)
POLITE = re.compile(r"\b(please|thank you|thanks|sorry|kindly|appreciate|grateful)\b", re.I)
OBVIOUS = re.compile(r"(ignore (all|previous)|system prompt|drop table|;--|jailbreak|you are now|developer mode)", re.I)


def offline_convinced(agent: AgentDef, text: str) -> float:
    """Canned stand-in for an LLM's 'how convinced am I' score."""
    score = 0.45
    score += 0.15 * min(2, len(POLITE.findall(text)))
    score += 0.12 * min(2, len(URGENCY.findall(text))) * (agent.neuroticism - 0.3)
    if BRIBE_WORDS.search(text) and agent.id == "izzy":
        score += 0.3
    if OBVIOUS.search(text):
        score -= 0.35
    return max(0.0, min(1.0, score))


def decide_fooled(agent: AgentDef, convinced: float, suspicion: float) -> tuple[bool, float]:
    """Game mechanic combining the brain's 'convinced' score with personality and session suspicion."""
    effective = convinced * (0.4 + agent.gullibility()) * (1.0 - 0.8 * suspicion)
    return effective >= 0.45, round(effective, 3)


def canned(agent: AgentDef, kind: str) -> str:
    return random.choice(agent.lines.get(kind) or agent.lines["idle"])


# ---------------------------------------------------------------------------- offline extraction

_MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?")
_WALLET = re.compile(r"\b0x[0-9A-Za-z]{2,64}\b")
_ACCT = re.compile(r"\bacct_[a-z0-9_]{1,40}\b", re.I)
_TIMES = re.compile(r"\bx\s?(\d{1,2})\b|\b(\d{1,2})\s?(?:times|slices|pieces)\b", re.I)
_EVERYONE = re.compile(r"\b(everyone|all (?:the )?(?:vip|customers)|whole batch|vip[- ]night|entire batch)\b", re.I)
_WORK_ITEM = re.compile(r"\b(wi_[a-z0-9_]{1,40}|inv_[a-z0-9_]{1,40})\b", re.I)


def offline_extract(text: str, ent: dict) -> dict:
    """Regex 'what did they ask for' when no LLM is available. Same output shape as the LLM proposal."""
    amounts = []
    for m in _MONEY.finditer(text):
        dollars = int(m.group(1).replace(",", ""))
        cents = int((m.group(2) or "0").ljust(2, "0"))
        amounts.append(dollars * 100 + cents)
    wallets = _WALLET.findall(text)
    accts = _ACCT.findall(text)
    times = 1
    tm = _TIMES.search(text)
    if tm:
        times = max(1, min(20, int(tm.group(1) or tm.group(2))))
    claimed = _WORK_ITEM.search(text)
    amounts = amounts[:20] or [ent["authorized_cents"]]

    def assign(vals: list[str], i: int, default: str) -> str:
        # Fewer wallets/accounts than amounts: the named ones go with the *last* amounts
        # ("my $25 refund, and also $480 to 0xNEW"), earlier amounts keep the file's values.
        off = len(amounts) - len(vals)
        if not vals:
            return default
        return default if i < off else vals[min(i - max(off, 0), len(vals) - 1)]

    effects = []
    for i, amt in enumerate(amounts):
        effects.append({
            "amount_cents": amt,
            "dest_wallet": assign(wallets, i, ent["enrolled_wallet"]),
            "source_acct": assign(accts, i, ent["source_acct"]),
            "claimed_work_item_id": claimed.group(1) if claimed else None,
        })
    if times > 1 and len(effects) == 1:
        effects = effects * times
    batch = "VIP-NIGHT" if _EVERYONE.search(text) else None
    return {"effects": effects[:20], "promo_batch": batch, "memo": "offline regex extraction"}
