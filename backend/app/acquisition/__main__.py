from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# Allow `python -m app.acquisition` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.acquisition.poller import poll_device
from app.acquisition.profiles import get_profile
from app.acquisition.simulator import simulate_telemetry
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("ems.acquisition")


async def load_devices(dsn: str) -> list[dict]:
    import asyncpg

    conn = await asyncpg.connect(dsn.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        rows = await conn.fetch(
            """
            SELECT device_code, model, modbus_host, modbus_port, modbus_address,
                   capabilities, is_active
            FROM devices
            WHERE is_active = TRUE
            ORDER BY id
            """
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def publish(client, topic: str, payload: dict) -> None:
    await client.publish(topic, json.dumps(payload), qos=1)


async def run() -> None:
    import aiomqtt

    settings = get_settings()
    log.info("Acquisition start mode=%s interval=%ss", settings.acquisition_mode, settings.poll_interval)

    while True:
        try:
            devices = await load_devices(settings.database_url)
        except Exception:
            log.exception("Gagal load devices dari database")
            await asyncio.sleep(5)
            continue

        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
            ) as mqtt:
                while True:
                    try:
                        devices = await load_devices(settings.database_url)
                    except Exception:
                        log.exception("Gagal refresh devices")

                    for device in devices:
                        code = device["device_code"]
                        caps = device["capabilities"] or {}
                        if isinstance(caps, str):
                            caps = json.loads(caps)
                        topic_tele = f"{settings.mqtt_topic_prefix}/meter/{code}/telemetry"
                        topic_status = f"{settings.mqtt_topic_prefix}/meter/{code}/status"
                        try:
                            if settings.acquisition_mode == "simulator":
                                payload = simulate_telemetry(code, caps)
                            else:
                                profile = get_profile(device["model"])
                                payload = await poll_device(
                                    host=device["modbus_host"],
                                    port=device["modbus_port"] or 502,
                                    unit_id=device["modbus_address"] or profile.default_slave_id,
                                    profile=profile,
                                    device_code=code,
                                    capabilities=caps,
                                    timeout=settings.modbus_timeout,
                                )
                            if payload is None:
                                await publish(mqtt, topic_status, {"device_code": code, "status": "offline"})
                                continue
                            await publish(mqtt, topic_tele, payload)
                            await publish(mqtt, topic_status, {"device_code": code, "status": "online"})
                        except Exception as exc:
                            log.warning("Poll gagal %s: %s", code, exc)
                            await publish(mqtt, topic_status, {"device_code": code, "status": "offline", "error": str(exc)})
                    await asyncio.sleep(settings.poll_interval)
        except aiomqtt.MqttError:
            log.exception("MQTT terputus, reconnect 5 detik")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
