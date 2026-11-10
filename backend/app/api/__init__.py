from fastapi import APIRouter, Depends

from app.api.admin import router as admin_router
from app.api.alarms import router as alarms_router
from app.api.auth import router as auth_router
from app.api.client_errors import router as client_errors_router
from app.api.deps import get_current_user
from app.api.devices import router as devices_router
from app.api.health import router as health_router
from app.api.readings import router as readings_router
from app.api.summary import router as summary_router

# Wajib login (viewer atau admin) untuk semua data monitoring.
LOGIN_REQUIRED = [Depends(get_current_user)]

api_router = APIRouter()
# Publik: health check, login/logout, dan laporan error jaringan dari frontend
# (dikirim justru saat API tidak terjangkau; sudah dibatasi rate limit).
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(client_errors_router)

api_router.include_router(devices_router, dependencies=LOGIN_REQUIRED)
api_router.include_router(readings_router, dependencies=LOGIN_REQUIRED)
api_router.include_router(summary_router, dependencies=LOGIN_REQUIRED)
api_router.include_router(alarms_router, dependencies=LOGIN_REQUIRED)

# Khusus admin (pengecekan role ada di router admin sendiri).
api_router.include_router(admin_router)
