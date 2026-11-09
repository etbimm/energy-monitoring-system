from __future__ import annotations

import inspect
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from app.acquisition.decoder import merge_decode
from app.acquisition.normalize import to_telemetry
from app.acquisition.profiles import MeterProfile, register_blocks

log = logging.getLogger("ems.modbus")


def _unit_kwargs(method, unit_id: int) -> dict:
    params = inspect.signature(method).parameters
    if "device_id" in params:
        return {"device_id": unit_id}
    return {"slave": unit_id}


async def read_block(client: AsyncModbusTcpClient, profile: MeterProfile, unit_id: int, address: int, count: int) -> list[int]:
    if profile.function_code == "FC04":
        method = client.read_input_registers
    else:
        method = client.read_holding_registers
    response = await method(address, count=count, **_unit_kwargs(method, unit_id))
    if response.isError():
        raise ModbusException(str(response))
    return list(response.registers)


async def read_device(
    client: AsyncModbusTcpClient,
    unit_id: int,
    profile: MeterProfile,
    device_code: str,
    capabilities: dict,
) -> dict:
    """Baca semua blok register satu meter lewat client yang sudah terhubung."""
    blocks: list[tuple[int, list[int]]] = []
    for address, count in register_blocks(profile):
        words = await read_block(client, profile, unit_id, address, count)
        blocks.append((address, words))
    decoded = merge_decode(profile, blocks)
    return to_telemetry(device_code, decoded, capabilities)


class GatewayConnection:
    """Koneksi Modbus TCP persisten ke satu gateway RS485-to-Ethernet.

    Semua meter di belakang gateway yang sama dibaca berurutan memakai satu
    koneksi (RS485 hanya bisa satu transaksi pada satu waktu). Koneksi dibuka
    ulang otomatis bila putus atau terjadi error baca.
    """

    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client: AsyncModbusTcpClient | None = None

    async def _ensure(self) -> AsyncModbusTcpClient:
        if self._client is not None and self._client.connected:
            return self._client
        self.close()
        client = AsyncModbusTcpClient(host=self.host, port=self.port, timeout=self.timeout)
        if not await client.connect():
            client.close()
            raise ConnectionError(f"Tidak bisa konek Modbus TCP {self.host}:{self.port}")
        self._client = client
        return client

    async def read(self, unit_id: int, profile: MeterProfile, device_code: str, capabilities: dict) -> dict:
        client = await self._ensure()
        try:
            return await read_device(client, unit_id, profile, device_code, capabilities)
        except (ConnectionError, OSError):
            # Koneksi rusak: tutup agar siklus berikutnya konek ulang.
            self.close()
            raise

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


async def poll_device(
    host: str,
    port: int,
    unit_id: int,
    profile: MeterProfile,
    device_code: str,
    capabilities: dict,
    timeout: float = 2.0,
) -> dict:
    """Baca satu meter dengan koneksi sekali pakai (untuk uji manual)."""
    gateway = GatewayConnection(host, port, timeout)
    try:
        return await gateway.read(unit_id, profile, device_code, capabilities)
    finally:
        gateway.close()
