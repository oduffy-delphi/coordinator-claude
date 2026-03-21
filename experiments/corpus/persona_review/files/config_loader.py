"""Configuration loader for application settings.

Reads YAML configuration files with environment variable interpolation
and schema validation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")

DEFAULT_CONFIG_PATHS = [
    Path("/etc/myapp/config.yaml"),
    Path.home() / ".config" / "myapp" / "config.yaml",
    Path("config.yaml"),
]


def _interpolate_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} patterns with environment variable values."""

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return ENV_VAR_PATTERN.sub(replacer, value)


def _deep_interpolate(obj: Any) -> Any:
    """Recursively interpolate environment variables in a config structure."""
    if isinstance(obj, str):
        return _interpolate_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: _deep_interpolate(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_interpolate(item) for item in obj]
    return obj


def find_config_file(custom_path: Path | None = None) -> Path:
    """Locate the configuration file using the search path precedence.

    Custom path takes highest priority, followed by the default search order.
    Raises FileNotFoundError if no config file is found.
    """
    if custom_path is not None:
        if custom_path.is_file():
            return custom_path
        raise FileNotFoundError(f"Config file not found: {custom_path}")

    for path in DEFAULT_CONFIG_PATHS:
        if path.is_file():
            return path

    raise FileNotFoundError(
        "No configuration file found. Searched: "
        + ", ".join(str(p) for p in DEFAULT_CONFIG_PATHS)
    )


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and validate configuration from a YAML file.

    Performs environment variable interpolation on all string values.
    Returns the parsed configuration dictionary.
    """
    config_path = find_config_file(path)
    raw_text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(raw_text)

    if config is None:
        return {}

    if not isinstance(config, dict):
        raise TypeError(f"Expected dict at top level, got {type(config).__name__}")

    return _deep_interpolate(config)


def get_nested(config: dict[str, Any], key_path: str, default: Any = None) -> Any:
    """Retrieve a nested configuration value using dot notation.

    Example: get_nested(config, "database.host", "localhost")
    """
    keys = key_path.split(".")
    current = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple configuration dictionaries with later values winning.

    Performs a deep merge — nested dicts are merged recursively,
    not replaced wholesale.
    """
    result: dict[str, Any] = {}
    for config in configs:
        for key, value in config.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = merge_configs(result[key], value)
            else:
                result[key] = value
    return result
