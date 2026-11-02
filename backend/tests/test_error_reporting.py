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
