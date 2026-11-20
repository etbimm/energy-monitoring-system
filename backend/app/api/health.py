import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.services import mqtt_state

router = APIRouter(tags=["health"])
log = logging.getLogger("ems.health")


@router.get("/health")
@router.get("/api/health")
async def health(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """Status database dan koneksi MQTT subscriber backend."""
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        log.warning("Health check database query failed")
        database = "error"

    mqtt = "ok" if mqtt_state.mqtt_state() == "ok" else "error"
    healthy = database == "ok" and mqtt == "ok"

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "database": database,
            "mqtt": mqtt,
        },
    )
