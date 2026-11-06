from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import EnergyTotalsOut, TimeSeriesPoint
from app.services.queries import get_energy_totals, get_readings

router = APIRouter(prefix="/api", tags=["readings"])


@router.get("/readings", response_model=list[TimeSeriesPoint])
async def readings(
    device: str | None = Query(default=None, description="device_code, kosong = agregasi role"),
    role: str | None = Query(default="incoming"),
    bucket: str = Query(default="5m"),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
) -> list[TimeSeriesPoint]:
    end = to_time or datetime.now(timezone.utc)
    start = from_time or (end - timedelta(hours=24))
    try:
        return await get_readings(
            session,
            device_code=device,
            start=start,
            end=end,
            bucket=bucket,
            role=role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/energy", response_model=EnergyTotalsOut)
async def energy_totals(
    device: str | None = Query(default=None, description="device_code, kosong = semua meter pada role"),
    role: str | None = Query(default="incoming"),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
) -> EnergyTotalsOut:
    """Total energi rentang waktu, dihitung sebagai jumlah delta per meter."""
    end = to_time or datetime.now(timezone.utc)
    start = from_time or (end - timedelta(hours=24))
    if start > end:
        raise HTTPException(status_code=400, detail="'from' harus sebelum 'to'")
    return await get_energy_totals(
        session, start=start, end=end, device_code=device, role=role
    )
