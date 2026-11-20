"""Status koneksi MQTT subscriber backend (dipakai endpoint health)."""

# "ok" | "disconnected"
_state = "disconnected"


def set_state(value: str) -> None:
    global _state
    _state = value


def mqtt_state() -> str:
    return _state
