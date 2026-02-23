# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
utils.py — Shared utilities: retry logic and failure logging.
"""

import time
from collections import deque
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


def fmt_day(date_str: str) -> str:
    """Format a date string as a short human-readable label.

    Args:
        date_str: Date in 'YYYY-MM-DD' format.

    Returns:
        Formatted string like 'Mon 24 Feb'.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%a %d %b")


def fmt_hour(time_str: str) -> str:
    """Format an ISO datetime string as a short hour label.

    Args:
        time_str: Datetime in 'YYYY-MM-DDTHH:MM' format.

    Returns:
        Formatted string like 'HH:00'.
    """
    dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
    return dt.strftime("%H:%M")

DEFAULT_LOG_PATH = Path("logs/weather_alert.log")
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5


def with_retry(
    fn: Callable[..., Any],
    *args: Any,
    label: str = "API call",
    log_path: Path = DEFAULT_LOG_PATH,
    **kwargs: Any,
) -> Any:
    """Call a function up to MAX_ATTEMPTS times, retrying on any exception.

    Args:
        fn: Zero-argument callable to invoke (wrap args in a closure).
        *args: Positional arguments forwarded to fn (kept for signature compat).
        label: Human-readable name for the call, used in warning messages.
        log_path: Path to the log file for recording final failures.
        **kwargs: Keyword arguments forwarded to fn.

    Returns:
        The return value of fn on success.

    Raises:
        RuntimeError: If all MAX_ATTEMPTS attempts raise exceptions.
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
                    f"{e}. Retrying in {RETRY_DELAY_SECONDS}s..."
                )
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                msg = f"All {MAX_ATTEMPTS} attempts failed for {label}. Check your internet connection."
                print(f"[weather] {msg}")
                _log_error(str(e), log_path=log_path)
                raise RuntimeError(msg) from e


def _log_error(message: str, log_path: Path = DEFAULT_LOG_PATH) -> None:
    """Append a timestamped ERROR line to the log file.

    Args:
        message: Error description to log.
        log_path: Destination log file path.
    """
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a") as f:
            f.write(f"{timestamp} [ERROR] API call failed after {MAX_ATTEMPTS} attempts: {message}\n")
    except OSError:
        pass  # Never crash on logging failure


def write_last_run(
    status: str,
    detail: str,
    log_dir: Path = Path("logs"),
) -> None:
    """Append a status record to logs/last_run.txt after each run.

    Format: ``2026-02-23 20:00:01|OK|No alerts``

    Args:
        status: 'OK' or 'ERROR'.
        detail: Human-readable summary of the run outcome.
        log_dir: Directory containing last_run.txt.
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_dir / "last_run.txt", "a") as f:
            f.write(f"{timestamp}|{status}|{detail}\n")
    except OSError:
        pass


def read_last_run(log_dir: Path = Path("logs")) -> dict | None:
    """Read the most recent run record from logs/last_run.txt.

    Args:
        log_dir: Directory containing last_run.txt.

    Returns:
        Dict with keys timestamp, status, detail — or None if file is missing
        or empty.
    """
    path = log_dir / "last_run.txt"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            buf: deque[str] = deque(f, maxlen=1)
        if not buf:
            return None
        last = buf[0].rstrip("\n")
        parts = last.split("|", 2)
        if len(parts) != 3:
            return None
        return {"timestamp": parts[0], "status": parts[1], "detail": parts[2]}
    except OSError:
        return None
