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
    """
    Load config from a TOML file and return it as a nested dict.
    Raises FileNotFoundError if the file doesn't exist.
    Raises ValueError if required keys are missing.
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
    """Check that required top-level sections and keys exist."""
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
