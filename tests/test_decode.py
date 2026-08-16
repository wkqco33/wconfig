from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pytest

from wconfig import Config, ConfigDecodeError


@dataclass
class DatabaseSettings:
    host: str
    port: int
    enabled: bool


@dataclass
class AppSettings:
    database: DatabaseSettings


@dataclass
class ServerSettings:
    env: Literal["dev", "stage", "prod"]
    port: int


@dataclass
class CacheSettings:
    hosts: list[str]
    limits: dict[str, int]
    fallback_ports: tuple[int, ...]
    backup_host: str | None


def test_decode_builds_nested_dataclasses():
    config = Config().set_defaults(
        {
            "database": {
                "host": "localhost",
                "port": "5432",
                "enabled": "true",
            }
        }
    )

    settings = config.decode(AppSettings)

    assert settings == AppSettings(
        database=DatabaseSettings(host="localhost", port=5432, enabled=True)
    )


def test_decode_supports_literal():
    config = Config().set_defaults({"env": "stage", "port": 8080})

    settings = config.decode(ServerSettings)

    assert settings.env == "stage"
    assert settings.port == 8080


def test_decode_literal_invalid_value_raises_error():
    config = Config().set_defaults({"env": "invalid_env", "port": 8080})

    with pytest.raises(ConfigDecodeError, match="Expected one of"):
        config.decode(ServerSettings)


def test_decode_supports_containers_and_optional_values():
    config = Config().set_defaults(
        {
            "hosts": ["cache-a.local", "cache-b.local"],
            "limits": {"soft": "10", "hard": "20"},
            "fallback_ports": ["6379", "6380"],
            "backup_host": None,
        }
    )

    settings = config.decode(CacheSettings)

    assert settings == CacheSettings(
        hosts=["cache-a.local", "cache-b.local"],
        limits={"soft": 10, "hard": 20},
        fallback_ports=(6379, 6380),
        backup_host=None,
    )


def test_decode_reports_nested_path_for_container_failures():
    config = Config().set_defaults(
        {
            "limits": {"soft": "not-a-number"},
            "hosts": ["cache.local"],
            "fallback_ports": ["6379"],
            "backup_host": None,
        }
    )

    with pytest.raises(ConfigDecodeError, match="CacheSettings.limits.soft"):
        config.decode(CacheSettings)
