# Project: weather-alert
# Owner: GreenUnicorn
# Built with: Claude (Anthropic)
"""
config.py — Load and validate the TOML configuration file.

We use tomllib (Python 3.11+ stdlib) so no extra install is needed.
The config path defaults to "config.toml" in the current working directory,
but can be overridden for testing.
"""

import tomllib
from pathlib import Path


DEFAULT_CONFIG_PATH = Path("config.toml")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load and validate a TOML configuration file.

    Args:
        path: Path to the TOML config file.

    Returns:
        Nested dict of configuration values.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If required keys or sections are missing.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Copy config.toml.example to config.toml and fill in your location."
        )

    with open(path, "rb") as f:
        config = tomllib.load(f)

    _validate(config)
    return config


def _validate(config: dict) -> None:
    """Validate that all required config sections and keys are present.

    Expected config schema::

        [location]
        latitude  = <float>   # decimal degrees, e.g. 40.7128
        longitude = <float>   # decimal degrees, e.g. -74.0060
        name      = <str>     # display name, e.g. "New York, NY"

        [alerts]
        rain_probability_threshold = <int>    # 0-100 percent
        wind_speed_threshold       = <float>  # km/h
        temperature_min            = <float>  # °C
        feels_like_min             = <float>  # °C
        lookahead_hours            = <int>    # 1-24

        [notifications]
        macos = <bool>   # true to send macOS native notifications
        log   = <bool>   # true to log alerts to file

        [log]
        path = <str>     # relative or absolute path to the log file

    Args:
        config: Parsed TOML config dict.

    Raises:
        ValueError: If any required section or key is absent.
    """
    required_sections = ["location", "alerts", "notifications", "log"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: [{section}]")

    location = config["location"]
    for key in ("latitude", "longitude", "name"):
        if key not in location:
            raise ValueError(f"Missing required config key: [location].{key}")

    alerts = config["alerts"]
    for key in ("rain_probability_threshold", "wind_speed_threshold",
                "temperature_min", "feels_like_min", "lookahead_hours"):
        if key not in alerts:
            raise ValueError(f"Missing required config key: [alerts].{key}")
