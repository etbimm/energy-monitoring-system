from __future__ import annotations

import time
from collections import deque

from fastapi import APIRouter, HTTPException, Request

from app.schemas import ClientErrorIn
from app.services.error_reporting import report_error, resolve_error

router = APIRouter(prefix="/api", tags=["client-errors"])
_REPORT_WINDOW_SECONDS = 60
_REPORT_LIMIT = 30
_MAX_TRACKED_IPS = 10_000

# Jendela waktu laporan per alamat IP. Satu klien yang error berulang tidak
# boleh menghabiskan kuota klien lain.
_report_times: dict[str, deque[float]] = {}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _prune_ips(now: float) -> None:
    if len(_report_times) <= _MAX_TRACKED_IPS:
        return
    for key in [
        key
        for key, bucket in _report_times.items()
        if not bucket or now - bucket[-1] > _REPORT_WINDOW_SECONDS
    ]:
        del _report_times[key]
    # Tetap batasi memori walau semua IP masih aktif dalam jendela waktu.
    while len(_report_times) > _MAX_TRACKED_IPS:
        _report_times.pop(next(iter(_report_times)))


def _allow_report(ip: str, now: float | None = None) -> bool:
    """Catat satu laporan untuk `ip`; False bila kuota IP tersebut habis."""
    now = time.monotonic() if now is None else now
    bucket = _report_times.setdefault(ip, deque())
    while bucket and now - bucket[0] > _REPORT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _REPORT_LIMIT:
        return False
    bucket.append(now)
    _prune_ips(now)
    return True


@router.post("/client-errors")
async def client_error(payload: ClientErrorIn, request: Request) -> dict[str, bool]:
    if not _allow_report(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Terlalu banyak laporan error.")

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
