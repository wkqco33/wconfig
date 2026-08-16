from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from wconfig import Config, MissingConfigKeyError, ValueSource, load_config


@dataclass
class ApiSettings:
    url: str
    timeout: int = 30


def test_get_require_and_has_use_nested_keys():
    config = Config().set_defaults(
        {"server": {"host": "localhost", "tls": {"enabled": True}}}
    )

    assert config.get("server.host") == "localhost"
    assert config.get("server.port", 8080) == 8080
    assert config.require("server.tls.enabled") is True
    assert config.has("server.tls.enabled") is True
    assert config.has("server.tls.cert") is False

    with pytest.raises(MissingConfigKeyError):
        config.require("server.port")


def test_load_config_convenience_api(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[api]\nurl = 'https://file.local'\n", encoding="utf-8")

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("APP_API__URL=https://dotenv.local\n", encoding="utf-8")

    config = load_config(
        defaults={"api": {"timeout": 5}},
        files=(config_path,),
        dotenv=dotenv_path,
        environ={"APP_API__URL": "https://env.local"},
        env_prefix="APP",
    )

    assert config.as_dict() == {
        "api": {
            "timeout": 5,
            "url": "https://env.local",
        }
    }


def test_normalized_keys_can_be_queried_with_mixed_separators():
    config = Config().set_defaults(
        {
            "Service-Config": {
                "API-Key": "secret",
            }
        }
    )

    assert config.get("service_config.api_key") == "secret"
    assert config.get("service-config.api-key") == "secret"


def test_decode_can_target_nested_key():
    config = Config().set_defaults(
        {"api": {"url": "https://example.com", "timeout": "15"}}
    )

    settings = config.decode(ApiSettings, key="api")

    assert settings == ApiSettings(url="https://example.com", timeout=15)


def test_get_source_reports_winning_source_for_key(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("api:\n  url: https://file.local\n", encoding="utf-8")

    config = (
        Config(env_prefix="APP")
        .set_defaults({"api": {"url": "https://default.local"}}, name="defaults")
        .load_file(config_path, name="app-config")
        .load_env({"APP_API__URL": "https://env.local"})
    )

    source = config.get_source("api.url")

    assert source == ValueSource(
        key="api.url",
        value="https://env.local",
        source=config.sources()[-1],
    )


def test_get_source_raises_for_missing_key():
    config = Config().set_defaults({"api": {"url": "https://example.com"}})

    with pytest.raises(MissingConfigKeyError):
        config.get_source("api.timeout")
