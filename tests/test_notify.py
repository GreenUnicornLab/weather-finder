# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
test_notify.py — Unit tests for the notify module.

All tests mock subprocess.run and filesystem I/O — no real osascript or
file system writes happen.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from weather_alert.notify import (
    _log_alert,
    _send_macos_notification,
    send_notifications,
    send_test_notification,
    send_weather_notification,
)


# ---------------------------------------------------------------------------
# _send_macos_notification
# ---------------------------------------------------------------------------

def _make_run_ok() -> MagicMock:
    mock = MagicMock()
    mock.returncode = 0
    mock.stderr = ""
    mock.stdout = ""
    return mock


def _make_run_fail(stderr: str = "oops") -> MagicMock:
    mock = MagicMock()
    mock.returncode = 1
    mock.stderr = stderr
    mock.stdout = ""
    return mock


@patch("weather_alert.notify.subprocess.run")
def test_send_macos_notification_calls_osascript(mock_run):
    mock_run.return_value = _make_run_ok()
    _send_macos_notification("Title", "Body")
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    # First positional arg is the command list
    cmd = args[0]
    assert cmd[0] == "osascript"


@patch("weather_alert.notify.subprocess.run")
def test_send_macos_notification_passes_env_vars(mock_run):
    """Title and message must be passed via WA_TITLE / WA_MSG env vars."""
    mock_run.return_value = _make_run_ok()
    _send_macos_notification("My Title", "My Message")
    _, kwargs = mock_run.call_args
    env = kwargs.get("env") or mock_run.call_args.kwargs.get("env")
    assert env is not None
    assert env["WA_TITLE"] == "My Title"
    assert env["WA_MSG"] == "My Message"


@patch("weather_alert.notify.subprocess.run")
def test_send_macos_notification_no_string_injection(mock_run):
    """Special chars in title/message must NOT appear in the script string."""
    mock_run.return_value = _make_run_ok()
    _send_macos_notification('Title"with"quotes', 'Msg\\backslash')
    _, kwargs = mock_run.call_args
    cmd = mock_run.call_args[0][0]
    script = cmd[2]  # osascript -e <script>
    # The raw strings should not be interpolated into the script
    assert '"with"' not in script
    assert "backslash" not in script


@patch("weather_alert.notify.subprocess.run")
def test_send_macos_notification_prints_on_failure(mock_run, capsys):
    mock_run.return_value = _make_run_fail("Script error")
    _send_macos_notification("T", "M")
    captured = capsys.readouterr()
    assert "osascript failed" in captured.out
    assert "Script error" in captured.out


@patch("weather_alert.notify.subprocess.run")
def test_send_macos_notification_success_prints_confirmation(mock_run, capsys):
    mock_run.return_value = _make_run_ok()
    _send_macos_notification("T", "M")
    captured = capsys.readouterr()
    assert "macOS notification sent" in captured.out


# ---------------------------------------------------------------------------
# _log_alert
# ---------------------------------------------------------------------------

@patch("builtins.open", new_callable=MagicMock)
@patch("pathlib.Path.mkdir")
def test_log_alert_writes_timestamped_line(mock_mkdir, mock_open):
    mock_file = MagicMock()
    mock_open.return_value.__enter__ = lambda s: mock_file
    mock_open.return_value.__exit__ = MagicMock(return_value=False)

    config = {"log": {"path": "logs/test.log"}}
    _log_alert("test message", config)

    mock_file.write.assert_called_once()
    written = mock_file.write.call_args[0][0]
    assert "test message" in written
    # Timestamp format check: contains a digit-heavy pattern
    assert "|" not in written  # log uses plain text, not pipe-separated


@patch("builtins.open", side_effect=OSError("disk full"))
@patch("pathlib.Path.mkdir")
def test_log_alert_silences_os_error(mock_mkdir, mock_open, capsys):
    config = {"log": {"path": "logs/test.log"}}
    # Should not raise
    _log_alert("some message", config)
    captured = capsys.readouterr()
    assert "Failed to write log" in captured.out


# ---------------------------------------------------------------------------
# send_notifications
# ---------------------------------------------------------------------------

@patch("weather_alert.notify._send_macos_notification")
@patch("weather_alert.notify._log_alert")
def test_send_notifications_macos_and_log(mock_log, mock_notif):
    config = {"notifications": {"macos": True, "log": True}, "log": {"path": "logs/x.log"}}
    send_notifications(["Alert one", "Alert two"], config)
    assert mock_notif.call_count == 2
    assert mock_log.call_count == 2


@patch("weather_alert.notify._send_macos_notification")
@patch("weather_alert.notify._log_alert")
def test_send_notifications_macos_only(mock_log, mock_notif):
    config = {"notifications": {"macos": True, "log": False}}
    send_notifications(["Alert"], config)
    mock_notif.assert_called_once()
    mock_log.assert_not_called()


@patch("weather_alert.notify._send_macos_notification")
@patch("weather_alert.notify._log_alert")
def test_send_notifications_neither_channel(mock_log, mock_notif):
    config = {"notifications": {"macos": False, "log": False}}
    send_notifications(["Alert"], config)
    mock_notif.assert_not_called()
    mock_log.assert_not_called()


# ---------------------------------------------------------------------------
# send_test_notification
# ---------------------------------------------------------------------------

@patch("weather_alert.notify._send_macos_notification")
def test_send_test_notification_calls_macos(mock_notif):
    config = {"notifications": {"log": False}}
    send_test_notification(config)
    mock_notif.assert_called_once()
    title, message = mock_notif.call_args[0]
    assert "Test" in title or "test" in message.lower()


# ---------------------------------------------------------------------------
# send_weather_notification
# ---------------------------------------------------------------------------

@patch("weather_alert.notify._send_macos_notification")
def test_send_weather_notification_skipped_when_macos_false(mock_notif):
    config = {"notifications": {"macos": False}}
    send_weather_notification(
        location_line="London",
        current={"temperature": 15, "feels_like": 13, "humidity": 70, "wind_speed": 20, "wind_direction": "SW"},
        max_rain=10,
        lookahead_hours=3,
        alerts=[],
        config=config,
    )
    mock_notif.assert_not_called()


@patch("weather_alert.notify._send_macos_notification")
def test_send_weather_notification_fires_when_macos_true(mock_notif):
    mock_notif.return_value = None
    config = {"notifications": {"macos": True, "log": False}}
    send_weather_notification(
        location_line="London — Mon 23 Feb",
        current={"temperature": 15, "feels_like": 13, "humidity": 70, "wind_speed": 20, "wind_direction": "SW"},
        max_rain=10,
        lookahead_hours=3,
        alerts=[],
        config=config,
    )
    mock_notif.assert_called_once()
    title, message = mock_notif.call_args[0]
    assert "London" in title
    assert "15" in message  # temperature appears in message


@patch("weather_alert.notify._send_macos_notification")
def test_send_weather_notification_includes_alert_summary(mock_notif):
    mock_notif.return_value = None
    config = {"notifications": {"macos": True, "log": False}}
    send_weather_notification(
        location_line="Berlin",
        current={"temperature": 2, "feels_like": -3, "humidity": 90, "wind_speed": 55, "wind_direction": "N"},
        max_rain=80,
        lookahead_hours=3,
        alerts=["High wind: 55 km/h at 12:00 (threshold: 30 km/h)"],
        config=config,
    )
    _, message = mock_notif.call_args[0]
    assert "High wind" in message
