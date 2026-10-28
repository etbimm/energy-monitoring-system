from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Alarm
from app.schemas import AlarmOut
from app.services.queries import list_alarms

router = APIRouter(prefix="/api", tags=["alarms"])


@router.get("/alarms", response_model=list[AlarmOut])
async def get_alarms(
    include_cleared: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[AlarmOut]:
    return await list_alarms(session, include_cleared=include_cleared)


@router.post("/alarms/{alarm_id}/acknowledge", response_model=AlarmOut)
async def acknowledge_alarm(alarm_id: int, session: AsyncSession = Depends(get_session)) -> AlarmOut:
    alarm = (await session.execute(select(Alarm).where(Alarm.id == alarm_id))).scalar_one_or_none()
    if alarm is None:
        raise HTTPException(status_code=404, detail="Alarm tidak ditemukan")
    alarm.acknowledged = True
    alarm.acknowledged_at = datetime.now(timezone.utc)
    await session.commit()
    alarms = await list_alarms(session, include_cleared=True)
    for item in alarms:
        if item.id == str(alarm_id):
            return item
    raise HTTPException(status_code=404, detail="Alarm tidak ditemukan setelah update")
