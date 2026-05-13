"""Configuration loading for Seasonal VCaptcha."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import os

DEFAULT_CONFIG: dict[str, Any] = {
    "service": {
        "name": "seasonal-vcaptcha",
        "instance": "default",
        "user": "seasonal-vcaptcha",
        "group": "seasonal-vcaptcha",
        "runtime_dir": "/run/seasonal-vcaptcha",
        "state_dir": "/var/lib/seasonal-vcaptcha",
        "temp_dir": "/tmp/seasonal-vcaptcha",
    },
    "api": {
        "enabled": True,
        "unix_socket": {
            "enabled": True,
            "path": "/run/seasonal-vcaptcha/seasonal-vcaptcha.sock",
            "mode": "0660",
            "group": "asterisk",
        },
        "tcp": {
            "enabled": False,
            "bind": "127.0.0.1",
            "port": 8765,
        },
        "request_timeout_seconds": 6,
        "max_body_bytes": 10 * 1024 * 1024,
        "max_concurrent_requests": 1,
    },
    "recognizer": {
        "engine": "vosk",
        "vosk": {
            "model_path": "/opt/seasonal-vcaptcha/models/model-small-en-us",
            "sample_rate": 16000,
            "grammar": {
                "enabled": True,
                "phrases": [
                    "zero",
                    "oh",
                    "one",
                    "two",
                    "three",
                    "four",
                    "five",
                    "six",
                    "seven",
                    "eight",
                    "nine",
                    "0",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                ],
            },
        },
    },
    "audio": {
        "sox_path": "/usr/bin/sox",
        "target_sample_rate": 16000,
        "target_channels": 1,
        "target_encoding": "signed-integer",
        "target_bits": 16,
        "max_duration_seconds": 10,
        "cleanup_temp_files": True,
    },
    "cli": {
        "mode": "auto",
        "format": "digits",
        "socket_path": "/run/seasonal-vcaptcha/seasonal-vcaptcha.sock",
        "timeout_seconds": 6,
        "diagnostics_to_stderr": True,
    },
    "recognition": {
        "min_digits": 1,
        "max_digits": 8,
        "allow_empty_result": True,
        "digit_aliases": {
            "zero": "0",
            "oh": "0",
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
        },
    },
    "logging": {
        "level": "info",
        "format": "text",
        "destination": "stderr",
    },
    "metrics": {
        "enabled": False,
        "path": "/metrics",
    },
}

DEFAULT_CONFIG_PATHS = (
    "./config.yaml",
    "/etc/seasonal-vcaptcha/config.yaml",
)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency issue only
        raise RuntimeError("PyYAML is required to load config.yaml") from exc

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config file must contain a mapping: {path}")
    return data


def find_config_path(explicit_path: str | None = None) -> Path | None:
    if explicit_path:
        return Path(explicit_path)

    env_path = os.environ.get("SEASONAL_VCAPTCHA_CONFIG")
    if env_path:
        return Path(env_path)

    for candidate in DEFAULT_CONFIG_PATHS:
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def load_config(explicit_path: str | None = None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    path = find_config_path(explicit_path)
    if path is not None:
        if not path.is_file():
            raise FileNotFoundError(f"config file not found: {path}")
        config = deep_merge(config, _load_yaml(path))

    vosk_model = os.environ.get("VOSK_MODEL")
    if vosk_model:
        config["recognizer"]["vosk"]["model_path"] = vosk_model

    socket_path = os.environ.get("SEASONAL_VCAPTCHA_SOCKET")
    if socket_path:
        config["cli"]["socket_path"] = socket_path
        config["api"]["unix_socket"]["path"] = socket_path

    return config
