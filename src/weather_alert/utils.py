# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
utils.py — Shared utilities: retry logic and failure logging.
"""

import time
from datetime import datetime
from pathlib import Path

DEFAULT_LOG_PATH = Path("logs/weather_alert.log")
MAX_ATTEMPTS = 3
RETRY_DELAY = 5  # seconds


def with_retry(fn, *args, label: str = "API call", log_path: Path = DEFAULT_LOG_PATH, **kwargs):
    """
    Call fn(*args, **kwargs) up to MAX_ATTEMPTS times.

    On each failure prints a warning and waits RETRY_DELAY seconds.
    If all attempts fail, logs the error and raises RuntimeError.
    """
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                print(
                    f"[weather] {label} failed (attempt {attempt}/{MAX_ATTEMPTS}): "
                    f"{e}. Retrying in {RETRY_DELAY}s..."
                )
                time.sleep(RETRY_DELAY)
            else:
                msg = f"[weather] All {MAX_ATTEMPTS} attempts failed. Check your internet connection."
                print(msg)
                _log_error(str(e), log_path=log_path)
                raise RuntimeError(msg) from e

    raise RuntimeError("Unexpected retry exit")  # should never reach here


def _log_error(message: str, log_path: Path = DEFAULT_LOG_PATH) -> None:
    """Append a timestamped ERROR line to the log file."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a") as f:
            f.write(f"{timestamp} [ERROR] API call failed after {MAX_ATTEMPTS} attempts: {message}\n")
    except OSError:
        pass  # Never crash on logging failure


def write_last_run(status: str, detail: str, log_dir: Path = Path("logs")) -> None:
    """
    Append a status line to logs/last_run.txt after each run-once.

    Format: 2026-02-23 20:00:01|OK|No alerts
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_dir / "last_run.txt", "a") as f:
            f.write(f"{timestamp}|{status}|{detail}\n")
    except OSError:
        pass


def read_last_run(log_dir: Path = Path("logs")) -> dict | None:
    """
    Read the last line of logs/last_run.txt.
    Returns dict with keys: timestamp, status, detail — or None if file missing.
    """
    path = log_dir / "last_run.txt"
    if not path.exists():
        return None
    try:
        lines = path.read_text().strip().splitlines()
        if not lines:
            return None
        last = lines[-1]
        parts = last.split("|", 2)
        if len(parts) != 3:
            return None
        return {"timestamp": parts[0], "status": parts[1], "detail": parts[2]}
    except OSError:
        return None
