"""Backoff eksponensial untuk koneksi ulang MQTT.

Urutan jeda: 5s, 10s, 20s, 40s, lalu maksimal 60s. Reset ke awal setiap
koneksi berhasil supaya broker yang sehat tidak menunggu lama.
"""

RETRY_INITIAL_SECONDS = 5.0
RETRY_MAX_SECONDS = 60.0


def backoff_delay(attempt: int) -> float:
    """Jeda sebelum percobaan reconnect ke-N (attempt dimulai dari 1)."""
    if attempt < 1:
        attempt = 1
    return min(RETRY_INITIAL_SECONDS * (2 ** (attempt - 1)), RETRY_MAX_SECONDS)
