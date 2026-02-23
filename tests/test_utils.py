# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""Tests for utils.py retry logic."""

import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from weather_alert.utils import with_retry, write_last_run, read_last_run


# ---------------------------------------------------------------------------
# with_retry
# ---------------------------------------------------------------------------

def test_retry_succeeds_on_first_attempt():
    """A function that succeeds on the first call should return its value."""
    fn = MagicMock(return_value=42)
    result = with_retry(fn, label="test")
    assert result == 42
    assert fn.call_count == 1


def test_retry_succeeds_on_second_attempt():
    """A function that fails once then succeeds should return the success value."""
    fn = MagicMock(side_effect=[RuntimeError("fail"), 99])
    with patch("weather_alert.utils.time.sleep"):
        result = with_retry(fn, label="test")
    assert result == 99
    assert fn.call_count == 2


def test_retry_exhausts_all_attempts_and_raises():
    """A function that always fails should raise RuntimeError after MAX_ATTEMPTS."""
    fn = MagicMock(side_effect=RuntimeError("always fails"))
    with patch("weather_alert.utils.time.sleep"):
        with pytest.raises(RuntimeError, match="All 3 attempts failed"):
            with_retry(fn, label="test", log_path=Path("/dev/null"))
    assert fn.call_count == 3


def test_retry_sleeps_between_attempts():
    """Retry should sleep between failed attempts (but not after the last)."""
    fn = MagicMock(side_effect=[RuntimeError("fail"), RuntimeError("fail"), RuntimeError("fail")])
    with patch("weather_alert.utils.time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError):
            with_retry(fn, label="test", log_path=Path("/dev/null"))
    # Should sleep twice (between attempts 1→2 and 2→3, not after 3)
    assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# write_last_run / read_last_run
# ---------------------------------------------------------------------------

def test_write_and_read_last_run(tmp_path):
    """write_last_run then read_last_run should round-trip correctly."""
    write_last_run("OK", "No alerts", log_dir=tmp_path)
    result = read_last_run(log_dir=tmp_path)
    assert result is not None
    assert result["status"] == "OK"
    assert result["detail"] == "No alerts"


def test_read_last_run_missing_file(tmp_path):
    """read_last_run returns None when the file does not exist."""
    result = read_last_run(log_dir=tmp_path / "nonexistent")
    assert result is None


def test_read_last_run_returns_most_recent(tmp_path):
    """read_last_run always returns the LAST line written."""
    write_last_run("OK", "No alerts", log_dir=tmp_path)
    write_last_run("ERROR", "API failed", log_dir=tmp_path)
    result = read_last_run(log_dir=tmp_path)
    assert result["status"] == "ERROR"
    assert result["detail"] == "API failed"
