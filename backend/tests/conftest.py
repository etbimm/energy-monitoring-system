import pytest

from app.acquisition import simulator
from app.services import error_reporting


@pytest.fixture(autouse=True)
def isolated_error_reporter(monkeypatch):
    """Tes tidak boleh menyentuh database atau Telegram sungguhan.

    Reporter global diganti dengan reporter memori yang mencatat pesan.
    """
    sent: list[str] = []

    async def record(message: str) -> None:
        sent.append(message)

    monkeypatch.setattr(error_reporting, "error_reporter", error_reporting.ErrorReporter(sender=record))
    return sent


@pytest.fixture(autouse=True)
def fresh_simulator_counters():
    """Counter energi simulator tidak boleh terbawa antar tes."""
    simulator.reset_counters()
    yield
    simulator.reset_counters()
