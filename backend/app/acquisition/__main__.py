from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import aiomqtt

# Allow `python -m app.acquisition` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.acquisition.poller import GatewayConnection
from app.acquisition.profiles import get_profile
from app.acquisition.scheduling import group_by_gateway, next_deadline
from app.acquisition.simulator import simulate_telemetry
from app.config import get_settings
from app.services.error_reporting import report_error, resolve_error

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


# Notifikasi Telegram "meter offline" hanya dikirim backend (offline watcher,
# berdasarkan last_seen_at). Acquisition cukup mencatat log saat status baca
# meter berubah, agar satu kejadian tidak menghasilkan dua notifikasi.
_failing_meters: set[str] = set()


def _mark_failed(code: str, reason: str) -> None:
    if code not in _failing_meters:
        _failing_meters.add(code)
        log.warning("Power meter %s %s", code, reason)


def _mark_ok(code: str) -> None:
    if code in _failing_meters:
        _failing_meters.discard(code)
        log.info("Power meter %s kembali terbaca", code)


async def publish(client, topic: str, payload: dict) -> None:
    await client.publish(topic, json.dumps(payload), qos=1)


# Daftar meter dimuat ulang dari database berkala, bukan setiap siklus.
DEVICE_RELOAD_SECONDS = 60


def _capabilities(device: dict) -> dict:
    caps = device["capabilities"] or {}
    if isinstance(caps, str):
        caps = json.loads(caps)
    return {
        **caps,
        "thdCurrent": True,
        "thdVoltage": device["model"] != "WEIDMULLER EM220",
    }


async def poll_one(mqtt, device: dict, gateway: GatewayConnection | None) -> None:
    """Baca satu meter lalu publish telemetry + status ke MQTT."""
    settings = get_settings()
    code = device["device_code"]
    caps = _capabilities(device)
    topic_tele = f"{settings.mqtt_topic_prefix}/meter/{code}/telemetry"
    topic_status = f"{settings.mqtt_topic_prefix}/meter/{code}/status"
    try:
        if gateway is None:
            payload = simulate_telemetry(code, caps, device["model"])
        else:
            profile = get_profile(device["model"])
            payload = await gateway.read(
                unit_id=device["modbus_address"] or profile.default_slave_id,
                profile=profile,
                device_code=code,
                capabilities=caps,
            )
        if payload is None:
            await publish(mqtt, topic_status, {"device_code": code, "status": "offline"})
            _mark_failed(code, "tidak mengirim telemetry")
            return
        await publish(mqtt, topic_tele, payload)
        await publish(mqtt, topic_status, {"device_code": code, "status": "online"})
        _mark_ok(code)
    except aiomqtt.MqttError:
        # Putusnya MQTT ditangani loop utama (reconnect), bukan status meter.
        raise
    except Exception as exc:
        await publish(
            mqtt,
            topic_status,
            {"device_code": code, "status": "offline", "error": type(exc).__name__},
        )
        _mark_failed(code, f"gagal dibaca ({type(exc).__name__}: {exc})")


async def poll_gateway(mqtt, devices: list[dict], gateway: GatewayConnection | None) -> None:
    # Meter dalam satu gateway (satu jalur RS485) dibaca berurutan.
    for device in devices:
        await poll_one(mqtt, device, gateway)


class Poller:
    """Polling semua meter: gateway berbeda paralel, interval tetap."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.simulator = self.settings.acquisition_mode == "simulator"
        self.devices: list[dict] = []
        self.loaded_at = float("-inf")
        self.gateways: dict[tuple[str, int], GatewayConnection] = {}

    async def reload_devices(self, force: bool = False) -> None:
        loop = asyncio.get_running_loop()
        if not force and loop.time() - self.loaded_at < DEVICE_RELOAD_SECONDS:
            return
        try:
            self.devices = await load_devices(self.settings.database_url)
            self.loaded_at = loop.time()
            await resolve_error("database:acquisition", "Database kembali dapat diakses oleh acquisition.")
        except Exception as exc:
            await report_error(
                "database:acquisition",
                "Acquisition gagal memuat daftar power meter dari database.",
                exc,
            )
            if force:
                raise

    def _gateway(self, key: tuple[str, int]) -> GatewayConnection | None:
        if self.simulator:
            return None
        if key not in self.gateways:
            self.gateways[key] = GatewayConnection(key[0], key[1], self.settings.modbus_timeout)
        return self.gateways[key]

    async def cycle(self, mqtt) -> None:
        groups = group_by_gateway(self.devices, simulator=self.simulator)
        # Tutup koneksi gateway yang tidak lagi dipakai.
        for key in [k for k in self.gateways if k not in groups]:
            self.gateways.pop(key).close()
        await asyncio.gather(
            *(poll_gateway(mqtt, devices, self._gateway(key)) for key, devices in groups.items())
        )

    def close(self) -> None:
        for gateway in self.gateways.values():
            gateway.close()
        self.gateways.clear()


async def run() -> None:
    settings = get_settings()
    log.info("Acquisition start mode=%s interval=%ss", settings.acquisition_mode, settings.poll_interval)
    poller = Poller()

    while True:
        try:
            await poller.reload_devices(force=True)
        except Exception:
            await asyncio.sleep(5)
            continue

        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
            ) as mqtt:
                await resolve_error("mqtt:acquisition", "Koneksi MQTT acquisition kembali normal.")
                loop = asyncio.get_running_loop()
                started = loop.time()
                while True:
                    await poller.reload_devices()
                    await poller.cycle(mqtt)
                    started, skipped = next_deadline(started, settings.poll_interval, loop.time())
                    if skipped:
                        log.warning(
                            "Siklus polling lebih lama dari %ss; %d siklus dilewati",
                            settings.poll_interval,
                            skipped,
                        )
                    await asyncio.sleep(max(0.0, started - loop.time()))
        except aiomqtt.MqttError as exc:
            await report_error("mqtt:acquisition", "Koneksi MQTT acquisition terputus.", exc)
            log.warning("MQTT terputus, reconnect 5 detik")
            poller.close()
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
