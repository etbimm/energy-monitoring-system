from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.services.queries import (
    _bucket_expr,
    _bucket_interval,
    _point,
    _severity_rank,
    local_day_start,
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
