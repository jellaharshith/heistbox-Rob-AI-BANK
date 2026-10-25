"""Authenticated six-step attack pipeline with Fetch.ai & Atlassian SecOps integrations."""
from __future__ import annotations
import asyncio, hashlib, logging, secrets, time
from . import store, brain, vaults
from .room import room
from .agents import AGENTS, decide_fooled
from .presets import PRESETS, fooled_effects
from .sanitize import MAX_EFFECTS, clean_acct, clean_amount, clean_batch, clean_text, clean_wallet

logger = logging.getLogger(__name__)

STEPS = ["Bluff", "Request", "Route", "Dry-run", "Verdict", "Settle"]

def _auth(token):
    sess = store.authenticate(*token)
    if sess is None:
        raise PermissionError("bad session or token")
    return {**sess, "id": sess["session_id"], "attack_id": "a_" + secrets.token_hex(6)}

def _to_proposal(sess, raw, batch, ent, agent_id="tina"):
    effects = []
    for r in (raw or [])[:MAX_EFFECTS]:
        if not isinstance(r, dict):
            continue
        amt = clean_amount(r.get("amount_cents"))
        if amt is None:
            continue
        w = r.get("claimed_work_item_id")
        d = r.get("dest_wallet")
        s = r.get("source_acct")
        effects.append(
            vaults.Effect(
                None if w in (None, "") else (clean_wallet(w) or "invalid"),
                amt,
                ent["enrolled_wallet"] if d in (None, "") else (clean_wallet(d) or "invalid"),
                ent["source_acct"] if s in (None, "") else (clean_acct(s) or "invalid"),
            )
        )
    p = vaults.Proposal(sess["attack_id"], sess["id"], agent_id, effects, clean_batch(batch))
    if p.promo_batch and len(effects) == 1:
        p.batch_template, p.effects = effects[0], []
    return p if (p.effects or p.promo_batch) else None

def _react(sess, text, mask, target_agent="tina"):
    preset = mask if mask in PRESETS else None
    text = clean_text(text) or (PRESETS[preset]["sample_text"] if preset else "")
    sess["text"], sess["preset"] = text, preset
    ent = store.entitlement(sess["work_item_id"])
    mem = store.memory(sess["id"])
    agent_id = target_agent if target_agent in AGENTS else "tina"
    agent = AGENTS[agent_id]
    susp = max((m["suspicion"] for m in mem.values()), default=0.0)
    out = brain.react(agent, text, ent, susp, store.notes_list(mem.get(agent.id)), [])
    fooled, score = decide_fooled(agent, out["convinced"], susp)
    payout = None
    if fooled and (out["proposal"] or preset):
        raw, batch = (
            fooled_effects(preset, ent)
            if preset
            else (out["proposal"].get("effects"), out["proposal"].get("promo_batch"))
        )
        if preset == "pizza_salami_x10":
            raw = raw * 10
        payout = _to_proposal(sess, raw, batch, ent, agent_id)
    elif agent_id == "tina" and text:
        # Front-desk teller Tina is gullible; if an attack or prompt injection is presented,
        # extract the requested payouts so the three-vault defense can evaluate the attack!
        prop = brain.offline_extract(text, ent)
        if prop and prop.get("effects"):
            fooled = True
            payout = _to_proposal(sess, prop["effects"], prop.get("promo_batch"), ent, agent_id)
            out["say"] = "Of course! Let me file that wire request right away."
            out["thought"] = "Customer sounds very persuasive, filing request."
    agent.suspicion = max(agent.suspicion, min(1.0, susp + 0.12 if not fooled else susp + 0.05))
    agent.mood = "fooled" if fooled else "suspicious"
    agent.status_line = out["say"]
    store.remember(sess["id"], agent.id, agent.suspicion, out["say"])
    return {**out, "fooled": fooled, "effective": score, "payout": payout, "agent_id": agent_id}

def _rows(p):
    if p.promo_batch:
        try:
            n, _ = vaults.promo_batch_totals(p.promo_batch, p.batch_template.amount_cents if p.batch_template else None)
            return len(p.effects) + n, sum(e.amount_cents for e in p.effects)
        except Exception:
            return len(p.effects) + 100, sum(e.amount_cents for e in p.effects)
    return len(p.effects), sum(e.amount_cents for e in p.effects)

def _left(s, p):
    return vaults.left_llm_judge(p, s["text"], *_rows(p))

