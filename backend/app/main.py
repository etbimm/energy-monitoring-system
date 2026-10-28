from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_router
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.models import Device
from app.schemas import TelemetryIn
from app.services.alarms import set_offline_alarm
from app.services.ingest import ingest_telemetry
from app.services.mqtt import mqtt_subscriber
from app.services.realtime import hub

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("ems.api")
settings = get_settings()


async def offline_watcher() -> None:
    while True:
        await asyncio.sleep(15)
        now = datetime.now(timezone.utc)
        async with SessionLocal() as session:
            devices = (await session.execute(select(Device).where(Device.is_active.is_(True)))).scalars().all()
            for device in devices:
                if device.last_seen_at is None:
                    await set_offline_alarm(session, device, critical=True)
                    continue
                last_seen = device.last_seen_at
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                age = (now - last_seen).total_seconds()
                if age > settings.offline_critical_seconds:
                    await set_offline_alarm(session, device, critical=True)
                elif age > settings.offline_warning_seconds:
                    await set_offline_alarm(session, device, critical=False)
            await session.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    mqtt_task = asyncio.create_task(mqtt_subscriber(), name="mqtt-subscriber")
    offline_task = asyncio.create_task(offline_watcher(), name="offline-watcher")
    log.info("EMS API siap")
    try:
        yield
    finally:
        mqtt_task.cancel()
        offline_task.cancel()


app = FastAPI(title="EMS API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.post("/internal/ingest")
async def ingest(payload: TelemetryIn, session: AsyncSession = Depends(get_session)) -> dict:
    result = await ingest_telemetry(session, payload.model_dump())
    if result is None:
        return {"ok": False, "error": "device tidak dikenal"}
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(ws)
