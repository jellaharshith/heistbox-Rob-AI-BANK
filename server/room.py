"""Realtime room: one shared broadcast to every connected WebSocket, plus rounds/weather and the think loop."""
from __future__ import annotations

import asyncio
import json
import random
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from fastapi import WebSocket

from server import brain, config, store
from server.agents import AGENTS

PHASES = [("clear_night", "Clear Night"), ("rain", "Rain"), ("fog", "Fog"), ("dust", "Dust")]


def _iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Room:
    def __init__(self):
        self.clients: dict[WebSocket, asyncio.Queue] = {}
        self.seq = 0
        self.round_id = 1
        self.round_started = datetime.now(timezone.utc)
        self.phase = 0
        self.recent: deque[str] = deque(maxlen=12)
        self.stats = self._zero_stats()
        self._tasks: list[asyncio.Task] = []

    @staticmethod
    def _zero_stats() -> dict:
        return {"attacks": 0, "blocked_rows_right": 0, "allowed_cents_right": 0, "left_would_pay_cents": 0}

    # ------------------------------------------------------------------ broadcast
    def envelope(self, type_: str, data: dict) -> str:
        self.seq += 1
        return json.dumps({"type": type_, "seq": self.seq, "ts": _iso(), "round_id": self.round_id, "data": data})

    def emit(self, type_: str, data: dict) -> None:
        msg = self.envelope(type_, data)
        if type_ == "ticker":
            self.recent.append(data["message"])
        for q in list(self.clients.values()):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass  # slow client: drop rather than stall the room

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self.clients[ws] = q
        for a in AGENTS.values():
            q.put_nowait(self.envelope("agent_state", a.state()))
        q.put_nowait(self.envelope("weather", self.weather()))

        async def sender():
            while True:
                await ws.send_text(await q.get())

        send_task = asyncio.create_task(sender())
        try:
            while True:
                await ws.receive_text()  # inbound ignored (ping etc.); this just detects disconnect
        except Exception:  # noqa: BLE001
            pass
        finally:
            send_task.cancel()
            self.clients.pop(ws, None)

    # ------------------------------------------------------------------ rounds & weather
    def weather(self) -> dict:
        cond, label = PHASES[self.phase]
        quarter = config.ROUND_SECONDS / 4
        ends = self.round_started + timedelta(seconds=(self.phase + 1) * quarter)
        return {"condition": cond, "label": label, "round_id": self.round_id, "phase": self.phase, "phase_ends_at": _iso(ends)}

    async def _round_loop(self) -> None:
        while True:
            await asyncio.sleep(1)
            elapsed = (datetime.now(timezone.utc) - self.round_started).total_seconds()
            if elapsed >= config.ROUND_SECONDS:
                top = await asyncio.to_thread(store.leaderboard, 5)
                self.emit("round_end", {"round_id": self.round_id, "started_at": _iso(self.round_started),
                                        "ended_at": _iso(), **self.stats, "top": top})
                self.round_id += 1
                self.round_started = datetime.now(timezone.utc)
                self.phase = 0
                self.stats = self._zero_stats()
                for a in AGENTS.values():
                    a.suspicion, a.mood = 0.0, "idle"
                    self.emit("agent_state", a.state())
                self.emit("weather", self.weather())
            else:
                p = min(3, int(elapsed // (config.ROUND_SECONDS / 4)))
                if p != self.phase:
                    self.phase = p
                    self.emit("weather", self.weather())

    # ------------------------------------------------------------------ think loop
    async def _think_loop(self) -> None:
        order = list(AGENTS.values())
        i = 0
        while True:
            await asyncio.sleep(random.uniform(config.THINK_MIN_S, config.THINK_MAX_S))
            if not self.clients:
                continue
            agent = order[i % len(order)]
            i += 1
            agent.mood = "thinking"
            self.emit("agent_state", agent.state())
            out = await asyncio.to_thread(brain.ambient, agent, list(self.recent))
            self.emit("agent_action", {"agent_id": agent.id, "session_id": None, "alias": None,
                                       "thought": out["thought"], "action": out["action"], "target": out["target"],
                                       "tool": out["tool"], "say": out["say"] or None, "backend": out["backend"],
                                       "latency_ms": round(out["latency_ms"], 1)})
            agent.mood = "suspicious" if agent.suspicion > 0.5 else "idle"
            agent.status_line = out["say"] or out["thought"]
            self.emit("agent_state", agent.state())

    def start(self) -> None:
        self._tasks.append(asyncio.create_task(self._round_loop()))
        if config.THINK_LOOP:
            self._tasks.append(asyncio.create_task(self._think_loop()))

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()


room = Room()
started_at = time.monotonic()
