from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Protocol

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


class NotificationStore(Protocol):
    """Penyimpanan status notifikasi aktif (dibagi antar proses & restart)."""

    async def active(self) -> dict[str, str]: ...

    async def claim(self, key: str, summary: str) -> bool:
        """True bila key baru tercatat (belum pernah dinotifikasi)."""

    async def release(self, key: str) -> bool:
        """True bila key aktif dan berhasil dihapus."""


class DbNotificationStore:
    """Status notifikasi di tabel `notification_state`.

    Dengan INSERT ... ON CONFLICT, hanya satu proses (backend/acquisition)
    yang mengirim notifikasi untuk key yang sama, dan restart service tidak
    mengirim ulang error yang masih aktif.
    """

    async def active(self) -> dict[str, str]:
        from sqlalchemy import text

        from app.db import SessionLocal

        async with SessionLocal() as session:
            rows = (await session.execute(text("SELECT key, summary FROM notification_state"))).all()
        return {row.key: row.summary for row in rows}

    async def claim(self, key: str, summary: str) -> bool:
        from sqlalchemy import text

        from app.db import SessionLocal

        async with SessionLocal() as session:
            inserted = (
                await session.execute(
                    text(
                        "INSERT INTO notification_state (key, summary) VALUES (:key, :summary) "
                        "ON CONFLICT (key) DO NOTHING RETURNING key"
                    ),
                    {"key": key, "summary": summary},
                )
            ).first()
            await session.commit()
        return inserted is not None

    async def release(self, key: str) -> bool:
        from sqlalchemy import text

        from app.db import SessionLocal

        async with SessionLocal() as session:
            deleted = (
                await session.execute(
                    text("DELETE FROM notification_state WHERE key = :key RETURNING key"),
                    {"key": key},
                )
            ).first()
            await session.commit()
        return deleted is not None


_STORE_TIMEOUT_SECONDS = 3.0
_QUEUE_SIZE = 100


class ErrorReporter:
    def __init__(
        self,
        sender: Callable[[str], Awaitable[None]] | None = None,
        store: NotificationStore | None = None,
        background: bool = False,
        min_interval: float = 1.0,
    ) -> None:
        self._active: dict[str, str] = {}
        # Key yang aktif tetapi gagal dicatat di store (mis. database mati);
        # notifikasi pulihnya tetap dikirim walau store tidak punya catatannya.
        self._unpersisted: set[str] = set()
        self._sender = sender
        self._store = store
        self._loaded = store is None
        # Mode background: pesan dimasukkan antrean dan dikirim worker terpisah,
        # sehingga request API / ingest tidak menunggu Telegram (timeout 5 s).
        self._background = background
        self._min_interval = min_interval
        self._queue: asyncio.Queue[str] | None = None
        self._worker: asyncio.Task | None = None

    async def _store_call(self, coro):
        return await asyncio.wait_for(coro, _STORE_TIMEOUT_SECONDS)

    async def _ensure_loaded(self) -> None:
        """Muat error yang masih aktif dari store sekali (setelah restart)."""
        if self._loaded or self._store is None:
            return
        try:
            stored = await self._store_call(self._store.active())
        except Exception as exc:
            log.debug("Gagal memuat status notifikasi (%s)", type(exc).__name__)
            return
        for key, summary in stored.items():
            self._active.setdefault(key, summary)
        self._loaded = True

    async def report(
        self,
        key: str,
        summary: str,
        error: Exception | str | None = None,
        *,
        title: str = "EMS ERROR",
    ) -> None:
        safe_summary = _safe_text(summary)
        await self._ensure_loaded()
        if key in self._active:
            log.debug("Error masih aktif [%s]: %s", key, safe_summary)
            return

        self._active[key] = safe_summary
        if self._store is not None:
            try:
                claimed = await self._store_call(self._store.claim(key, safe_summary))
            except Exception as exc:
                log.debug("Gagal mencatat status notifikasi (%s)", type(exc).__name__)
                self._unpersisted.add(key)
                claimed = True
            if not claimed:
                log.debug("Error [%s] sudah dinotifikasi sebelumnya", key)
                return

        detail = ""
        if error is not None:
            detail = _safe_text(
                f"{type(error).__name__}: {error}"
                if isinstance(error, Exception)
                else error,
                800,
            )
        log.error("Error baru [%s]: %s%s", key, safe_summary, f" ({detail})" if detail else "")

        message = f"{title}\n{safe_summary}"
        if detail:
            message += f"\nDetail: {detail}"
        await self._notify(message)

    async def resolve(
        self,
        key: str,
        summary: str | None = None,
        *,
        title: str = "EMS PULIH",
    ) -> None:
        await self._ensure_loaded()
        previous = self._active.pop(key, None)
        if previous is None:
            return

        unpersisted = key in self._unpersisted
        self._unpersisted.discard(key)
        if self._store is not None:
            try:
                released = await self._store_call(self._store.release(key))
            except Exception as exc:
                log.debug("Gagal menghapus status notifikasi (%s)", type(exc).__name__)
                released = True
            if not released and not unpersisted:
                # Sudah dipulihkan proses lain; jangan kirim ganda.
                return

        recovery = _safe_text(summary or previous)
        log.info("Error pulih [%s]: %s", key, recovery)
        await self._notify(f"{title}\n{recovery}")

    async def _notify(self, message: str) -> None:
        if self._background:
            self._enqueue(message)
            return
        await self._deliver(message)

    def _enqueue(self, message: str) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=_QUEUE_SIZE)
        if self._worker is None or self._worker.done():
            self._worker = asyncio.get_running_loop().create_task(
                self._run_worker(), name="telegram-notifier"
            )
        try:
            self._queue.put_nowait(message)
        except asyncio.QueueFull:
            log.warning("Antrean notifikasi Telegram penuh; pesan dibuang")

    async def _run_worker(self) -> None:
        assert self._queue is not None
        while True:
            message = await self._queue.get()
            try:
                await self._deliver(message)
            finally:
                self._queue.task_done()
            # Jaga di bawah batas Telegram (~1 pesan/detik per chat).
            await asyncio.sleep(self._min_interval)

    async def drain(self) -> None:
        """Tunggu sampai semua pesan di antrean terkirim (mis. saat shutdown)."""
        if self._queue is not None and self._worker is not None and not self._worker.done():
            await self._queue.join()

    async def _deliver(self, message: str) -> None:
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
        except httpx.HTTPStatusError as exc:
            # Kode status + alasan dari Telegram (tanpa URL yang memuat token).
            try:
                reason = exc.response.json().get("description", "")
            except Exception:
                reason = ""
            log.warning(
                "Gagal mengirim notifikasi Telegram (HTTP %s %s)",
                exc.response.status_code,
                _safe_text(str(reason), 200),
            )
        except Exception as exc:
            log.warning("Gagal mengirim notifikasi Telegram (%s)", type(exc).__name__)


error_reporter = ErrorReporter(store=DbNotificationStore(), background=True)


async def report_error(
    key: str,
    summary: str,
    error: Exception | str | None = None,
) -> None:
    await error_reporter.report(key, summary, error)


async def resolve_error(key: str, summary: str | None = None) -> None:
    await error_reporter.resolve(key, summary)
