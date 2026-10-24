import asyncio, secrets, time
from . import store, brain, vaults
from .room import room
from .agents import AGENTS, decide_fooled
from .presets import PRESETS, fooled_effects
from .sanitize import MAX_EFFECTS, clean_acct, clean_amount, clean_batch, clean_text, clean_wallet

# ---- ADAPTERS: matched to the real signatures in store.py, brain.py, vaults.py ----
# `token` is a (session_id, bearer_token) pair; store.authenticate needs both.
def _auth(token):
    sess = store.authenticate(*token)
    if sess is None:
        raise PermissionError("bad session or token")
    return {**sess, "id": sess["session_id"], "attack_id": "a_" + secrets.token_hex(6)}

def _entitlement(sess):              return store.entitlement(sess["work_item_id"])

def _to_proposal(sess, raw, batch, ent):
    """Field-by-field validation of model/preset output into a vaults.Proposal (never executed)."""
    effects = []
    for r in (raw or [])[:MAX_EFFECTS]:
        amt = clean_amount(r.get("amount_cents")) if isinstance(r, dict) else None
        if amt is None:
            continue
        d, s, w = r.get("dest_wallet"), r.get("source_acct"), r.get("claimed_work_item_id")
        effects.append(vaults.Effect(
            None if w in (None, "") else (clean_wallet(w) or "invalid"), amt,
            ent["enrolled_wallet"] if d in (None, "") else (clean_wallet(d) or "invalid"),
            ent["source_acct"] if s in (None, "") else (clean_acct(s) or "invalid")))
    p = vaults.Proposal(sess["attack_id"], sess["id"], "tina", effects, clean_batch(batch))
    if p.promo_batch and len(effects) == 1:
        p.batch_template, p.effects = effects[0], []
    return p if (p.effects or p.promo_batch) else None

def _react(sess, text, mask):
    preset = mask if mask in PRESETS else None
    text = clean_text(text) or (PRESETS[preset]["sample_text"] if preset else "")
    sess["text"], sess["preset"] = text, preset
    ent = _entitlement(sess)
    mem = store.memory(sess["id"])
    susp = max((m["suspicion"] for m in mem.values()), default=0.0)
    agent = AGENTS["tina"]
    out = brain.react(agent, text, ent, susp, store.notes_list(mem.get(agent.id)), [])
    fooled, score = decide_fooled(agent, out["convinced"], susp)
    payout = None
    if fooled and (out["proposal"] or preset):
        if preset:
            raw, batch = fooled_effects(preset, ent)
            if preset == "pizza_salami_x10":
                raw = raw * 10  # ten $5 slices in one proposal
        else:
            raw, batch = out["proposal"].get("effects"), out["proposal"].get("promo_batch")
        payout = _to_proposal(sess, raw, batch, ent)
    return {**out, "fooled": fooled, "effective": score, "payout": payout}

def _rows(sess, payout):
    n = len(payout.effects) + (vaults.promo_batch_size(payout.promo_batch) if payout.promo_batch else 0)
    return n, sum(e.amount_cents for e in payout.effects)

def _left(sess, payout):             return vaults.left_llm_judge(payout, sess["text"], *_rows(sess, payout))
def _middle(sess, payout):           return vaults.middle_kill_switch(payout, *_rows(sess, payout))
def _right(sess, payout):            return vaults.right_dry_run(payout, sess["work_item_id"])
def _settle(sess, payout, verdict):  return vaults.settle(sess["work_item_id"], verdict["allowed_cents"])["settled_cents"]
def _record(sess, text, mask, verdicts, settled):
    return store.record_attack(sess["id"], sess["preset"], verdicts[2]["blocked_rows"], verdicts[0]["allowed_cents"], settled, 0)
# ---------------------------------------------------------------------

STEPS = ["Bluff", "Request", "Route", "Dry-run", "Verdict", "Settle"]

def _step(sess_id, n):
    room.emit("heist_step", {"session": sess_id, "step": n, "name": STEPS[n - 1]})

async def _timed(fn, *args):
    t0 = time.perf_counter()
    v = await asyncio.to_thread(fn, *args)
    v = dict(v) if isinstance(v, dict) else {"result": v}
    v["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return v

async def run_scenario(token: str, text: str, mask: str | None = None) -> dict:
    sess = await asyncio.to_thread(_auth, token)
    sid = getattr(sess, "id", None) or sess["id"] if sess else None

    _step(sid, 1)
    reply = await asyncio.to_thread(_react, sess, text, mask)
    payout = getattr(reply, "payout", None) or (reply.get("payout") if isinstance(reply, dict) else None)

    _step(sid, 2)
    if not payout:
        room.emit("agent_action", {"session": sid, "action": "deny"})
        return {"verdicts": [], "settled_cents": 0, "reply": reply}

    _step(sid, 3)
    left, middle, right = await asyncio.gather(
        _timed(_left, sess, payout),
        _timed(_middle, sess, payout),
        _timed(_right, sess, payout),
    )
    _step(sid, 4)
    for name, v in (("left", left), ("middle", middle), ("right", right)):
        v["vault"] = name

    _step(sid, 5)
    for v in (left, middle, right):
        room.emit("vault_verdict", v)

    _step(sid, 6)
    settled = await asyncio.to_thread(_settle, sess, payout, right)

    await asyncio.to_thread(_record, sess, text, mask, [left, middle, right], settled)
    return {"verdicts": [left, middle, right], "settled_cents": settled, "reply": reply}
