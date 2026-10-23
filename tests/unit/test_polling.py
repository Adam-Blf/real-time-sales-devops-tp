import pytest

from tests.support.polling import PollingTimeout, wait_for


def test_returns_first_truthy_result():
    attempts = iter([None, False, "ready"])
    assert wait_for(lambda: next(attempts), timeout=5, interval=0) == "ready"


def test_fails_cleanly_after_timeout():
    with pytest.raises(PollingTimeout, match="never"):
        wait_for(lambda: None, timeout=0.05, interval=0.01, description="never")


def test_reports_last_error():
    def probe():
        raise ConnectionError("refused")

    with pytest.raises(PollingTimeout, match="refused"):
        wait_for(probe, timeout=0.05, interval=0.01)
