from datetime import datetime, timezone

from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import PhaseReading, Reading
from app.services.ingest import phase_values, reading_values

TS = datetime(2026, 11, 9, 1, 0, tzinfo=timezone.utc)
PAYLOAD = {
    "voltage": 400.0,
    "power": 10.0,
    "power_factor": 0.95,
    "phases": {
        "L1": {"voltage": 230.0, "power": 3.3},
        "L2": {"voltage": 231.0},
        "N": {"voltage": 1.0},  # bukan fasa valid -> diabaikan
    },
}


def test_reading_values_maps_payload():
    row = reading_values(7, TS, PAYLOAD)
    assert row["time"] == TS and row["device_id"] == 7
    assert row["voltage"] == 400.0 and row["power_factor"] == 0.95
    assert row["thd_current"] is None


def test_phase_values_only_valid_phases():
    rows = phase_values(7, TS, PAYLOAD)
    assert [r["phase"] for r in rows] == ["L1", "L2"]
    assert rows[0]["power"] == 3.3


def test_insert_uses_on_conflict_do_nothing():
    for model, values in (
        (Reading, reading_values(7, TS, PAYLOAD)),
        (PhaseReading, phase_values(7, TS, PAYLOAD)),
    ):
        sql = str(
            pg_insert(model).values(values).on_conflict_do_nothing().compile(dialect=postgresql.dialect())
        )
        assert "ON CONFLICT DO NOTHING" in sql
