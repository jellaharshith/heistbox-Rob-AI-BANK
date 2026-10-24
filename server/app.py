import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
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
