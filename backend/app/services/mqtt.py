from __future__ import annotations

import asyncio
import json
import logging

from app.config import get_settings
from app.db import SessionLocal
from app.services.error_reporting import report_error, resolve_error
from app.services.ingest import ingest_telemetry

log = logging.getLogger("ems.mqtt")


async def mqtt_subscriber() -> None:
    import aiomqtt

    settings = get_settings()
    topic = f"{settings.mqtt_topic_prefix}/meter/+/telemetry"

    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
            ) as client:
                await client.subscribe(topic, qos=1)
                await resolve_error("mqtt:backend-subscriber", "Koneksi MQTT backend kembali normal.")
                log.info("MQTT subscribe %s", topic)
                async for message in client.messages:
                    try:
                        payload = json.loads(message.payload.decode())
                    except json.JSONDecodeError:
                        await report_error(
                            f"mqtt:invalid-payload:{message.topic}",
                            f"Payload MQTT bukan JSON pada topic {message.topic}.",
                        )
                        continue
                    await resolve_error(
                        f"mqtt:invalid-payload:{message.topic}",
                        f"Payload MQTT pada topic {message.topic} kembali valid.",
                    )
                    code = str(payload.get("device_code", "unknown"))
                    try:
                        async with SessionLocal() as session:
                            await ingest_telemetry(session, payload)
                        await resolve_error(
                            f"database:ingest:{code}",
                            f"Penyimpanan telemetry {code} kembali normal.",
                        )
                    except Exception as exc:
                        await report_error(
                            f"database:ingest:{code}",
                            f"Gagal menyimpan telemetry {code}.",
                            exc,
                        )
        except aiomqtt.MqttError as exc:
            await report_error(
                "mqtt:backend-subscriber",
                "MQTT subscriber backend terputus.",
                exc,
            )
            log.warning("MQTT subscriber retry 5 detik")
            await asyncio.sleep(5)
