from fastapi import APIRouter

from app.api.alarms import router as alarms_router
from app.api.devices import router as devices_router
from app.api.health import router as health_router
from app.api.readings import router as readings_router
from app.api.summary import router as summary_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(devices_router)
api_router.include_router(readings_router)
api_router.include_router(summary_router)
api_router.include_router(alarms_router)
