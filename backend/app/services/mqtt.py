from __future__ import annotations

import asyncio
import json
import logging

from app.config import get_settings
from app.db import SessionLocal
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
                log.info("MQTT subscribe %s", topic)
                async for message in client.messages:
                    try:
                        payload = json.loads(message.payload.decode())
                    except json.JSONDecodeError:
                        log.warning("Payload MQTT bukan JSON: %s", message.topic)
                        continue
                    async with SessionLocal() as session:
                        try:
                            await ingest_telemetry(session, payload)
                        except Exception:
                            log.exception("Gagal ingest %s", message.topic)
                            await session.rollback()
        except aiomqtt.MqttError:
            log.exception("MQTT subscriber terputus, retry 5 detik")
            await asyncio.sleep(5)
