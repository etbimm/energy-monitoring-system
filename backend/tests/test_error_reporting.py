import pytest

from app.services.error_reporting import ErrorReporter


@pytest.mark.asyncio
async def test_error_notification_is_deduplicated_until_recovery():
    messages = []

    async def send(message: str) -> None:
        messages.append(message)

    reporter = ErrorReporter(sender=send)

    await reporter.report("mqtt:subscriber", "MQTT terputus.")
    await reporter.report("mqtt:subscriber", "MQTT terputus.")
    await reporter.resolve("mqtt:subscriber", "MQTT kembali normal.")
    await reporter.resolve("mqtt:subscriber", "MQTT kembali normal.")

    assert messages == [
        "EMS ERROR\nMQTT terputus.",
        "EMS PULIH\nMQTT kembali normal.",
    ]


@pytest.mark.asyncio
async def test_error_details_redact_credentials(caplog):
    messages = []

    async def send(message: str) -> None:
        messages.append(message)

    reporter = ErrorReporter(sender=send)
    await reporter.report(
        "database:connection",
        "Database gagal diakses.",
        RuntimeError("MQTT_PASSWORD=private TELEGRAM_BOT_TOKEN=abc123"),
    )

    assert "private" not in caplog.text
    assert "abc123" not in caplog.text
    assert "[REDACTED]" in caplog.text
    assert "private" not in messages[0]
    assert "abc123" not in messages[0]


class MemoryStore:
    """Store bersama (mensimulasikan tabel notification_state)."""

    def __init__(self):
        self.rows: dict[str, str] = {}
        self.fail = False

    async def active(self):
        if self.fail:
            raise RuntimeError("db down")
        return dict(self.rows)

    async def claim(self, key, summary):
        if self.fail:
            raise RuntimeError("db down")
        if key in self.rows:
            return False
        self.rows[key] = summary
        return True

    async def release(self, key):
        if self.fail:
            raise RuntimeError("db down")
        return self.rows.pop(key, None) is not None


@pytest.mark.asyncio
async def test_shared_store_prevents_duplicate_across_processes():
    messages = []

    async def send(message: str) -> None:
        messages.append(message)

    store = MemoryStore()
    backend = ErrorReporter(sender=send, store=store)
    acquisition = ErrorReporter(sender=send, store=store)

    await backend.report("meter:PM-1", "Meter offline.")
    await acquisition.report("meter:PM-1", "Meter offline.")
    assert messages == ["EMS ERROR\nMeter offline."]


@pytest.mark.asyncio
async def test_restart_does_not_resend_but_still_sends_recovery():
    messages = []

    async def send(message: str) -> None:
        messages.append(message)

    store = MemoryStore()
    await ErrorReporter(sender=send, store=store).report("meter:PM-1", "Meter offline.")

    restarted = ErrorReporter(sender=send, store=store)
    await restarted.report("meter:PM-1", "Meter offline.")
    await restarted.resolve("meter:PM-1", "Meter kembali.")
    assert messages == ["EMS ERROR\nMeter offline.", "EMS PULIH\nMeter kembali."]
    assert store.rows == {}


@pytest.mark.asyncio
async def test_store_failure_falls_back_to_memory_and_still_recovers():
    messages = []

    async def send(message: str) -> None:
        messages.append(message)

    store = MemoryStore()
    store.fail = True
    reporter = ErrorReporter(sender=send, store=store)
    await reporter.report("database:x", "DB mati.")
    store.fail = False
    await reporter.resolve("database:x", "DB pulih.")
    assert messages == ["EMS ERROR\nDB mati.", "EMS PULIH\nDB pulih."]


@pytest.mark.asyncio
async def test_custom_titles():
    messages = []

    async def send(message: str) -> None:
        messages.append(message)

    reporter = ErrorReporter(sender=send)
    await reporter.report("alarm:PM-1:pf", "PF kritis", title="EMS ALARM KRITIS")
    await reporter.resolve("alarm:PM-1:pf", "PF normal", title="EMS ALARM PULIH")
    assert messages == ["EMS ALARM KRITIS\nPF kritis", "EMS ALARM PULIH\nPF normal"]


@pytest.mark.asyncio
async def test_background_mode_does_not_block_caller():
    import asyncio

    messages = []
    gate = asyncio.Event()

    async def slow_send(message: str) -> None:
        await gate.wait()  # mensimulasikan Telegram lambat
        messages.append(message)

    reporter = ErrorReporter(sender=slow_send, background=True, min_interval=0)
    await asyncio.wait_for(reporter.report("api:x", "API error."), 1)
    await asyncio.wait_for(reporter.resolve("api:x", "API pulih."), 1)
    assert messages == []  # pemanggil tidak menunggu pengiriman

    gate.set()
    await asyncio.wait_for(reporter.drain(), 1)
    assert messages == ["EMS ERROR\nAPI error.", "EMS PULIH\nAPI pulih."]
