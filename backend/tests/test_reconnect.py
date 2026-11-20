from app.services.reconnect import backoff_delay


def test_backoff_is_exponential_with_max():
    assert [backoff_delay(attempt) for attempt in range(1, 7)] == [5.0, 10.0, 20.0, 40.0, 60.0, 60.0]


def test_backoff_never_below_initial():
    assert backoff_delay(0) == 5.0
    assert backoff_delay(-5) == 5.0
