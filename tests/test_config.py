"""
test_config.py — Tests for config loading and validation.

We write a temporary TOML file in each test so we don't depend on
a real config.toml existing in the project.
"""

import pytest
import tomllib
from pathlib import Path
from weather_alert.config import load_config


VALID_TOML = """
[location]
latitude = 51.5074
longitude = -0.1278
name = "London"

[alerts]
rain_probability_threshold = 50
wind_speed_threshold = 30
temperature_min = 5
feels_like_min = 2
lookahead_hours = 3

[schedule]
quiet_hours_start = 22
quiet_hours_end = 7

[notifications]
macos = true
log = true
email = false
slack = false
sound = false

[log]
path = "logs/weather_alert.log"
"""


def test_load_valid_config(tmp_path):
    """A valid config file should load without error."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(VALID_TOML)

    config = load_config(config_file)

    assert config["location"]["name"] == "London"
    assert config["alerts"]["rain_probability_threshold"] == 50
    assert config["notifications"]["macos"] is True


def test_missing_file_raises(tmp_path):
    """A missing config file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.toml")


def test_missing_section_raises(tmp_path):
    """A config without a required section should raise ValueError."""
    bad_toml = "[location]\nlatitude = 1.0\nlongitude = 2.0\nname = 'X'\n"
    config_file = tmp_path / "config.toml"
    config_file.write_text(bad_toml)

    with pytest.raises(ValueError, match="Missing required config section"):
        load_config(config_file)


def test_missing_key_raises(tmp_path):
    """A config missing a required key inside a section should raise ValueError."""
    # Missing 'name' in [location]
    bad_toml = """
[location]
latitude = 1.0
longitude = 2.0

[alerts]
rain_probability_threshold = 50
wind_speed_threshold = 30
temperature_min = 5
feels_like_min = 2
lookahead_hours = 3

[notifications]
macos = true
log = true
email = false
slack = false
sound = false

[log]
path = "logs/weather_alert.log"
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(bad_toml)

    with pytest.raises(ValueError, match="name"):
        load_config(config_file)
