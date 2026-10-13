"""Chapter 7: in-memory multi-turn session store (process-local)."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any
from uuid import uuid4


class SessionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._data: dict[str, dict[str, Any]] = {}

    def create(self, tenant_id: str = "default", role: str = "ehs_engineer") -> dict[str, Any]:
        sid = f"ses_{uuid4().hex[:12]}"
        rec = {
            "session_id": sid,
            "tenant_id": tenant_id,
            "role": role,
            "history": [],  # [{role, content}, ...]
            "turns": 0,
        }
        with self._lock:
            self._data[sid] = rec
        return deepcopy(rec)

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            rec = self._data.get(session_id)
            return deepcopy(rec) if rec else None

    def append_turn(self, session_id: str, user: str, assistant: str) -> dict[str, Any]:
        with self._lock:
            rec = self._data.get(session_id)
            if not rec:
                raise KeyError(session_id)
            rec["history"].append({"role": "user", "content": user})
            rec["history"].append({"role": "assistant", "content": assistant})
            # keep last 20 messages (10 turns)
            if len(rec["history"]) > 20:
                rec["history"] = rec["history"][-20:]
            rec["turns"] += 1
            return deepcopy(rec)

    def history(self, session_id: str) -> list[dict[str, str]]:
        rec = self.get(session_id)
        if not rec:
            return []
        return list(rec.get("history") or [])


sessions = SessionStore()
