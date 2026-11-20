from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from datetime import timedelta

import pytest

from app.services.queries import (
    READINGS_1MIN,
    _bucket_expr,
    _bucket_interval,
    _device_rows_stmt,
    _point,
    _severity_rank,
    get_summary,
    local_day_start,
    validate_range,
)


def _sql(expr) -> str:
    return str(
        select(expr).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_daily_bucket_interval():
    assert _bucket_interval("1d") == "1 day"


def test_severity_rank_compiles_to_sql_case():
    sql = _sql(_severity_rank())
    assert "max(CASE WHEN" in sql
    assert "ELSE 0 END" in sql


def test_local_day_start_uses_wib_midnight():
    # 06:00 WIB tanggal 6 = 23:00 UTC tanggal 5 -> hari lokal mulai 5 Nov 17:00 UTC.
    now = datetime(2026, 11, 5, 23, 0, tzinfo=timezone.utc)
    assert local_day_start(now) == datetime(2026, 11, 5, 17, 0, tzinfo=timezone.utc)


def test_daily_bucket_uses_local_timezone():
    assert "'Asia/Jakarta'" in _sql(_bucket_expr("1 day"))
    assert "Asia/Jakarta" not in _sql(_bucket_expr("5 minutes"))


def test_point_label_is_local_time():
    row = SimpleNamespace(
        power=1, apparent_power=1, reactive_power=0, energy_active=1,
        energy_reactive=0, energy_apparent=1, voltage=400, current=1,
        frequency=50, power_factor=1, thd_current=None,
    )
    point = _point(datetime(2026, 11, 6, 1, 30, tzinfo=timezone.utc), row)
    assert point.label == "08:30"


def test_charts_read_from_continuous_aggregate():
    assert "readings_1min.bucket" in _sql(_bucket_expr("5 minutes", READINGS_1MIN.c.bucket))


def test_raw_range_is_limited_to_seven_days():
    end = datetime(2026, 11, 9, tzinfo=timezone.utc)
    validate_range(end - timedelta(days=7), end, "raw")
    with pytest.raises(ValueError, match="raw maksimal 7 hari"):
        validate_range(end - timedelta(days=8), end, "raw")


def test_bucket_point_count_is_limited():
    end = datetime(2026, 11, 9, tzinfo=timezone.utc)
    validate_range(end - timedelta(days=13), end, "1m")  # ~18.700 titik
    with pytest.raises(ValueError, match="terlalu besar"):
        validate_range(end - timedelta(days=30), end, "1m")  # ~43.200 titik
    validate_range(end - timedelta(days=365 * 5), end, "1d")


def test_reversed_range_rejected():
    end = datetime(2026, 11, 9, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        validate_range(end, end - timedelta(hours=1), "5m")


def test_single_device_query_filters_in_database():
    # get_device_by_code tidak boleh menarik semua device lalu mencari di memori.
    sql = str(
        _device_rows_stmt("PM-MCC1-01").compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "devices.is_active IS true" in sql
    assert "devices.device_code = 'PM-MCC1-01'" in sql


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession:
    """Session minimal: setiap execute mengembalikan batch berikutnya."""

    def __init__(self, *batches):
        self._batches = list(batches)

    async def execute(self, _stmt):
        return _Rows(self._batches.pop(0))


@pytest.mark.asyncio
async def test_summary_uses_lightweight_rows():
    now = datetime.now(timezone.utc)
    rows = [
        SimpleNamespace(
            role="incoming", last_seen_at=now, power=10.0,
            apparent_power=12.0, reactive_power=3.0, rank=0,
        ),
        # Meter non-incoming tidak ikut total daya, tetapi status tetap dihitung.
        SimpleNamespace(
            role="outcoming", last_seen_at=now - timedelta(seconds=60),
            power=99.0, apparent_power=99.0, reactive_power=99.0, rank=0,
        ),
        SimpleNamespace(
            role="incoming", last_seen_at=None,
            power=None, apparent_power=None, reactive_power=None, rank=None,
        ),
    ]
    energy = [SimpleNamespace(active=5.0, reactive=2.0, apparent=3.0)]

    summary = await get_summary(_FakeSession(rows, energy))

    assert summary.total_power == 10.0
    assert summary.total_apparent_power == 12.0
    assert summary.total_reactive_power == 3.0
    assert summary.energy_today == 5.0
    assert (summary.online, summary.warning, summary.offline) == (1, 1, 1)
    assert summary.total == 3