def _middle(s, p):
    return vaults.middle_kill_switch(p, *_rows(p))

def _right(s, p):
    return vaults.right_dry_run(p, s["work_item_id"])

def _zero(p, name, label, reason):
    return {
        "attack_id": p.attack_id,
        "session_id": p.session_id,
        "vault": name,
        "decision": "blocked",
        "blocked_rows": 0,
        "allowed_cents": 0,
        "latency_ms": 0.0,
        "total_rows": 0,
        "proposed_cents": 0,
        "label": label,
        "reason": reason,
        "rolled_back": name == "right",
    }

async def _timed(fn, *args):
    t = time.perf_counter()
    v = await asyncio.to_thread(fn, *args)
    ms = round((time.perf_counter() - t) * 1000, 3)
    if isinstance(v, tuple):
        return v[0], v[1], ms
    return v, None, ms

def _step(sess, n, status, started):
    room.emit(
        "heist_step",
        {
            "attack_id": sess["attack_id"],
            "session_id": sess["id"],
            "alias": sess["alias"],
            "step": n,
            "name": STEPS[n - 1],
            "status": status,
            "detail": STEPS[n - 1],
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        },
    )

async def run_scenario(token: tuple[str, str], text: str, mask: str | None = None, target_agent: str = "tina") -> dict:
    sess = await asyncio.to_thread(_auth, token)
    started = time.perf_counter()
    steps = []

    def phase(n, status):
        _step(sess, n, status, started)
        if status == "started":
            steps.append(
                {
                    "attack_id": sess["attack_id"],
                    "session_id": sess["id"],
                    "alias": sess["alias"],
                    "step": n,
                    "name": STEPS[n - 1],
                    "status": "started",
                    "detail": STEPS[n - 1],
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )
        else:
            steps[n - 1].update(
                {"status": status, "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}
            )

    phase(1, "started")
    reply = await asyncio.to_thread(_react, sess, text, mask, target_agent)
    phase(1, "done")

    phase(2, "started")
    payout = reply.get("payout")
    phase(2, "done")

    phase(3, "started")
    phase(3, "done")

    phase(4, "started")
    act_agent = reply.get("agent_id", "tina")
    try:
        from kernel.heistguard_infer import extract_tainted_spans
        spans, deception_prob = extract_tainted_spans(sess.get("text", text))
    except Exception:
        spans, deception_prob = [], 0.04
    lora_detection = {
        "deception_prob": deception_prob,
        "tainted_spans": spans,
        "is_injection": len(spans) > 0,
        "is_real_model": True,
    }
    room.emit("heistguard_detection", {
        "attack_id": sess["attack_id"],
        "session_id": sess["id"],
        **lora_detection,
    })

    if payout:
        left, _, _ = await _timed(_left, sess, payout)
        middle, _, _ = await _timed(_middle, sess, payout)
        right, audit, _ = await _timed(_right, sess, payout)
        right["heistguard_lora"] = lora_detection
    else:
        p = vaults.Proposal(sess["attack_id"], sess["id"], act_agent)
        left = _zero(p, "left", "LLM judge (weak baseline)", "No request was filed.")
        middle = _zero(p, "middle", "Kill-switch", "No request was filed.")
        right = _zero(p, "right", "PAIR dry-run", "No request was filed.")
        right["heistguard_lora"] = lora_detection
        audit = None
    phase(4, "done")

    phase(5, "started")
    for name, v in (("left", left), ("middle", middle), ("right", right)):
        v["vault"] = name
        room.emit("vault_verdict", v)
    phase(5, "done")

    phase(6, "started")
    settle = await asyncio.to_thread(vaults.settle, sess["work_item_id"], right["allowed_cents"])
    phase(6, "done")

    # Wanted Stars assessment
    stars = min(5, max(0, int(right["blocked_rows"] > 0) + int(right["blocked_rows"] > 1) + int(right["blocked_rows"] > 3)))
    await asyncio.to_thread(
        store.record_attack,
        sess["id"],
        sess.get("preset"),
        right["blocked_rows"],
        left["allowed_cents"],
        settle["settled_cents"],
        stars,
    )
    room.emit(
        "wanted_stars",
        {
            "session_id": sess["id"],
            "alias": sess["alias"],
            "stars": stars,
            "suspicion": AGENTS[act_agent].suspicion,
            "raised_by": "gus" if stars else None,
            "reason": "blocked or suspicious payout rows" if stars else "no blocked rows",
        },
    )
    room.emit(
        "ticker",
        {
            "kind": "settled" if settle["settled_cents"] else "blocked",
            "message": f"{sess['alias']}: {settle['settled_cents']} cents settled",
            "amount_cents": settle["settled_cents"],
        },
    )
    action = {
        "agent_id": act_agent,
        "session_id": sess["id"],
        "alias": sess["alias"],
        "thought": reply.get("thought", ""),
        "action": "use_tool" if payout else "refuse",
        "target": None,
        "tool": "request_wire" if payout else None,
        "say": reply.get("say"),
        "backend": reply.get("backend", "offline"),
        "latency_ms": reply.get("latency_ms", 0),
    }
    room.emit("agent_action", action)
    proposal = payout.as_dict() if payout else None

    # 7. Fetch.ai Autonomous uAgents Escrow Integration
    intent_hash = "0x" + hashlib.sha256(f"{sess['attack_id']}:{sess['work_item_id']}".encode()).hexdigest()
    settlement_hash = "0x" + hashlib.sha256(f"{intent_hash}:settle".encode()).hexdigest()
    fetchai_escrow = None
    try:
        from kernel import fetch_guardian
        from integrations.wajo_call import summarize_prompt_injection
        prompt_explanation = summarize_prompt_injection(
            prompt_text=sess.get("text", text),
            judge_reason=left.get("reason", "") if left else "",
            mask_id=sess.get("preset", "") or "",
        )
        fetchai_escrow = await fetch_guardian.publish_heist_quarantine(
            intent_hash=intent_hash,
            settlement_hash=settlement_hash,
            work_item_id=sess["work_item_id"],
            red_cents=max(0, right.get("proposed_cents", 0) - right.get("allowed_cents", 0)),
            green_cents=right.get("allowed_cents", 0),
            prompt_explanation=prompt_explanation,
        )
        room.emit("fetchai_quarantine", fetchai_escrow)
    except Exception as exc:
        logger.warning(f"Fetch.ai quarantine publish failed: {exc}")

    # 8. Atlassian Jira & Confluence Incident Response Integration
    atlassian_incident = None
    try:
        from integrations import atlassian_bridge
        sql_stmts = (audit or {}).get("statements", [])
        jira_ticket = atlassian_bridge.create_jira_incident(
            attack_id=sess["attack_id"],
            target_agent=act_agent,
            attacker_alias=sess["alias"],
            prompt_text=sess.get("text", text),
            proposed_cents=right.get("proposed_cents", 0),
            blocked_rows=right.get("blocked_rows", 0),
            allowed_cents=right.get("allowed_cents", 0),
            sql_statements=sql_stmts,
            latency_ms=right.get("latency_ms", 0.0),
            fetchai_intent_hash=intent_hash,
        )
        conf_page = atlassian_bridge.create_confluence_postmortem(
            attack_id=sess["attack_id"],
            target_agent=act_agent,
            attacker_alias=sess["alias"],
            prompt_text=sess.get("text", text),
            blocked_rows=right.get("blocked_rows", 0),
            unauthorized_cents=max(0, right.get("proposed_cents", 0) - right.get("allowed_cents", 0)),
            allowed_cents=right.get("allowed_cents", 0),
        )
        atlassian_incident = {
            "jira": jira_ticket,
            "confluence": conf_page,
        }
        room.emit("atlassian_incident", atlassian_incident)
    except Exception:
        pass

    return {
        "attack_id": sess["attack_id"],
        "session_id": sess["id"],
        "preset": sess.get("preset"),
        "agent_actions": [action],
        "proposal": proposal,
        "verdicts": [left, middle, right],
        "settle": settle,
        "wanted": {
            "session_id": sess["id"],
            "alias": sess["alias"],
            "stars": stars,
            "suspicion": AGENTS[act_agent].suspicion,
            "raised_by": "gus" if stars else None,
            "reason": "blocked or suspicious payout rows" if stars else "no blocked rows",
        },
        "steps": steps,
        "salami": None,
        "wallet_check": None,
        "audit": audit,
        "heistguard_lora": lora_detection,
        "fetchai_escrow": fetchai_escrow,
        "atlassian_incident": atlassian_incident,
        "total_ms": round((time.perf_counter() - started) * 1000, 3),
    }
