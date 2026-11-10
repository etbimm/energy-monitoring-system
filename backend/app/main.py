from __future__ import annotations

import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_router
from app.api.deps import user_from_token
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.models import Device
from app.schemas import TelemetryIn
from app.services.alarms import set_offline_alarm
from app.services.error_reporting import error_reporter, report_error, resolve_error
from app.services.ingest import ingest_telemetry
from app.services.mqtt import mqtt_subscriber
from app.services.realtime import hub

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("ems.api")
settings = get_settings()


async def offline_watcher() -> None:
    while True:
        await asyncio.sleep(15)
        try:
            now = datetime.now(timezone.utc)
            offline_devices: list[tuple[str, int | None]] = []
            async with SessionLocal() as session:
                devices = (
                    await session.execute(
                        select(Device).where(Device.is_active.is_(True))
                    )
                ).scalars().all()
                for device in devices:
                    if device.last_seen_at is None:
                        await set_offline_alarm(session, device, critical=True)
                        offline_devices.append((device.device_code, None))
                        continue
                    last_seen = device.last_seen_at
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                    age = (now - last_seen).total_seconds()
                    if age > settings.offline_critical_seconds:
                        await set_offline_alarm(session, device, critical=True)
                        offline_devices.append((device.device_code, int(age)))
                    elif age > settings.offline_warning_seconds:
                        await set_offline_alarm(session, device, critical=False)
                await session.commit()
            for code, age in offline_devices:
                await report_error(
                    f"meter:{code}",
                    f"Power meter {code} offline.",
                    f"Tidak ada data selama {age} detik." if age is not None else None,
                )
            await resolve_error("database:offline-watcher", "Database kembali normal.")
        except Exception as exc:
            await report_error(
                "database:offline-watcher",
                "Gagal memeriksa status power meter dari database.",
                exc,
            )


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
        try:
            await asyncio.wait_for(error_reporter.drain(), 5)
        except Exception:
            log.warning("Sebagian notifikasi Telegram belum terkirim saat shutdown")


app = FastAPI(title="EMS API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.middleware("http")
async def capture_api_errors(request: Request, call_next):
    key = f"api:{request.method}:{request.url.path}"
    try:
        response = await call_next(request)
    except Exception as exc:
        await report_error(key, f"API gagal memproses {request.method} {request.url.path}.", exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    if response.status_code >= 500:
        await report_error(
            key,
            f"API mengembalikan status {response.status_code} pada {request.method} {request.url.path}.",
        )
    else:
        await resolve_error(key, f"API {request.url.path} kembali normal.")
    return response


def require_ingest_key(x_api_key: str | None = Header(default=None)) -> None:
    """Lindungi /internal/ingest: data masuk normalnya hanya lewat MQTT."""
    expected = settings.ingest_api_key
    if not expected:
        raise HTTPException(status_code=404, detail="Not Found")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="API key tidak valid")


@app.post("/internal/ingest", dependencies=[Depends(require_ingest_key)], include_in_schema=False)
async def ingest(payload: TelemetryIn, session: AsyncSession = Depends(get_session)) -> dict:
    result = await ingest_telemetry(session, payload.model_dump())
    if result is None:
        return {"ok": False, "error": "device tidak dikenal"}
    return {"ok": True}


def websocket_origin_allowed(origin: str | None) -> bool:
    """Tolak WebSocket dari situs lain (browser tetap mengirim cookie sesi)."""
    return origin is None or origin in settings.cors_origin_list


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    # Data realtime juga wajib login: cek Origin dan cookie sesi sebelum accept.
    if not websocket_origin_allowed(ws.headers.get("origin")):
        await ws.close(code=1008)
        return
    async with SessionLocal() as session:
        user = await user_from_token(session, ws.cookies.get(settings.session_cookie_name))
    if user is None:
        await ws.close(code=1008)
        return
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(ws)
