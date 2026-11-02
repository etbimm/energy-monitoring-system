from __future__ import annotations

import time
from collections import deque

from fastapi import APIRouter, HTTPException

from app.schemas import ClientErrorIn
from app.services.error_reporting import report_error, resolve_error

router = APIRouter(prefix="/api", tags=["client-errors"])
_REPORT_WINDOW_SECONDS = 60
_REPORT_LIMIT = 30
_report_times: deque[float] = deque()


@router.post("/client-errors")
async def client_error(payload: ClientErrorIn) -> dict[str, bool]:
    now = time.monotonic()
    while _report_times and now - _report_times[0] > _REPORT_WINDOW_SECONDS:
        _report_times.popleft()
    if len(_report_times) >= _REPORT_LIMIT:
        raise HTTPException(status_code=429, detail="Terlalu banyak laporan error.")
    _report_times.append(now)

    await report_error(
        f"frontend:{payload.key}",
        f"Frontend gagal mengakses API: {payload.summary}",
    )
    return {"ok": True}


@router.post("/client-errors/{key}/resolve")
async def client_error_resolved(key: str) -> dict[str, bool]:
    if not key or len(key) > 120 or not all(
        char.isalnum() or char in "._-" for char in key
    ):
        raise HTTPException(status_code=400, detail="ID error tidak valid.")
    await resolve_error(f"frontend:{key}", "Koneksi API dari frontend kembali normal.")
    return {"ok": True}
