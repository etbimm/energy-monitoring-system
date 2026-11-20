from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db import get_session
from app.models import Alarm, Device
from app.schemas import AlarmOut
from app.services.queries import alarm_out, list_alarms

router = APIRouter(prefix="/api", tags=["alarms"])


@router.get("/alarms", response_model=list[AlarmOut])
async def get_alarms(
    include_cleared: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[AlarmOut]:
    return await list_alarms(session, include_cleared=include_cleared)


@router.post(
    "/alarms/{alarm_id}/acknowledge",
    response_model=AlarmOut,
    dependencies=[Depends(require_admin)],
)
async def acknowledge_alarm(alarm_id: int, session: AsyncSession = Depends(get_session)) -> AlarmOut:
    # Ambil alarm beserta device-nya sekali saja, lalu bentuk respons dari
    # objek yang sama (tanpa query ulang seluruh daftar alarm).
    row = (
        await session.execute(
            select(Alarm, Device)
            .join(Device, Device.id == Alarm.device_id)
            .where(Alarm.id == alarm_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alarm tidak ditemukan")

    alarm, device = row
    alarm.acknowledged = True
    alarm.acknowledged_at = datetime.now(timezone.utc)
    await session.flush()
    result = alarm_out(alarm, device)
    await session.commit()
    return result
