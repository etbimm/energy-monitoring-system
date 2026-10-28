from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import DeviceOut
from app.services.queries import list_devices

router = APIRouter(prefix="/api", tags=["devices"])


@router.get("/devices", response_model=list[DeviceOut])
async def get_devices(session: AsyncSession = Depends(get_session)) -> list[DeviceOut]:
    return await list_devices(session)


@router.get("/devices/{device_code}", response_model=DeviceOut)
async def get_device(device_code: str, session: AsyncSession = Depends(get_session)) -> DeviceOut:
    devices = await list_devices(session)
    for device in devices:
        if device.id == device_code:
            return device
    raise HTTPException(status_code=404, detail="Device tidak ditemukan")


@router.get("/devices/{device_code}/latest", response_model=DeviceOut)
async def get_device_latest(device_code: str, session: AsyncSession = Depends(get_session)) -> DeviceOut:
    return await get_device(device_code, session)
