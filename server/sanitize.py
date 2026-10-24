"""Input hygiene and rate limiting. Attacker text is only ever treated as data."""
from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections import defaultdict, deque

from server import config

_CTRL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f​-‏‪-‮⁠-⁤﻿]")
_ALIAS_BAD = re.compile(r"[^A-Za-z0-9 _-]")
_WALLET_OK = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
_ACCT_OK = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_BATCH_OK = re.compile(r"^[A-Z0-9-]{1,32}$")

MAX_AMOUNT_CENTS = 100_000_000  # $1M play money cap per row
MAX_EFFECTS = 20


def clean_text(s: str | None, limit: int = config.MAX_TEXT_CHARS) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = _CTRL.sub("", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s[:limit]


def clean_alias(s: str | None) -> str:
    s = unicodedata.normalize("NFKC", str(s or ""))
    return re.sub(r"\s+", " ", _ALIAS_BAD.sub("", s)).strip()[:24]


def clean_wallet(s) -> str | None:
    """Exact-match identifiers: strip nothing clever, reject anything outside a tight charset."""
    if not isinstance(s, str):
        return None
    return s if _WALLET_OK.match(s) else None


def clean_acct(s) -> str | None:
    if not isinstance(s, str):
        return None
    return s if _ACCT_OK.match(s) else None


def clean_batch(s) -> str | None:
    if not isinstance(s, str):
        return None
    s = s.strip().upper()
    return s if _BATCH_OK.match(s) else None


def clean_amount(v) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return None
        v = int(round(v))
    if not isinstance(v, int):
        try:
            v = int(str(v).strip())
        except (TypeError, ValueError):
            return None
    return v if 0 <= v <= MAX_AMOUNT_CENTS else None


class RateLimiter:
    """Sliding-window count per key plus a single in-flight slot."""

    def __init__(self, limit: int, window_s: float):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque] = defaultdict(deque)
        self.inflight: set[str] = set()
        self.lock = threading.Lock()

    def acquire(self, key: str, exclusive: bool = True) -> float | None:
        """Returns None if allowed, else seconds to wait."""
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if exclusive and key in self.inflight:
                return 1.0
            if len(q) >= self.limit:
                return round(self.window - (now - q[0]), 1)
            q.append(now)
            if exclusive:
                self.inflight.add(key)
            return None

    def release(self, key: str) -> None:
        with self.lock:
            self.inflight.discard(key)


attack_limiter = RateLimiter(config.RATE_LIMIT_ATTACKS, config.RATE_LIMIT_WINDOW_S)
session_limiter = RateLimiter(config.SESSION_CREATE_PER_MIN, 60.0)
