from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import SummaryOut
from app.services.queries import get_summary

router = APIRouter(prefix="/api", tags=["summary"])


@router.get("/summary/today", response_model=SummaryOut)
async def summary_today(session: AsyncSession = Depends(get_session)) -> SummaryOut:
    return await get_summary(session)
