from app.services.queries import _bucket_interval


def test_daily_bucket_interval():
    assert _bucket_interval("1d") == "1 day"
