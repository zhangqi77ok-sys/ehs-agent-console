"""Ch16: last eval result endpoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import get_identity

router = APIRouter(prefix="/api/eval", tags=["eval"])

_LAST = Path(__file__).resolve().parents[2] / "eval" / "last_result.json"


@router.get("/last")
def last_eval(identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    if not _LAST.exists():
        return {
            "available": False,
            "hint": "运行: cd backend && LLM_PROVIDER=mock python scripts/run_eval.py",
            "viewer": identity.get("actor") or identity.get("role"),
        }
    try:
        data = json.loads(_LAST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"last_result corrupt: {exc}") from exc
    return {"available": True, **data}
