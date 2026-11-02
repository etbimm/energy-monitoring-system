from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable

import httpx

from app.config import get_settings

log = logging.getLogger("ems.errors")
_SENSITIVE_VALUE = re.compile(
    r"(?i)\b([\w-]*(?:password|passwd|token|secret|authorization|api[_-]?key))\b\s*[:=]\s*([^\s,;]+)"
)
_URL_CREDENTIALS = re.compile(r"(://)[^/@\s]+:[^/@\s]+@")
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")


def _safe_text(value: str, limit: int = 500) -> str:
    value = _URL_CREDENTIALS.sub(r"\1[REDACTED]@", value)
    value = _BEARER_TOKEN.sub("Bearer [REDACTED]", value)
    value = _SENSITIVE_VALUE.sub(r"\1=[REDACTED]", value)
    return value[:limit]


class ErrorReporter:
    def __init__(
        self,
        sender: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._active: dict[str, str] = {}
        self._sender = sender

    async def report(
        self,
        key: str,
        summary: str,
        error: Exception | str | None = None,
    ) -> None:
        safe_summary = _safe_text(summary)
        if key in self._active:
            log.debug("Error masih aktif [%s]: %s", key, safe_summary)
            return

        self._active[key] = safe_summary
        detail = ""
        if error is not None:
            detail = _safe_text(
                f"{type(error).__name__}: {error}"
                if isinstance(error, Exception)
                else error,
                800,
            )
        log.error("Error baru [%s]: %s%s", key, safe_summary, f" ({detail})" if detail else "")

        message = f"EMS ERROR\n{safe_summary}"
        if detail:
            message += f"\nDetail: {detail}"
        await self._notify(message)

    async def resolve(self, key: str, summary: str | None = None) -> None:
        previous = self._active.pop(key, None)
        if previous is None:
            return

        recovery = _safe_text(summary or previous)
        log.info("Error pulih [%s]: %s", key, recovery)
        await self._notify(f"EMS PULIH\n{recovery}")

    async def _notify(self, message: str) -> None:
        try:
            if self._sender is not None:
                await self._sender(message)
                return

            settings = get_settings()
            if not settings.telegram_bot_token or not settings.telegram_chat_id:
                return

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.telegram_chat_id,
                        "text": message[:4000],
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            log.warning("Gagal mengirim notifikasi Telegram (%s)", type(exc).__name__)


error_reporter = ErrorReporter()


async def report_error(
    key: str,
    summary: str,
    error: Exception | str | None = None,
) -> None:
    await error_reporter.report(key, summary, error)


async def resolve_error(key: str, summary: str | None = None) -> None:
    await error_reporter.resolve(key, summary)
