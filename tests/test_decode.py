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


from collections.abc import Mapping as AbcMapping, Sequence as AbcSequence
from enum import Enum, IntEnum
from pathlib import Path


class Environment(str, Enum):
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40


class SettingKey(str, Enum):
    API = "api"


@dataclass
class ServiceSettings:
    env: Environment
    log_level: LogLevel
    data_dir: Path
    endpoints: AbcSequence[str]
    weights: AbcMapping[str, int]


def test_decode_supports_enum_path_and_abstract_types():
    config = Config().set_defaults(
        {
            "env": "stage",
            "log_level": 20,
            "data_dir": "/var/data",
            "endpoints": ["api.local", "backup.local"],
            "weights": {"api.local": "10", "backup.local": "20"},
        }
    )

    settings = config.decode(ServiceSettings)

    assert settings.env == Environment.STAGE
    assert settings.log_level == LogLevel.INFO
    assert settings.data_dir == Path("/var/data")
    assert list(settings.endpoints) == ["api.local", "backup.local"]
    assert settings.weights == {"api.local": 10, "backup.local": 20}


def test_decode_enum_supports_name_lookup_and_case_insensitivity():
    config = Config().set_defaults(
        {
            "env": "PROD",
            "log_level": "WARN",
            "data_dir": "/var/data",
            "endpoints": [],
            "weights": {},
        }
    )

    settings = config.decode(ServiceSettings)

    assert settings.env == Environment.PROD
    assert settings.log_level == LogLevel.WARN


def test_decode_enum_invalid_value_raises_error():
    config = Config().set_defaults(
        {
            "env": "unknown_env",
            "log_level": "INFO",
            "data_dir": "/var/data",
            "endpoints": [],
            "weights": {},
        }
    )

    with pytest.raises(ConfigDecodeError, match="Expected Environment"):
        config.decode(ServiceSettings)


def test_decode_sequence_from_comma_separated_and_json_strings():
    @dataclass
    class ClusterSettings:
        hosts: list[str]
        ports: tuple[int, ...]
        tags: set[str]

    config_csv = Config().set_defaults(
        {
            "hosts": "server1.local, server2.local , server3.local",
            "ports": "8080, 8081, 8082",
            "tags": "web, api",
        }
    )
    settings_csv = config_csv.decode(ClusterSettings)
    assert settings_csv.hosts == ["server1.local", "server2.local", "server3.local"]
    assert settings_csv.ports == (8080, 8081, 8082)
    assert settings_csv.tags == {"web", "api"}

    config_json = Config().set_defaults(
        {
            "hosts": '["s1.local", "s2.local"]',
            "ports": "[9000, 9001]",
            "tags": '["production"]',
        }
    )
    settings_json = config_json.decode(ClusterSettings)
    assert settings_json.hosts == ["s1.local", "s2.local"]
    assert settings_json.ports == (9000, 9001)
    assert settings_json.tags == {"production"}


def test_decode_supports_typed_mapping_keys_and_parenthesized_tuples():
    @dataclass
    class ClusterSettings:
        limits: AbcMapping[SettingKey, int]
        ports: tuple[int, ...]

    config = Config().set_defaults(
        {
            "limits": {"api": "10"},
            "ports": "(9000, 9001)",
        }
    )

    settings = config.decode(ClusterSettings)

    assert settings.limits == {SettingKey.API: 10}
    assert settings.ports == (9000, 9001)
