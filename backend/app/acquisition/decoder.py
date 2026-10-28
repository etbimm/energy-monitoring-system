from __future__ import annotations

import math
import struct
from typing import Any

from app.acquisition.profiles import MeterProfile, RegisterType


def read_uint32_le(words: list[int]) -> int:
    return int(words[0]) + int(words[1]) * 65536


def read_int32_le(words: list[int]) -> int:
    value = read_uint32_le(words)
    return value - 0x100000000 if value > 0x7FFFFFFF else value


def read_float32_le(words: list[int]) -> float:
    packed = struct.pack("<HH", words[0] & 0xFFFF, words[1] & 0xFFFF)
    return struct.unpack("<f", packed)[0]


def read_uint32_be(words: list[int]) -> int:
    return int(words[0]) * 65536 + int(words[1])


def read_int32_be(words: list[int]) -> int:
    value = read_uint32_be(words)
    return value - 0x100000000 if value > 0x7FFFFFFF else value


def read_float32_be(words: list[int]) -> float:
    packed = struct.pack(">HH", words[0] & 0xFFFF, words[1] & 0xFFFF)
    return struct.unpack(">f", packed)[0]


def decode_raw(reg_type: RegisterType, words: list[int], word_order: str = "little") -> float:
    little = word_order == "little"
    if reg_type == "uint16":
        return float(words[0] & 0xFFFF)
    if reg_type == "int16":
        raw = words[0] & 0xFFFF
        return float(raw - 0x10000 if raw > 0x7FFF else raw)
    if reg_type == "uint32":
        return float(read_uint32_le(words) if little else read_uint32_be(words))
    if reg_type == "int32":
        return float(read_int32_le(words) if little else read_int32_be(words))
    if reg_type == "float32":
        return read_float32_le(words) if little else read_float32_be(words)
    return float(words[0])


def _round3(value: float) -> float:
    return round(value * 1000) / 1000


def decode(
    profile: MeterProfile,
    words: list[int],
    base_addr: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Ubah word Modbus mentah menjadi nilai engineering.

    Hasil: { label: {value, unit, key} }
    Register di luar rentang `words` dilewati (bukan error).
    """
    out: dict[str, dict[str, Any]] = {}
    base = profile.registers[0].addr if base_addr is None else base_addr

    for reg in profile.registers:
        start = reg.addr - base
        slice_ = words[start : start + reg.count]
        if start < 0 or len(slice_) < reg.count:
            continue
        raw = decode_raw(reg.type, slice_, profile.word_order)
        if isinstance(raw, float) and (math.isnan(raw) or math.isinf(raw)):
            continue
        out[reg.label] = {
            "value": _round3(raw / reg.scale),
            "unit": reg.unit,
            "key": reg.key,
        }
    return out


def decode_by_key(profile: MeterProfile, words: list[int], base_addr: int | None = None) -> dict[str, float]:
    decoded = decode(profile, words, base_addr)
    return {item["key"]: item["value"] for item in decoded.values()}


def merge_decode(profile: MeterProfile, blocks: list[tuple[int, list[int]]]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for base_addr, words in blocks:
        merged.update(decode_by_key(profile, words, base_addr))
    return merged
