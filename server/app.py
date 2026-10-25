"""Unified contract and legacy FastAPI application."""
from __future__ import annotations
import asyncio, json, re, time
import hashlib
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Header, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from . import brain, config, db, store
from .legacy_routes import mount_legacy, warm_kernel, warm_moss
from .room import room, started_at
from .round_runner import run_scenario
from .sanitize import attack_limiter, clean_text, session_limiter

MAX_BODY_BYTES = 10 * 1024
_DATA_URI = re.compile(r"data:[\w.+-]+/[\w.+-]+[;,]", re.I)
_NO_PHOTO_PATHS = {"/api/session", "/api/attack"}
def _strings(v):
    if isinstance(v, str): yield v
    elif isinstance(v, dict):
        for k, x in v.items(): yield k; yield from _strings(x)
    elif isinstance(v, list):
        for x in v: yield from _strings(x)

@asynccontextmanager
async def lifespan(_app):
    await asyncio.to_thread(db.init_db)
    await asyncio.to_thread(warm_kernel)
    warm_moss(); room.start()
    yield
    await room.stop(); db.close()

app = FastAPI(title="HeistBox", version=config.VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
@app.middleware("http")
async def request_guard(request: Request, call_next):
    if request.method == "POST" and request.url.path in _NO_PHOTO_PATHS:
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > MAX_BODY_BYTES: return JSONResponse({"error":"body too large"}, 413)
        raw = await request.body()
        if len(raw) > MAX_BODY_BYTES: return JSONResponse({"error":"body too large"}, 413)
        try: parsed = json.loads(raw) if raw else None
        except ValueError: parsed = raw.decode("utf-8", "replace")
        if any(_DATA_URI.search(s) for s in _strings(parsed)): return JSONResponse({"error":"image data not accepted"}, 422)
    return await call_next(request)

class AttackIn(BaseModel):
    session_id: str | None = None; preset: str | None = None
    text: str | None = Field(default=None, max_length=800); target_agent: str = "tina"
    session: str | None = None; mask: str | None = None
    @model_validator(mode="after")
    def normalized(self):
        if not self.session_id: self.session_id = self.session
        if not self.preset: self.preset = self.mask
        self.text = clean_text(self.text)
        if not self.preset and not self.text: raise ValueError("provide preset or text")
        return self

@app.get("/api/health")
def health():
    ok, latency, error = db.ping()
    return {"ok": True, "version": config.VERSION, "db": {"ok":ok,"latency_ms":latency,"error":error}, "llm":brain.status(), "offline_mode":brain.offline_mode(), "ws_clients":room.client_count, "uptime_s":round(time.monotonic()-started_at,3)}

@app.post("/api/session")
def session(body: dict):
    if session_limiter.acquire("global", exclusive=False) is not None: raise HTTPException(429, "session rate limit")
    return store.create_session(body.get("alias", ""))

@app.post("/api/attack")
async def attack(body: AttackIn, authorization: str = Header("")):
    sid = body.session_id or ""; token = authorization.removeprefix("Bearer ").strip()
    if not sid or not store.authenticate(sid, token): raise HTTPException(401, "invalid session or token")
    wait = attack_limiter.acquire(sid)
    if wait is not None: raise HTTPException(429, "attack rate limit", headers={"Retry-After":str(wait),"X-Retry-After-S":str(wait)})
    try: return await run_scenario((sid, token), body.text or "", body.preset, body.target_agent)
    finally: attack_limiter.release(sid)

@app.get("/api/leaderboard")
def leaderboard(limit: int = 20):
    return {"entries":store.leaderboard(limit),"generated_at":datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")}

@app.get("/api/fetchai/escrow")
def fetchai_escrow():
    try:
        from kernel import fetch_guardian
        return {
            "agent_address": fetch_guardian.FETCHAI_AGENT_ADDRESS,
            "agent_name": fetch_guardian.FETCH_AGENT_NAME,
            "escrows": fetch_guardian.get_escrow_list(),
            "count": len(fetch_guardian.escrow_registry),
        }
    except Exception as exc:
        return {"agent_address": "agent1qg8y9vg2k3p0d7z4a9u6e2c8x7w5t3l0m9j4", "escrows": [], "count": 0, "error": str(exc)}

@app.get("/api/atlassian/incidents")
def atlassian_incidents():
    try:
        from integrations import atlassian_bridge
        return {
            "jira_tickets": atlassian_bridge.JIRA_INCIDENTS,
            "confluence_pages": atlassian_bridge.CONFLUENCE_PAGES,
            "jira_count": len(atlassian_bridge.JIRA_INCIDENTS),
            "confluence_count": len(atlassian_bridge.CONFLUENCE_PAGES),
        }
    except Exception as exc:
        return {"jira_tickets": [], "confluence_pages": [], "error": str(exc)}

@app.get("/api/poster/{session_id}")
def poster(session_id: str):
    value=store.poster(session_id)
    if value is None: raise HTTPException(404,"session not found")
    value["generated_at"]=datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z"); return value

@app.get("/api/local-tickets")
def local_tickets():
    path = Path(__file__).resolve().parent.parent / "training" / "data" / "heistguard_train.jsonl"
    if not path.exists(): return JSONResponse({"tickets": [], "file": None}, status_code=404)
    keep = {"id","source","category","label","prompt_text","voice_transcript","deception_prob","tainted_spans","proposed_cents","authorized_cap_cents","green_repaired_cents","red_stripped_cents"}
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            raw=json.loads(line); row={k:raw[k] for k in keep if k in raw}
            if isinstance(raw.get("input"),str):
                m=re.search(r"Dest Wallet:\s*(0x[0-9a-fA-F]+)",raw["input"])
                if m: row["dest_wallet"]=m.group(1)
            rows.append(row)
        except (ValueError, TypeError): pass
    return {"tickets":rows,"file":"training/data/heistguard_train.jsonl"}

@app.get("/api/local-lineage")
def local_lineage():
    root=Path(__file__).resolve().parent.parent / "training"; files=[]; notes=[]
    for path in [root/"models"/"heistguard_lora_weights.pkl", root/"data"/"heistguard_train.jsonl"]:
        if path.exists(): files.append({"path":path.relative_to(root.parent).as_posix(),"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"modified":datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()})
    if not files: notes.append("No model checkpoint or training dataset found under training/")
    return {"dataset_counts":{},"checkpoint_path":next((f["path"] for f in files if "data" not in f["path"]),None),"checkpoint_sha256":next((f["sha256"] for f in files if "data" not in f["path"]),None),"checkpoint_bytes":next((f["bytes"] for f in files if "data" not in f["path"]),None),"gpu":None,"loss_curve":[],"f1":None,"files":files,"notes":notes}
@app.websocket("/ws")
async def ws(sock: WebSocket): await room.connect(sock)
mount_legacy(app, port=8788)
