import asyncio
import json
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from . import store, brain, db
from .room import room
from .round_runner import run_scenario

@asynccontextmanager
async def lifespan(_app):
    await asyncio.to_thread(db.init_db)  # start/connect Postgres, migrate, ensure seed
    room.start()                         # round/weather loop + agent think loop
    yield
    await room.stop()
    db.close()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Photos never reach the server: player bodies are tiny JSON, so anything big or carrying a data: URI is refused.
MAX_BODY_BYTES = 10 * 1024
_NO_PHOTO_PATHS = {"/api/session", "/api/attack"}
_DATA_URI = re.compile(r"data:[\w.+-]+/[\w.+-]+[;,]", re.IGNORECASE)

def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield k
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)

@app.middleware("http")
async def reject_image_payloads(request: Request, call_next):
    if request.method == "POST" and request.url.path in _NO_PHOTO_PATHS:
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "body too large"}, status_code=413)
        raw = await request.body()
        if len(raw) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "body too large"}, status_code=413)
        try:
            parsed = json.loads(raw) if raw else None
        except ValueError:
            parsed = raw.decode("utf-8", "replace")
        if any(_DATA_URI.search(s) for s in _strings(parsed)):
            return JSONResponse({"detail": "image data not accepted"}, status_code=422)
    return await call_next(request)

class AttackIn(BaseModel):
    session: str
    text: str = Field(max_length=500)
    mask: str | None = None

@app.get("/api/health")
def health():
    return {"ok": True, "offline": brain.offline_mode()}

@app.post("/api/session")
def session(body: dict):
    return store.create_session(body.get("alias", "anon"))

@app.post("/api/attack")
async def attack(body: AttackIn, authorization: str = Header("")):
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return await run_scenario((body.session, token), body.text, body.mask)
    except PermissionError as e:
        raise HTTPException(429, str(e))

@app.get("/api/leaderboard")
def leaderboard():
    return store.leaderboard()

@app.websocket("/ws")
async def ws(sock: WebSocket):
    await room.connect(sock)  # accepts, sends snapshot, streams events until disconnect
